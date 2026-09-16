# Production deploy v1

PubChat production deployment must not create an avoidable `502 Bad Gateway` window while the backend is being updated.

## Why the old restart path was unstable

The legacy deployment flow ran a single Uvicorn process and finished every deploy with `systemctl restart pubchat-backend`. During the stop/start gap nothing was listening on port `9000`, so nginx correctly returned `502` to normal API requests. The SPA could then lose its authenticated bootstrap and realtime sockets at the same time.

## Production process model

`backend/run_server.py` now has two explicit modes:

- `DEBUG=True`: one reload-enabled development process;
- `DEBUG=False`: built-in Uvicorn multiprocess supervisor with at least two workers (`WEB_CONCURRENCY`, minimum `2`).

The production systemd unit exposes `ExecReload=/bin/kill -HUP $MAINPID`. Uvicorn handles `SIGHUP` by replacing workers gracefully one by one while the supervisor keeps the listening socket open. Existing WebSocket clients connected to a replaced worker may reconnect through the normal Realtime v2 flow; unrelated HTTP traffic continues through the remaining worker.

## Health contract

- `GET /health/live` means an ASGI worker is alive and can answer HTTP.
- `GET /health/ready` checks PostgreSQL and, outside DEBUG, Redis. It returns `503` until the worker is dependency-ready.

The deploy script uses readiness as a gate before declaring success.

## One-time migration from the legacy service

After pulling the release containing this document, install the tracked service unit once:

```bash
cd /home/projects/pubchat
sudo bash ops/install-production-service.sh
```

This command performs one intentional full restart to move the existing single-process installation under the multiprocess supervisor. It then waits for `/health/ready` and prints service/log diagnostics on failure.

After this migration, normal code deploys must use rolling reload rather than `systemctl restart`.

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
5. frontend dependency sync and build;
6. verification that the installed systemd unit supports HUP reload;
7. rolling backend reload;
8. `/health/ready` gate;
9. nginx config validation and reload.

A failed readiness gate does not report a successful deploy and prints service diagnostics.

## Client recovery

The SPA authenticated bootstrap now retries transient network/`502`/`503`/`504` failures with bounded exponential backoff. This is a secondary safety net; it is not a substitute for the rolling server deployment contract.

## Migration discipline

Rolling application workers can overlap briefly across code versions. Schema migrations used with this deploy path must therefore remain expand/contract compatible during the overlap window. Destructive contract steps belong in a later deployment after all old workers are gone.

## Operational invariant

A routine PubChat deploy must not deliberately take the only HTTP listener down. Full `systemctl restart pubchat-backend` is reserved for one-time service-model changes or incident recovery, not normal releases.
