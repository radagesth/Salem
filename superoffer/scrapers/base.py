import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Union, Any, Callable
from urllib.parse import quote

import requests

from superoffer.utils.config import StoreConfig, STORE_CONFIGS
from superoffer.utils.price_normalizer import normalize_price
from superoffer.utils.messages import get_logger, debug, warn
from superoffer.utils.proxy_manager import ProxyManager

logger = get_logger("superoffer.scrapers")

SUPER_OFFER_THRESHOLD = 30.0

_request_cache: Dict[str, Any] = {}
_proxy_manager: Optional[ProxyManager] = None


def set_proxy_manager(pm: ProxyManager):
    global _proxy_manager
    _proxy_manager = pm


@dataclass
class ProductOffer:
    name: str
    brand: str
    price: float
    original_price: Optional[float] = None
    url: str = ""
    image_url: str = ""
    imagen_local: str = ""
    store: str = ""
    sku: str = ""
    discount_percentage: Optional[float] = None
    query_used: str = ""

    def __post_init__(self):
        if self.original_price and self.original_price > self.price > 0:
            self.discount_percentage = round(
                (1 - self.price / self.original_price) * 100, 1
            )

    def es_super_oferta(self, threshold: float = SUPER_OFFER_THRESHOLD) -> bool:
        return self.discount_percentage is not None and self.discount_percentage >= threshold


def extract_items(data: Union[Dict, List, None], config: StoreConfig) -> List[Dict]:
    if data is None:
        return []
    if config.response_uses_list and isinstance(data, list):
        return data
    if isinstance(data, dict):
        keys = config.response_items_key.split("/") if config.response_items_key else []
        current: Any = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key, [])
            elif isinstance(current, list):
                break
        if isinstance(current, list):
            return current
        for fallback in ("products", "results", "items", "data"):
            if fallback in data:
                val = data[fallback]
                if isinstance(val, list):
                    return val
                if isinstance(val, dict):
                    for sub in ("items", "results", "data"):
                        if sub in val:
                            return val[sub]
        return data.get("results", data.get("products", data.get("items", [])))
    return []


def parse_item(item: Dict, config: StoreConfig, store_name: str, base_url: str) -> Optional[ProductOffer]:
    try:
        if config.nested_pricing:
            price_data = item.get("pricing", item)
        else:
            price_data = item
        price = normalize_price(price_data.get(config.price_key, 0))
        opk = config.original_price_key or f"original_{config.price_key}"
        orig = normalize_price(price_data.get(opk, price_data.get("originalPrice", 0))) or None
        name = item.get(config.name_key, item.get("productName", item.get("title", "")))
        brand = item.get(config.brand_key, "")
        raw_url = item.get(config.url_key, item.get("link", ""))
        if raw_url and not raw_url.startswith("http"):
            raw_url = f"{base_url}{raw_url}"
        raw_image = item.get(config.image_key, item.get("images", [""])[0] if isinstance(item.get("images"), list) else "")
        sku = str(item.get(config.sku_key, item.get("id", item.get("productId", ""))))
        if price <= 0 or not name:
            return None
        return ProductOffer(
            name=str(name)[:150],
            brand=str(brand) if brand else "",
            price=price,
            original_price=orig if orig and orig != price else None,
            url=raw_url,
            image_url=str(raw_image) if isinstance(raw_image, str) else "",
            store=store_name,
            sku=sku,
        )
    except (KeyError, TypeError, ValueError, IndexError):
        return None


class ScraperCache:
    def __init__(self, ttl_seconds: int = 300):
        self._cache: Dict[str, tuple[float, Any]] = {}
        self.ttl = ttl_seconds

    def get(self, key: str) -> Any:
        if key in self._cache:
            ts, val = self._cache[key]
            if time.time() - ts < self.ttl:
                debug(f"Cache hit: {key[:60]}")
                return val
            del self._cache[key]
        return None

    def set(self, key: str, val: Any):
        self._cache[key] = (time.time(), val)

    def clear(self):
        self._cache.clear()


