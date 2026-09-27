import json
from types import SimpleNamespace
from uuid import uuid4

from routers.auth import get_current_user_profile


def test_get_current_user_profile_includes_nullable_names_only():
    user = SimpleNamespace(
        id=uuid4(),
        phone_number="+919876543210",
        first_name=None,
        last_name=None,
        is_verified=True,
        role="user",
        refresh_token_hash="sensitive-token-hash",
    )

    response = get_current_user_profile(current_user=user)
    payload = json.loads(response.body)

    assert payload["data"] == {
        "id": str(user.id),
        "phone_number": user.phone_number,
        "first_name": None,
        "last_name": None,
        "is_verified": True,
        "role": "user",
    }