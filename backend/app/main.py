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
from app.i18n.middleware import GermanTextMiddleware
from app.mcp.server import mount_mcp
from app.mlops import auto_export as model_auto_export
from app.mlops import tracking_hooks

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

    # German text fields for a German reader (doc 113). Added after CORS, so it wraps it,
    # and outside the HTTP exception handlers, so the error envelope's message is translated
    # too. Only an unhandled 500 (written by Starlette's outermost layer) stays English.
    app.add_middleware(GermanTextMiddleware, prefix=settings.api_prefix)

    register_exception_handlers(app)
    # Doc 123: training runs go to MLflow when it is set up; a no-op otherwise.
    tracking_hooks.install()
    # Doc 145: trained models exported when their training finishes, if switched on.
    model_auto_export.install()
    app.include_router(api_router, prefix=settings.api_prefix)

    # Last, and after the router: the MCP mount composes itself into the app's lifespan,
    # and the tool layer dispatches back into these routes in-process (doc 64).
    mount_mcp(app, settings.api_host, settings.api_port)

    return app


app = create_app()


def _clean_up_cloud_links() -> None:
    """Doc 149: links without a dataset go, with their cache folders. Never fatal."""
    from app.cloud.cache import clean_up_links

    try:
        clean_up_links()
    except Exception:  # noqa: BLE001 - a clean-up must not keep the backend from starting
        logger.exception("Cleaning up cloud links failed")


def main() -> None:
    """Start the sidecar. Binds loopback only — never expose this off-machine."""
    import uvicorn

    settings = get_settings()
    _clean_up_cloud_links()
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
