import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from superoffer.scrapers.base import ProductOffer

HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "output", "price_history.json"
)


def load_history() -> Dict[str, List[dict]]:
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_entry(product_name: str, offers: List[ProductOffer], store_name: str):
    history = load_history()
    key = f"{product_name}|{store_name}"
    if key not in history:
        history[key] = []
    today = datetime.now().isoformat()[:10]
    for offer in offers:
        entry = {
            "fecha": today,
            "timestamp": datetime.now().isoformat(),
            "producto": offer.name,
            "precio": offer.price,
            "precio_original": offer.original_price,
            "descuento": offer.discount_percentage,
            "tienda": offer.store,
            "url": offer.url,
        }
        same_day = [e for e in history[key] if e.get("fecha") == today]
        if not same_day or any(
            abs(e["precio"] - offer.price) > 1 for e in same_day
        ):
            history[key].append(entry)
    max_entries = 30
    for k in history:
        history[k] = history[k][-max_entries:]
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def get_lowest_price(product_name: str, store_name: str) -> Optional[float]:
    history = load_history()
    key = f"{product_name}|{store_name}"
    entries = history.get(key, [])
    prices = [e["precio"] for e in entries if e.get("precio", 0) > 0]
    return min(prices) if prices else None
