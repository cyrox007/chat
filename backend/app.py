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
    from views.rooms import routers as install_ws_routes
    
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    csrf_middleware(app)
    error_handling_middleware(app)

    csrf_routes.install(app)
    service_routes.install(app)
    user_routes.install(app)
    install_http_routes.install(app)
    install_ws_routes.install(app)

    return app

app = create_app()