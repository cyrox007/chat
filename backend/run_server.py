import os

import uvicorn

from settings import config


def build_server_options() -> dict:
    """Return development or production-safe Uvicorn options.

    Development binds its own TCP socket and uses WatchFiles reload. Production
    prefers a socket inherited from systemd, so the listener remains available
    even while the Uvicorn supervisor itself is restarted. The production
    supervisor still keeps at least two workers for rolling SIGHUP reloads.
    """
    options = {
        "proxy_headers": True,
        "forwarded_allow_ips": os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"),
    }

    if config.DEBUG:
        options.update(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", config.SERVER_PORT)),
            reload=True,
        )
        return options

    config.ensure_security_settings()

    inherited_fd = os.getenv("UVICORN_FD")
    if inherited_fd:
        options["fd"] = int(inherited_fd)
    else:
        # Direct binding remains supported for local/CI production-semantic
        # rehearsals that are not launched by systemd socket activation.
        options.update(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", config.SERVER_PORT)),
        )

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
