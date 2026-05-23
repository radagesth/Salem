import os
import sys
from pathlib import Path


def load_dotenv(dotenv_path: str = ".env"):
    env_file = Path(dotenv_path)
    if not env_file.exists():
        env_file = Path(__file__).resolve().parent.parent.parent / dotenv_path
    if not env_file.exists():
        return
    loaded = 0
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("\"'")
            if key and not os.environ.get(key):
                os.environ[key] = val
                loaded += 1
    if loaded:
        print(f"  [INFO] Cargadas {loaded} variable(s) de entorno desde {env_file.name}")
