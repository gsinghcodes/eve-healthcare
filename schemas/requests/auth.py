from pydantic import BaseModel, field_validator

from utils.auth_utils import normalize_otp, normalize_phone_number


class RequestOTPRequest(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        normalized_value = normalize_phone_number(value)

        if not normalized_value:
            raise ValueError("Phone number must be in +91XXXXXXXXXX format")

        return normalized_value


class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        normalized_value = normalize_phone_number(value)

        if not normalized_value:
            raise ValueError("Phone number must be in +91XXXXXXXXXX format")

        return normalized_value

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        normalized_value = normalize_otp(value)

        if not normalized_value:
            raise ValueError("OTP must be a 6-digit numeric value")

        return normalized_value


