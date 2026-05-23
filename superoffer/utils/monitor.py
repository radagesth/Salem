from __future__ import annotations
import json
import os
import time
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from superoffer.scrapers.base import ProductOffer

MONITOR_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "output", "monitor_state.json"
)


def load_monitor_state() -> Dict:
    if not os.path.exists(MONITOR_FILE):
        return {}
    try:
        with open(MONITOR_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_monitor_state(state: Dict):
    os.makedirs(os.path.dirname(MONITOR_FILE), exist_ok=True)
    try:
        with open(MONITOR_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def check_price_drops(new_results: Dict[str, Dict[str, List[ProductOffer]]],
                      threshold_pct: float = 10.0) -> List[Dict]:
    state = load_monitor_state()
    drops = []
    for prod_name, store_offers in new_results.items():
        for store_key, offers in store_offers.items():
            for offer in offers:
                key = f"{prod_name}|{store_key}|{offer.name}"
                prev_price = state.get(key)
                if prev_price is not None and prev_price > 0 and offer.price > 0:
                    drop = (prev_price - offer.price) / prev_price * 100
                    if drop >= threshold_pct:
                        drops.append({
                            "producto": prod_name,
                            "tienda": offer.store,
                            "nombre": offer.name,
                            "precio_anterior": prev_price,
                            "precio_nuevo": offer.price,
                            "baja_pct": round(drop, 1),
                            "url": offer.url,
                        })
                state[key] = offer.price
    save_monitor_state(state)
    return drops
