import pytest
from pydantic import ValidationError

from schemas.requests.auth import RequestOTPRequest, VerifyOTPRequest


def _validate_model(model_cls, payload):
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(payload)
    return model_cls.parse_obj(payload)


def test_request_otp_rejects_invalid_phone_number():
    with pytest.raises(ValidationError):
        _validate_model(RequestOTPRequest, {"phone_number": "12345"})


def test_verify_otp_rejects_invalid_phone_number_and_otp():
    with pytest.raises(ValidationError):
        _validate_model(VerifyOTPRequest, {"phone_number": "+91987654321", "otp": "123"})

    with pytest.raises(ValidationError):
        _validate_model(VerifyOTPRequest, {"phone_number": "invalid", "otp": "123456"})
