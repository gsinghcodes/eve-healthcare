from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from services.schedule_service import ScheduleService

router = APIRouter(
    prefix="/api/v1/schedules",
    tags=["Schedules"],
)

schedule_service = ScheduleService()


@router.get(
    "/center-tests/{center_test_id}/available",
    summary="Get available schedules",
    description="Return fixed appointment slots for a diagnostic test and date.",
)
def get_available_schedules(
    center_test_id: UUID,
    appointment_date: date = Query(..., description="Date in YYYY-MM-DD format"),
):
    data = schedule_service.get_available_schedules(
        center_test_id=center_test_id,
        appointment_date=appointment_date,
    )

    return JSONResponse(
        content=data,
        status_code=data["status"],
    )