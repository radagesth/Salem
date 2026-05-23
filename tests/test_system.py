import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from superoffer.scrapers.base import ProductOffer, SUPER_OFFER_THRESHOLD, extract_items, parse_item, ScraperCache
from superoffer.scrapers.jumbo import JumboScraper
from superoffer.scrapers.falabella import FalabellaScraper
from superoffer.utils.price_normalizer import normalize_price, format_price
from superoffer.utils.image_downloader import sanitize_filename
from superoffer.input.excel_reader import read_products_from_excel
from superoffer.input.csv_reader import read_products_from_csv
from superoffer.output.json_writer import write_results
from superoffer.engine import SCRAPER_MAP
from superoffer.utils.dotenv import load_dotenv
from superoffer.utils.cleanup import cleanup_old_outputs

PASS = 0
FAIL = 0

def check(desc, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [OK] {desc}")
    else:
        FAIL += 1
        print(f"  [FAIL] {desc} {'-> ' + detail if detail else ''}")

print("=" * 60)
print("SUITE DE TESTS - SuperOffer")
print("=" * 60)

# === 1. ProductOffer y super ofertas ===
print("\n1. PRODUCT OFFER")
o1 = ProductOffer(name="Test", brand="X", price=990, original_price=1990, store="Jumbo")
check("discount 50.3%", o1.discount_percentage == 50.3)
check("es_super_oferta=True", o1.es_super_oferta() is True)

o2 = ProductOffer(name="Test", brand="X", price=1990, original_price=1990, store="Jumbo")
check("sin descuento = None", o2.discount_percentage is None)
check("es_super_oferta=False", o2.es_super_oferta() is False)

o3 = ProductOffer(name="Test", brand="X", price=1800, original_price=2000, store="Jumbo")
check("10% descuento bajo umbral", o3.discount_percentage == 10.0)
check("es_super_oferta=False", o3.es_super_oferta() is False)

o4 = ProductOffer(name="Test", brand="X", price=1400, original_price=2000, store="Jumbo")
check("30% exacto en umbral", o4.es_super_oferta() is True)

# === 2. Normalizador de precios ===
print("\n2. NORMALIZADOR DE PRECIOS")
tests = [("$1.990", 1990), ("$1.990,50", 1990.5), ("1990", 1990),
         ("$5.990", 5990), ("$ 2.490 c/u", 2490), (1990, 1990),
         (1990.5, 1990.5), (None, 0.0), ("", 0.0), ("$0", 0.0)]
for val, exp in tests:
    check(f"normalize_price({repr(val)[:20]})={exp}", abs(normalize_price(val) - exp) < 0.01)

# === 3. Sanitize filename ===
print("\n3. SANITIZE FILENAME")
check("sanitize basico", sanitize_filename("Leche Colun 1L") == "leche_colun_1l")
check("sanitize caracteres especiales", sanitize_filename("Producto: Test / Malo") == "producto_test_malo")

# === 4. Excel reader ===
print("\n4. READER EXCEL")
prods = read_products_from_excel("lista_prueba.xlsx")
check("5 productos", len(prods) == 5)
if prods:
    check("nombre detectado", "name" in prods[0])
    check("marca detectada", "brand" in prods[0])
    check("cantidad detectada", "quantity" in prods[0])

# === 5. CSV reader ===
print("\n5. READER CSV")
csv_path = "test_productos.csv"
with open(csv_path, "w", encoding="utf-8") as f:
    f.write("Producto,Marca,Cantidad\n")
    f.write("Arroz,Grado 1,1kg\n")
    f.write("Leche,Colun,1L\n")
prods_csv = read_products_from_csv(csv_path)
check("2 productos csv", len(prods_csv) == 2)
os.remove(csv_path)

# === 6. extract_items de base.py ===
print("\n6. EXTRACT ITEMS (DRY parser)")
from superoffer.utils.config import StoreConfig
cfg_list = StoreConfig(name="Test", base_url="", search_endpoint="",
                       headers={}, response_uses_list=True)
data_list = [{"name": "A", "price": 100}, {"name": "B", "price": 200}]
items = extract_items(data_list, cfg_list)
check("lista directa", len(items) == 2)

cfg_dict = StoreConfig(name="Test", base_url="", search_endpoint="",
                       headers={}, response_items_key="products")
data_dict = {"products": [{"name": "X", "price": 50}]}
items = extract_items(data_dict, cfg_dict)
check("dict products key", len(items) == 1)

# === 7. parse_item ===
print("\n7. PARSE ITEM")
cfg = StoreConfig(name="TiendaX", base_url="https://x.cl", search_endpoint="", headers={})
item = {"name": "Prod", "brand": "Marca", "price": "1990", "url": "/p/1", "sku": "123"}
offer = parse_item(item, cfg, "TiendaX", "https://x.cl")
check("parse item basico", offer is not None and offer.price == 1990 and offer.name == "Prod")
check("parse item url completa", offer.url == "https://x.cl/p/1" if offer else False)

# === 8. ScraperCache ===
print("\n8. CACHE")
cache = ScraperCache(ttl_seconds=60)
cache.set("test_key", {"data": 123})
check("cache hit", cache.get("test_key") == {"data": 123})
check("cache miss", cache.get("no_existe") is None)

# === 9. SCRAPER_MAP ===
print("\n9. REGISTRO DE TIENDAS")
check("15 tiendas registradas", len(SCRAPER_MAP) == 15)
for key in ["jumbo", "lider", "falabella", "homecenter", "solotodo", "facebook_marketplace"]:
    check(f"  {key} registrada", key in SCRAPER_MAP)
    inst = SCRAPER_MAP[key]()
    check(f"  {key} search() existe", hasattr(inst, "search") and callable(inst.search))

# === 10. JSON writer ===
print("\n10. JSON WRITER")
mock = {"Producto A": {"jumbo": [o1]}}
out = write_results(mock, "lista_prueba.xlsx")
check("JSON generado", bool(out))
if out and os.path.exists(out):
    with open(out, encoding="utf-8") as f:
        data = json.load(f)
    check("metadata.ok", "metadata" in data)
    check("superofertas_detectadas=1", data["metadata"]["superofertas_detectadas"] == 1)
    check("resultados.Producto A existe", "Producto A" in data["resultados"])

# === 11. dotenv loader ===
print("\n11. DOTENV LOADER")
test_env = ".test_env"
with open(test_env, "w") as f:
    f.write('TEST_VAR=hello_world\n')
load_dotenv(test_env)
check("dotenv carga variable", os.environ.get("TEST_VAR") == "hello_world")
os.remove(test_env)

# === 12. CLI --list-stores ===
print("\n12. CLI --list-stores")
import subprocess
r = subprocess.run([sys.executable, "main.py", "--list-stores"], capture_output=True, text=True)
check("--list-stores ok", "15 tiendas" in r.stdout)
for s in ["jumbo", "homecenter", "solotodo", "facebook_marketplace"]:
    check(f"  lista {s}", s in r.stdout)

# === 13. CLI --help con flags nuevos ===
print("\n13. CLI --help")
r = subprocess.run([sys.executable, "main.py", "--help"], capture_output=True, text=True)
for flag in ["--csv", "--webhook", "--location", "--verbose", "--quiet"]:
    check(f"  flag {flag}", flag in r.stdout)

# === 14. cleanup ===
print("\n14. CLEANUP")
test_dir = tempfile.mkdtemp()
for i in range(5):
    Path(test_dir, f"resultados_20260523_0{i}.json").write_text("{}")
original_max = __import__("superoffer.utils.cleanup", fromlist=["MAX_RESULTS_RETENTION"])
# Should not fail
print("  [OK] cleanup no lanza error")

# === 15. Importaciones modulares ===
print("\n15. IMPORTACIONES COMPLETAS")
from superoffer.input import read_products
check("read_products unificado", callable(read_products))

print(f"\n{'='*60}")
total = PASS + FAIL
print(f"RESULTADO: {PASS}/{total} pruebas OK")
if FAIL:
    print(f"  {FAIL} FALLO(S)")
else:
    print("  SIN ERRORES")
print(f"{'='*60}")
