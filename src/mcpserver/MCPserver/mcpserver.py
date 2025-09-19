# mcpserver.py
from typing import Dict, Any
import requests
from mcp.server.fastmcp import FastMCP

# 1) High-level MCP server with decorators
mcp = FastMCP("bank-ai")

@mcp.tool()
def login(username: str, password: str) -> Dict[str, Any]:
    """Login a user and return auth info (includes JWT)."""
    # Prefer POST body (avoids credentials in query logs)
    resp = requests.post(
        "http://userservice:5000/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()

@mcp.tool()
def get_contacts(username: str, token: str) -> Any:
    """Retrieve the contact list for a user (requires JWT token)."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"http://contacts:5000/contacts/{username}",
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()

# 2) Expose an HTTP server for K8s by mounting the FastMCP SSE app into FastAPI
#    (This requires SDK versions that include `mcp.sse_app()`.)
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="bank-ai")
# Health endpoint for K8s probes
@app.get("/healthz")
def healthz():
    return JSONResponse({"status": "ok"})

# Mount the MCP SSE application under /mcp
# Clients connect to:  http://<host>:8000/mcp/sse
app.mount("/mcp", mcp.sse_app())

if __name__ == "__main__":
    # Run ASGI app (FastAPI + FastMCP SSE) on port 8000
    import uvicorn
    uvicorn.run("MCPserver.mcpserver:app", host="0.0.0.0", port=8000)
