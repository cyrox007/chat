import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from fastapi.middleware.cors import CORSMiddleware
from middlewares import csrf_middleware, error_handling_middleware

from settings import config

def create_app() -> FastAPI:
    from views.csrf import routers as csrf_routes
    from views.service import routers as service_routes
    from views.users import routers as user_routes
    from views.rooms import routers as http_routes_chat
    from views.rooms import ws_routers as ws_routes_chat
    from views.messenger import routers as http_routers_messenger
    from views.messenger import ws_routers as ws_routers_messenger

    from views.admin import routers as admin_routers
    
    app = FastAPI()

    # Добавляем CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.FRONTEND_URL,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"]
    )

    # Подключаем статические файлы
    app.mount("/static", StaticFiles(directory="static"), name="static")
    # Проверяем существование директории
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    csrf_middleware(app)
    error_handling_middleware(app)

    csrf_routes.install(app)
    service_routes.install(app)
    user_routes.install(app)
    http_routes_chat.install(app)
    ws_routes_chat.install(app)
    http_routers_messenger.install(app)
    ws_routers_messenger.install(app)

    admin_routers.install(app)

    return app

app = create_app()