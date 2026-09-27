from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.payment_service import PaymentService


def _prepare_webhook_service(booking, schedule):
	service = PaymentService()
	payment = SimpleNamespace(
		id=uuid4(),
		booking_id=booking.id,
		status="PENDING",
	)
	service.payment_repository.get_by_provider_payment_id_for_update = MagicMock(
		return_value=payment
	)
	service.payment_repository.get_by_provider_payment_id = MagicMock(
		return_value=payment
	)
	service.booking_repository.get_by_id = MagicMock(return_value=booking)
	service.booking_repository.get_by_id_for_update = MagicMock(
		return_value=booking
	)
	service.schedule_repository.get_by_id_for_update = MagicMock(
		return_value=schedule
	)
	service.webhook_event_repository.get_by_event_id = MagicMock(return_value=None)
	service.webhook_event_repository.create = MagicMock(
		return_value=SimpleNamespace(id=uuid4())
	)
	service.webhook_event_repository.mark_processed = MagicMock()
	return service, payment


def _booking(expires_at):
	return SimpleNamespace(
		id=uuid4(),
		schedule_id=uuid4(),
		status="PENDING",
		expires_at=expires_at,
	)


def test_successful_payment_confirms_still_valid_pending_booking():
	booking = _booking(datetime.now(timezone.utc) + timedelta(minutes=1))
	schedule = SimpleNamespace(status="PENDING")
	service, payment = _prepare_webhook_service(booking, schedule)

	response = service._process_webhook_in_session(
		session=MagicMock(),
		event_id="event-valid",
		event_type="payment.succeeded",
		provider_payment_id="provider-payment",
		status="SUCCESS",
		payload={},
	)

	assert response["status"] == 200
	assert booking.status == "CONFIRMED"
	assert schedule.status == "CONFIRMED"
	assert payment.status == "SUCCESS"


def test_successful_payment_does_not_resurrect_expired_booking():
	booking = _booking(datetime.now(timezone.utc) - timedelta(seconds=1))
	schedule = SimpleNamespace(status="PENDING")
	service, payment = _prepare_webhook_service(booking, schedule)

	response = service._process_webhook_in_session(
		session=MagicMock(),
		event_id="event-expired",
		event_type="payment.succeeded",
		provider_payment_id="provider-payment",
		status="SUCCESS",
		payload={},
	)

	assert response["status"] == 200
	assert booking.status == "EXPIRED"
	assert schedule.status == "CANCELLED"
	assert payment.status == "SUCCESS"


def test_contradictory_webhook_does_not_overwrite_final_payment_status():
	booking = _booking(datetime.now(timezone.utc) + timedelta(minutes=1))
	schedule = SimpleNamespace(status="CONFIRMED")
	service, payment = _prepare_webhook_service(booking, schedule)
	payment.status = "SUCCESS"

	response = service._process_webhook_in_session(
		session=MagicMock(),
		event_id="event-contradictory",
		event_type="payment.failed",
		provider_payment_id="provider-payment",
		status="FAILED",
		payload={},
	)

	assert response["status"] == 409
	assert payment.status == "SUCCESS"
	assert booking.status == "PENDING"
	service.webhook_event_repository.create.assert_not_called()


def test_payment_initiation_rejects_existing_pending_payment():
	user_id = uuid4()
	booking = SimpleNamespace(
		id=uuid4(),
		user_id=user_id,
		schedule_id=uuid4(),
		status="PENDING",
		expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
		amount=100,
	)
	session_context = MagicMock()
	session_context.__enter__.return_value = MagicMock()
	service = PaymentService()
	service.booking_repository.get_by_id = MagicMock(return_value=booking)
	service.booking_repository.get_by_id_for_update = MagicMock(return_value=booking)
	service.schedule_repository.get_by_id_for_update = MagicMock(
		return_value=SimpleNamespace(status="PENDING")
	)
	service.payment_repository.get_pending_for_booking = MagicMock(
		return_value=SimpleNamespace(id=uuid4())
	)
	service.payment_repository.create = MagicMock()

	with patch("services.payment_service.SessionLocal", return_value=session_context):
		response = service.create_payment(booking_id=booking.id, user_id=user_id)

	assert response["status"] == 409
	service.payment_repository.create.assert_not_called()
