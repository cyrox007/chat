from fastapi import Depends, FastAPI, APIRouter, status

from components.auth.permissions import require_admin
from views.admin import handlers


def install(app: FastAPI):
    router = APIRouter(
        prefix="/admin",
        dependencies=[Depends(require_admin)],
    )

    router.add_api_route(
        "/dashboard/stats",
        methods=["GET"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.dashboard_stats,
    )
    router.add_api_route(
        "/penalties/assign",
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        endpoint=handlers.assign_penalty,
    )
    router.add_api_route(
        "/penalties/{penalty_id}",
        methods=["DELETE"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.delete_penalty,
    )
    router.add_api_route(
        "/users",
        methods=["GET"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.get_users,
    )
    router.add_api_route(
        "/users/{target_uid}/rooms",
        methods=["GET"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.get_user_rooms,
    )
    router.add_api_route(
        "/users/{target_uid}/penalties",
        methods=["GET"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.get_user_penalties,
    )
    router.add_api_route(
        "/users/{target_uid}",
        methods=["PUT"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.update_user,
    )

    app.include_router(router)
