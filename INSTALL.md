# SuperOffer - Manual de Instalacion en Servidor

## Requisitos minimos

- **Python 3.10+** (probado en 3.10, 3.11, 3.12)
- **pip** actualizado
- **Git** (para clonar)
- **Conexion a Internet** (las APIs de las tiendas requieren salida HTTP/HTTPS)
- **Sistema operativo**: Linux (Ubuntu/Debian recomendado), Windows Server, o macOS

## Instalacion Rapida (Linux/Ubuntu)

```bash
# 1. Clonar repositorio
git clone https://github.com/radagesth/Salem.git
cd Salem

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# 4. (Opcional) Instalar Playwright para scraping con navegador
playwright install chromium

# 5. Configurar variables de entorno
cp .env.example .env
nano .env   # completar FACEBOOK_COOKIE, WEBHOOK_URL, etc.

# 6. Verificar instalacion
python main.py --list-stores
```

## Instalacion en Windows Server

```powershell
# 1. Clonar repositorio
git clone https://github.com/radagesth/Salem.git
cd Salem

# 2. Crear entorno virtual
python -m venv venv
.\venv\Scripts\Activate

# 3. Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# 4. (Opcional) Playwright
playwright install chromium

# 5. Configurar .env
copy .env.example .env
notepad .env

# 6. Verificar
python main.py --list-stores
```

## Instalacion con Docker

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir playwright && playwright install chromium
COPY . .
CMD ["python", "main.py"]
```

Construir y ejecutar:

```bash
docker build -t superoffer .
docker run --rm -v $(pwd)/.env:/app/.env superoffer python main.py lista.xlsx
```

## Archivo de configuracion (superoffer.yml)

Opcional. Ubicar en el mismo directorio que `main.py`. Ejemplo:

```yaml
stores:
  enabled: [jumbo, lider, tottus, falabella]
defaults:
  webhook: ""
  location: "Santiago"
  workers: 6
super_offer_threshold: 30.0
```

## Variables de entorno (.env)

| Variable | Obligatorio | Descripcion |
|----------|-------------|-------------|
| `FACEBOOK_COOKIE` | No (*) | Cookie de sesion para Facebook Marketplace |
| `WEBHOOK_URL` | No | URL para notificaciones POST |
| `LOCATION` | No | Comuna por defecto (ej: Providencia) |
| `TELEGRAM_TOKEN` | No | Token del bot de Telegram |
| `TELEGRAM_CHAT_ID` | No | Chat ID de Telegram |
| `WHATSAPP_TOKEN` | No | Token API de WhatsApp Cloud |
| `WHATSAPP_PHONE` | No | Numero destino WhatsApp |

(*) Facebook Marketplace requiere cookie valida.

## Modos de uso

### Busqueda normal (requiere archivo Excel/CSV)
```bash
python main.py lista_productos.xlsx
python main.py lista_productos.csv --csv --html
python main.py lista.xlsx --stores jumbo lider --scoring --excel
```

### Modo catalogo (sin archivo de entrada, escanea categorias)
```bash
python main.py --scan
python main.py --scan --stores jumbo tottus
```

### Interfaz Web
```bash
python main.py --web
# Abrir en navegador: http://127.0.0.1:5000
```

### Monitor de bajas de precio
```bash
python main.py lista.xlsx --monitor --monitor-threshold 15
```

### Proxy
```bash
python main.py lista.xlsx --proxies "http://proxy1:8080,http://proxy2:8080"
python main.py lista.xlsx --proxy-file proxies.txt
```

### Ubicacion y region
```bash
python main.py lista.xlsx --location Providencia
python main.py lista.xlsx --region cl
```

### Reportes adicionales
```bash
python main.py lista.xlsx --html              # Reporte HTML con graficos
python main.py lista.xlsx --excel             # Excel formateado con colores
python main.py lista.xlsx --csv               # CSV simple
```

## Programar ejecucion periodica (cron / tareas)

### Linux (crontab)
```cron
# Ejecutar cada dia a las 8:00
0 8 * * * cd /home/user/Salem && venv/bin/python main.py lista.xlsx --html --webhook 2>&1 | logger -t superoffer
```

### Windows (Task Scheduler)
```powershell
# Crear tarea programada
$action = New-ScheduledTaskAction -Execute "C:\Salem\venv\Scripts\python.exe" `
  -Argument "C:\Salem\main.py C:\Salem\lista.xlsx --html --csv"
$trigger = New-ScheduledTaskTrigger -Daily -At 08:00
Register-ScheduledTask -TaskName "SuperOffer" -Action $action -Trigger $trigger
```

## Actualizar

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## Solucion de problemas

### "No module named ..."
```bash
pip install -r requirements.txt
```

### "Playwright no instalado"
```bash
pip install playwright
playwright install chromium
```

### "Error de conexion con tienda"
- Verificar que el servidor tiene salida a internet
- Probar con `--verbose` para ver detalles
- Algunas tiendas bloquean IPs no chilenas (usar proxy)

### "Facebook Marketplace no retorna resultados"
- La cookie de sesion expira. Renovar desde el navegador:
  1. Iniciar sesion en facebook.com
  2. DevTools > Application > Cookies
  3. Copiar valor completo de "cookie" a `FACEBOOK_COOKIE` en `.env`

### "Database is locked" (SQLite)
Ocurre solo si ejecutas dos instancias simultaneas. Usa `--workers 1` o espera a que termine la otra ejecucion.

## Estructura de directorios

```
Salem/
  main.py                    # CLI principal
  requirements.txt           # Dependencias
  superoffer.yml             # Configuracion (opcional)
  .env                       # Variables de entorno (no se sube a git)
  .env.example               # Template de .env
  superoffer/
    engine.py                # Orquestador principal
    web_ui.py                # Interfaz web Flask
    scrapers/                # Scrapers individuales (15 tiendas)
    input/                   # Lectura de Excel/CSV
    output/                  # Writers (JSON, CSV, HTML, Excel)
    utils/                   # Utilidades (cache, proxy, sqlite, etc.)
    regions/                 # Configuraciones regionales
  tests/                     # Suite de pruebas
  output/                    # Resultados generados (gitignored)
    resultados_*.json
    resultados_*.csv
    resultados_*.xlsx
    reporte_*.html
    imagenes/
    price_history.db
```
