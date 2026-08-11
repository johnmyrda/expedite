import pytest
from pydantic import ValidationError

from expedite.validation import (
    _field_adapter,
    validate_cost,
    validate_name,
    validate_phone,
)


def test_name_field_adapter_includes_string_constraints() -> None:
    adapter = _field_adapter("name")

    assert adapter.validate_python("Jane") == "Jane"

    with pytest.raises(ValidationError, match="at least 2 characters"):
        adapter.validate_python("B")


def test_name_validation_uses_custom_message_metadata() -> None:
    assert validate_name("B") == "Names are usually longer"


def test_work_request_field_adapter_includes_string_constraints() -> None:
    adapter = _field_adapter("work_request")

    assert adapter.validate_python("Pack order") == "Pack order"

    with pytest.raises(ValidationError, match="at least 1 character"):
        adapter.validate_python("")


def test_cost_field_adapter_validates_and_normalizes_string() -> None:
    adapter = _field_adapter("cost")

    assert adapter.validate_python("$12.50") == "12.50"

    with pytest.raises(ValidationError, match="Cost is not parseable as a number"):
        adapter.validate_python("not a number")

    with pytest.raises(ValidationError, match=r"Cost is \$0"):
        adapter.validate_python("0")


def test_phone_field_adapter_uses_phonenumbers_parse_validation() -> None:
    adapter = _field_adapter("phone")

    assert adapter.validate_python("+16502530000") == "+16502530000"
    assert adapter.validate_python("(650) 253-0000") == "+16502530000"

    with pytest.raises(ValidationError, match="too short"):
        adapter.validate_python("123")

    with pytest.raises(ValidationError, match="did not seem to be a phone number"):
        adapter.validate_python("not a phone number")


def test_ui_validation_removes_pydantic_value_error_prefix() -> None:
    assert validate_cost("not a number") == "Cost is not parseable as a number."
    assert validate_phone("123") == "Phone number is too short."
