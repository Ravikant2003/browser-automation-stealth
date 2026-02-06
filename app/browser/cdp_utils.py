import asyncio
import json
import websockets


class CDPClient:
    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self._ws = None
        self._id = 0
        self._pending = {}
        self._listener_task = None

    async def connect(self):
        self._ws = await websockets.connect(self.websocket_url)
        self._listener_task = asyncio.create_task(self._listener())

    async def close(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self._ws:
            await self._ws.close()

    async def _listener(self):
        try:
            async for message in self._ws:
                data = json.loads(message)
                if "id" in data and data["id"] in self._pending:
                    fut = self._pending.pop(data["id"])
                    if not fut.done():
                        fut.set_result(data)
        except asyncio.CancelledError:
            return

    async def execute(self, method: str, params: dict | None = None):
        if params is None:
            params = {}
        self._id += 1
        msg_id = self._id
        payload = {"id": msg_id, "method": method, "params": params}
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self._pending[msg_id] = fut
        await self._ws.send(json.dumps(payload))
        resp = await fut
        if "error" in resp:
            raise RuntimeError(resp["error"])
        return resp.get("result", {})


async def enable_default_domains(client: CDPClient):
    await client.execute("Page.enable")
    await client.execute("Runtime.enable")
    await client.execute("Network.enable")


async def add_stealth_script(client: CDPClient):
    script = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    window.chrome = window.chrome || { runtime: {} };
    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
    """
    await client.execute("Page.addScriptToEvaluateOnNewDocument", {"source": script})


async def human_mouse_move(client: CDPClient, steps: int = 15):
    x, y = 100, 100
    for i in range(steps):
        x += 5 + (i % 3)
        y += 3 + (i % 2)
        await client.execute(
            "Input.dispatchMouseEvent",
            {"type": "mouseMoved", "x": x, "y": y, "buttons": 0},
        )
        await asyncio.sleep(0.05)


async def evaluate_expression(client: CDPClient, expression: str, return_by_value: bool = True):
    result = await client.execute(
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": return_by_value},
    )
    if return_by_value:
        return result.get("result", {}).get("value")
    return result


async def evaluate_object_id(client: CDPClient, expression: str) -> str:
    result = await evaluate_expression(client, expression, return_by_value=False)
    obj = result.get("result", {})
    object_id = obj.get("objectId")
    if not object_id:
        raise RuntimeError("No objectId returned from Runtime.evaluate.")
    return object_id

