from superoffer.input.excel_reader import read_products_from_excel
from superoffer.input.csv_reader import read_products_from_csv


def read_products(filepath: str):
    if filepath.endswith(".csv"):
        return read_products_from_csv(filepath)
    return read_products_from_excel(filepath)
