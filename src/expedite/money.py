"""Money parsing and display helpers."""

from decimal import Decimal, InvalidOperation


def parse_money_amount(value: object) -> Decimal:
    if isinstance(value, str):
        normalized = value.strip().replace("$", "").replace(",", "")
    elif isinstance(value, Decimal | int | float):
        normalized = str(value)
    else:
        normalized = ""

    try:
        amount = Decimal(normalized)
    except (InvalidOperation, ValueError) as error:
        raise ValueError("Money amount is not parseable.") from error
    if not amount.is_finite():
        raise ValueError("Money amount must be finite.")
    return amount


def parse_price_cents(value: str | None) -> int:
    try:
        amount = parse_money_amount(value)
    except ValueError as error:
        raise ValueError("Enter a valid price.") from error
    if amount < 0:
        raise ValueError("Price must be zero or greater.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Price cannot have more than two decimal places.")
    return int(amount * 100)


def display_price(cents: int) -> str:
    return f"${cents / 100:,.2f}"
