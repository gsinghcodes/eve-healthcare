from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.center_service import CenterService
from services.center_test_service import CenterTestService


def test_center_manager_can_only_update_owned_centers():
    user_id = uuid4()
    center = SimpleNamespace(id=uuid4(), owner_user_id=uuid4())
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = CenterService()
    service.center_repository = MagicMock()
    service.center_repository.get_center_by_id.return_value = center

    with patch("services.center_service.SessionLocal", return_value=session_context):
        response = service.update_center(
            center_id=center.id,
            request=MagicMock(),
            user_id=user_id,
            is_admin=False,
        )

    assert response["status"] == 403
    service.center_repository.update_center.assert_not_called()


def test_created_center_is_assigned_to_creating_manager():
    user_id = uuid4()
    request = SimpleNamespace(
        name="North Clinic",
        address="Main St",
        latitude=40.7,
        longitude=-74.0,
        opening_time=None,
        closing_time=None,
    )
    created_center = SimpleNamespace(id=uuid4())
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = CenterService()
    service.center_repository = MagicMock()
    service.center_repository.get_center_by_name.return_value = None
    service.center_repository.create_center.return_value = created_center

    with patch("services.center_service.SessionLocal", return_value=session_context):
        response = service.create_center(
            center=request,
            user_id=user_id,
            is_admin=False,
        )

    assert response["status"] == 201
    assert service.center_repository.create_center.call_args.kwargs[
        "owner_user_id"
    ] == user_id


def test_center_manager_cannot_add_offering_to_another_center():
    user_id = uuid4()
    center = SimpleNamespace(id=uuid4(), owner_user_id=uuid4())
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = CenterTestService()
    service.center_test_repository = MagicMock()
    service.center_repository = MagicMock()
    service.center_repository.get_center_by_id.return_value = center

    with patch(
        "services.center_test_service.SessionLocal",
        return_value=session_context,
    ):
        response = service.create_center_test(
            center_id=center.id,
            test_id=uuid4(),
            price=10,
            user_id=user_id,
            is_admin=False,
        )

    assert response["status"] == 403
    service.center_test_repository.create.assert_not_called()


def test_center_manager_cannot_update_another_centers_offering():
    user_id = uuid4()
    center = SimpleNamespace(id=uuid4(), owner_user_id=uuid4())
    offering = SimpleNamespace(id=uuid4(), center_id=center.id)
    session_context = MagicMock()
    session_context.__enter__.return_value = MagicMock()
    service = CenterTestService()
    service.center_test_repository = MagicMock()
    service.center_test_repository.get_by_id.return_value = offering
    service.center_repository = MagicMock()
    service.center_repository.get_center_by_id.return_value = center

    with patch(
        "services.center_test_service.SessionLocal",
        return_value=session_context,
    ):
        response = service.update_center_test(
            center_test_id=offering.id,
            price=10,
            user_id=user_id,
            is_admin=False,
        )

    assert response["status"] == 403
    service.center_test_repository.update.assert_not_called()