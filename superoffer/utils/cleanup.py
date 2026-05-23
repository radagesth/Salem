import os
import sys
from superoffer.utils.config import OUTPUT_DIR, MAX_RESULTS_RETENTION


def cleanup_old_outputs():
    if not os.path.isdir(OUTPUT_DIR):
        return
    files = [
        f for f in os.listdir(OUTPUT_DIR)
        if f.startswith("resultados_") and f.endswith(".json")
    ]
    files.sort(reverse=True)
    if len(files) <= MAX_RESULTS_RETENTION:
        return
    to_delete = files[MAX_RESULTS_RETENTION:]
    for fname in to_delete:
        path = os.path.join(OUTPUT_DIR, fname)
        try:
            os.remove(path)
        except OSError:
            pass
    if to_delete:
        print(f"  [INFO] Limpieza: eliminados {len(to_delete)} archivo(s) antiguo(s) (max: {MAX_RESULTS_RETENTION})")


def cleanup_images(max_age_days: int = 7, max_count: int = 100):
    images_dir = os.path.join(OUTPUT_DIR, "imagenes")
    if not os.path.isdir(images_dir):
        return
    files = []
    for fname in os.listdir(images_dir):
        fpath = os.path.join(images_dir, fname)
        if os.path.isfile(fpath):
            files.append((os.path.getmtime(fpath), fpath))
    files.sort(key=lambda x: -x[0])
    if len(files) > max_count:
        for _, fpath in files[max_count:]:
            try:
                os.remove(fpath)
            except OSError:
                pass
        print(f"  [INFO] Limpieza: eliminadas {len(files) - max_count} imagen(es) antigua(s)")
    import time
    cutoff = time.time() - (max_age_days * 86400)
    for mtime, fpath in files:
        if mtime < cutoff:
            try:
                os.remove(fpath)
            except OSError:
                pass
