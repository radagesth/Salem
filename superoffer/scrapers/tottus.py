from typing import List
from superoffer.scrapers.base import SupermarketScraper, ProductOffer


class TottusScraper(SupermarketScraper):
    def __init__(self):
        super().__init__("tottus")

    def search(self, query: str, max_results: int = 10) -> List[ProductOffer]:
        return self.search_all_pages(query, max_results)