class SupermarketScraper(ABC):
    def __init__(self, store_key: str, timeout: Optional[int] = None):
        self.store_key = store_key
        self.config: StoreConfig = STORE_CONFIGS[store_key]
        self.timeout = timeout or self.config.timeout
        self.session = requests.Session()
        self.session.headers.update(self.config.headers)
        self.cache = ScraperCache()
        self._retries = 2
        self._retry_delay = 2.0

    @abstractmethod
    def search(self, query: str, max_results: int = 10) -> List[ProductOffer]:
        ...

    def search_all_pages(self, query: str, max_results: int = 10) -> List[ProductOffer]:
        all_offers: List[ProductOffer] = []
        max_pages = self.config.max_pages
        for page in range(1, max_pages + 1):
            if len(all_offers) >= max_results:
                break
            remaining = max_results - len(all_offers)
            url = self.build_search_url(query, remaining, page)
            data = self._request(url)
            if data is None:
                break
            page_offers = self._parse_items(data, remaining)
            if not page_offers:
                break
            all_offers.extend(page_offers)
        return sorted(all_offers, key=lambda o: o.price)[:max_results]

    def build_search_url(self, query: str, max_results: int = 10, page: int = 1) -> str:
        qp = self.config.query_param
        rp = self.config.result_param
        url = f"{self.config.base_url}{self.config.search_endpoint}?{qp}={quote(query)}&{rp}={max_results}"
        if self.config.has_pagination and page > 1:
            pp = self.config.page_param
            url += f"&{pp}={page}"
        return url

    def build_category_url(self, category: str, max_results: int = 10, page: int = 1) -> str:
        ep = self.config.category_endpoint or self.config.search_endpoint
        cp = self.config.category_param
        rp = self.config.result_param
        url = f"{self.config.base_url}{ep}?{cp}={quote(category)}&{rp}={max_results}"
        if self.config.has_pagination and page > 1:
            url += f"&{self.config.page_param}={page}"
        return url

    def scrape_with_playwright(self, url: str, selector: str = "pre",
                               click_more: str = "") -> Optional[str]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            warn(self.config.name, "Playwright no instalado. pip install playwright")
            return None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=self.timeout * 1000)
                page.wait_for_load_state("networkidle")
                if click_more:
                    for _ in range(3):
                        try:
                            page.click(click_more)
                            page.wait_for_timeout(1000)
                        except Exception:
                            break
                if selector == "pre":
                    content = page.content()
                else:
                    el = page.query_selector(selector)
                    content = el.inner_html() if el else page.content()
                browser.close()
                return content
        except Exception as e:
            warn(self.config.name, f"Playwright fallo: {e}")
            return None

    def _request(self, url: str, use_proxy: bool = True) -> Optional[Union[Dict[str, Any], List[Any]]]:
        cached = self.cache.get(url)
        if cached is not None:
            return cached
        last_error: Optional[Exception] = None
        for attempt in range(self._retries + 1):
            try:
                proxies = None
                if use_proxy and _proxy_manager and _proxy_manager.count > 0:
                    proxies = _proxy_manager.get_rotated()
                resp = self.session.get(url, timeout=self.timeout, proxies=proxies)
                if resp.status_code == 429:
                    wait = self._retry_delay * (2 ** attempt)
                    warn(self.config.name, f"Rate limited (429). Esperando {wait:.0f}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                self.cache.set(url, data)
                return data
            except requests.ConnectionError as e:
                last_error = e
                warn(self.config.name, f"Intento {attempt+1}/{self._retries+1}: conexion fallida")
                if attempt < self._retries:
                    time.sleep(self._retry_delay)
            except requests.Timeout as e:
                last_error = e
                warn(self.config.name, f"Intento {attempt+1}/{self._retries+1}: timeout ({self.timeout}s)")
                if attempt < self._retries:
                    time.sleep(self._retry_delay)
            except requests.HTTPError as e:
                status = e.response.status_code if e.response is not None else "?"
                if status == 429 and attempt < self._retries:
                    wait = self._retry_delay * (2 ** attempt)
                    warn(self.config.name, f"Rate limited ({status}). Esperando {wait:.0f}s...")
                    time.sleep(wait)
                    continue
                warn(self.config.name, f"HTTP {status} en {url[:80]}...")
                return None
            except requests.RequestException as e:
                last_error = e
                if attempt < self._retries:
                    time.sleep(self._retry_delay)
            except ValueError:
                warn(self.config.name, f"JSON invalido desde {url[:80]}...")
                return None
        if last_error:
            warn(self.config.name, f"Fallo tras {self._retries+1} intentos: {last_error}")
        return None

    def _parse_items(self, data: Union[Dict, List, None], max_results: int = 10) -> List[ProductOffer]:
        items = extract_items(data, self.config)
        offers: List[ProductOffer] = []
        for item in items[:max_results]:
            offer = parse_item(item, self.config, self.config.name, self.config.base_url)
            if offer:
                offers.append(offer)
        return sorted(offers, key=lambda o: o.price)
