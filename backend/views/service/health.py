from fastapi import status
from fastapi.responses import JSONResponse

from components.realtime import realtime_service
from database import Database
from settings import config
from utils.version import PROJECT_VERSION


async def liveness():
    """Process-level probe: the ASGI worker is alive and serving requests."""
    return {"status": "ok", "version": PROJECT_VERSION}


async def readiness():
    """Dependency-aware probe used by deployment and reverse-proxy checks.

    A worker is ready only when PostgreSQL responds and, in production,
    distributed realtime Redis is connected and responds to PING. We expose
    only boolean component state, never connection details or credentials.
    """
    database_ok = await Database.health_check()
    redis_ok = True

    if not config.DEBUG:
        client = realtime_service.redis
        redis_ok = client is not None
        if client is not None:
            try:
                redis_ok = bool(await client.ping())
            except Exception:
                redis_ok = False

    ready = database_ok and redis_ok
    payload = {
        "status": "ok" if ready else "not_ready",
        "version": PROJECT_VERSION,
        "checks": {
            "database": database_ok,
            "redis": redis_ok,
        },
    }
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=payload,
    )
