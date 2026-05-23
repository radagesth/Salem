import logging
import sys
from typing import Optional


_LOG_LEVEL = logging.INFO
_QUIET = False


def setup(verbose: bool = False, quiet: bool = False):
    global _LOG_LEVEL, _QUIET
    if quiet:
        _LOG_LEVEL = logging.WARNING
    elif verbose:
        _LOG_LEVEL = logging.DEBUG
    else:
        _LOG_LEVEL = logging.INFO
    _QUIET = quiet
    logging.basicConfig(
        level=_LOG_LEVEL,
        format="%(message)s",
        stream=sys.stderr if quiet else sys.stdout,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def ok(msg: str):
    logging.info(f"  [OK] {msg}")


def info(msg: str):
    logging.info(f"  [INFO] {msg}")


def debug(msg: str):
    logging.debug(f"  [DEBUG] {msg}")


def warn(store: str, msg: str):
    logging.warning(f"  [WARN] {store}: {msg}")


def error(store: str, msg: str, detail: str = ""):
    if detail:
        logging.error(f"  [ERROR] {store}: {msg} ({detail})")
    else:
        logging.error(f"  [ERROR] {store}: {msg}")


def summary(items_processed: int, total_offers: int, output_file: str):
    logging.info(f"\n  [INFO] Procesados {items_processed} producto(s)")
    logging.info(f"  [INFO] {total_offers} oferta(s) encontrada(s) en total")
    logging.info(f"  [OK] Resultados guardados en: {output_file}")


def is_quiet() -> bool:
    return _QUIET
