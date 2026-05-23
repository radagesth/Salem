import re
from typing import Union


def normalize_price(raw_price: Union[str, float, int, None]) -> float:
    if raw_price is None:
        return 0.0
    if isinstance(raw_price, (int, float)):
        if raw_price < 0:
            return 0.0
        return float(raw_price)
    if not isinstance(raw_price, str):
        return 0.0
    if not raw_price.strip():
        return 0.0
    cleaned = re.sub(r"[^\d.,]", "", raw_price)
    if not cleaned:
        return 0.0
    parts_dot = cleaned.split(".")
    parts_comma = cleaned.split(",")
    has_dot = len(parts_dot) > 1
    has_comma = len(parts_comma) > 1
    if has_dot and has_comma:
        cleaned = cleaned.replace(".", "")
        cleaned = cleaned.replace(",", ".")
    elif has_dot and not has_comma:
        cleaned = cleaned.replace(".", "")
    elif has_comma and not has_dot:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def format_price(price: float) -> str:
    if price < 0:
        price = 0
    return f"${price:,.0f}".replace(",", ".")
