# SuperOffer - Manual de Despliegue e Instalacion

## Requisitos minimos

- **Python 3.10+**
- **pip** actualizado
- **Git**
- **Conexion a Internet** (para APIs de tiendas)
- **Sistema**: Linux (Ubuntu/Debian recomendado), Windows Server, macOS

## Instalacion Rapida (Linux)

```bash
git clone https://github.com/radagesth/Salem.git
cd Salem
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium  # opcional
cp .env.example .env
nano .env   # configurar credenciales
python main.py --list-stores
```

## Instalacion en Windows Server

```powershell
git clone https://github.com/radagesth/Salem.git
cd Salem
python -m venv venv
.\venv\Scripts\Activate
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
copy .env.example .env
notepad .env
python main.py --list-stores
```

## Variables de entorno (.env)

| Variable | Descripcion |
|----------|-------------|
| `FACEBOOK_COOKIE` | Cookie de sesion Facebook Marketplace |
| `WEBHOOK_URL` | URL para notificaciones POST |
| `LOCATION` | Comuna por defecto (ej: Providencia) |
| `TELEGRAM_TOKEN` | Token bot de Telegram |
| `TELEGRAM_CHAT_ID` | Chat ID Telegram |
| `WHATSAPP_TOKEN` | Token API WhatsApp Cloud |

## Modos de uso

```bash
# Busqueda normal
python main.py lista.xlsx
python main.py lista.csv --csv --html --excel --scoring

# Modo catalogo (sin archivo)
python main.py --scan --stores jumbo lider

# Interfaz web
python main.py --web
# Abrir http://127.0.0.1:5000

# Monitor de bajas de precio
python main.py lista.xlsx --monitor --monitor-threshold 15

# Proxy
python main.py lista.xlsx --proxies "http://p1:8080,http://p2:8080"

# Reportes
python main.py lista.xlsx --html --excel --csv
```

## Programar ejecucion periodica

**Linux (cron):**
```cron
0 8 * * * cd /home/user/Salem && venv/bin/python main.py lista.xlsx --html --webhook
```

**Windows (Task Scheduler):**
```powershell
$action = New-ScheduledTaskAction -Execute "C:\Salem\venv\Scripts\python.exe" `
  -Argument "C:\Salem\main.py C:\Salem\lista.xlsx --html"
$trigger = New-ScheduledTaskTrigger -Daily -At 08:00
Register-ScheduledTask -TaskName "SuperOffer" -Action $action -Trigger $trigger
```

## Actualizar

```bash
git pull
source venv/bin/activate  # o .\venv\Scripts\Activate en Windows
pip install -r requirements.txt --upgrade
```

## Solucion de problemas

| Problema | Solucion |
|----------|----------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| Playwright no instalado | `pip install playwright && playwright install chromium` |
| Error de conexion | Verificar internet, probar `--verbose`, usar proxy |
| Facebook sin resultados | Cookie expirada: renovar desde DevTools > Application > Cookies |
| SQLite locked | No ejecutar dos instancias simultaneas |
