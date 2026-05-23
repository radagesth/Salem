import csv
import os
import sys
from typing import List, Dict


def read_products_from_csv(filepath: str) -> List[Dict[str, str]]:
    if not os.path.exists(filepath):
        print(f"  [ERROR] El archivo '{filepath}' no existe.", file=sys.stderr)
        return []
    if not filepath.endswith(".csv"):
        print(f"  [ERROR] '{filepath}' no es un archivo CSV.", file=sys.stderr)
        return []
    try:
        with open(filepath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header_lower = {k.strip().lower(): k for k in (reader.fieldnames or [])}
            name_col = _find_csv_col(header_lower, ["producto", "product", "nombre", "name", "item", "articulo"])
            if not name_col:
                cols = ", ".join(f"'{k}'" for k in header_lower)
                print(f"  [ERROR] No se encontro columna de productos en '{filepath}'.", file=sys.stderr)
                print(f"  [ERROR] Columnas detectadas: {cols}", file=sys.stderr)
                return []
            brand_col = _find_csv_col(header_lower, ["marca", "brand"])
            qty_col = _find_csv_col(header_lower, ["cantidad", "quantity", "qty", "cant"])
            category_col = _find_csv_col(header_lower, ["categoria", "category"])
            products = []
            for row in reader:
                if not any(row.values()):
                    continue
                name = (row.get(name_col) or "").strip()
                if not name:
                    continue
                prod = {"name": name}
                if brand_col:
                    prod["brand"] = (row.get(brand_col) or "").strip()
                if qty_col:
                    prod["quantity"] = (row.get(qty_col) or "").strip()
                if category_col:
                    prod["category"] = (row.get(category_col) or "").strip()
                products.append(prod)
            return products
    except Exception as e:
        print(f"  [ERROR] No se pudo leer '{filepath}': {e}", file=sys.stderr)
        return []


def _find_csv_col(header_lower: Dict[str, str], candidates: List[str]) -> str:
    for col_lower, col_orig in header_lower.items():
        if col_lower in candidates:
            return col_orig
    return ""
