import base64
import json
from pathlib import Path

from app.browser.cdp_utils import CDPClient, evaluate_expression


def ensure_output_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def save_metadata(output_dir: Path, metadata: dict):
    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2))


async def save_screenshot(client: CDPClient, output_dir: Path, filename: str = "phase1_result.png"):
    result = await client.execute("Page.captureScreenshot", {"format": "png"})
    data = result.get("data")
    if not data:
        raise RuntimeError("No screenshot data returned.")
    path = output_dir / filename
    path.write_bytes(base64.b64decode(data))
    return path


async def save_html(client: CDPClient, output_dir: Path, filename: str = "page.html"):
    html = await evaluate_expression(client, "document.documentElement.outerHTML")
    if not html:
        raise RuntimeError("No HTML returned.")
    path = output_dir / filename
    path.write_text(html)
    return path
