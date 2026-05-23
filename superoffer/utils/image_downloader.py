import os
import re
import sys
import requests
from urllib.parse import urlparse
from superoffer.utils.messages import warn

IMAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output", "imagenes")


def sanitize_filename(name: str, max_len: int = 80) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"\s+", "_", name.strip())
    name = name.lower()[:max_len].rstrip("._")
    return name or "producto"


def download_image(image_url: str, product_name: str, store_name: str) -> str:
    if not image_url:
        return ""
    sanitized = sanitize_filename(f"{store_name}_{product_name}")
    ext = _guess_extension(image_url)
    filename = f"{sanitized}{ext}"
    save_path = os.path.join(IMAGES_DIR, filename)
    if os.path.exists(save_path):
        return save_path
    try:
        os.makedirs(IMAGES_DIR, exist_ok=True)
    except OSError as e:
        warn("ImageDownloader", f"No se pudo crear directorio: {e}")
        return ""
    try:
        resp = requests.get(
            image_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            timeout=10,
            stream=True,
        )
        resp.raise_for_status()
        if "image" not in resp.headers.get("Content-Type", ""):
            return ""
        actual_ext = _ext_from_content_type(resp.headers.get("Content-Type", ""))
        if actual_ext and actual_ext != ext:
            filename = f"{sanitized}{actual_ext}"
            save_path = os.path.join(IMAGES_DIR, filename)
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return save_path
    except requests.RequestException as e:
        warn("ImageDownloader", f"No se pudo descargar {image_url[:60]}...: {e}")
        return ""
    except OSError as e:
        warn("ImageDownloader", f"No se pudo guardar {filename}: {e}")
        return ""


def _guess_extension(url: str) -> str:
    path = urlparse(url).path
    match = re.search(r"\.(jpg|jpeg|png|gif|webp|bmp|svg)(?:\?|$)", path, re.IGNORECASE)
    return f".{match.group(1).lower()}" if match else ".jpg"


def _ext_from_content_type(content_type: str) -> str:
    mapping = {
        "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
        "image/webp": ".webp", "image/bmp": ".bmp", "image/svg+xml": ".svg",
    }
    for ctype, ext in mapping.items():
        if ctype in content_type:
            return ext
    return ""
