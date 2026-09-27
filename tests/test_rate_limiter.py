from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Lock
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from redis.exceptions import RedisError

from core.config import settings
from routers.auth import (
    enforce_otp_request_limit,
    enforce_otp_verification_limit,
    enforce_refresh_limit,
)
from routers.booking import enforce_booking_limit
from routers.payments import enforce_payment_limit
from schemas.requests.auth import RequestOTPRequest, VerifyOTPRequest
from utils.rate_limiter import (
    RATE_LIMIT_MESSAGE,
    RateLimit,
    check_rate_limits,
)


class AtomicRedisFake:
    def __init__(self):
        self.values = {}
        self.lock = Lock()
        self.now_ms = 0
        self.fail = False
        self.last_keys = []

    def eval(self, script, number_of_keys, *args):
        if self.fail:
            raise RedisError("simulated redis outage")

        keys = args[:number_of_keys]
        arguments = args[number_of_keys:]
        self.last_keys = list(keys)
        blocked = 0
        retry_after_ms = 0

        with self.lock:
            for index, key in enumerate(keys):
                limit = int(arguments[index * 2])
                window_ms = int(arguments[index * 2 + 1])
                value = self.values.get(key)
                if value and value[1] <= self.now_ms:
                    value = None

                if value is None:
                    count = 1
                    expiry = self.now_ms + window_ms
                else:
                    count = value[0] + 1
                    expiry = value[1]

                self.values[key] = (count, expiry)
                remaining_ms = max(0, expiry - self.now_ms)
                if count > limit:
                    blocked = 1
                    retry_after_ms = max(retry_after_ms, remaining_ms)

        return [blocked, retry_after_ms]


def _request(redis_client, ip="198.51.100.1"):
    return SimpleNamespace(
        client=SimpleNamespace(host=ip),
        app=SimpleNamespace(state=SimpleNamespace(redis=redis_client)),
    )


def _otp(phone_number):
    return RequestOTPRequest(phone_number=phone_number)


def _verify(phone_number):
    return VerifyOTPRequest(phone_number=phone_number, otp="123456")


def _assert_rate_limited(callback):
    with pytest.raises(HTTPException) as error:
        callback()
    assert error.value.status_code == 429
    assert error.value.detail == RATE_LIMIT_MESSAGE
    assert int(error.value.headers["Retry-After"]) >= 1


def test_otp_ip_limit_allows_three_then_rejects_fourth():
    redis_client = AtomicRedisFake()
    request = _request(redis_client)

    for _ in range(3):
        enforce_otp_request_limit(request, _otp("+919876543210"))

    _assert_rate_limited(
        lambda: enforce_otp_request_limit(request, _otp("+919876543210"))
    )


def test_otp_phone_limit_is_independent_of_ip_and_hashes_phone_key():
    redis_client = AtomicRedisFake()
    phone_number = "+919876543210"

    for index in range(3):
        enforce_otp_request_limit(
            _request(redis_client, f"198.51.100.{index + 1}"),
            _otp(phone_number),
        )

    phone_key = f"rate_limit:otp:phone:{sha256(phone_number.encode()).hexdigest()}"
    assert phone_key in redis_client.last_keys
    assert phone_number not in " ".join(redis_client.last_keys)
    _assert_rate_limited(
        lambda: enforce_otp_request_limit(
            _request(redis_client, "198.51.100.10"),
            _otp(phone_number),
        )
    )


def test_different_phone_numbers_have_independent_otp_limits():
    redis_client = AtomicRedisFake()
    for index in range(3):
        enforce_otp_request_limit(
            _request(redis_client, f"198.51.100.{index + 1}"),
            _otp("+919876543210"),
        )

    enforce_otp_request_limit(
        _request(redis_client, "198.51.100.10"),
        _otp("+919876543211"),
    )


def test_otp_counters_expire_after_their_configured_window():
    redis_client = AtomicRedisFake()
    request = _request(redis_client)

    for index in range(3):
        enforce_otp_request_limit(
            request,
            _otp(f"+9198765432{index:02d}"),
        )
    _assert_rate_limited(
        lambda: enforce_otp_request_limit(request, _otp("+919876543299"))
    )

    redis_client.now_ms += settings.OTP_IP_RATE_WINDOW_SECONDS * 1000 + 1
    enforce_otp_request_limit(request, _otp("+919876543298"))


def test_otp_verification_limit_allows_five_then_rejects_sixth():
    redis_client = AtomicRedisFake()
    request = _request(redis_client)
    payload = _verify("+919876543210")

    for _ in range(5):
        assert enforce_otp_verification_limit(request, payload) is payload
    _assert_rate_limited(lambda: enforce_otp_verification_limit(request, payload))


def test_otp_verification_identifiers_are_independently_limited():
    redis_client = AtomicRedisFake()
    request = _request(redis_client)
    for _ in range(5):
        enforce_otp_verification_limit(request, _verify("+919876543210"))

    enforce_otp_verification_limit(request, _verify("+919876543211"))


def test_refresh_limit_allows_ten_then_rejects_eleventh():
    redis_client = AtomicRedisFake()
    request = _request(redis_client)

    for _ in range(10):
        enforce_refresh_limit(request)
    _assert_rate_limited(lambda: enforce_refresh_limit(request))


def test_booking_limits_are_per_authenticated_user():
    redis_client = AtomicRedisFake()
    request = _request(redis_client)
    first_user = SimpleNamespace(id="user-1")
    second_user = SimpleNamespace(id="user-2")

    for _ in range(10):
        enforce_booking_limit(request, current_user=first_user)
    _assert_rate_limited(
        lambda: enforce_booking_limit(request, current_user=first_user)
    )
    enforce_booking_limit(request, current_user=second_user)


def test_payment_creation_limit_is_per_authenticated_user():
    redis_client = AtomicRedisFake()
    request = _request(redis_client)
    user = SimpleNamespace(id="user-1")

    for _ in range(5):
        enforce_payment_limit(request, current_user=user)
    _assert_rate_limited(lambda: enforce_payment_limit(request, current_user=user))


def test_concurrent_attempts_cannot_exceed_configured_success_limit():
    redis_client = AtomicRedisFake()
    limit = 25

    def attempt(_):
        try:
            check_rate_limits(
                redis_client,
                [RateLimit("rate_limit:concurrency:test", limit, 60)],
            )
            return True
        except HTTPException as error:
            assert error.status_code == 429
            return False

    with ThreadPoolExecutor(max_workers=16) as executor:
        accepted = list(executor.map(attempt, range(100)))

    assert sum(accepted) == limit
    assert redis_client.values["rate_limit:concurrency:test"][0] == 100


def test_redis_failure_logs_and_fails_closed():
    redis_client = AtomicRedisFake()
    redis_client.fail = True

    with pytest.raises(HTTPException) as error:
        check_rate_limits(
            redis_client,
            [RateLimit("rate_limit:security:test", 1, 60)],
        )

    assert error.value.status_code == 503
    assert error.value.detail == "Rate limiting temporarily unavailable."


def test_rate_limiter_handles_multiple_windows_in_one_atomic_call():
    redis_client = AtomicRedisFake()
    check_rate_limits(
        redis_client,
        [
            RateLimit("rate_limit:otp:ip:test", 3, 60),
            RateLimit("rate_limit:otp:phone:test", 3, 600),
        ],
    )

    assert redis_client.last_keys == [
        "rate_limit:otp:ip:test",
        "rate_limit:otp:phone:test",
    ]


def test_invalid_otp_payload_does_not_reach_limiter():
    with pytest.raises(ValidationError):
        _verify("invalid")
