"""FastAPI application factory and sidecar entrypoint.

Run directly with ``python -m app`` or via ``uvicorn app.main:app``. The Tauri shell
uses the former (see apps/desktop/src-tauri/src/sidecar.rs).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)

# The webview and the Vite dev server are the only legitimate callers. Not "*" —
# this process holds an HF token and local filesystem reach.
_ALLOWED_ORIGINS = (
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "tauri://localhost",
    "http://tauri.localhost",
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Accepts settings so tests can vary configuration."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="DinoTraining backend",
        description="FastAPI + PyTorch sidecar for annotate → train → infer → generate.",
        version=__version__,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_ALLOWED_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Content-Type"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_app()


def main() -> None:
    """Start the sidecar. Binds loopback only — never expose this off-machine."""
    import uvicorn

    settings = get_settings()
    logger.info(
        "Starting DinoTraining backend v%s on %s:%s%s",
        __version__,
        settings.api_host,
        settings.api_port,
        settings.api_prefix,
    )
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
