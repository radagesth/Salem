#!/usr/bin/env python3
"""
SuperOffer - Localizador de Ofertas en Supermercados
Uso: python main.py lista_productos.xlsx
"""
import sys
import os
import argparse

from superoffer.engine import OfferEngine
from superoffer.utils.messages import setup
from superoffer.utils.config_loader import load_yaml_config, apply_config_to_args
from superoffer.utils.proxy_manager import ProxyManager
from superoffer.utils.dotenv import load_dotenv


STORE_CHOICES = [
    "jumbo", "lider", "santa_isabel", "tottus", "unimarc",
    "falabella", "ripley", "paris", "mercadolibre",
    "mayorista10", "superbodega", "acuenta",
    "homecenter", "solotodo",
    "facebook_marketplace",
]


def main():
    parser = argparse.ArgumentParser(
        description="SuperOffer - Busca ofertas de productos en supermercados chilenos",
        epilog="Ejemplo: python main.py lista.xlsx --stores jumbo lider -o resultados.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input_file", nargs="?",
                        help="Archivo Excel/CSV con la lista de productos a buscar")
    parser.add_argument("--output", "-o", default=None,
                        help="Ruta del JSON de salida")
    parser.add_argument("--stores", "-s", nargs="+", default=None,
                        choices=STORE_CHOICES, metavar="TIENDA",
                        help=f"Tiendas (default: todas). Opciones: {', '.join(STORE_CHOICES)}")
    parser.add_argument("--workers", "-w", type=int, default=8, metavar="N",
                        help="Busquedas simultaneas (default: 8)")
    parser.add_argument("--location", "-l", default=None, metavar="COMUNA",
                        help="Comuna o ubicacion para filtrar resultados (ej: Providencia, Las Condes)")
    parser.add_argument("--csv", action="store_true",
                        help="Exportar tambien a CSV")
    parser.add_argument("--webhook", default=None, metavar="URL",
                        help="URL de webhook para notificar al finalizar")
    parser.add_argument("--list-stores", action="store_true",
                        help="Muestra tiendas disponibles y sale")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Modo verbose (muestra detalles de depuracion)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Modo silencioso (solo errores)")

    # === NEW FLAGS ===
    parser.add_argument("--html", action="store_true",
                        help="Generar reporte HTML con graficos de tendencias")
    parser.add_argument("--excel", action="store_true",
                        help="Exportar a Excel formateado (.xlsx)")
    parser.add_argument("--scoring", action="store_true",
                        help="Usar scoring inteligente para ranking de ofertas")
    parser.add_argument("--config", "-c", default=None, metavar="ARCHIVO",
                        help="Ruta a archivo de configuracion YAML (superoffer.yml)")
    parser.add_argument("--region", default=None, metavar="CODIGO",
                        help="Region/pais (cl, ar, etc.). Default: cl")
    parser.add_argument("--proxy-file", default=None, metavar="ARCHIVO",
                        help="Archivo con lista de proxies (uno por linea)")
    parser.add_argument("--proxies", default=None, metavar="PROXIES",
                        help="Lista de proxies separada por comas")
    parser.add_argument("--scan", action="store_true",
                        help="Modo catalogo: explorar categorias sin archivo de entrada")
    parser.add_argument("--monitor", action="store_true",
                        help="Modo monitor: detectar bajas de precio")
    parser.add_argument("--monitor-threshold", type=float, default=10.0, metavar="%",
                        help="Umbral %% de baja para monitor (default: 10%%)")
    parser.add_argument("--web", action="store_true",
                        help="Iniciar interfaz web (puerto 5000)")
    parser.add_argument("--web-host", default="127.0.0.1", metavar="HOST",
                        help="Host para interfaz web (default: 127.0.0.1)")
    parser.add_argument("--web-port", type=int, default=5000, metavar="PUERTO",
                        help="Puerto para interfaz web (default: 5000)")
    parser.add_argument("--super-offer-threshold", type=float, default=30.0, metavar="%",
                        help="Umbral %% de descuento para super oferta (default: 30%%)")

    args = parser.parse_args()
    setup(verbose=args.verbose, quiet=args.quiet)

    # Load YAML config
    yaml_config = load_yaml_config(args.config)
    args = apply_config_to_args(args, yaml_config)

    # Region
    if args.region:
        from superoffer.utils.region import load_region
        load_region(args.region)

    # Dotenv
    load_dotenv()

    # --list-stores
    if args.list_stores:
        from superoffer.engine import SCRAPER_MAP
        print("Tiendas disponibles:\n")
        for i, s in enumerate(STORE_CHOICES, 1):
            inst = SCRAPER_MAP[s]()
            print(f"  {i:2d}. {s:25s} -> {inst.config.name:20s} ({inst.config.base_url})")
        print(f"\nTotal: {len(STORE_CHOICES)} tiendas")
        return

    # --web
    if args.web:
        from superoffer.web_ui import run_webui
        run_webui(host=args.web_host, port=args.web_port)
        return

    # --scan (catalog mode, no input file needed)
    if args.scan:
        if args.input_file:
            print("  [ERROR] El modo --scan no necesita archivo de entrada.", file=sys.stderr)
            sys.exit(1)
    elif not args.input_file:
        parser.print_help()
        print(f"\n  [ERROR] Debes especificar un archivo de entrada o usar --scan.", file=sys.stderr)
        sys.exit(1)

    if args.input_file and not args.scan and not os.path.exists(args.input_file):
        print(f"  [ERROR] El archivo '{args.input_file}' no existe.", file=sys.stderr)
        sys.exit(1)

    if args.workers < 1:
        print(f"  [ERROR] --workers debe ser >= 1 (recibido: {args.workers})", file=sys.stderr)
        sys.exit(1)

    # Location
    if args.location:
        print(f"  [INFO] Filtro de ubicacion: {args.location}")
        from superoffer.utils.config import STORE_CONFIGS
        loc = args.location.lower().replace(" ", "_")
        for cfg in STORE_CONFIGS.values():
            if hasattr(cfg, "location_id") and cfg.location_id:
                cfg.headers["x-location-id"] = loc

    # Proxy
    proxy_manager = None
    if args.proxies or args.proxy_file:
        proxy_list = []
        if args.proxies:
            proxy_list.extend([p.strip() for p in args.proxies.split(",") if p.strip()])
        if args.proxy_file:
            if os.path.exists(args.proxy_file):
                with open(args.proxy_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            proxy_list.append(line)
        if proxy_list:
            proxy_manager = ProxyManager(proxy_list)
            print(f"  [INFO] Proxy manager: {len(proxy_list)} proxy(es)")

    # Webhook from env
    webhook_url = args.webhook or os.environ.get("WEBHOOK_URL")
    if not webhook_url:
        notifiers = yaml_config.get("notifiers", {}) if yaml_config else {}
        for url in notifiers.values():
            if isinstance(url, str) and url.startswith("http"):
                webhook_url = url
                break

    engine = OfferEngine(
        stores=args.stores,
        max_workers=args.workers,
        csv_output=args.csv,
        webhook_url=webhook_url,
        html_output=args.html,
        excel_output=args.excel,
        use_scoring=args.scoring,
        catalog_mode=args.scan,
        monitor_mode=args.monitor,
        monitor_threshold=args.monitor_threshold,
        proxy_manager=proxy_manager,
        config=yaml_config,
        super_offer_threshold=args.super_offer_threshold,
    )
    result = engine.run(args.input_file or "", args.output)
    if not result:
        sys.exit(1)


if __name__ == "__main__":
    main()
