import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from superoffer.scrapers.base import SupermarketScraper, ProductOffer, set_proxy_manager
from superoffer.scrapers.jumbo import JumboScraper
from superoffer.scrapers.lider import LiderScraper
from superoffer.scrapers.santa_isabel import SantaIsabelScraper
from superoffer.scrapers.tottus import TottusScraper
from superoffer.scrapers.unimarc import UnimarcScraper
from superoffer.scrapers.falabella import FalabellaScraper
from superoffer.scrapers.ripley import RipleyScraper
from superoffer.scrapers.paris import ParisScraper
from superoffer.scrapers.mercadolibre import MercadoLibreScraper
from superoffer.scrapers.mayorista10 import Mayorista10Scraper
from superoffer.scrapers.superbodega import SuperBodegaScraper
from superoffer.scrapers.acuenta import AcuentaScraper
from superoffer.scrapers.homecenter import HomecenterScraper
from superoffer.scrapers.solotodo import SoloTodoScraper
from superoffer.scrapers.facebook_marketplace import FacebookMarketplaceScraper
from superoffer.input import read_products
from superoffer.output.json_writer import write_results
from superoffer.output.csv_writer import write_csv
from superoffer.output.html_report import generate_html
from superoffer.output.excel_writer import write_xlsx
from superoffer.utils.messages import get_logger, info, error, summary, is_quiet
from superoffer.utils.price_history_db import save_entry, export_to_json
from superoffer.utils.notifier import send_notification
from superoffer.utils.cleanup import cleanup_old_outputs, cleanup_images
from superoffer.utils.proxy_manager import ProxyManager
from superoffer.utils.monitor import check_price_drops
from superoffer.utils.scoring import rank_offers

logger = get_logger("superoffer.engine")

SCRAPER_MAP: Dict[str, type] = {
    "jumbo": JumboScraper,
    "lider": LiderScraper,
    "santa_isabel": SantaIsabelScraper,
    "tottus": TottusScraper,
    "unimarc": UnimarcScraper,
    "falabella": FalabellaScraper,
    "ripley": RipleyScraper,
    "paris": ParisScraper,
    "mercadolibre": MercadoLibreScraper,
    "mayorista10": Mayorista10Scraper,
    "superbodega": SuperBodegaScraper,
    "acuenta": AcuentaScraper,
    "homecenter": HomecenterScraper,
    "solotodo": SoloTodoScraper,
    "facebook_marketplace": FacebookMarketplaceScraper,
}


class OfferEngine:
    def __init__(self, stores: Optional[List[str]] = None, max_workers: int = 8,
                 csv_output: bool = False, webhook_url: Optional[str] = None,
                 html_output: bool = False, excel_output: bool = False,
                 use_scoring: bool = False, catalog_mode: bool = False,
                 monitor_mode: bool = False, monitor_threshold: float = 10.0,
                 proxy_manager: Optional[ProxyManager] = None,
                 config: Optional[dict] = None,
                 super_offer_threshold: float = 30.0):
        self.store_keys = stores or list(SCRAPER_MAP.keys())
        self.max_workers = max_workers
        self.csv_output = csv_output
        self.html_output = html_output
        self.excel_output = excel_output
        self.use_scoring = use_scoring
        self.catalog_mode = catalog_mode
        self.monitor_mode = monitor_mode
        self.monitor_threshold = monitor_threshold
        self.webhook_url = webhook_url
        self.config = config or {}
        self.super_offer_threshold = super_offer_threshold
        self.scrapers: Dict[str, SupermarketScraper] = {}
        for key in self.store_keys:
            if key in SCRAPER_MAP:
                self.scrapers[key] = SCRAPER_MAP[key]()
        if proxy_manager:
            set_proxy_manager(proxy_manager)
        if not is_quiet():
            info(f"Motor iniciado con {len(self.scrapers)} tienda(s)")

    def search_product(self, product_name: str, brand: str = "") -> Dict[str, List[ProductOffer]]:
        query = f"{product_name} {brand}".strip()
        info(f"Buscando: '{query}'")
        results: Dict[str, List[ProductOffer]] = {}
        n_workers = min(len(self.scrapers), self.max_workers)
        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            future_map = {
                executor.submit(scraper.search, query): store_key
                for store_key, scraper in self.scrapers.items()
            }
            for future in as_completed(future_map):
                store_key = future_map[future]
                try:
                    offers = future.result()
                    store_name = self.scrapers[store_key].config.name
                    if offers:
                        for o in offers:
                            o.query_used = query
                        results[store_key] = offers
                        info(f"{store_name}: {len(offers)} oferta(s)")
                    else:
                        logger.debug(f"{store_name}: sin resultados")
                except Exception as e:
                    error(self.scrapers[store_key].config.name, f"Fallo: {type(e).__name__}: {e}")
        return results

    def run(self, input_file: str, output_path: Optional[str] = None) -> str:
        if self.catalog_mode:
            return self._run_catalog(output_path)
        info(f"Leyendo productos desde: {input_file}")
        products = read_products(input_file)
        if not products:
            error("SuperOffer", "No se encontraron productos en el archivo.",
                  "Usa columnas: 'Producto', 'Nombre' o similar.")
            return ""
        info(f"{len(products)} producto(s). Buscando en {len(self.scrapers)} tienda(s)...")
        all_results: Dict[str, Dict[str, List[ProductOffer]]] = {}
        total_offers = 0
        for i, product in enumerate(products, 1):
            name = product.get("name", "")
            brand = product.get("brand", "")
            msg = f"[{i}/{len(products)}] {name}"
            if brand:
                msg += f" ({brand})"
            info(msg)
            store_offers = self.search_product(name, brand)
            if store_offers:
                if self.use_scoring:
                    for sk in store_offers:
                        store_offers[sk] = rank_offers(store_offers[sk], 10)
                all_results[name] = store_offers
                for sk, offers in store_offers.items():
                    total_offers += len(offers)
                    product_query = f"{name} {brand}".strip()
                    save_entry(product_query, offers, self.scrapers[sk].config.name)
            else:
                info(f"Nada encontrado para '{name}'")
        output_file = write_results(all_results, input_file, output_path)
        if self.csv_output and output_file:
            base = output_file.rsplit("\\", 1)[0] if "\\" in output_file else output_file.rsplit("/", 1)[0]
            write_csv(all_results, base)
        if self.html_output and output_file:
            generate_html(all_results, input_file)
        if self.excel_output and output_file:
            base = output_file.rsplit("\\", 1)[0] if "\\" in output_file else output_file.rsplit("/", 1)[0]
            write_xlsx(all_results, base)
        if self.monitor_mode and all_results:
            drops = check_price_drops(all_results, self.monitor_threshold)
            if drops:
                logger.info("Bajas de precio detectadas: %d", len(drops))
                for d in drops:
                    logger.info("  %s: $%.0f -> $%.0f (%.1f%%)", d["producto"],
                                d["precio_anterior"], d["precio_nuevo"], d["baja_pct"])
        summary(len(all_results), total_offers, output_file or "(vacio)")
        cleanup_old_outputs()
        cleanup_images()
        if output_file and self.webhook_url:
            send_notification(self.config, output_file,
                             self._resumen(all_results, total_offers),
                             {"metadata": {"superofertas_detectadas": self._count_super(all_results),
                                           "total_productos": len(all_results)}})
        return output_file or ""

    def _run_catalog(self, output_path: Optional[str] = None) -> str:
        from superoffer.utils.catalog_scanner import scan_categories
        info("Modo catalogo: explorando categorias...")
        results = scan_categories(self.store_keys, self.max_workers)
        total = sum(len(v) for v in results.values())
        info(f"Catalogo: {len(results)} categorias, {total} ofertas")
        timestamp = __import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")
        import json, os
        from superoffer.utils.config import OUTPUT_DIR
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = output_path or os.path.join(OUTPUT_DIR, f"catalogo_{timestamp}.json")
        payload = {
            "metadata": {
                "fecha_generacion": __import__("datetime").datetime.now().isoformat(),
                "modo": "catalogo",
                "total_categorias": len(results),
                "total_ofertas": total,
            },
            "resultados": {k: [{"producto": o.name, "tienda": o.store, "precio": o.price,
                                "original": o.original_price, "descuento": o.discount_percentage,
                                "super_oferta": o.es_super_oferta(), "url": o.url}
                               for o in v] for k, v in results.items()},
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        info(f"Catalogo guardado en: {path}")
        return path

    def _resumen(self, results: Dict, total: int) -> str:
        super_offers = self._count_super(results)
        return f"SuperOffer: {len(results)} productos, {total} ofertas, {super_offers} superofertas"

    def _count_super(self, results: Dict) -> int:
        return sum(
            1 for so in results.values()
            for offers in so.values()
            for o in offers if o.es_super_oferta()
        )
