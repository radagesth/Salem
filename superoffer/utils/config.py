import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StoreConfig:
    name: str
    base_url: str
    search_endpoint: str
    headers: Dict[str, str]
    location_id: str = ""
    query_param: str = "q"
    result_param: str = "_results"
    timeout: int = 15
    response_items_key: str = ""
    response_uses_list: bool = False
    price_key: str = "price"
    original_price_key: str = ""
    name_key: str = "name"
    brand_key: str = "brand"
    url_key: str = "url"
    image_key: str = "image"
    sku_key: str = "sku"
    nested_pricing: bool = False
    has_pagination: bool = False
    page_param: str = "page"
    max_pages: int = 1
    category_endpoint: str = ""
    category_param: str = "category"
    use_playwright: bool = False
    js_selector: str = "pre"
    js_click_more: str = ""
    category_tree: Dict[str, List[str]] = field(default_factory=dict)


STORE_CONFIGS: Dict[str, StoreConfig] = {
    "jumbo": StoreConfig(
        name="Jumbo", base_url="https://www.jumbo.cl",
        search_endpoint="/api/catalog_system/pub/products/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json",
                 "x-location-id": "2001200"},
        location_id="2001200", response_uses_list=True,
        original_price_key="listPrice", name_key="productName",
    ),
    "lider": StoreConfig(
        name="Lider", base_url="https://www.lider.cl",
        search_endpoint="/supermercado/api/products/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json",
                 "x-location-id": "57"},
        location_id="57", response_items_key="products",
        nested_pricing=True,
    ),
    "santa_isabel": StoreConfig(
        name="Santa Isabel", base_url="https://www.santaisabel.cl",
        search_endpoint="/api/catalog_system/pub/products/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json",
                 "x-location-id": "2001200"},
        location_id="2001200", response_uses_list=True,
        original_price_key="listPrice", name_key="productName",
    ),
    "tottus": StoreConfig(
        name="Tottus", base_url="https://www.tottus.cl",
        search_endpoint="/api/products/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json"},
        response_items_key="products", nested_pricing=True, has_pagination=True, max_pages=3,
    ),
    "unimarc": StoreConfig(
        name="Unimarc", base_url="https://www.unimarc.cl",
        search_endpoint="/api/v1/products/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json"},
        response_items_key="products",
    ),
    "falabella": StoreConfig(
        name="Falabella", base_url="https://www.falabella.cl",
        search_endpoint="/api/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json"},
        result_param="limit", response_items_key="results",
    ),
    "ripley": StoreConfig(
        name="Ripley", base_url="https://www.ripley.cl",
        search_endpoint="/api/products/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json"},
        result_param="size", response_items_key="products", nested_pricing=True,
    ),
    "paris": StoreConfig(
        name="Paris", base_url="https://www.paris.cl",
        search_endpoint="/api/products/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json"},
        result_param="limit", response_items_key="products",
    ),
    "mercadolibre": StoreConfig(
        name="MercadoLibre", base_url="https://www.mercadolibre.cl",
        search_endpoint="/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json"},
        response_items_key="results", name_key="title", url_key="permalink",
        image_key="thumbnail", sku_key="id",
    ),
    "mayorista10": StoreConfig(
        name="Mayorista 10", base_url="https://www.mayorista10.cl",
        search_endpoint="/api/products/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json"},
        response_items_key="products",
    ),
    "superbodega": StoreConfig(
        name="SuperBodega", base_url="https://www.superbodega.cl",
        search_endpoint="/api/products/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json"},
        response_items_key="products", nested_pricing=True,
    ),
    "acuenta": StoreConfig(
        name="Acuenta", base_url="https://www.acuenta.cl",
        search_endpoint="/api/products/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json"},
        response_items_key="products",
    ),
    "homecenter": StoreConfig(
        name="Homecenter", base_url="https://www.homecenter.cl",
        search_endpoint="/api/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json", "Content-Type": "application/json"},
        result_param="limit", response_items_key="results",
    ),
    "solotodo": StoreConfig(
        name="SoloTodo", base_url="https://www.solotodo.cl",
        search_endpoint="/api/v1/products",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "application/json"},
        query_param="search", result_param="limit", response_items_key="results",
        price_key="price", nested_pricing=True,
    ),
    "facebook_marketplace": StoreConfig(
        name="Facebook Marketplace", base_url="https://www.facebook.com",
        search_endpoint="/marketplace/search",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                 "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                 "Accept-Language": "es-CL,es;q=0.9,en;q=0.8"},
        query_param="query", timeout=20,
    ),
}


OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
MAX_RESULTS_RETENTION = 20
