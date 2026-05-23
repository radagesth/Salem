import io
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, jsonify, request, render_template_string, send_from_directory, Response

from superoffer.engine import OfferEngine, SCRAPER_MAP
from superoffer.input import read_products
from superoffer.utils.config import OUTPUT_DIR, STORE_CONFIGS
from superoffer.utils.config_loader import load_yaml_config, find_config
from superoffer.utils.price_history_db import get_history as get_price_history, export_to_json
from superoffer.utils.dotenv import load_dotenv
from superoffer.utils.messages import is_quiet

app = Flask(__name__)
_engine: Optional[OfferEngine] = None
_config: dict = {}
_log_buffer: List[dict] = []
_query_history: List[dict] = []
HISTORY_FILE = os.path.join(OUTPUT_DIR, "query_history.json")

_log_handler = logging.StreamHandler(io.StringIO())
_log_handler.setLevel(logging.INFO)


class BufferHandler(logging.Handler):
    def emit(self, record):
        _log_buffer.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "level": record.levelname,
            "message": self.format(record),
        })
        if len(_log_buffer) > 500:
            _log_buffer[:50] = []


logging.getLogger("superoffer").addHandler(BufferHandler())


def _load_history():
    global _query_history
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                _query_history = json.load(f)
        except (json.JSONDecodeError, OSError):
            _query_history = []


def _save_history():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(_query_history[-200:], f, ensure_ascii=False, indent=2)
    except OSError:
        pass


