from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from schemas.requests.diagnostic_test import CreateDiagnosticTestRequest
from services.diagnostic_test_service import DiagnosticTestService
from routers.middlewares.auth import require_roles

router = APIRouter(
    prefix="/api/v1/tests",
    tags=["Diagnostic Tests"],
)

test_service = DiagnosticTestService()


@router.get("")
def get_tests():
    data = test_service.get_global_tests()

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )


@router.get("/{test_id}")
def get_test(test_id: UUID):
    data = test_service.get_test(test_id)

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )


@router.post("")
def create_test(
    request: CreateDiagnosticTestRequest,
    _: object = Depends(require_roles("admin")),
):
    data = test_service.create_test(
        name=request.name,
        description=request.description,
        image_url=request.image_url,
    )

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )
