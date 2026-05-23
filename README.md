# SuperOffer

Localizador de ofertas en supermercados chilenos desde la terminal.

Acepta un archivo Excel o CSV con productos, busca en **15 tiendas online** y genera un JSON con las 10 mejores ofertas ordenadas por precio.

## Instalacion

```bash
pip install -r requirements.txt
```

## Uso basico

```bash
python main.py lista_productos.xlsx
python main.py lista_productos.csv
python main.py lista.xlsx -o resultados.json
```

## Formato del archivo de entrada

**Excel (.xlsx/.xls):** Columna `Producto` (o `Nombre`, `Item`, etc.) con los items a buscar.
Opcional: `Marca`, `Cantidad`, `Categoria`.

**CSV (.csv):** Mismas columnas. Separado por comas, UTF-8.

Ejemplo:

| Producto | Marca | Cantidad |
|----------|-------|----------|
| Leche entera | Colun | 1L |
| Arroz grado 2 | | 1kg |

## Opciones

| Flag | Descripcion |
|------|-------------|
| `-o, --output ARCHIVO` | Ruta del JSON de salida |
| `-s, --stores TIENDA [TIENDA...]` | Tiendas a consultar |
| `-w, --workers N` | Busquedas simultaneas (default: 8) |
| `-l, --location COMUNA` | Filtrar por ubicacion (ej: Providencia) |
| `--csv` | Exportar tambien a CSV |
| `--webhook URL` | Notificar via webhook al finalizar |
| `-v, --verbose` | Modo detallado (debug) |
| `-q, --quiet` | Modo silencioso (solo errores) |
| `--list-stores` | Listar tiendas disponibles |

## Tiendas disponibles (15)

1. Jumbo, Lider, Santa Isabel, Tottus, Unimarc
2. Falabella, Ripley, Paris, MercadoLibre
3. Mayorista 10, SuperBodega, Acuenta
4. Homecenter, SoloTodo
5. Facebook Marketplace

## Super ofertas

Los productos con descuento >= 30% se marcan como `super_oferta: true`
y su imagen se descarga automaticamente a `output/imagenes/`.

## Variables de entorno

Copia `.env.example` a `.env` y completa:

```env
FACEBOOK_COOKIE=c_user=123; xs=abc...   # Cookie de sesion de Facebook
WEBHOOK_URL=https://hooks.slack.com/...  # Webhook de notificacion
LOCATION=Providencia                     # Ubicacion por defecto
```

## Webhook

Al finalizar la busqueda, se envia un POST JSON a la URL configurada:

```json
{
  "text": "SuperOffer: 5 productos, 47 ofertas, 3 superofertas",
  "results_file": "output/resultados_20260523_120000.json",
  "superofertas": 3,
  "total_productos": 5
}
```

## Salida

- **JSON**: `output/resultados_<timestamp>.json`
- **CSV** (opcional): `output/resultados_<timestamp>.csv`
- **Imagenes**: `output/imagenes/<tienda>_<producto>.jpg`

## Agregar una tienda

1. Agrega el `StoreConfig` en `superoffer/utils/config.py`
2. Si la API responde con estructura JSON estandar, el scraper generico en `base.py` la maneja automaticamente via `extract_items()` y `parse_item()`. Solo necesitas crear un archivo de 5 lineas como `scrapers/nueva.py`.
3. Si la API es especial (ej: Facebook), hereda de `SupermarketScraper` y sobrescribe `search()`.
4. Registra en `SCRAPER_MAP` en `engine.py` y en `STORE_CHOICES` en `main.py`.

## Tests

```bash
python -m pytest tests/ -v
```
