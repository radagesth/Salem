from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from superoffer.scrapers.base import ProductOffer

logger = logging.getLogger("superoffer.scoring")

STORE_REPUTATION: Dict[str, float] = {
    "Jumbo": 0.9, "Lider": 0.85, "Santa Isabel": 0.8, "Tottus": 0.85,
    "Unimarc": 0.75, "Falabella": 0.9, "Ripley": 0.85, "Paris": 0.85,
    "MercadoLibre": 0.7, "Mayorista 10": 0.75, "SuperBodega": 0.7,
    "Acuenta": 0.7, "Homecenter": 0.85, "SoloTodo": 0.8,
    "Facebook Marketplace": 0.5,
}


def score_offer(offer: ProductOffer, weights: Optional[Dict[str, float]] = None) -> float:
    if weights is None:
        weights = {"price": 0.5, "discount": 0.25, "reputation": 0.15, "availability": 0.1}
    price_score = max(0, 1 - (offer.price / 50000)) if offer.price > 0 else 0
    discount_score = min(offer.discount_percentage / 100, 1.0) if offer.discount_percentage else 0
    reputation = STORE_REPUTATION.get(offer.store, 0.5)
    avail_score = 1.0 if not offer.sku else 0.9
    score = (
        weights["price"] * price_score +
        weights["discount"] * discount_score +
        weights["reputation"] * reputation +
        weights["availability"] * avail_score
    )
    return round(score, 4)


def rank_offers(offers: List[ProductOffer], top_n: int = 10) -> List[ProductOffer]:
    scored = [(score_offer(o), o) for o in offers]
    scored.sort(key=lambda x: (-x[0], x[1].price))
    return [o for _, o in scored[:top_n]]
