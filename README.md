<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/tiendas-15-success" alt="15 stores">
  <img src="https://img.shields.io/badge/tests-59%2F59-passing-brightgreen" alt="Tests">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License">
</p>

# SuperOffer 🛒

**Localizador de ofertas en supermercados chilenos desde la terminal, la web o tu scheduler.**

Acepta un archivo Excel o CSV con productos — o escanea categorías con `--scan` — busca en **15 tiendas online chilenas** y entrega un JSON con las 10 mejores ofertas ordenadas por precio, con detección automática de super ofertas (≥30% descuento), descarga de imágenes, reportes HTML con gráficos y notificaciones por Telegram/Discord/WhatsApp.

---

## ✨ Funcionalidades

| Característica | Descripción |
|----------------|-------------|
| **15 tiendas** | Jumbo, Lider, Santa Isabel, Tottus, Unimarc, Falabella, Ripley, Paris, MercadoLibre, Mayorista10, SuperBodega, Acuenta, Homecenter, SoloTodo, Facebook Marketplace |
| **Múltiples formatos de entrada** | Excel (`.xlsx/.xls`) y CSV con detección automática de columnas |
| **Múltiples formatos de salida** | JSON, CSV, Excel formateado (con colores), HTML con gráficos Chart.js |
| **Super ofertas** | Detección automática de descuentos ≥30%, descarga de imágenes |
| **Configuración vía YAML** | Archivo `superoffer.yml` para defaults, tiendas, umbrales, notificadores |
| **Variables de entorno** | `.env` para credenciales (Facebook, webhook, Telegram, WhatsApp) |
| **Historial SQLite** | Persistencia de precios en SQLite con consulta de mínimo histórico |
| **Proxy rotativo** | Soporte de proxies HTTP/SOCKS5 con rotación automática |
| **Cache en memoria** | TTL configurable (300s) para evitar re-fetch de APIs |
| **Retry + rate limiting** | Reintentos automáticos con backoff exponencial |
| **Paginación real** | Iteración de múltiples páginas de resultados (ej: Tottus, Lider) |
| **Timeout por tienda** | Timeout configurable individualmente |
| **Scoring inteligente** | Ranking que combina precio, descuento, reputación y disponibilidad |
| **i18n / Regiones** | Soporte multi-país (Chile, Argentina) con formato de moneda y comunas |
| **Geolocalización** | Coordenadas y distancia entre comunas vía haversine |
| **Modo catálogo (`--scan`)** | Escanea categorías completas sin archivo de entrada |
| **Monitor de bajas (`--monitor`)** | Detecta y reporta bajas de precio respecto a ejecuciones anteriores |
| **Notificaciones** | Webhook, Telegram, Discord (embeds con colores), WhatsApp Cloud API |
| **Interfaz Web** | Dashboard Flask con búsqueda interactiva y visualización de resultados |
| **Playwright backend** | Scraping headless con Chromium para tiendas con JavaScript pesado |
| **Auto-limpieza** | Rotación de archivos JSON antiguos e imágenes huérfanas |

---

## 🚀 Instalación rápida

```bash
git clone https://github.com/radagesth/Salem.git
cd Salem
pip install -r requirements.txt
playwright install chromium        # opcional
cp .env.example .env               # editar credenciales
python main.py --list-stores
```

### O con entorno virtual

```bash
python -m venv venv
source venv/bin/activate          # Linux/macOS
.\venv\Scripts\Activate           # Windows
pip install -r requirements.txt
```

---

## 📖 Uso

### Búsqueda básica

```bash
python main.py lista_productos.xlsx
python main.py lista_productos.csv
python main.py lista.xlsx -o resultados.json
```

### Reportes adicionales

```bash
python main.py lista.xlsx --html              # reporte HTML con Chart.js
python main.py lista.xlsx --excel             # Excel formateado (colores)
python main.py lista.xlsx --csv               # CSV plano
python main.py lista.xlsx --html --excel      # todos los formatos
```

### Filtrar tiendas y ubicación

```bash
python main.py lista.xlsx --stores jumbo lider tottus
python main.py lista.xlsx --location Providencia
python main.py lista.xlsx --location "Las Condes" --stores jumbo
```

### Scoring inteligente

```bash
python main.py lista.xlsx --scoring
```

### Modo catálogo (sin archivo de entrada)

```bash
python main.py --scan
python main.py --scan --stores jumbo lider tottus
```

### Monitorear bajas de precio

```bash
python main.py lista.xlsx --monitor
python main.py lista.xlsx --monitor --monitor-threshold 15
```

### Interfaz web

```bash
python main.py --web
# Abrir http://127.0.0.1:5000
```

### Proxy

```bash
python main.py lista.xlsx --proxies "http://proxy1:8080,http://proxy2:8080"
python main.py lista.xlsx --proxy-file proxies.txt
```

### Región / país

```bash
python main.py lista.xlsx --region cl         # Chile (default)
python main.py lista.xlsx --region ar         # Argentina
```

### Verbose / silencioso

```bash
python main.py lista.xlsx --verbose
python main.py lista.xlsx --quiet
```

