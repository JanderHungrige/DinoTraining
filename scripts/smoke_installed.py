"""Smoke-test an installed DinoTraining (doc 131).

    python scripts/smoke_installed.py <executable> [--wrap "xvfb-run -a"]

First start unattended (installs Python and PyTorch), health, a torch check in the
installed environment, then a second start that must need no setup. Standard library
only: it runs on the release runners right after the installer was built.
"""

from __future__ import annotations

import argparse
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HEALTH = "http://127.0.0.1:{port}/api/v1/health"
FIRST_START_S = 25 * 60
SECOND_START_S = 3 * 60
TORCH_CHECK = (
    "import torch, torchvision, onnxruntime;"
    "t = torch.ones(2, 3) @ torch.ones(3, 2);"
    "assert t.sum().item() == 12.0;"
    "print('torch', torch.__version__, 'torchvision', torchvision.__version__,"
    " 'onnxruntime', onnxruntime.__version__)"
)


class SmokeFailure(Exception):
    pass


def env_python(runtime: Path) -> Path:
    """The Python of the environment `runtime/current` names (doc 129)."""
    pointer = runtime / "current"
    if not pointer.is_file():
        raise SmokeFailure(f"no {pointer}: the first start installed nothing")
    env = runtime / "envs" / pointer.read_text(encoding="utf-8").strip()
    python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        raise SmokeFailure(f"the current environment has no Python at {python}")
    return python


def folder_mb(path: Path) -> int:
    """Size on disk in MB, each hard-linked file counted once."""
    seen: set[tuple[int, int]] = set()
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                stat = (Path(root) / name).lstat()
            except OSError:
                continue
            key = (stat.st_dev, stat.st_ino)
            if key not in seen:
                seen.add(key)
                total += stat.st_size
    return total // (1024 * 1024)


def healthy(port: int) -> bool:
    try:
        with urllib.request.urlopen(HEALTH.format(port=port), timeout=5) as response:
            return bool(response.status == 200)
    except OSError:
        return False


def stop(process: subprocess.Popen[bytes]) -> None:
    """The app and its backend. The shell passes SIGTERM on; Windows needs the tree."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], check=False)
    else:
        # Its own process group (see `start`): under xvfb-run, a signal to the wrapper
        # alone would leave the app, and its backend on the port, running.
        os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            process.kill()
        else:
            os.killpg(process.pid, signal.SIGKILL)


def start(
    command: list[str], env: dict[str, str], log: Path, port: int, limit: float
) -> float:
    """Start, wait for /health, stop; the seconds it took."""
    began = time.monotonic()
    with log.open("ab") as out:
        process = subprocess.Popen(
            command,
            env=env,
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=os.name != "nt",
        )
    try:
        while time.monotonic() - began < limit:
            if healthy(port):
                return time.monotonic() - began
            if process.poll() is not None:
                raise SmokeFailure(
                    f"the app exited ({process.returncode}) before /health answered"
                )
            time.sleep(3)
        raise SmokeFailure(f"/health did not answer within {limit:.0f} s")
    finally:
        stop(process)
        time.sleep(3)  # the port, for the next start


def run(executable: Path, wrap: list[str], work: Path, port: int) -> list[str]:
    work.mkdir(parents=True, exist_ok=True)
    runtime, log = work / "runtime", work / "app.log"
    env = {
        **os.environ,
        "DINO_RUNTIME_DIR": str(runtime),
        "DINO_DATA_DIR": str(work / "data"),
    }
    env["DINO_API_PORT"] = str(port)
    command = [*wrap, str(executable)]

    first = start(command, {**env, "DINO_SETUP_AUTO": "cpu"}, log, port, FIRST_START_S)
    python = env_python(runtime)
    checked = subprocess.run(
        [str(python), "-c", TORCH_CHECK], capture_output=True, text=True, check=False
    )
    if checked.returncode != 0:
        raise SmokeFailure(f"the installed PyTorch does not run:\n{checked.stderr}")
    current = (runtime / "current").read_text(encoding="utf-8")

    second = start(command, env, log, port, SECOND_START_S)
    if (runtime / "current").read_text(encoding="utf-8") != current:
        raise SmokeFailure("the second start reinstalled the environment")
    env_dir = python.parent.parent
    return [
        f"- first start (install + backend): {first:.0f} s",
        f"- second start: {second:.0f} s",
        f"- {checked.stdout.strip()}",
        (
            f"- installed environment: {folder_mb(env_dir)} MB,"
            f" uv cache: {folder_mb(runtime / 'cache')} MB,"
            f" Python: {folder_mb(runtime / 'python')} MB"
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--wrap", default="", help='e.g. "xvfb-run -a" on Linux')
    parser.add_argument("--port", type=int, default=8756)
    parser.add_argument("--work", type=Path, default=None)
    args = parser.parse_args()
    work = args.work or Path(tempfile.mkdtemp(prefix="dino-smoke-"))
    work.mkdir(parents=True, exist_ok=True)
    try:
        lines = run(args.executable, shlex.split(args.wrap), work, args.port)
    except SmokeFailure as failure:
        print(f"SMOKE TEST FAILED: {failure}", file=sys.stderr)
        log = work / "app.log"
        if log.is_file():
            print("--- app log (tail) ---", file=sys.stderr)
            print(
                "\n".join(log.read_text(errors="replace").splitlines()[-80:]),
                file=sys.stderr,
            )
        return 1
    print("\n".join(lines))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as out:
            out.write("#### Smoke test\n" + "\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
