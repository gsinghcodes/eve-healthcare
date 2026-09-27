import re
from typing import Optional


PHONE_NUMBER_PATTERN = re.compile(r"\+91\d{10}")
OTP_PATTERN = re.compile(r"\d{6}")


def normalize_phone_number(phone_number: Optional[str]) -> Optional[str]:
    if phone_number is None:
        return None

    normalized_phone = phone_number.strip()

    if not PHONE_NUMBER_PATTERN.fullmatch(normalized_phone):
        return None

    return normalized_phone


def normalize_otp(otp: Optional[str]) -> Optional[str]:
    if otp is None:
        return None

    normalized_otp = otp.strip()

    if not OTP_PATTERN.fullmatch(normalized_otp):
        return None

    return normalized_otp
