"""Money parsing and display helpers."""

from decimal import Decimal, InvalidOperation


def parse_price_cents(value: str | None) -> int:
    normalized = (value or "").strip().replace("$", "").replace(",", "")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as error:
        raise ValueError("Enter a valid price.") from error
    if not amount.is_finite() or amount < 0:
        raise ValueError("Price must be zero or greater.")
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Price cannot have more than two decimal places.")
    return int(amount * 100)


def display_price(cents: int) -> str:
    return f"${cents / 100:,.2f}"
