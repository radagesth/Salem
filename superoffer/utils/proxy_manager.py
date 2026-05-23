import os
import random
import sys
from typing import Dict, List, Optional, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ProxyManager:
    def __init__(self, proxies: Optional[List[str]] = None):
        self._proxies: List[str] = []
        self._current_index = 0
        if proxies:
            self._proxies = proxies
        env_proxies = os.environ.get("SUPEROFFER_PROXIES", "")
        if env_proxies:
            self._proxies.extend([p.strip() for p in env_proxies.split(",") if p.strip()])
        env_file = os.environ.get("SUPEROFFER_PROXY_FILE", "")
        if env_file and os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self._proxies.append(line)

    @property
    def count(self) -> int:
        return len(self._proxies)

    def get_random(self) -> Optional[Dict[str, str]]:
        if not self._proxies:
            return None
        proxy = random.choice(self._proxies)
        return self._to_dict(proxy)

    def get_rotated(self) -> Optional[Dict[str, str]]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._current_index % len(self._proxies)]
        self._current_index += 1
        return self._to_dict(proxy)

    @staticmethod
    def _to_dict(proxy: str) -> Dict[str, str]:
        if proxy.startswith("socks5://") or proxy.startswith("socks4://"):
            return {"http": proxy, "https": proxy}
        if not proxy.startswith("http"):
            proxy = f"http://{proxy}"
        return {"http": proxy, "https": proxy}

    def create_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503])
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
