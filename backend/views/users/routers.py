from fastapi import APIRouter, Depends, FastAPI, status

from components.auth.middleware import auth_middle
from components.auth.permissions import validate_profile_update
from views.users import compat_handlers, handlers


def install(app: FastAPI):
    router = APIRouter(prefix="/users", tags=["legacy-users"])

    # Legacy auth endpoints remain temporarily for old clients. The SPA uses
    # /identity/v2 and new native clients must not depend on these routes.
    router.add_api_route(
        "/registration",
        methods=["POST"],
        status_code=status.HTTP_201_CREATED,
        endpoint=handlers.register,
        deprecated=True,
    )
    router.add_api_route(
        "/check-username",
        methods=["POST"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.check_username,
        deprecated=True,
    )
    router.add_api_route(
        "/check-email",
        methods=["POST"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.check_email,
        deprecated=True,
    )
    router.add_api_route(
        "/check-phone",
        methods=["POST"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.check_phone,
        deprecated=True,
    )
    router.add_api_route(
        "/login",
        methods=["POST"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.login,
        deprecated=True,
    )
    router.add_api_route(
        "/logout",
        methods=["GET"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.logout,
        deprecated=True,
    )

    # Public profile/batch projections moved to /identity/v2 so legacy User
    # fields such as email/phone/date_of_birth cannot leak through these APIs.
    router.add_api_route(
        "/statuses",
        methods=["POST"],
        status_code=status.HTTP_200_OK,
        endpoint=compat_handlers.get_user_statuses,
        dependencies=[Depends(auth_middle)],
    )
    router.add_api_route(
        "/delete",
        methods=["DELETE"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.delete_user,
        dependencies=[Depends(auth_middle)],
        deprecated=True,
    )
    router.add_api_route(
        "/update",
        methods=["PUT"],
        status_code=status.HTTP_200_OK,
        endpoint=handlers.update_profile,
        dependencies=[Depends(auth_middle), Depends(validate_profile_update)],
        deprecated=True,
    )

    app.include_router(router)
