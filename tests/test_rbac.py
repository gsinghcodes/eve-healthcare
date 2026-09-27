from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from routers.middlewares.auth import require_roles


def test_require_roles_accepts_a_permitted_role():
    user = SimpleNamespace(role="center_manager")

    assert require_roles("center_manager", "admin")(user) is user


def test_require_roles_rejects_an_unpermitted_role():
    user = SimpleNamespace(role="user")

    with pytest.raises(HTTPException) as error:
        require_roles("center_manager", "admin")(user)

    assert error.value.status_code == 403