from typing import List, Optional
from superoffer.scrapers.base import SupermarketScraper, ProductOffer


class PlaywrightScraper(SupermarketScraper):
    def __init__(self, store_key: str):
        super().__init__(store_key)

    def search(self, query: str, max_results: int = 10) -> List[ProductOffer]:
        url = self.build_search_url(query, max_results)
        selector = self.config.js_selector or "pre"
        click_more = getattr(self.config, "js_click_more", "")
        html = self.scrape_with_playwright(url, selector, click_more)
        if not html:
            return []
        import json
        import re
        from superoffer.scrapers.base import extract_items, parse_item

        for pattern in (
            r'__NEXT_DATA__[^>]*>\s*(.*?)\s*</',
            r'__INITIAL_STATE__\s*=\s*(.*?);',
            r'__PRELOADED_STATE__\s*=\s*(.*?);',
            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
        ):
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    items = extract_items(data, self.config)
                    if items:
                        offers = []
                        for item in items[:max_results]:
                            offer = parse_item(item, self.config, self.config.name, self.config.base_url)
                            if offer:
                                offers.append(offer)
                        return sorted(offers, key=lambda o: o.price)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        return []
