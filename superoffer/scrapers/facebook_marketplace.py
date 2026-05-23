import json
import os
import re
from typing import List, Optional, Dict, Any
import requests
from superoffer.scrapers.base import SupermarketScraper, ProductOffer
from superoffer.utils.price_normalizer import normalize_price
from superoffer.utils.messages import warn


class FacebookMarketplaceScraper(SupermarketScraper):
    def __init__(self):
        super().__init__("facebook_marketplace")
        cookie = os.environ.get("FACEBOOK_COOKIE", "")
        if cookie:
            self.session.headers.update({"Cookie": cookie})

    def build_search_url(self, query: str, max_results: int = 10) -> str:
        q = query.replace(" ", "%20")
        return f"{self.config.base_url}/marketplace/search/?query={q}"

    def search(self, query: str, max_results: int = 10) -> List[ProductOffer]:
        url = self.build_search_url(query, max_results)
        cookie_set = "FACEBOOK_COOKIE" in os.environ
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 404 or "marketplace" not in resp.url:
                if not cookie_set:
                    warn("Facebook Marketplace", "Requiere login. Usa FACEBOOK_COOKIE")
                else:
                    warn("Facebook Marketplace", "Cookie invalida o expirada. Renuevala.")
                return []
            if resp.status_code == 429:
                warn("Facebook Marketplace", "Rate limit. Espera unos minutos.")
                return []
            if resp.status_code != 200:
                warn("Facebook Marketplace", f"HTTP {resp.status_code}")
                return []
            offers = self._parse_html(resp.text, max_results)
            if not offers:
                offers = self._parse_embedded_json(resp.text, max_results)
            if not offers:
                warn("Facebook Marketplace", "No se pudo extraer productos. El formato pudo cambiar.")
            return sorted(offers, key=lambda o: o.price)
        except requests.ConnectionError:
            warn("Facebook Marketplace", "No se pudo conectar.")
            return []
        except requests.Timeout:
            warn("Facebook Marketplace", f"Timeout ({self.timeout}s).")
            return []
        except Exception as e:
            warn("Facebook Marketplace", f"Error: {type(e).__name__}: {e}")
            return []

    def _parse_html(self, html: str, max_results: int) -> List[ProductOffer]:
        offers = []
        name_patterns = [
            r'"marketplace_listing_title"[=:]\s*"([^"]+)"',
            r'<span[^>]*class="[^"]*title[^"]*"[^>]*>\s*([^<]+)',
            r'<a[^>]*aria-label="([^"]+)"',
            r'"name"\s*:\s*"([^"]+)"',
        ]
        price_patterns = [
            r'"listing_price"[=:]\s*["\']?(\d[\d.,]*)',
            r'<div[^>]*class="[^"]*price[^"]*"[^>]*>\s*\$?([\d.,]+)',
            r'{"__typename":"MarketplaceListing".*?"price":"(\d[\d.,]*)"',
        ]
        url_patterns = [
            r'"url"\s*:\s*"(https?://[^"]+)"',
            r'href="(\/marketplace\/item\/[^"]+)"',
        ]
        names = self._first_match_all(html, name_patterns)
        prices = self._first_match_all(html, price_patterns)
        urls = self._first_match_all(html, url_patterns)
        for i in range(min(len(names), len(prices))):
            try:
                price = normalize_price(prices[i])
                if price <= 0:
                    continue
                item_url = urls[i] if i < len(urls) else ""
                if item_url and not item_url.startswith("http"):
                    item_url = f"{self.config.base_url}{item_url}"
                offers.append(ProductOffer(
                    name=names[i][:100], brand="Facebook Marketplace",
                    price=price, url=item_url, store=self.config.name, sku=f"fb_{i}",
                ))
            except (IndexError, ValueError, TypeError):
                continue
        return offers[:max_results]

    def _parse_embedded_json(self, html: str, max_results: int) -> List[ProductOffer]:
        offers = []
        patterns = [
            r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            r'<script[^>]*>window\.__INITIAL_STATE__\s*=\s*({.*?});</script>',
            r'<script[^>]*>__PRELOADED_STATE__\s*=\s*({.*?});</script>',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if not match:
                continue
            try:
                data = json.loads(match.group(1))
                extracted = self._traverse_json(data, max_results)
                if extracted:
                    offers.extend(extracted)
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        return offers[:max_results]

    def _traverse_json(self, data: Any, max_results: int, depth: int = 0) -> List[ProductOffer]:
        if depth > 6:
            return []
        offers = []
        if isinstance(data, dict):
            if "listing_price" in data or "price" in data:
                price_raw = data.get("listing_price") or data.get("price", "0")
                price = normalize_price(price_raw)
                name = data.get("marketplace_listing_title") or data.get("name", data.get("title", ""))
                url = data.get("url", data.get("link", ""))
                image = data.get("image", data.get("thumbnail", ""))
                if isinstance(image, list):
                    image = image[0] if image else ""
                if isinstance(image, dict):
                    image = image.get("uri", "")
                lid = data.get("id", data.get("node", {}).get("id", ""))
                if price > 0 and name:
                    offers.append(ProductOffer(
                        name=str(name)[:100], brand="Facebook Marketplace",
                        price=price, store=self.config.name,
                        url=url if isinstance(url, str) and url.startswith("http") else "",
                        image_url=str(image) if isinstance(image, str) else "",
                        sku=str(lid),
                    ))
            for key in ("node", "listing", "marketplace_listing", "edges", "items",
                        "results", "data", "nodes", "listings", "pageProps", "props"):
                val = data.get(key)
                if val is not None:
                    offers.extend(self._traverse_json(val, max_results, depth + 1))
        elif isinstance(data, list):
            for item in data:
                offers.extend(self._traverse_json(item, max_results, depth + 1))
        return offers[:max_results]

    @staticmethod
    def _first_match_all(text: str, patterns: list) -> list:
        for p in patterns:
            matches = re.findall(p, text)
            if matches:
                return matches
        return []
