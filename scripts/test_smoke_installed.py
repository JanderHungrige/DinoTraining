"""Tests for scripts/smoke_installed.py (doc 131), with a fake app instead of an installer."""

from __future__ import annotations

import socket
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smoke_installed

#: A stand-in for the installed app: with DINO_SETUP_AUTO it "installs" an environment
#: whose Python is the one running the tests, then serves /health until stopped.
FAKE_APP = textwrap.dedent(
    r"""
    import http.server, os, sys
    from pathlib import Path
    runtime = Path(os.environ["DINO_RUNTIME_DIR"])
    if os.environ.get("DINO_SETUP_AUTO"):
        env = runtime / "envs" / "1"
        python = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python.parent.mkdir(parents=True, exist_ok=True)
        # A wrapper, not a symlink: a symlinked venv Python loses its venv (and torch).
        python.write_text('#!/bin/sh\nexec "' + sys.executable + '" "$@"\n')
        python.chmod(0o755)
        (runtime / "current").write_text("1")
    elif os.environ.get("FAKE_REINSTALL_ON_SECOND"):
        (runtime / "envs" / "2" / "bin").mkdir(parents=True)
        (runtime / "current").write_text("2")
    class Health(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"{}")
        def log_message(self, *args):
            pass
    http.server.HTTPServer(("127.0.0.1", int(os.environ["DINO_API_PORT"])), Health).serve_forever()
    """
)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@pytest.fixture
def fake_app(tmp_path: Path) -> Path:
    app = tmp_path / "fake_app.py"
    app.write_text(FAKE_APP, encoding="utf-8")
    return app


POSIX_ONLY = pytest.mark.skipif(
    sys.platform == "win32", reason="the fake Python is a sh wrapper"
)


@POSIX_ONLY
def test_a_working_install_passes_and_reports(fake_app: Path, tmp_path: Path) -> None:
    pytest.importorskip("torch")
    pytest.importorskip("onnxruntime")
    lines = smoke_installed.run(
        fake_app, [sys.executable], tmp_path / "work", free_port()
    )
    assert lines[0].startswith("- first start")
    assert any("torch" in line for line in lines)


@POSIX_ONLY
def test_a_second_start_that_reinstalls_fails(
    fake_app: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("torch")
    pytest.importorskip("onnxruntime")
    monkeypatch.setenv("FAKE_REINSTALL_ON_SECOND", "1")
    with pytest.raises(smoke_installed.SmokeFailure, match="reinstalled"):
        smoke_installed.run(fake_app, [sys.executable], tmp_path / "work", free_port())


def test_an_app_that_exits_fails_with_the_reason(tmp_path: Path) -> None:
    broken = tmp_path / "broken.py"
    broken.write_text("raise SystemExit(3)\n", encoding="utf-8")
    with pytest.raises(smoke_installed.SmokeFailure, match="exited"):
        smoke_installed.run(broken, [sys.executable], tmp_path / "work", free_port())


def test_no_current_environment_is_a_failure(tmp_path: Path) -> None:
    with pytest.raises(smoke_installed.SmokeFailure, match="installed nothing"):
        smoke_installed.env_python(tmp_path)


def test_hard_links_count_once(tmp_path: Path) -> None:
    (tmp_path / "a").write_bytes(b"x" * 3 * 1024 * 1024)
    (tmp_path / "b").hardlink_to(tmp_path / "a")
    assert smoke_installed.folder_mb(tmp_path) == 3
