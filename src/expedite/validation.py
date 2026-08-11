"""Non-blocking intake-field validation messages."""

from typing import Annotated

from pydantic import TypeAdapter, ValidationError

from expedite.models import Message, Order


def _field_adapter(field_name: str) -> TypeAdapter[object]:
    field = Order.model_fields[field_name]
    return TypeAdapter(Annotated[field.annotation, *field.metadata])


def _field_message(field_name: str) -> str | None:
    field = Order.model_fields[field_name]
    for metadata in field.metadata:
        if isinstance(metadata, Message):
            return metadata.text
    return None


_NAME_ADAPTER = _field_adapter("name")
_PHONE_ADAPTER = _field_adapter("phone")
_WORK_REQUEST_ADAPTER = _field_adapter("work_request")
_COST_ADAPTER = _field_adapter("cost")


def _clean_error_message(message: object) -> str:
    text = str(message)
    return text.removeprefix("Value error, ")


def _validate_field(
    field_name: str,
    adapter: TypeAdapter[object],
    value: str | None,
) -> str | None:
    try:
        adapter.validate_python(value)
    except ValidationError as error:
        return _field_message(field_name) or _clean_error_message(error.errors()[0]["msg"])
    return None


def validate_name(value: str | None) -> str | None:
    return _validate_field("name", _NAME_ADAPTER, value)


def validate_phone(value: str | None) -> str | None:
    return _validate_field("phone", _PHONE_ADAPTER, value)


def validate_work_request(value: str | None) -> str | None:
    return _validate_field("work_request", _WORK_REQUEST_ADAPTER, value)


def validate_cost(value: str | None) -> str | None:
    return _validate_field("cost", _COST_ADAPTER, value)
