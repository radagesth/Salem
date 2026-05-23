import json
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, jsonify, request, render_template_string, send_from_directory

from superoffer.engine import OfferEngine, SCRAPER_MAP
from superoffer.input import read_products
from superoffer.utils.config import OUTPUT_DIR
from superoffer.utils.messages import setup as setup_logging
from superoffer.utils.config_loader import load_yaml_config

app = Flask(__name__)
_engine: Optional[OfferEngine] = None
_config: dict = {}

INDEX_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SuperOffer Web</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; color: #333; padding: 20px; }
  .container { max-width: 800px; margin: 0 auto; }
  h1 { font-size: 26px; margin-bottom: 20px; color: #2c3e50; }
  .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  textarea, select, input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; margin-bottom: 10px; }
  button { background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; cursor: pointer; }
  button:hover { background: #2980b9; }
  .result-item { padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
  .result-item:last-child { border: none; }
  .price { font-size: 18px; font-weight: 700; color: #27ae60; }
  .super-badge { background: #e74c3c; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
  .store-badge { background: #ecf0f1; padding: 2px 8px; border-radius: 4px; font-size: 12px; color: #7f8c8d; }
  .results-list { list-style: none; }
  .results-list li { margin-bottom: 20px; padding: 15px; background: #fafafa; border-radius: 8px; }
  .results-list h3 { margin-bottom: 8px; color: #2c3e50; }
  .results-list .offer { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; }
  .nav { display: flex; gap: 10px; margin-bottom: 20px; }
  .nav a { color: #3498db; text-decoration: none; padding: 5px 10px; }
  .nav a:hover { text-decoration: underline; }
  .loading { display: none; text-align: center; padding: 20px; color: #7f8c8d; }
</style></head><body>
<div class="container">
  <h1>SuperOffer</h1>
  <div class="nav"><a href="/">Buscar</a><a href="/results">Resultados</a><a href="/stores">Tiendas</a></div>
  <div class="card">
    <form id="searchForm">
      <label><strong>Productos</strong> (uno por linea)</label>
      <textarea id="products" rows="5" placeholder="Leche entera&#10;Arroz grado 2&#10;Aceite maravilla"></textarea>
      <label><strong>Tiendas</strong></label>
      <select id="stores" multiple size="4">
        <option value="jumbo" selected>Jumbo</option>
        <option value="lider" selected>Lider</option>
        <option value="tottus" selected>Tottus</option>
        <option value="falabella" selected>Falabella</option>
      </select>
      <button type="submit">Buscar Ofertas</button>
    </form>
    <div class="loading" id="loading">Buscando ofertas...</div>
  </div>
  <div id="results"></div>
</div>
<script>
document.getElementById('searchForm').onsubmit = async function(e) {
  e.preventDefault();
  const products = document.getElementById('products').value.split('\\n').filter(Boolean);
  const stores = Array.from(document.getElementById('stores').selectedOptions).map(o => o.value);
  if (!products.length) return;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('results').innerHTML = '';
  const res = await fetch('/api/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ products, stores })
  });
  const data = await res.json();
  document.getElementById('loading').style.display = 'none';
  let html = '<div class="card"><h2>Resultados</h2>';
  for (const [prod, offers] of Object.entries(data.results || {})) {
    html += '<li><h3>' + prod + ' <span class="store-badge">' + offers.total_ofertas + ' ofertas</span></h3>';
    for (const o of (offers.mejores_opciones || [])) {
      const badge = o.super_oferta ? '<span class="super-badge">SUPER</span>' : '';
      html += '<div class="offer"><span>' + o.tienda + ' - ' + o.producto.slice(0,40) + ' ' + badge + '</span><span class="price">$' + o.precio.toLocaleString('es-CL') + '</span></div>';
    }
    html += '</li>';
  }
  html += '</div>';
  document.getElementById('results').innerHTML = html;
};
</script></body></html>"""


@app.route("/")
def index():
    return INDEX_HTML


@app.route("/api/search", methods=["POST"])
def api_search():
    global _engine
    body = request.get_json()
    products_text = body.get("products", [])
    stores = body.get("stores")
    if isinstance(products_text, list):
        product_list = [{"name": p.strip()} for p in products_text if p.strip()]
    else:
        product_list = [{"name": products_text}]
    if not product_list:
        return jsonify({"error": "No products specified"}), 400
    engine = _engine or OfferEngine(
        stores=stores,
        max_workers=4,
        csv_output=False,
        webhook_url=None,
    )
    results: dict = {}
    total_offers = 0
    for prod in product_list:
        name = prod["name"]
        offers = engine.search_product(name, prod.get("brand", ""))
        if offers:
            results[name] = {}
            all_offers = []
            for sk, offs in offers.items():
                results[name][sk] = offs
                all_offers.extend(offs)
            all_offers.sort(key=lambda o: o.price)
            top = all_offers[:10]
            results[name] = {
                "total_ofertas": len(all_offers),
                "superofertas": sum(1 for o in all_offers if o.es_super_oferta()),
                "mejores_opciones": [
                    {"producto": o.name, "tienda": o.store, "precio": o.price,
                     "original": o.original_price, "descuento": o.discount_percentage,
                     "super_oferta": o.es_super_oferta(), "url": o.url}
                    for o in top
                ],
            }
            total_offers += len(all_offers)
    return jsonify({
        "total_productos": len(product_list),
        "total_ofertas": total_offers,
        "results": results,
    })


@app.route("/results")
def list_results():
    if not os.path.isdir(OUTPUT_DIR):
        return "<p>No hay resultados aun.</p>"
    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".json")], reverse=True)[:20]
    html = '<h2>Resultados Recientes</h2><ul>'
    for f in files:
        html += f'<li><a href="/view/{f}">{f}</a></li>'
    html += '</ul>'
    return html


@app.route("/view/<filename>")
def view_result(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return "<p>Archivo no encontrado</p>", 404
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    html = '<h2>' + filename + '</h2>'
    meta = data.get("metadata", {})
    html += f'<p>{meta.get("total_productos")} productos, {meta.get("total_ofertas")} ofertas, {meta.get("superofertas_detectadas")} superofertas</p>'
    for prod, info in data.get("resultados", {}).items():
        html += f'<li><h3>{prod}</h3>'
        for o in info.get("mejores_opciones", []):
            badge = ' <span class="super-badge">SUPER</span>' if o.get("super_oferta") else ""
            html += f'<div>{o["tienda"]} - ${o["precio"]:,.0f}{badge}</div>'
        html += '</li>'
    return html


@app.route("/stores")
def list_stores():
    html = '<h2>Tiendas Disponibles</h2><ul>'
    for key, cls in SCRAPER_MAP.items():
        inst = cls()
        html += f'<li><strong>{inst.config.name}</strong> ({key})</li>'
    html += '</ul>'
    return html


def run_webui(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    print(f"  [OK] SuperOffer Web UI: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
