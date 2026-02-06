import asyncio
import time

from pydoll.connection.connection_handler import ConnectionHandler
from pydoll.elements.web_element import WebElement

from app.browser.cdp_utils import (
    CDPClient,
    add_stealth_script,
    enable_default_domains,
    evaluate_expression,
    evaluate_object_id,
    human_mouse_move,
)
from app.browser.launcher import discover_page_websocket_url, launch_chrome_if_needed
from app.config import settings
from app.utils.artifacts import ensure_output_dir, save_html, save_metadata, save_screenshot
from app.utils.ip_utils import get_public_ip


async def wait_for_cloudflare_clear(client: CDPClient):
    while True:
        title = await evaluate_expression(client, "document.title")
        if not title:
            await asyncio.sleep(settings.CF_POLL_INTERVAL_SEC)
            continue
        if settings.CLOUD_FLARE_TITLE_FRAGMENT in title.lower():
            await asyncio.sleep(settings.CF_POLL_INTERVAL_SEC)
            continue
        return


async def run():
    public_ip = get_public_ip()
    ensure_output_dir(settings.OUTPUT_DIR)
    print(f"[init] output_dir={settings.OUTPUT_DIR}")

    launch_chrome_if_needed()
    ws_url = discover_page_websocket_url()
    print(f"[cdp] ws_url={ws_url}")

    client = CDPClient(ws_url)
    await client.connect()
    await enable_default_domains(client)
    await add_stealth_script(client)

    # Pydoll connection handler for hybrid CDP + PyDoll element ops.
    handler = ConnectionHandler(ws_address=ws_url)

    try:
        print(f"[nav] navigating to {settings.TARGET_URL}")
        await client.execute("Page.navigate", {"url": settings.TARGET_URL})
        await asyncio.sleep(2)

        # Human-like movement via CDP.
        print("[cdp] human_mouse_move")
        await human_mouse_move(client)

        # Use CDP to get an element objectId, then wrap it with PyDoll.
        body_object_id = await evaluate_object_id(client, "document.body")
        body = WebElement(object_id=body_object_id, connection_handler=handler)
        try:
            await body.wait_until(is_visible=True, timeout=5)
            await body.click()
        except Exception as e:
            print(f"[pydoll] body wait/click skipped: {e}")

        print("[cf] waiting for challenge to clear")
        await wait_for_cloudflare_clear(client)
        print("[cf] cleared")

        print("[artifact] saving screenshot")
        await save_screenshot(client, settings.OUTPUT_DIR)
        print("[artifact] saving html")
        await save_html(client, settings.OUTPUT_DIR)

        save_metadata(
            settings.OUTPUT_DIR,
            {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "public_ip": public_ip,
                "target_url": settings.TARGET_URL,
                "cdp_endpoint": settings.CDP_HTTP_ENDPOINT,
            },
        )
        print("[artifact] metadata saved")
    finally:
        # Intentionally avoid stopping the host Chrome instance.
        await client.close()


if __name__ == "__main__":
    asyncio.run(run())
