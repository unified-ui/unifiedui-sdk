"""Tests for core utility functions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from unifiedui_sdk.core.utils import generate_id, safe_str, str_uuid, utc_now


class TestGenerateId:
    """Tests for generate_id."""

    def test_returns_string(self) -> None:
        result = generate_id()
        assert isinstance(result, str)

    def test_returns_valid_uuid(self) -> None:
        result = generate_id()
        parsed = uuid.UUID(result)
        assert parsed.version == 4

    def test_generates_unique_ids(self) -> None:
        ids = {generate_id() for _ in range(100)}
        assert len(ids) == 100


class TestUtcNow:
    """Tests for utc_now."""

    def test_returns_datetime(self) -> None:
        result = utc_now()
        assert isinstance(result, datetime)

    def test_has_utc_timezone(self) -> None:
        result = utc_now()
        assert result.tzinfo == UTC

    def test_is_current_time(self) -> None:
        before = datetime.now(tz=UTC)
        result = utc_now()
        after = datetime.now(tz=UTC)
        assert before <= result <= after


class TestStrUuid:
    """Tests for str_uuid."""

    def test_converts_uuid_to_string(self) -> None:
        uid = uuid.uuid4()
        assert str_uuid(uid) == str(uid)

    def test_returns_string_type(self) -> None:
        uid = uuid.uuid4()
        assert isinstance(str_uuid(uid), str)


class TestSafeStr:
    """Tests for safe_str."""

    def test_none_returns_empty(self) -> None:
        assert safe_str(None) == ""

    def test_string_passthrough(self) -> None:
        assert safe_str("hello") == "hello"

    def test_int_conversion(self) -> None:
        assert safe_str(42) == "42"

    def test_list_conversion(self) -> None:
        assert safe_str([1, 2, 3]) == "[1, 2, 3]"

    def test_dict_conversion(self) -> None:
        result = safe_str({"a": 1})
        assert "a" in result

    def test_empty_string(self) -> None:
        assert safe_str("") == ""

    def test_object_with_broken_str(self) -> None:
        class BadStr:
            def __str__(self) -> str:
                msg = "broken"
                raise RuntimeError(msg)

            def __repr__(self) -> str:
                return "BadStr()"

        assert safe_str(BadStr()) == "BadStr()"
