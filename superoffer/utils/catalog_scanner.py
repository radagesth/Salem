import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from superoffer.engine import SCRAPER_MAP
from superoffer.scrapers.base import SupermarketScraper, ProductOffer
from superoffer.utils.config import STORE_CONFIGS

logger = logging.getLogger("superoffer.catalog")


def scan_categories(store_keys: Optional[List[str]] = None,
                    max_workers: int = 4) -> Dict[str, List[ProductOffer]]:
    if store_keys is None:
        store_keys = list(SCRAPER_MAP.keys())
    results: Dict[str, List[ProductOffer]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_map = {}
        for sk in store_keys:
            cfg = STORE_CONFIGS.get(sk)
            if not cfg or not cfg.category_tree:
                logger.info("%s: sin categorias configuradas, omitiendo", sk)
                continue
            scraper = SCRAPER_MAP[sk]()
            for cat_name, subcats in cfg.category_tree.items():
                cats = subcats if subcats else [cat_name]
                for cat in cats:
                    future = ex.submit(_scan_store_category, scraper, cat)
                    future_map[future] = (sk, cat, cat_name)
        for future in as_completed(future_map):
            sk, cat, cat_name = future_map[future]
            try:
                offers = future.result()
                if offers:
                    key = f"{sk}/{cat_name}"
                    results.setdefault(key, []).extend(offers)
                    logger.info("%s [%s]: %d ofertas", sk, cat_name, len(offers))
            except Exception as e:
                logger.warning("%s [%s]: fallo - %s", sk, cat_name, e)
    return results


def _scan_store_category(scraper: SupermarketScraper, category: str,
                         max_results: int = 20) -> List[ProductOffer]:
    url = scraper.build_category_url(category, max_results)
    data = scraper._request(url)
    return scraper._parse_items(data, max_results)
