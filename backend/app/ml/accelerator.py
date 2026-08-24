"""What this machine *could* use, versus what this build *can* use (doc 57).

Wave 8 ships a **CPU-only sidecar** so the installer stays around 350–650 MB rather than
the 2.5 GB a CUDA torch wheel costs on Windows (doc 56). A user with an NVIDIA GPU then
gets a build that cannot see it — which is fine only if the app *says so* and offers the
fix. Silence there is the worst outcome: training crawls and nothing explains why.

**Three questions this module keeps apart, because conflating them is the whole problem:**

1. *Is there NVIDIA hardware with a working driver?* — `nvidia-smi`, not torch. A CPU-only
   torch reports `cuda.is_available() == False` on a machine with four A100s.
2. *Can this build use it?* — `torch.version.cuda`. A property of the wheel that was
   frozen into the sidecar, decided at build time and not changeable at runtime.
3. *What is being used right now?* — `resolve_device`, which already existed.

Only the combination "hardware yes, build no" is actionable, and it is the one thing the
Admin panel needs to surface.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

#: Which torch build was frozen into this sidecar. Not user-configurable — it is decided
#: when the release is built, and reported so the app never guesses.
TorchVariant = Literal["cpu", "cuda", "rocm", "mps", "unknown"]

#: `nvidia-smi` is the driver's own tool. Present and exiting 0 means a usable driver;
#: present and failing means the driver is installed but broken, which is a different
#: problem and must not read as "no GPU".
_SMI_TIMEOUT_SECONDS = 5
_SMI_QUERY = "--query-gpu=name,memory.total,driver_version"


@dataclass(frozen=True, slots=True)
class NvidiaGpu:
    """One GPU as `nvidia-smi` reports it."""

    name: str
    memory_mb: int
    driver_version: str


@dataclass(frozen=True, slots=True)
class AcceleratorReport:
    """What the Admin panel needs to decide whether to offer anything."""

    #: The device this process is actually using. Never `auto`.
    device: str
    #: The torch build frozen into this sidecar.
    torch_variant: TorchVariant
    #: NVIDIA hardware found by the driver, regardless of what torch can do with it.
    nvidia: tuple[NvidiaGpu, ...] = ()
    #: Set when the driver is present but did not answer. Reported rather than swallowed:
    #: "your driver is broken" and "you have no GPU" need different actions.
    driver_error: str | None = None

    @property
    def can_use_nvidia(self) -> bool:
        """True when this build could actually run on the hardware that is present."""
        return self.torch_variant == "cuda" and bool(self.nvidia)

    @property
    def upgrade_available(self) -> bool:
        """**The only actionable state.** NVIDIA hardware is here and this build cannot
        use it, so downloading GPU support would change something."""
        return bool(self.nvidia) and self.torch_variant != "cuda"

    @property
    def summary(self) -> str:
        """One line for the panel, so the wording lives in one place."""
        if self.upgrade_available:
            names = ", ".join(gpu.name for gpu in self.nvidia)
            return f"{names} found, but this build runs on {self.device}."
        if self.can_use_nvidia:
            names = ", ".join(gpu.name for gpu in self.nvidia)
            return f"Running on {self.device} — {names}."
        if self.torch_variant == "mps":
            return f"Running on {self.device}. Apple GPU support is built in."
        if self.driver_error:
            return f"An NVIDIA driver is installed but did not respond: {self.driver_error}"
        return f"Running on {self.device}. No NVIDIA GPU found."


def torch_variant() -> TorchVariant:
    """Which torch build this is, from torch itself.

    Imported inside the function: this module is read by the API layer at startup and torch
    takes seconds to import. Everything above `nvidia` detection works without it.
    """
    try:
        import torch
    except ImportError:  # pragma: no cover - torch is a hard dependency of the sidecar
        return "unknown"

    if getattr(torch.version, "cuda", None):
        return "cuda"
    if getattr(torch.version, "hip", None):
        return "rocm"
    # `is_built`, not `is_available`: this reports what the *wheel* can do, and the macOS
    # wheel is MPS-capable whether or not this particular Mac has a usable GPU. Calling it
    # "cpu" would tell a user on Apple silicon that they are missing acceleration they
    # already have.
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_built():
        return "mps"
    return "cpu"


def parse_smi(output: str) -> tuple[NvidiaGpu, ...]:
    """Parse `nvidia-smi --query-gpu=... --format=csv,noheader,nounits`.

    One GPU per line, three comma-separated fields. A line that does not parse is skipped
    rather than failing the whole probe — a machine with one odd GPU among four should
    still report the three that made sense.
    """
    found: list[NvidiaGpu] = []
    for line in output.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 3 or not parts[0]:
            continue
        try:
            memory = int(float(parts[1]))
        except ValueError:
            continue
        found.append(NvidiaGpu(name=parts[0], memory_mb=memory, driver_version=parts[2]))
    return tuple(found)


def detect_nvidia() -> tuple[tuple[NvidiaGpu, ...], str | None]:
    """Ask the driver, not torch. Returns `(gpus, error)`.

    `nvidia-smi` ships with the driver, so its absence is a reliable "no usable NVIDIA
    GPU" — and it answers on a CPU-only torch build, which is the entire point.

    Never raises. A probe that throws on an unusual machine would take the Admin panel
    down with it, and this is decoration on that panel rather than something it needs.
    """
    binary = shutil.which("nvidia-smi")
    if binary is None:
        return (), None

    try:
        result = subprocess.run(  # noqa: S603 - fixed binary from PATH, no shell, no input
            [binary, _SMI_QUERY, "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=_SMI_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("nvidia-smi failed: %s", exc)
        return (), str(exc)

    if result.returncode != 0:
        # Driver present, driver unhappy. A different problem from having no GPU, and the
        # user needs to know which one they have.
        message = (result.stderr or result.stdout).strip().splitlines()
        return (), (message[0] if message else f"exit code {result.returncode}")

    return parse_smi(result.stdout), None


def report(device: str) -> AcceleratorReport:
    """Everything the Admin panel needs, in one call."""
    gpus, error = detect_nvidia()
    return AcceleratorReport(
        device=device,
        torch_variant=torch_variant(),
        nvidia=gpus,
        driver_error=error,
    )


__all__ = [
    "AcceleratorReport",
    "NvidiaGpu",
    "TorchVariant",
    "detect_nvidia",
    "parse_smi",
    "report",
    "torch_variant",
]
