"""What the machine could use, versus what this build can (doc 57).

Everything here guards one confusion: **torch cannot answer "is there a GPU here"**. A
CPU-only build reports `cuda.is_available() == False` on a machine with four A100s, so an
app that asks torch tells that user they have no GPU — and they never find out why training
crawls. The driver is asked instead.
"""

from __future__ import annotations

import subprocess

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.accelerator import AcceleratorReport, NvidiaGpu, detect_nvidia, parse_smi, report

SMI_TWO = "NVIDIA GeForce RTX 4090, 24564, 550.54.14\nNVIDIA RTX A6000, 49140, 550.54.14\n"


class TestParsingWhatTheDriverSays:
    def test_it_reads_a_single_gpu(self) -> None:
        gpus = parse_smi("NVIDIA GeForce RTX 4090, 24564, 550.54.14\n")
        assert gpus == (NvidiaGpu("NVIDIA GeForce RTX 4090", 24564, "550.54.14"),)

    def test_it_reads_several(self) -> None:
        assert len(parse_smi(SMI_TWO)) == 2

    def test_a_float_memory_value_is_accepted(self) -> None:
        # `nounits` usually gives integers, but not on every driver version.
        assert parse_smi("A100, 40960.0, 535.1")[0].memory_mb == 40960

    def test_a_broken_line_is_skipped_not_fatal(self) -> None:
        """A machine with one odd GPU among four should still report the three that
        parsed, rather than reporting none."""
        gpus = parse_smi("A100, 40960, 535.1\nnonsense\nA100, 40960, 535.1\n")
        assert len(gpus) == 2

    def test_empty_output_is_no_gpus(self) -> None:
        assert parse_smi("") == ()

    def test_a_nameless_row_is_skipped(self) -> None:
        assert parse_smi(", 1024, 535.1") == ()


class TestAskingTheDriver:
    def test_no_nvidia_smi_means_no_gpu_and_no_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Absence of the driver's own tool is a reliable "no usable NVIDIA GPU", not a
        # failure to report.
        monkeypatch.setattr("app.ml.accelerator.shutil.which", lambda _name: None)
        assert detect_nvidia() == ((), None)

    def test_a_failing_driver_is_an_error_not_an_absence(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """"Your driver is broken" and "you have no GPU" need different actions, so they
        must not produce the same answer."""
        monkeypatch.setattr("app.ml.accelerator.shutil.which", lambda _name: "/usr/bin/nvidia-smi")
        monkeypatch.setattr(
            "app.ml.accelerator.subprocess.run",
            lambda *a, **k: subprocess.CompletedProcess(
                a[0], 9, "", "NVIDIA-SMI has failed because it couldn't communicate\n"
            ),
        )
        gpus, error = detect_nvidia()
        assert gpus == ()
        assert error is not None and "communicate" in error

    def test_a_timeout_does_not_take_the_panel_down(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("app.ml.accelerator.shutil.which", lambda _name: "/usr/bin/nvidia-smi")

        def explode(*_a: object, **_k: object) -> None:
            raise subprocess.TimeoutExpired("nvidia-smi", 5)

        monkeypatch.setattr("app.ml.accelerator.subprocess.run", explode)
        gpus, error = detect_nvidia()
        assert gpus == () and error is not None

    def test_it_reports_what_the_driver_returned(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.ml.accelerator.shutil.which", lambda _name: "/usr/bin/nvidia-smi")
        monkeypatch.setattr(
            "app.ml.accelerator.subprocess.run",
            lambda *a, **k: subprocess.CompletedProcess(a[0], 0, SMI_TWO, ""),
        )
        gpus, error = detect_nvidia()
        assert [g.name for g in gpus] == ["NVIDIA GeForce RTX 4090", "NVIDIA RTX A6000"]
        assert error is None


class TestTheOnlyActionableState:
    """`upgrade_available` decides whether the Admin panel offers anything at all."""

    def _report(self, variant: str, gpus: tuple[NvidiaGpu, ...]) -> AcceleratorReport:
        return AcceleratorReport(device="cpu", torch_variant=variant, nvidia=gpus)  # type: ignore[arg-type]

    def test_hardware_present_and_build_cannot_use_it(self) -> None:
        found = self._report("cpu", (NvidiaGpu("RTX 4090", 24564, "550.1"),))
        assert found.upgrade_available is True
        assert "RTX 4090" in found.summary
        assert "runs on cpu" in found.summary

    def test_nothing_to_offer_when_the_build_already_uses_cuda(self) -> None:
        found = self._report("cuda", (NvidiaGpu("RTX 4090", 24564, "550.1"),))
        assert found.upgrade_available is False
        assert found.can_use_nvidia is True

    def test_nothing_to_offer_without_hardware(self) -> None:
        # The common case, and the one where a standing offer would be noise.
        assert self._report("cpu", ()).upgrade_available is False

    def test_an_apple_build_is_not_told_it_is_missing_acceleration(self) -> None:
        """macOS ships one wheel and it is MPS-capable. Calling that build "cpu" would
        tell a user on Apple silicon they lack acceleration they already have."""
        found = AcceleratorReport(device="mps", torch_variant="mps")
        assert found.upgrade_available is False
        assert "Apple GPU support is built in" in found.summary

    def test_a_broken_driver_is_surfaced_in_the_summary(self) -> None:
        found = AcceleratorReport(
            device="cpu", torch_variant="cpu", driver_error="could not communicate"
        )
        assert "did not respond" in found.summary


class TestTheEndpoint:
    def test_it_answers(self) -> None:
        body = TestClient(app).get("/api/v1/system/accelerator").json()
        assert set(body) >= {
            "device",
            "torch_variant",
            "nvidia",
            "upgrade_available",
            "driver_error",
            "summary",
        }

    def test_it_reports_this_machine_honestly(self) -> None:
        # Whatever this machine is, the three questions must agree with each other.
        body = TestClient(app).get("/api/v1/system/accelerator").json()
        if body["upgrade_available"]:
            assert body["nvidia"] and body["torch_variant"] != "cuda"
        else:
            assert not body["nvidia"] or body["torch_variant"] == "cuda"

    def test_a_driver_probe_failure_does_not_500(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # This is decoration on the Admin panel; it must never take the panel down.
        monkeypatch.setattr("app.ml.accelerator.shutil.which", lambda _name: "/usr/bin/nvidia-smi")

        def explode(*_a: object, **_k: object) -> None:
            raise OSError("no such process")

        monkeypatch.setattr("app.ml.accelerator.subprocess.run", explode)
        assert TestClient(app).get("/api/v1/system/accelerator").status_code == 200


def test_report_uses_the_resolved_device() -> None:
    assert report("cuda").device == "cuda"
