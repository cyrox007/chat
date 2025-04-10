from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from fastapi.middleware.cors import CORSMiddleware
from utils.csrf import validate_csrf_token
from middlewares import csrf_middleware, error_handling_middleware

def create_app() -> FastAPI:
    from views.csrf import routers as csrf_routes
    from views.service import routers as service_routes
    from views.users import routers as user_routes
    from views.rooms import routers as install_http_routes
    from views.rooms import ws_routers as install_ws_routes
    from views.messenger import ws_routers as install_ws_routes_messener
    
    app = FastAPI()

    # Добавляем CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Подключаем статические файлы
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    csrf_middleware(app)
    error_handling_middleware(app)

    csrf_routes.install(app)
    service_routes.install(app)
    user_routes.install(app)
    install_http_routes.install(app)
    install_ws_routes.install(app)
    install_ws_routes_messener.install(app)

    return app

app = create_app()