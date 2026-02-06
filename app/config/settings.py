import os
from pathlib import Path

RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"

CDP_HOST = os.getenv("CDP_HOST", "localhost" if not RUNNING_IN_DOCKER else "docker.for.mac.localhost")
CDP_PORT = int(os.getenv("CDP_PORT", "9222"))

CDP_HTTP_ENDPOINT = f"http://{CDP_HOST}:{CDP_PORT}/json"
CDP_VERSION_ENDPOINT = f"http://{CDP_HOST}:{CDP_PORT}/json/version"

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/output" if RUNNING_IN_DOCKER else "data/output"))

CLOUD_FLARE_TITLE_FRAGMENT = "just a moment"

CHROME_LAUNCH_TIMEOUT_SEC = int(os.getenv("CHROME_LAUNCH_TIMEOUT_SEC", "20"))
CF_POLL_INTERVAL_SEC = float(os.getenv("CF_POLL_INTERVAL_SEC", "1"))

TARGET_URL = os.getenv("TARGET_URL", "https://www.scrapingcourse.com/antibot-challenge")
