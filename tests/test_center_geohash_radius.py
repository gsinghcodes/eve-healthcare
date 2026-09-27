import geohash2
import json
import pytest
from datetime import time
from unittest.mock import MagicMock, patch
from uuid import UUID
from sqlalchemy.dialects import postgresql

from database.repositories.center_repo import CenterRepository
from schemas.requests.center import SearchCentersRequest
from services.center_service import CenterService
from utils.geohash import (
    STORED_GEOHASH_PRECISION,
    distance_km,
    geohashes_for_radius,
)
from utils.model_utils import serialize_model


def test_center_opening_hours_are_json_serializable():
    from types import SimpleNamespace

    center = SimpleNamespace(
        opening_time=time(9, 0),
        closing_time=time(17, 30),
    )

    serialized_center = serialize_model(center)

    assert json.loads(json.dumps(serialized_center)) == {
        "opening_time": "09:00:00",
        "closing_time": "17:30:00",
    }


@pytest.mark.parametrize(
    ("latitude", "longitude", "radius_km", "target_latitude", "target_longitude"),
    [
        (40.7, -74.0, 5, 40.72, -74.01),
        (0, 179.999, 1, 0, -179.999),
        (89.999, 0, 1, 89.999, 90),
        (-89.999, -170, 1, -89.999, 170),
        (20, 30, 500, 22, 32),
    ],
)
def test_geohash_cover_includes_in_radius_coordinates(
    latitude,
    longitude,
    radius_km,
    target_latitude,
    target_longitude,
):
    prefixes = geohashes_for_radius(latitude, longitude, radius_km)
    target_hash = geohash2.encode(
        target_latitude,
        target_longitude,
        precision=STORED_GEOHASH_PRECISION,
    )

    assert (
        distance_km(
            latitude,
            longitude,
            target_latitude,
            target_longitude,
        )
        <= radius_km
    )
    assert any(target_hash.startswith(prefix) for prefix in prefixes)


def test_service_converts_string_test_id_to_uuid():
    test_id = "550e8400-e29b-41d4-a716-446655440000"
    request = SearchCentersRequest(
        latitude=0,
        longitude=0,
        radius=1,
        test_id=test_id,
    )
    session = MagicMock()
    session_context = MagicMock()
    session_context.__enter__.return_value = session
    service = CenterService()
    repository = MagicMock()
    repository.get_centers_by_geohash_prefixes.return_value = ([], 0)
    service.center_repository = repository

    with patch("services.center_service.SessionLocal", return_value=session_context):
        response = service.get_centers_in_radius(request)

    assert response["status"] == 200
    assert repository.get_centers_by_geohash_prefixes.call_args.kwargs[
        "test_id"
    ] == UUID(test_id)


def test_get_center_by_id_includes_active_offerings_and_test_details():
    from types import SimpleNamespace

    center_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    center = SimpleNamespace(id=center_id, name="North Clinic", address="Main St")
    diagnostic_test = SimpleNamespace(id=UUID(int=2), name="Blood panel")
    offering = SimpleNamespace(
        id=UUID(int=3),
        price=25,
        is_active=True,
        test=diagnostic_test,
    )
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = CenterService()
    service.center_repository = MagicMock()
    service.center_repository.get_center_by_id.return_value = center
    service.center_test_repository = MagicMock()
    service.center_test_repository.get_by_center.return_value = [offering]

    with patch("services.center_service.SessionLocal", return_value=session_context):
        response = service.get_center_by_id(center_id)

    assert response["status"] == 200
    assert response["data"]["name"] == "North Clinic"
    assert response["data"]["tests"] == [
        {
            "id": str(offering.id),
            "price": 25,
            "is_active": True,
            "test": {"id": str(diagnostic_test.id), "name": "Blood panel"},
        }
    ]


def test_get_center_by_id_returns_not_found():
    center_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = CenterService()
    service.center_repository = MagicMock()
    service.center_repository.get_center_by_id.return_value = None

    with patch("services.center_service.SessionLocal", return_value=session_context):
        response = service.get_center_by_id(center_id)

    assert response["status"] == 404
    assert response["data"] is None


def test_service_paginates_sorted_radius_results():
    from types import SimpleNamespace

    request = SearchCentersRequest(
        latitude=0,
        longitude=0,
        radius=10,
        page=2,
        page_size=1,
    )
    centers = [
        SimpleNamespace(name="Near", latitude=0, longitude=0.01),
        SimpleNamespace(name="Middle", latitude=0, longitude=0.02),
        SimpleNamespace(name="Far", latitude=0, longitude=0.03),
    ]
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = CenterService()
    repository = MagicMock()
    repository.get_centers_by_geohash_prefixes.return_value = (centers[1:2], 3)
    service.center_repository = repository

    with patch("services.center_service.SessionLocal", return_value=session_context):
        response = service.get_centers_in_radius(request)

    assert response["data"] == {
        "items": [{"name": "Middle", "latitude": 0, "longitude": 0.02}],
        "view": "list",
        "total": 3,
        "pagination": {"page": 2, "page_size": 1, "total_pages": 3},
    }
    assert repository.get_centers_by_geohash_prefixes.call_args.kwargs["page"] == 2
    assert repository.get_centers_by_geohash_prefixes.call_args.kwargs["page_size"] == 1


def test_service_returns_all_radius_results_for_map_view():
    from types import SimpleNamespace

    request = SearchCentersRequest(
        latitude=0,
        longitude=0,
        radius=10,
        view="map",
        page_size=1,
    )
    centers = [
        SimpleNamespace(name="Near", latitude=0, longitude=0.01),
        SimpleNamespace(name="Middle", latitude=0, longitude=0.02),
        SimpleNamespace(name="Far", latitude=0, longitude=0.03),
    ]
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = CenterService()
    repository = MagicMock()
    repository.get_centers_by_geohash_prefixes.return_value = (centers, 3)
    service.center_repository = repository

    with patch("services.center_service.SessionLocal", return_value=session_context):
        response = service.get_centers_in_radius(request)

    assert response["data"]["view"] == "map"
    assert len(response["data"]["items"]) == 3
    assert response["data"]["total"] == 3
    assert response["data"]["pagination"] is None
    assert repository.get_centers_by_geohash_prefixes.call_args.kwargs["page"] is None
    assert (
        repository.get_centers_by_geohash_prefixes.call_args.kwargs["page_size"] is None
    )


def test_repository_applies_pagination_to_sql_query():
    session = MagicMock()
    session.scalar.return_value = 3
    session.scalars.return_value.all.return_value = []

    CenterRepository().get_centers_by_geohash_prefixes(
        prefixes=["u4pr"],
        session=session,
        latitude=51.5,
        longitude=-0.1,
        radius_km=10,
        page=3,
        page_size=20,
    )

    statement = session.scalars.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled).upper()

    assert "LIMIT" in sql
    assert "OFFSET" in sql
    assert any(value == 20 for value in compiled.params.values())
    assert any(value == 40 for value in compiled.params.values())
