import json
import os
import sys
from typing import Dict, Optional

_regions: Dict[str, dict] = {}
_current_region: Optional[str] = None

REGIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "regions")


def load_region(region_code: str = "cl") -> dict:
    global _current_region
    path = os.path.join(REGIONS_DIR, f"{region_code}.json")
    if not os.path.exists(path):
        print(f"  [ERROR] Region '{region_code}' no encontrada en {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _current_region = region_code
    return data


def get_region(region_code: Optional[str] = None) -> dict:
    if region_code:
        _regions[region_code] = load_region(region_code)
        return _regions[region_code]
    if _current_region:
        return _regions.setdefault(_current_region, load_region(_current_region))
    return load_region("cl")


def format_currency(amount: float, region_code: Optional[str] = None) -> str:
    region = get_region(region_code)
    fmt = region.get("currency_format", "$%s")
    return fmt.replace("%s", f"{amount:,.0f}".replace(",", "."))


def normalize_price_for_region(price_str, region_code: Optional[str] = None) -> float:
    region = get_region(region_code)
    pf = region.get("price_normalizer", {})
    from superoffer.utils.price_normalizer import normalize_price as np_base
    return np_base(price_str)
