# ==========================================================
# alpacaMcpExecutor_HTTP.py — FINAL AZURE VERSION
# Works with Alpaca MCP Server deployed over HTTP
# ==========================================================

import os
import json
import time
import asyncio
import aiohttp
from dotenv import load_dotenv

# ==========================================================
#  Timestamped Logger
# ==========================================================
def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ==========================================================
#  Load Environment Variables
# ==========================================================
log("INIT: Loading environment variables...")
load_dotenv()
os.environ.setdefault("TRANSFORMERS_NO_TORCHVISION", "1")

MCP_URL = "https://alpacashit-h3edbzd5hgabh6hs.westeurope-01.azurewebsites.net/mcp"
MCP_VERSION = "2024-11-05"


# ==========================================================
#  MCP HTTP Client
# ==========================================================
class MCPHTTPClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session_id: str | None = None
        self.http: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.http = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self.http:
            await self.http.close()
            self.http = None

    async def _post(self, payload: dict, extra_headers=None, timeout=25):
        """Low-level POST that sends JSON-RPC message and parses SSE or JSON."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-protocol-version": MCP_VERSION,
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        if extra_headers:
            headers.update(extra_headers)

        async with self.http.post(self.base_url, json=payload, headers=headers, timeout=timeout) as resp:
            text = await resp.text()
            log(f"HTTP {resp.status} | Headers: {dict(resp.headers)}")
            if resp.status >= 400:
                raise RuntimeError(f"MCP HTTP {resp.status}: {text[:300]}")

            # store session ID if new
            sid = resp.headers.get("mcp-session-id")
            if sid:
                self.session_id = sid

            # Parse SSE data: lines starting with "data:"
            messages = []
            for line in text.splitlines():
                if line.startswith("data:"):
                    try:
                        messages.append(json.loads(line[len("data:"):].strip()))
                    except Exception:
                        pass

            if messages:
                return messages[-1]

            # fallback: try normal JSON
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                raise RuntimeError(f"Unexpected MCP response: {text[:200]}")

    # ------------------------
    # High-level RPC wrappers
    # ------------------------
    async def initialize(self):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": MCP_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "azure-http-client", "version": "1.0"},
            },
        }
        log("➡️ MCP CALL → initialize")
        resp = await self._post(payload)
        log(f"✅ Session initialized | session_id={self.session_id}")
        return resp

    async def list_tools(self):
        payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        log("➡️ MCP CALL → tools/list")
        return await self._post(payload)

    async def call_tool(self, name: str, arguments: dict):
        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        log(f"➡️ MCP CALL → tools/call ({name}) | args={arguments}")
        return await self._post(payload)


# ==========================================================
#  High-level Trading Flow
# ==========================================================
async def execute_trade(symbol: str, qty: int, side: str = "buy"):
    """Places a stock order through HTTP MCP."""
    log(f"TRADE: {side.upper()} {qty} {symbol}")
    async with MCPHTTPClient(MCP_URL) as mcp:
        await mcp.initialize()
        result = await mcp.call_tool(
            "place_stock_order",
            {
                "symbol": symbol,
                "side": side,
                "quantity": qty,
                "order_type": "market",
                "time_in_force": "day",
            },
        )
        print("\n[ORDER RESULT]\n", json.dumps(result, indent=2))


async def run_alpaca_executor():
    log("INIT: Starting Alpaca MCP Executor (HTTP)...")

    async with MCPHTTPClient(MCP_URL) as mcp:
        # Step 1: Initialize
        init = await mcp.initialize()
        print("\n[INIT RESPONSE]\n", json.dumps(init, indent=2))

        # Step 2: List tools
        tools = await mcp.list_tools()
        print("\n[TOOLS/LIST RESULT]\n", json.dumps(tools, indent=2))

        # Step 3: Account info
        log("STEP 3: Fetching account info...")
        account = await mcp.call_tool("get_account_info", {})
        print("\n[ACCOUNT INFO]\n", json.dumps(account, indent=2))

        # Step 4: Positions
        log("STEP 4: Fetching positions...")
        positions = await mcp.call_tool("get_positions", {})
        print("\n[POSITIONS]\n", json.dumps(positions, indent=2))

        # Step 5: Test trade
        log("STEP 5: Placing test market order (AAPL, qty=1)...")
        order = await mcp.call_tool(
            "place_stock_order",
            {
                "symbol": "AAPL",
                "side": "buy",
                "quantity": 1,
                "order_type": "market",
                "time_in_force": "day",
            },
        )
        print("\n[TRADE RESULT]\n", json.dumps(order, indent=2))

    log("CLEANUP: ✅ All MCP HTTP operations complete.")


# ==========================================================
#  Entry Point
# ==========================================================
if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_alpaca_executor())
