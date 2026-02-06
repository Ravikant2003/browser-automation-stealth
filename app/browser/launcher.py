import json
import subprocess
import sys
import time
from urllib.request import urlopen

from app.config import settings


def _fetch_json(url: str):
    with urlopen(url, timeout=2) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_cdp_available() -> bool:
    try:
        _fetch_json(settings.CDP_HTTP_ENDPOINT)
        return True
    except Exception:
        return False


def wait_for_cdp(timeout_sec: int) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec:
        if is_cdp_available():
            return True
        time.sleep(0.5)
    return False


def launch_chrome_if_needed():
    if is_cdp_available():
        return

    if settings.RUNNING_IN_DOCKER:
        raise RuntimeError(
            "CDP not reachable inside Docker. Ensure host Chrome is running with --remote-debugging-port=9222."
        )

    chrome_args = [
        f"--remote-debugging-port={settings.CDP_PORT}",
        "--remote-debugging-address=0.0.0.0",
    ]

    if sys.platform == "darwin":
        subprocess.Popen(["open", "-a", "Google Chrome", "--args", *chrome_args])
    elif sys.platform.startswith("linux"):
        for bin_name in ("google-chrome", "chromium", "chromium-browser"):
            try:
                subprocess.Popen([bin_name, *chrome_args])
                break
            except FileNotFoundError:
                continue
        else:
            raise RuntimeError("Chrome/Chromium not found on PATH.")
    else:
        raise RuntimeError("Unsupported platform for auto-launch.")

    if not wait_for_cdp(settings.CHROME_LAUNCH_TIMEOUT_SEC):
        raise RuntimeError("Chrome did not start with CDP enabled in time.")


def discover_page_websocket_url() -> str:
    targets = _fetch_json(settings.CDP_HTTP_ENDPOINT)
    if not targets:
        # Create a new target/tab if none exist
        try:
            _fetch_json(f"http://{settings.CDP_HOST}:{settings.CDP_PORT}/json/new")
            time.sleep(0.5)
            targets = _fetch_json(settings.CDP_HTTP_ENDPOINT)
        except Exception:
            targets = []
    if not targets:
        raise RuntimeError("No CDP targets found.")

    new_tab = None
    any_page = None
    for t in targets:
        if t.get("type") == "page":
            any_page = any_page or t
            title = (t.get("title") or "").lower()
            url = (t.get("url") or "").lower()
            if "new tab" in title or url in ("chrome://newtab/", "about:blank"):
                new_tab = t
                break

    chosen = new_tab or any_page or targets[0]
    ws = chosen.get("webSocketDebuggerUrl")
    if not ws:
        raise RuntimeError("Target missing webSocketDebuggerUrl.")
    return ws


def discover_browser_websocket_url() -> str:
    version_info = _fetch_json(settings.CDP_VERSION_ENDPOINT)
    ws = version_info.get("webSocketDebuggerUrl")
    if not ws:
        raise RuntimeError("Browser webSocketDebuggerUrl not found.")
    return ws
