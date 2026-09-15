from fastapi import FastAPI

from views.support import gift_routers, settings_routers


def install(app: FastAPI) -> None:
    settings_routers.install(app)
    gift_routers.install(app)
