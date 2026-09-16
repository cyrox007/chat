import os

import uvicorn

from settings import config


def build_server_options() -> dict:
    """Return development or production-safe Uvicorn options.

    Production deliberately runs a small built-in Uvicorn worker pool. The
    multiprocess supervisor keeps the listening socket open while workers are
    replaced one by one on SIGHUP, which lets systemd perform rolling reloads
    instead of creating a self-inflicted 502 window on every deploy.
    """
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", config.SERVER_PORT))

    options = {
        "host": host,
        "port": port,
        "proxy_headers": True,
        "forwarded_allow_ips": os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"),
    }

    if config.DEBUG:
        options["reload"] = True
        return options

    config.ensure_security_settings()
    options.update(
        workers=max(2, int(os.getenv("WEB_CONCURRENCY", "2"))),
        timeout_graceful_shutdown=max(
            5,
            int(os.getenv("UVICORN_GRACEFUL_SHUTDOWN_SECONDS", "30")),
        ),
    )
    return options


if __name__ == "__main__":
    uvicorn.run("app:app", **build_server_options())
