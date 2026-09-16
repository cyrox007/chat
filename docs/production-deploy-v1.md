# Production deploy v1

PubChat production deployment must not create an avoidable `502 Bad Gateway` window while the backend or SPA is being updated.

## Why the old restart path was unstable

The legacy deployment flow ran a single Uvicorn process and finished every deploy with `systemctl restart pubchat-backend`. During the stop/start gap nothing was listening on port `9000`, so nginx correctly returned `502` to normal API requests. The SPA could then lose its authenticated bootstrap and realtime sockets at the same time.

The legacy frontend step also let Vite rebuild the live `dist` directory in place. Vite clears its output directory before writing a new build, so static assets could briefly disappear while nginx was still serving the site.

## Production process model

`backend/run_server.py` now has two explicit modes:

- `DEBUG=True`: one reload-enabled development process;
- `DEBUG=False`: built-in Uvicorn multiprocess supervisor with at least two workers (`WEB_CONCURRENCY`, minimum `2`).

Production additionally uses `pubchat-backend.socket`. systemd, not the Python process, owns `127.0.0.1:9000` and passes the listening file descriptor to Uvicorn. The socket therefore remains bound while the Uvicorn supervisor is replaced after a crash/restart, so connections can queue in the kernel backlog instead of immediately failing with connection-refused/`502`.

The service exposes `ExecReload=/bin/kill -HUP $MAINPID`. For routine deployments Uvicorn receives `SIGHUP` and replaces workers one by one. Existing WebSocket clients connected to a replaced worker may reconnect through the normal Realtime v2 flow; unrelated HTTP traffic continues through the remaining worker. The persistent systemd socket is a second safety net around the supervisor itself.

## Health contract

- `GET /health/live` means an ASGI worker is alive and can answer HTTP.
- `GET /health/ready` checks PostgreSQL and, outside DEBUG, Redis. It returns `503` until the worker is dependency-ready.

The deploy script uses readiness as a gate before declaring success.

## One-time migration from the legacy service

After pulling the release containing this document, install the tracked service/socket units once:

```bash
cd /home/projects/pubchat
sudo bash ops/install-production-service.sh
```

The legacy process already owns port `9000`, so the installer performs one intentional stop while moving ownership of that port to `pubchat-backend.socket`, then starts the multiprocess service and waits for `/health/ready`. This is the final expected deploy-related listener interruption; subsequent routine deployments do not stop the listener.

The installer prints socket/service/log diagnostics on failure.

## Normal deploy

```bash
cd /home/projects/pubchat
bash ops/deploy.sh
```

The script performs, in order:

1. fast-forward source update;
2. Python dependency sync;
3. production security/Redis configuration preflight;
4. Alembic migration to head;
5. frontend build into `frontend/dist.next` while the current `dist` stays live;
6. publish new hashed/static files first and `index.html` last, retaining old hashed assets for already-open tabs;
7. verification that the systemd-owned socket is active and the service supports HUP reload;
8. rolling backend reload;
9. `/health/ready` gate;
10. nginx config validation and reload.

A failed build never clears the live SPA directory. A missing persistent socket causes deployment to stop before backend reload. A failed readiness gate does not report a successful deploy and prints service diagnostics.

## Client recovery

The SPA authenticated bootstrap retries transient network/`502`/`503`/`504` failures with bounded exponential backoff. This is a secondary safety net; it is not a substitute for the server deployment contract.

## Migration discipline

Rolling application workers can overlap briefly across code versions. Schema migrations used with this deploy path must therefore remain expand/contract compatible during the overlap window. Destructive contract steps belong in a later deployment after all old workers are gone.

## Operational invariant

A routine PubChat deploy must not deliberately take the HTTP listener down. The listener belongs to systemd, application workers are replaced with rolling reload, and a full supervisor restart is protected by socket activation. Direct manual teardown of both `pubchat-backend.service` and `pubchat-backend.socket` is reserved for incident recovery or deliberate infrastructure maintenance.
