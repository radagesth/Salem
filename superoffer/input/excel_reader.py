import os
import sys
from typing import List, Dict
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException


def read_products_from_excel(filepath: str) -> List[Dict[str, str]]:
    if not os.path.exists(filepath):
        print(f"  [ERROR] El archivo '{filepath}' no existe. Revisa la ruta e intenta de nuevo.", file=sys.stderr)
        return []
    if not filepath.endswith((".xlsx", ".xls")):
        print(f"  [ERROR] '{filepath}' no es un archivo Excel valido. Usa archivos .xlsx o .xls.", file=sys.stderr)
        return []
    try:
        wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    except InvalidFileException:
        print(f"  [ERROR] '{filepath}' no es un archivo Excel valido o esta corrupto.", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [ERROR] No se pudo abrir '{filepath}': {e}", file=sys.stderr)
        return []
    ws = wb.active
    if ws is None:
        print(f"  [ERROR] El archivo '{filepath}' no contiene hojas de calculo.", file=sys.stderr)
        wb.close()
        return []
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not rows:
        print(f"  [ERROR] El archivo '{filepath}' esta vacio.", file=sys.stderr)
        return []
    header = [str(h).strip().lower() if h else "" for h in rows[0]]
    name_col = _find_column(header, ["producto", "product", "nombre", "name", "item", "articulo"])
    if name_col is None:
        column_list = ", ".join([f"'{c}'" for c in header if c])
        print(f"  [ERROR] No se encontro una columna de productos en '{filepath}'.", file=sys.stderr)
        print(f"  [ERROR] El encabezado debe incluir una columna llamada 'Producto', 'Nombre' o similar.", file=sys.stderr)
        if column_list:
            print(f"  [ERROR] Columnas detectadas: {column_list}", file=sys.stderr)
        return []
    brand_col = _find_column(header, ["marca", "brand", "marca"])
    qty_col = _find_column(header, ["cantidad", "quantity", "qty", "cant"])
    category_col = _find_column(header, ["categoria", "category", "categoria"])
    products = []
    empty_count = 0
    for i, row in enumerate(rows[1:], 2):
        if not any(row):
            continue
        product = {}
        if name_col is not None:
            val = str(row[name_col]).strip() if row[name_col] else ""
            product["name"] = val
            if not val:
                empty_count += 1
                continue
        if brand_col is not None:
            product["brand"] = str(row[brand_col]).strip() if row[brand_col] else ""
        if qty_col is not None:
            product["quantity"] = str(row[qty_col]).strip() if row[qty_col] else ""
        if category_col is not None:
            product["category"] = str(row[category_col]).strip() if row[category_col] else ""
        products.append(product)
    if not products:
        print(f"  [ERROR] No se encontraron productos con nombre en '{filepath}'.", file=sys.stderr)
        if empty_count:
            print(f"  [ERROR] {empty_count} fila(s) tienen el nombre de producto vacio.", file=sys.stderr)
        return []
    return products


def _find_column(header: List[str], candidates: List[str]) -> int | None:
    for i, col in enumerate(header):
        if col in candidates:
            return i
    return None
