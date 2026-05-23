import os
import sys
from typing import Any, Dict, Optional

SUPEROFFER_YML = "superoffer.yml"
SUPEROFFER_YAML = "superoffer.yaml"


def find_config() -> Optional[str]:
    for fname in (SUPEROFFER_YML, SUPEROFFER_YAML):
        path = os.path.join(os.getcwd(), fname)
        if os.path.exists(path):
            return path
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), fname)
        if os.path.exists(path):
            return path
    return None


def load_yaml_config(filepath: Optional[str] = None) -> Dict[str, Any]:
    if filepath is None:
        filepath = find_config()
    if filepath is None:
        return {}
    try:
        import yaml
        with open(filepath, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        print(f"  [INFO] Configuracion cargada desde: {filepath}")
        return cfg
    except ImportError:
        print("  [WARN] PyYAML no instalado. Instala con: pip install pyyaml", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"  [WARN] No se pudo cargar '{filepath}': {e}", file=sys.stderr)
        return {}


def apply_config_to_args(args, config: Dict[str, Any]):
    if not config:
        return
    stores_cfg = config.get("stores")
    if stores_cfg and args.stores is None:
        enabled = stores_cfg.get("enabled")
        if isinstance(enabled, list):
            args.stores = enabled
    defaults = config.get("defaults", {})
    if "webhook" in defaults and args.webhook is None:
        args.webhook = defaults["webhook"]
    if "location" in defaults and args.location is None:
        args.location = defaults["location"]
    if "workers" in defaults and args.workers == 8:
        args.workers = int(defaults["workers"])
    threshold = config.get("super_offer_threshold")
    if threshold is not None:
        args.super_offer_threshold = float(threshold)
    notifiers = config.get("notifiers", {})
    if notifiers and args.webhook is None:
        for platform, url in notifiers.items():
            if url:
                args.webhook = url
                break
    return args
