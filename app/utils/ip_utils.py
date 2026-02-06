import json
from urllib.request import urlopen


def get_public_ip() -> str | None:
    try:
        with urlopen("https://api.ipify.org?format=json", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("ip")
    except Exception:
        return None

