from __future__ import annotations
import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from superoffer.scrapers.base import ProductOffer

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
DB_PATH = os.path.join(DB_DIR, "price_history.db")

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(DB_DIR, exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _init_db(_local.conn)
    return _local.conn


def _init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_query TEXT NOT NULL,
            product_name TEXT NOT NULL,
            store_name TEXT NOT NULL,
            price REAL NOT NULL,
            original_price REAL,
            discount REAL,
            url TEXT,
            date TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            UNIQUE(product_query, store_name, product_name, date, price)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_lookup
        ON price_history(product_query, store_name, date)
    """)
    conn.commit()


def save_entry(product_query: str, offers: List[ProductOffer], store_name: str):
    conn = _get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().isoformat()
    for offer in offers:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO price_history
                (product_query, product_name, store_name, price, original_price,
                 discount, url, date, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                product_query, offer.name, store_name, offer.price,
                offer.original_price, offer.discount_percentage,
                offer.url, today, now
            ))
        except sqlite3.Error:
            pass
    conn.commit()


def get_lowest_price(product_query: str, store_name: str) -> Optional[float]:
    try:
        conn = _get_conn()
        cur = conn.execute("""
            SELECT MIN(price) as min_price FROM price_history
            WHERE product_query = ? AND store_name = ? AND price > 0
        """, (product_query, store_name))
        row = cur.fetchone()
        return row["min_price"] if row and row["min_price"] else None
    except sqlite3.Error:
        return None


def get_history(product_query: str, store_name: str, limit: int = 30
                ) -> List[Dict]:
    try:
        conn = _get_conn()
        cur = conn.execute("""
            SELECT date, price, original_price, discount, product_name
            FROM price_history
            WHERE product_query = ? AND store_name = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (product_query, store_name, limit))
        return [dict(r) for r in cur.fetchall()]
    except sqlite3.Error:
        return []


def export_to_json():
    try:
        conn = _get_conn()
        cur = conn.execute("SELECT * FROM price_history ORDER BY timestamp")
        rows = [dict(r) for r in cur.fetchall()]
        json_path = os.path.join(DB_DIR, "price_history_export.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
    except (sqlite3.Error, OSError):
        pass