---

## 🏪 Tiendas disponibles (15)

| # | Key | Nombre | URL |
|---|------|--------|-----|
| 1 | `jumbo` | Jumbo | jumbo.cl |
| 2 | `lider` | Lider | lider.cl |
| 3 | `santa_isabel` | Santa Isabel | santaisabel.cl |
| 4 | `tottus` | Tottus | tottus.cl |
| 5 | `unimarc` | Unimarc | unimarc.cl |
| 6 | `falabella` | Falabella | falabella.cl |
| 7 | `ripley` | Ripley | ripley.cl |
| 8 | `paris` | Paris | paris.cl |
| 9 | `mercadolibre` | MercadoLibre | mercadolibre.cl |
| 10 | `mayorista10` | Mayorista 10 | mayorista10.cl |
| 11 | `superbodega` | SuperBodega | superbodega.cl |
| 12 | `acuenta` | Acuenta | acuenta.cl |
| 13 | `homecenter` | Homecenter | homecenter.cl |
| 14 | `solotodo` | SoloTodo | solotodo.cl |
| 15 | `facebook_marketplace` | Facebook Marketplace | facebook.com |

---

## ⚙️ Configuración

### Archivo YAML (`superoffer.yml`)

```yaml
stores:
  enabled: [jumbo, lider, tottus, falabella]
defaults:
  webhook: "https://hooks.slack.com/..."
  location: "Santiago"
  workers: 6
super_offer_threshold: 30.0
notifiers:
  telegram: "123456789"           # chat_id
  discord: "https://discord.com/..."  # webhook URL
scoring:
  price_weight: 0.50
  discount_weight: 0.25
  reputation_weight: 0.15
monitor:
  enabled: true
  threshold: 10.0
```

### Variables de entorno (`.env`)

```env
FACEBOOK_COOKIE=c_user=123; xs=abc...
WEBHOOK_URL=https://hooks.slack.com/...
LOCATION=Providencia
TELEGRAM_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
WHATSAPP_TOKEN=EAAC...            # WhatsApp Cloud API
WHATSAPP_PHONE=56912345678
```

---

## 📁 Salidas

| Formato | Ruta | Contenido |
|---------|------|-----------|
| JSON | `output/resultados_<timestamp>.json` | Metadata + top 10 por producto con super ofertas e imágenes |
| CSV | `output/resultados_<timestamp>.csv` | Columnas: Producto, Tienda, Precio, Descuento, etc. |
| Excel | `output/resultados_<timestamp>.xlsx` | Con formato condicional y pestaña Resumen |
| HTML | `output/reporte_<timestamp>.html` | Dashboard con Chart.js, stats cards, tabla de ofertas |
| Imágenes | `output/imagenes/<tienda>_<producto>.jpg` | Descarga automática de imágenes de super ofertas |
| SQLite | `output/price_history.db` | Historial de precios persistente |

---

## 🧪 Tests

```bash
python tests/test_system.py
# 59/59 pruebas OK - SIN ERRORES
```

O con pytest:

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## 🏗️ Arquitectura

```
Salem/
  main.py                    # CLI (argparse + 20 flags)
  superoffer.yml             # Config YAML
  .env                       # Credenciales
  superoffer/
    engine.py                # Orquestador (OfferEngine)
    web_ui.py                # Interfaz web Flask
    scrapers/
      base.py                # Clase abstracta, cache, retry, proxy, paginación
      jumbo.py ...           # 14 scrapers genéricos (~5 líneas c/u)
      facebook_marketplace.py# Scraper custom con parsing HTML/JSON
      playwright_scraper.py  # Backend headless Chromium
    input/                   # Lectura Excel/CSV
    output/                  # JSON, CSV, HTML, Excel writers
    utils/                   # Cache, proxy, SQLite, scoring, regiones, etc.
    regions/                 # cl.json, ar.json
  tests/                     # Suite de pruebas
  output/                    # Resultados generados (gitignored)
```

### Flujo de datos

```
CLI → OfferEngine.run()
  → read_products() → Excel o CSV
  → Por cada producto:
      ThreadPoolExecutor → scrapers.search() → HTTP/Playwright
      → parse_item() → ProductOffer[]
      → save_entry() → SQLite
  → write_results() → JSON + CSV/HTML/Excel opcionales
  → cleanup() + webhook/notificaciones
```

---

## 🧩 Agregar una tienda nueva

1. Agrega `StoreConfig` en `superoffer/utils/config.py`
2. Si la API responde JSON estándar → crea un scraper de **5 líneas** que herede de `SupermarketScraper`
3. Si la API requiere JS → usa `PlaywrightScraper` o configura `use_playwright=True`
4. Registra en `SCRAPER_MAP` (engine.py) y `STORE_CHOICES` (main.py)

---

## 🤝 Contribuir

1. Fork el repo
2. Crea una rama (`git checkout -b feature/nueva-tienda`)
3. Commit (`git commit -m "Agrega scraper para ..."`)
4. Push (`git push origin feature/nueva-tienda`)
5. Abre un Pull Request

---

## 📄 Licencia

MIT
