from typing import List
from superoffer.scrapers.base import SupermarketScraper, ProductOffer


class RipleyScraper(SupermarketScraper):
    def __init__(self):
        super().__init__("ripley")

    def search(self, query: str, max_results: int = 10) -> List[ProductOffer]:
        url = self.build_search_url(query, max_results)
        data = self._request(url)
        return self._parse_items(data, max_results)
