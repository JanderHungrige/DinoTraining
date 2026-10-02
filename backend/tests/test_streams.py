"""Doc 139: the backend starts even without standard streams (a Windows GUI launch)."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from app.core.streams import ensure_streams

BACKEND = Path(__file__).resolve().parents[1]


def test_missing_streams_are_replaced_and_present_ones_kept(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kept = sys.stderr
    monkeypatch.setattr(sys, "stdout", None)
    assert ensure_streams() == ["stdout"]
    assert sys.stdout is not None
    # What uvicorn needs is that asking does not fail. The answer differs: Windows' NUL is a
    # character device and reports a TTY (found by the Windows CI, 2026-10-01).
    assert isinstance(sys.stdout.isatty(), bool)
    print("goes nowhere, fails nothing")
    assert sys.stderr is kept


def test_nothing_to_do_with_real_streams() -> None:
    assert ensure_streams() == []


@pytest.mark.skipif(os.name == "nt", reason="closes fds 1 and 2 in the child, a POSIX call")
def test_python_m_app_serves_with_its_streams_closed(tmp_path: Path) -> None:
    """The real failure: `python -m app` with no stdout or stderr exited with code 1."""
    port = "8798"
    env = {**os.environ, "DINO_API_PORT": port, "DINO_DATA_DIR": str(tmp_path)}

    def close_streams() -> None:
        os.close(1)
        os.close(2)

    child = subprocess.Popen(  # noqa: S603
        [sys.executable, "-m", "app"],
        cwd=BACKEND,
        env=env,
        stdin=subprocess.DEVNULL,
        preexec_fn=close_streams,  # noqa: PLW1509
    )
    try:
        for _ in range(120):
            time.sleep(0.5)
            assert child.poll() is None, f"the backend exited with {child.returncode}"
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/health", timeout=1):  # noqa: S310
                    return
            except OSError:
                continue
        pytest.fail("the backend did not answer /health within 60 s")
    finally:
        child.terminate()
        child.wait(timeout=30)
