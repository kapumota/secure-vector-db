from __future__ import annotations

import pytest
from fastapi import HTTPException

from secure_vector_db.api.auth import DEFAULT_DEV_API_KEY, require_api_key


def test_default_dev_api_key_is_available_for_existing_tests() -> None:
    assert isinstance(DEFAULT_DEV_API_KEY, str)
    assert DEFAULT_DEV_API_KEY


def test_require_api_key_accepts_default_dev_key() -> None:
    principal = require_api_key(DEFAULT_DEV_API_KEY)

    assert principal == "api-key-client"


def test_require_api_key_rejects_invalid_key() -> None:
    with pytest.raises(HTTPException) as exc:
        require_api_key("incorrecta")

    assert exc.value.status_code == 401
