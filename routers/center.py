# routers/diagnostic_centers.py

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from database.models.user_model import User
from routers.middlewares.auth import require_roles
from schemas.requests.center import (
    CreateCenterRequest,
    SearchCentersRequest,
    UpdateCenterRequest,
)
from schemas.requests.center_test import (
    CreateCenterTestRequest,
    UpdateCenterTestRequest,
)
from services.center_service import CenterService
from services.center_test_service import CenterTestService

router = APIRouter(
    prefix="/api/v1/centres",
    tags=["Diagnostic Centres"],
)

center_service = CenterService()
center_test_service = CenterTestService()


@router.post(
    "/search",
    summary="Search diagnostic centres",
    description="Find centres by radius and optional test, with selectable sorting.",
)
def search_centers(request: SearchCentersRequest):
    data = center_service.get_centers_in_radius(request=request)

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )


@router.get("/{center_id}", summary="Get diagnostic centre by ID")
def get_center(center_id: UUID):
    data = center_service.get_center_by_id(center_id=center_id)

    return JSONResponse(content=data, status_code=data["status"])


@router.post(
    "",
    summary="Create diagnostic centre",
    description="Create a diagnostic centre using its name, address and geographic coordinates.",
    status_code=201,
)
def create_center(
    request: CreateCenterRequest,
    user: User = Depends(require_roles("center_manager", "admin")),
):
    data = center_service.create_center(
        center=request,
        user_id=user.id,
        is_admin=user.role == "admin",
    )

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )


@router.put("/{center_id}", summary="Update diagnostic centre")
def update_center(
    center_id: UUID,
    request: UpdateCenterRequest,
    user: User = Depends(require_roles("center_manager", "admin")),
):
    data = center_service.update_center(
        center_id=center_id,
        request=request,
        user_id=user.id,
        is_admin=user.role == "admin",
    )
    return JSONResponse(content=data, status_code=data["status"])


@router.post(
    "/{center_id}/tests",
    summary="Add a test to a diagnostic centre",
    status_code=201,
)
def create_center_test(
    center_id: UUID,
    request: CreateCenterTestRequest,
    user: User = Depends(require_roles("center_manager", "admin")),
):
    data = center_test_service.create_center_test(
        center_id=center_id,
        test_id=request.test_id,
        price=request.price,
        title_override=request.title_override,
        description_override=request.description_override,
        image_url_override=request.image_url_override,
        user_id=user.id,
        is_admin=user.role == "admin",
    )
    return JSONResponse(content=data, status_code=data["status"])


@router.put("/tests/{center_test_id}", summary="Update a centre test offering")
def update_center_test(
    center_test_id: UUID,
    request: UpdateCenterTestRequest,
    user: User = Depends(require_roles("center_manager", "admin")),
):
    data = center_test_service.update_center_test(
        center_test_id=center_test_id,
        price=request.price,
        title_override=request.title_override,
        description_override=request.description_override,
        image_url_override=request.image_url_override,
        is_active=request.is_active,
        user_id=user.id,
        is_admin=user.role == "admin",
    )
    return JSONResponse(content=data, status_code=data["status"])