_load_history()

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SuperOffer Dashboard</title>
<style>
  :root { --bg: #0f1419; --card: #1a1f2e; --accent: #3498db; --success: #27ae60; --danger: #e74c3c; --warn: #f39c12; --text: #e1e8ed; --muted: #6b7280; --border: #2d3548; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); display: flex; min-height: 100vh; }
  .sidebar { width: 220px; background: var(--card); padding: 20px 0; border-right: 1px solid var(--border); flex-shrink: 0; }
  .sidebar h1 { font-size: 18px; padding: 0 20px; margin-bottom: 25px; color: #fff; }
  .sidebar h1 span { color: var(--accent); }
  .sidebar a { display: flex; align-items: center; gap: 10px; padding: 10px 20px; color: var(--muted); text-decoration: none; font-size: 14px; border-left: 3px solid transparent; transition: all 0.2s; }
  .sidebar a:hover, .sidebar a.active { color: var(--text); background: rgba(52,152,219,0.08); border-left-color: var(--accent); }
  .sidebar a .icon { width: 18px; text-align: center; }
  .main { flex: 1; padding: 25px; overflow-y: auto; max-height: 100vh; }
  .tab { display: none; }
  .tab.active { display: block; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 15px; margin-bottom: 25px; }
  .stat-card { background: var(--card); border-radius: 10px; padding: 18px; border: 1px solid var(--border); }
  .stat-card .num { font-size: 28px; font-weight: 700; }
  .stat-card .label { font-size: 12px; color: var(--muted); margin-top: 4px; }
  .stat-card .num.green { color: var(--success); }
  .stat-card .num.blue { color: var(--accent); }
  .stat-card .num.red { color: var(--danger); }
  .stat-card .num.yellow { color: var(--warn); }
  .card { background: var(--card); border-radius: 10px; padding: 20px; margin-bottom: 15px; border: 1px solid var(--border); }
  .card h2 { font-size: 16px; margin-bottom: 15px; color: #fff; }
  .card h3 { font-size: 14px; margin-bottom: 10px; color: var(--text); }
  textarea, select, input { width: 100%; padding: 10px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: var(--text); font-size: 14px; margin-bottom: 12px; font-family: inherit; }
  textarea:focus, select:focus, input:focus { outline: none; border-color: var(--accent); }
  select[multiple] { height: 140px; }
  select[multiple] option { padding: 6px 8px; }
  select[multiple] option:checked { background: var(--accent); }
  .btn { background: var(--accent); color: #fff; border: none; padding: 10px 22px; border-radius: 6px; font-size: 14px; cursor: pointer; transition: opacity 0.2s; }
  .btn:hover { opacity: 0.85; }
  .btn-sm { padding: 5px 12px; font-size: 12px; }
  .btn-danger { background: var(--danger); }
  .btn-success { background: var(--success); }
  .search-params { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .search-params label { font-size: 12px; color: var(--muted); display: block; margin-bottom: 4px; }
  .offer { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 14px; }
  .offer:last-child { border: none; }
  .offer .store { color: var(--muted); font-size: 12px; }
  .offer .price { font-weight: 600; color: var(--success); }
  .super-badge { background: var(--danger); color: #fff; padding: 1px 7px; border-radius: 3px; font-size: 10px; font-weight: 600; margin-left: 6px; }
  .log-entry { padding: 4px 0; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; border-bottom: 1px solid var(--border); }
  .log-entry .time { color: var(--muted); margin-right: 8px; }
  .log-entry.INFO { color: var(--text); }
  .log-entry.WARN { color: var(--warn); }
  .log-entry.ERROR { color: var(--danger); }
  .log-entry.DEBUG { color: var(--muted); }
  .logs-box { background: #0a0e14; border-radius: 8px; padding: 12px; max-height: 500px; overflow-y: auto; font-size: 13px; line-height: 1.5; }
  .history-item { padding: 12px; border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.2s; }
  .history-item:hover { background: rgba(52,152,219,0.05); }
  .history-item .h-date { color: var(--muted); font-size: 12px; }
  .history-item .h-prods { color: var(--text); font-size: 14px; }
  .history-item .h-meta { font-size: 12px; color: var(--muted); margin-top: 4px; }
  .history-item .h-meta span { margin-right: 15px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 500; }
  .badge-green { background: rgba(39,174,96,0.15); color: var(--success); }
  .badge-red { background: rgba(231,76,60,0.15); color: var(--danger); }
  .badge-blue { background: rgba(52,152,219,0.15); color: var(--accent); }
  .config-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
  .config-item { padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
  .config-item .k { color: var(--muted); }
  .config-item .v { color: var(--text); font-family: monospace; }
  .store-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
  .store-card { background: var(--bg); border-radius: 8px; padding: 12px; border: 1px solid var(--border); }
  .store-card .s-name { font-weight: 600; font-size: 14px; }
  .store-card .s-key { color: var(--muted); font-size: 11px; }
  .store-card .s-url { color: var(--accent); font-size: 11px; word-break: break-all; }
  .result-section { margin-top: 15px; }
  .result-section h3 { margin-bottom: 10px; }
  .result-section .count { font-size: 12px; color: var(--muted); font-weight: 400; }
  .loading { display: none; text-align: center; padding: 30px; }
  .spinner { display: inline-block; width: 30px; height: 30px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .empty { text-align: center; padding: 40px; color: var(--muted); }
  .resumen-strip { display: flex; gap: 20px; padding: 10px 0; font-size: 13px; color: var(--muted); }
  .resumen-strip span { display: flex; align-items: center; gap: 5px; }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  @media (max-width: 768px) { .sidebar { width: 60px; } .sidebar h1, .sidebar a span { display: none; } .main { padding: 15px; } .config-grid, .search-params { grid-template-columns: 1fr; } }
</style>
</head>
<body>

<nav class="sidebar">
  <h1>Super<span>Offer</span></h1>
  <a href="#" class="active" data-tab="dashboard"><span class="icon">&#9632;</span><span>Dashboard</span></a>
  <a href="#" data-tab="search"><span class="icon">&#9740;</span><span>Buscar</span></a>
  <a href="#" data-tab="history"><span class="icon">&#8986;</span><span>Historial</span></a>
  <a href="#" data-tab="logs"><span class="icon">&#9776;</span><span>Logs</span></a>
  <a href="#" data-tab="config"><span class="icon">&#9881;</span><span>Configuracion</span></a>
  <a href="#" data-tab="stores"><span class="icon">&#9733;</span><span>Tiendas</span></a>
</nav>

<div class="main">

<!-- DASHBOARD -->
<div id="tab-dashboard" class="tab active">
  <div class="stats" id="dash-stats">
    <div class="stat-card"><div class="num blue" id="stat-queries">0</div><div class="label">Consultas realizadas</div></div>
    <div class="stat-card"><div class="num green" id="stat-offers">0</div><div class="label">Ofertas encontradas</div></div>
    <div class="stat-card"><div class="num red" id="stat-super">0</div><div class="label">Super ofertas</div></div>
    <div class="stat-card"><div class="num yellow" id="stat-products">0</div><div class="label">Productos buscados</div></div>
  </div>
  <div class="card">
    <h2>Ultimas consultas</h2>
    <div id="dash-recent"></div>
  </div>
</div>

<!-- SEARCH -->
<div id="tab-search" class="tab">
  <div class="card">
    <h2>Buscar ofertas</h2>
    <form id="searchForm">
      <div class="search-params">
        <div>
          <label>Productos (uno por linea)</label>
          <textarea id="products" rows="5" placeholder="Leche entera&#10;Arroz grado 2&#10;Aceite maravilla"></textarea>
        </div>
        <div>
          <label>Tiendas (Ctrl+click para multiple)</label>
          <select id="stores" multiple size="5"></select>
          <div style="display:flex;gap:8px;margin-top:8px">
            <button type="button" class="btn btn-sm" onclick="selectAllStores(true)">Todo</button>
            <button type="button" class="btn btn-sm btn-danger" onclick="selectAllStores(false)">Ninguno</button>
          </div>
        </div>
      </div>
      <label>Ubicacion</label>
      <input type="text" id="location" placeholder="Providencia, Las Condes..." style="width:250px">
      <div style="margin-top:12px">
        <button type="submit" class="btn">Buscar</button>
        <span style="margin-left:10px;color:var(--muted);font-size:12px">o sube un archivo</span>
        <input type="file" id="fileInput" accept=".xlsx,.xls,.csv" style="display:inline-block;width:auto;margin-left:8px">
      </div>
    </form>
    <div class="loading" id="loading"><div class="spinner"></div><p style="margin-top:10px">Buscando ofertas...</p></div>
  </div>
  <div id="search-results"></div>
</div>

<!-- HISTORY -->
<div id="tab-history" class="tab">
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h2>Historial de consultas</h2>
      <button class="btn btn-sm btn-danger" onclick="clearHistory()">Limpiar</button>
    </div>
    <div id="history-list"></div>
  </div>
</div>

<!-- LOGS -->
<div id="tab-logs" class="tab">
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h2>Logs en vivo</h2>
      <button class="btn btn-sm" onclick="document.getElementById('log-container').innerHTML=''">Limpiar</button>
    </div>
    <div class="logs-box" id="log-container"></div>
  </div>
</div>

<!-- CONFIG -->
<div id="tab-config" class="tab">
  <div class="card"><h2>Configuracion activa</h2><div class="config-grid" id="config-grid"></div></div>
  <div class="card"><h2>Variables de entorno</h2><div class="config-grid" id="env-grid"></div></div>
  <div class="card"><h2>superoffer.yml</h2><pre id="yaml-view" style="background:#0a0e14;padding:12px;border-radius:6px;overflow-x:auto;font-size:13px"></pre></div>
</div>

<!-- STORES -->
<div id="tab-stores" class="tab">
  <div class="card"><h2>Tiendas disponibles (15)</h2><div class="store-list" id="store-list"></div></div>
</div>

</div>

<script>
// --- TABS ---
document.querySelectorAll('.sidebar a').forEach(a => {
  a.addEventListener('click', function(e) {
    e.preventDefault();
    document.querySelectorAll('.sidebar a').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    this.classList.add('active');
    document.getElementById('tab-' + this.dataset.tab).classList.add('active');
    if (this.dataset.tab === 'dashboard') refreshDashboard();
    if (this.dataset.tab === 'history') renderHistory();
    if (this.dataset.tab === 'logs') renderLogs();
    if (this.dataset.tab === 'config') loadConfig();
    if (this.dataset.tab === 'stores') loadStores();
  });
});

// --- STORES SELECT ---
async function loadStoreOptions() {
  const r = await fetch('/api/stores');
  const data = await r.json();
  const sel = document.getElementById('stores');
  sel.innerHTML = data.stores.map(s => `<option value="${s.key}" selected>${s.name}</option>`).join('');
}
function selectAllStores(v) {
  const sel = document.getElementById('stores');
  Array.from(sel.options).forEach(o => o.selected = v);
}
loadStoreOptions();

// --- SEARCH ---
document.getElementById('searchForm').onsubmit = async function(e) {
  e.preventDefault();
  const products = document.getElementById('products').value.split('\n').filter(Boolean);
  const stores = Array.from(document.getElementById('stores').selectedOptions).map(o => o.value);
  const location = document.getElementById('location').value.trim();
  if (!products.length) return;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('search-results').innerHTML = '';
  const res = await fetch('/api/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ products, stores, location })
  });
  const data = await res.json();
  document.getElementById('loading').style.display = 'none';
  let html = '';
  if (data.error) { html = '<div class="card"><p style="color:var(--danger)">' + data.error + '</p></div>'; }
  else {
    const totalO = data.total_ofertas || 0;
    const totalP = data.total_productos || 0;
    html = '<div class="card"><h2>Resultados</h2><div class="resumen-strip">'
      + '<span>' + totalP + ' productos</span><span>' + totalO + ' ofertas</span>'
      + '<span>' + (data.superofertas || 0) + ' superofertas</span>'
      + '</div></div>';
    for (const [prod, info] of Object.entries(data.results || {})) {
      html += '<div class="result-section card"><h3>' + prod + ' <span class="count">' + info.total_ofertas + ' ofertas · ' + info.superofertas + ' super</span></h3>';
      for (const o of (info.mejores_opciones || [])) {
        const badge = o.super_oferta ? '<span class="super-badge">SUPER</span>' : '';
        const disc = o.descuento ? ' <span style="color:var(--success)">(-' + o.descuento + '%)</span>' : '';
        html += '<div class="offer">'
          + '<span><span class="store">' + o.tienda + '</span> ' + o.producto.slice(0,60) + badge + disc + '</span>'
          + '<span class="price">$' + o.precio.toLocaleString('es-CL') + '</span>'
          + '</div>';
      }
      html += '</div>';
    }
  }
  document.getElementById('search-results').innerHTML = html;
  refreshDashboard();
};

// --- FILE UPLOAD ---
document.getElementById('fileInput').addEventListener('change', async function() {
  const file = this.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  document.getElementById('loading').style.display = 'block';
  document.getElementById('search-results').innerHTML = '';
  const res = await fetch('/api/search_file', { method: 'POST', body: formData });
  const data = await res.json();
  document.getElementById('loading').style.display = 'none';
  let html = '';
  const totalO = data.total_ofertas || 0;
  html = '<div class="card"><h2>Resultados: ' + file.name + '</h2><div class="resumen-strip">'
    + '<span>' + (data.total_productos || 0) + ' productos</span><span>' + totalO + ' ofertas</span>'
    + '</div></div>';
  for (const [prod, info] of Object.entries(data.results || {})) {
    html += '<div class="result-section card"><h3>' + prod + ' <span class="count">' + info.total_ofertas + ' ofertas</span></h3>';
    for (const o of (info.mejores_opciones || [])) {
      const badge = o.super_oferta ? '<span class="super-badge">SUPER</span>' : '';
      html += '<div class="offer"><span><span class="store">' + o.tienda + '</span> ' + o.producto.slice(0,60) + badge + '</span><span class="price">$' + o.precio.toLocaleString('es-CL') + '</span></div>';
    }
    html += '</div>';
  }
  document.getElementById('search-results').innerHTML = html;
  refreshDashboard();
});

// --- DASHBOARD ---
async function refreshDashboard() {
  const r = await fetch('/api/stats');
  const s = await r.json();
  document.getElementById('stat-queries').textContent = s.total_queries;
  document.getElementById('stat-offers').textContent = s.total_ofertas;
  document.getElementById('stat-super').textContent = s.total_super;
  document.getElementById('stat-products').textContent = s.total_productos;
  // recent
  const hr = await fetch('/api/history?limit=5');
  const h = await hr.json();
  let html = '';
  if (!h.length) { html = '<div class="empty">Aun no hay consultas.</div>'; }
  else {
    for (const q of h) {
      html += '<div class="history-item" onclick="viewHistory(\'' + q.id + '\')">'
        + '<div class="h-date">' + q.fecha + '</div>'
        + '<div class="h-prods">' + q.productos.slice(0,80) + '</div>'
        + '<div class="h-meta">'
        + '<span class="badge badge-blue">' + (q.total_productos || q.productos.split(',').length) + ' prod.</span>'
        + '<span class="badge badge-green">' + q.total_ofertas + ' of.</span>'
        + '<span class="badge badge-red">' + q.superofertas + ' super</span>'
        + ' <span style="color:var(--muted)">' + q.tiendas + '</span>'
        + '</div></div>';
    }
  }
  document.getElementById('dash-recent').innerHTML = html;
}

// --- HISTORY ---
async function renderHistory() {
  const r = await fetch('/api/history?limit=200');
  const h = await r.json();
  let html = '';
  if (!h.length) { html = '<div class="empty">No hay historial de consultas.</div>'; }
  else {
    for (const q of h) {
      const prods = q.productos || '';
      html += '<div class="history-item" onclick="viewHistory(\'' + q.id + '\')">'
        + '<div class="h-date">' + q.fecha + '</div>'
        + '<div class="h-prods">' + prods.slice(0,120) + '</div>'
        + '<div class="h-meta">'
        + '<span class="badge badge-blue">' + (q.total_productos || prods.split(',').length) + ' prod.</span>'
        + '<span class="badge badge-green">' + q.total_ofertas + ' of.</span>'
        + '<span class="badge badge-red">' + q.superofertas + ' super</span>'
        + ' <span style="color:var(--muted)">' + q.tiendas + '</span>'
        + '</div></div>';
    }
  }
  document.getElementById('history-list').innerHTML = html;
}

async function viewHistory(qid) {
  const r = await fetch('/api/history/' + qid);
  const q = await r.json();
  if (!q) return;
  let html = '<div class="card"><h2>Consulta: ' + q.fecha + '</h2>'
    + '<div class="resumen-strip"><span>' + (q.total_productos || q.productos.split(',').length) + ' productos</span>'
    + '<span>' + q.total_ofertas + ' ofertas</span>'
    + '<span>' + q.superofertas + ' superofertas</span>'
    + '<span>' + q.tiendas + '</span></div></div>';
  for (const [prod, info] of Object.entries(q.resultados || {})) {
    html += '<div class="result-section card"><h3>' + prod + ' <span class="count">' + info.total_ofertas + ' ofertas</span></h3>';
    for (const o of (info.mejores_opciones || [])) {
      const badge = o.super_oferta ? '<span class="super-badge">SUPER</span>' : '';
      html += '<div class="offer"><span><span class="store">' + o.tienda + '</span> ' + o.producto.slice(0,60) + badge + '</span><span class="price">$' + o.precio.toLocaleString('es-CL') + '</span></div>';
    }
    html += '</div>';
  }
  document.getElementById('tab-history').innerHTML = '<div class="card"><p><a href="#" onclick="location.reload()" style="color:var(--accent)">&larr; Volver al historial</a></p></div>' + html;
}

async function clearHistory() {
  await fetch('/api/history', { method: 'DELETE' });
  renderHistory();
}

// --- LOGS ---
let logPollInterval;
function startLogPoll() {
  if (logPollInterval) clearInterval(logPollInterval);
  logPollInterval = setInterval(renderLogs, 1500);
}
function stopLogPoll() { if (logPollInterval) { clearInterval(logPollInterval); logPollInterval = null; } }

async function renderLogs() {
  const r = await fetch('/api/logs');
  const logs = await r.json();
  const container = document.getElementById('log-container');
  if (!logs.length) { container.innerHTML = '<div class="empty">Esperando logs...</div>'; return; }
  container.innerHTML = logs.slice(-100).map(l =>
    '<div class="log-entry ' + l.level + '"><span class="time">' + l.time + '</span>[' + l.level + '] ' + l.message + '</div>'
  ).join('');
  container.scrollTop = container.scrollHeight;
}

// Watch tab visibility for log polling
document.querySelectorAll('.sidebar a').forEach(a => {
  a.addEventListener('click', function() {
    if (this.dataset.tab === 'logs') startLogPoll();
    else stopLogPoll();
  });
});

// --- CONFIG ---
async function loadConfig() {
  const r = await fetch('/api/config');
  const c = await r.json();
  let html = '';
  for (const [k, v] of Object.entries(c.config || {})) {
    html += '<div class="config-item"><span class="k">' + k + '</span><br><span class="v">' + JSON.stringify(v) + '</span></div>';
  }
  document.getElementById('config-grid').innerHTML = html || '<div class="empty">Sin configuracion YAML</div>';
  html = '';
  for (const [k, v] of Object.entries(c.env || {})) {
    const val = k.includes('TOKEN') || k.includes('COOKIE') || k.includes('SECRET') ? '****' : v;
    html += '<div class="config-item"><span class="k">' + k + '</span><br><span class="v">' + (val || '<span style="color:var(--muted)">(vacio)</span>') + '</span></div>';
  }
  document.getElementById('env-grid').innerHTML = html || '<div class="empty">Sin variables de entorno</div>';
  document.getElementById('yaml-view').textContent = c.yaml || '(no encontrado)';
}

// --- STORES ---
async function loadStores() {
  const r = await fetch('/api/stores');
  const data = await r.json();
  let html = '';
  for (const s of data.stores) {
    html += '<div class="store-card"><div class="s-name">' + s.name + '</div><div class="s-key">' + s.key + '</div><div class="s-url">' + s.url + '</div></div>';
  }
  document.getElementById('store-list').innerHTML = html;
}

// --- INIT ---
refreshDashboard();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return DASHBOARD_HTML


@app.route("/api/search", methods=["POST"])
def api_search():
    global _engine
    body = request.get_json()
    products_text = body.get("products", [])
    stores = body.get("stores")
    location = body.get("location", "")
    if isinstance(products_text, list):
        product_list = [{"name": p.strip()} for p in products_text if p.strip()]
    else:
        product_list = [{"name": products_text}]
    if not product_list:
        return jsonify({"error": "No se especificaron productos"}), 400
    if location:
        from superoffer.utils.config import STORE_CONFIGS
        loc = location.lower().replace(" ", "_")
        for cfg in STORE_CONFIGS.values():
            if cfg.location_id:
                cfg.headers["x-location-id"] = loc
    engine = _engine or OfferEngine(
        stores=stores, max_workers=4, csv_output=False, webhook_url=None,
    )
    results: dict = {}
    total_offers = 0
    super_offers = 0
    for prod in product_list:
        name = prod["name"]
        offers = engine.search_product(name, prod.get("brand", ""))
        if offers:
            all_offers = []
            for sk, offs in offers.items():
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
            super_offers += sum(1 for o in all_offers if o.es_super_oferta())
    _save_query({
        "productos": ", ".join(p["name"] for p in product_list),
        "tiendas": ", ".join(stores) if stores else "todas",
        "total_productos": len(product_list),
        "total_ofertas": total_offers,
        "superofertas": super_offers,
        "resultados": results,
    })
    return jsonify({
        "total_productos": len(product_list),
        "total_ofertas": total_offers,
        "superofertas": super_offers,
        "results": results,
    })


@app.route("/api/search_file", methods=["POST"])
def api_search_file():
    global _engine
    if "file" not in request.files:
        return jsonify({"error": "No se envio archivo"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Archivo vacio"}), 400
    tmp_path = os.path.join(OUTPUT_DIR, "_web_upload_" + file.filename)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file.save(tmp_path)
    engine = _engine or OfferEngine(stores=None, max_workers=4, csv_output=False, webhook_url=None)
    products = read_products(tmp_path)
    results: dict = {}
    total_offers = 0
    super_offers = 0
    for prod in products:
        name = prod.get("name", "")
        brand = prod.get("brand", "")
        offers = engine.search_product(name, brand)
        if offers:
            all_offers = []
            for sk, offs in offers.items():
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
            super_offers += sum(1 for o in all_offers if o.es_super_oferta())
    try:
        os.remove(tmp_path)
    except OSError:
        pass
    _save_query({
        "productos": ", ".join(p.get("name", "") for p in products),
        "tiendas": "archivo: " + file.filename,
        "total_productos": len(products),
        "total_ofertas": total_offers,
        "superofertas": super_offers,
        "resultados": results,
    })
    return jsonify({
        "total_productos": len(products),
        "total_ofertas": total_offers,
        "superofertas": super_offers,
        "results": results,
    })


@app.route("/api/stats")
def api_stats():
    return jsonify({
        "total_queries": len(_query_history),
        "total_ofertas": sum(q.get("total_ofertas", 0) for q in _query_history),
        "total_super": sum(q.get("superofertas", 0) for q in _query_history),
        "total_productos": sum(q.get("total_productos", 0) for q in _query_history),
    })


@app.route("/api/stores")
def api_stores():
    stores = []
    for key, cls in SCRAPER_MAP.items():
        inst = cls()
        stores.append({"key": key, "name": inst.config.name, "url": inst.config.base_url})
    return jsonify({"stores": stores})


@app.route("/api/logs")
def api_logs():
    return jsonify(_log_buffer[-200:])


@app.route("/api/config")
def api_config():
    global _config
    env_vars = {k: v for k, v in os.environ.items()
                if any(x in k.upper() for x in ["FACEBOOK", "WEBHOOK", "LOCATION", "TELEGRAM", "WHATSAPP", "SUPEROFFER"])}
    yaml_path = find_config()
    yaml_content = ""
    if yaml_path:
        try:
            with open(yaml_path, encoding="utf-8") as f:
                yaml_content = f.read()
        except OSError:
            pass
    config_display = {}
    if _config:
        for k, v in _config.items():
            if isinstance(v, (str, int, float, bool, list)):
                config_display[k] = v
            elif isinstance(v, dict):
                for sk, sv in v.items():
                    if isinstance(sv, (str, int, float, bool, list)):
                        config_display[f"{k}.{sk}"] = sv
    return jsonify({"config": config_display, "env": env_vars, "yaml": yaml_content})


@app.route("/api/history", methods=["GET", "DELETE"])
def api_history():
    if request.method == "DELETE":
        _query_history.clear()
        _save_history()
        return jsonify({"ok": True})
    limit = request.args.get("limit", 200, type=int)
    return jsonify(_query_history[-limit:])


@app.route("/api/history/<int:qid>")
def api_history_detail(qid):
    for q in _query_history:
        if q.get("id") == qid:
            return jsonify(q)
    return jsonify(None), 404


def _save_query(data: dict):
    qid = int(time.time() * 1000)
    entry = {
        "id": qid,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "productos": data.get("productos", ""),
        "tiendas": data.get("tiendas", ""),
        "total_productos": data.get("total_productos", 0),
        "total_ofertas": data.get("total_ofertas", 0),
        "superofertas": data.get("superofertas", 0),
        "resultados": data.get("resultados", {}),
    }
    _query_history.append(entry)
    _save_history()


def run_webui(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    global _config
    _config = load_yaml_config()
    load_dotenv()
    print(f"  [OK] SuperOffer Dashboard: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)
