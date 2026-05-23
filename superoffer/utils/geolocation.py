from typing import Dict, Optional, Tuple
from superoffer.utils.region import get_region


COMMUNE_COORDS: Dict[str, Tuple[float, float]] = {}


def _load_communes():
    global COMMUNE_COORDS
    if COMMUNE_COORDS:
        return
    region = get_region()
    communes = region.get("communes", {})
    for name, coords in communes.items():
        lat = coords.get("lat") if isinstance(coords, dict) else coords[0]
        lng = coords.get("lng") if isinstance(coords, dict) else coords[1]
        COMMUNE_COORDS[name.lower()] = (float(lat), float(lng))


def get_coordinates(commune: str) -> Optional[Tuple[float, float]]:
    _load_communes()
    key = commune.strip().lower().replace(" ", "_")
    return COMMUNE_COORDS.get(key)


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    import math
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng/2)**2)
    return 2 * R * math.asin(math.sqrt(a))


def commune_distance(commune1: str, commune2: str) -> Optional[float]:
    c1 = get_coordinates(commune1)
    c2 = get_coordinates(commune2)
    if c1 and c2:
        return haversine(c1[0], c1[1], c2[0], c2[1])
    return None
