"""Minimal unauthenticated liveness and readiness HTTP surface."""

from __future__ import annotations

from collections.abc import Callable
import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)
ReadinessCheck = Callable[[], None]


def register_health_routes(
    app: FastAPI,
    *,
    readiness_check: ReadinessCheck | None,
) -> None:
    @app.get("/health", include_in_schema=False)
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", include_in_schema=False)
    def readiness() -> JSONResponse:
        try:
            if readiness_check is None:
                raise RuntimeError("Readiness dependency is unavailable.")
            readiness_check()
        except Exception as exc:
            logger.warning(
                "Application is not ready",
                extra={"event": "readiness_failed", "error_class": type(exc).__name__},
            )
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        return JSONResponse(status_code=200, content={"status": "ready"})
