import os
import secrets
import subprocess
from pathlib import Path

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

ROOT = Path(os.environ["GPU_PROJECT"]).resolve(strict=True)
TOKEN = os.environ["GPU_MCP_TOKEN"]
if len(TOKEN) < 32:
    raise ValueError("GPU_MCP_TOKEN must contain at least 32 characters")

mcp = FastMCP("gpu-server", stateless_http=True, json_response=True)

@mcp.tool()
def remote_shell(command: str) -> dict:
    """Run a short shell command on the GPU server. Use this for remote file reads, edits and tests. Start long training jobs with tmux or the cluster scheduler, then inspect their logs."""
    result = subprocess.run(
        ["bash", "-lc", command], cwd=ROOT,
        capture_output=True, text=True, errors="replace", timeout=90,
    )
    return {"exit_code": result.returncode,
            "stdout": result.stdout[-20000:], "stderr": result.stderr[-10000:]}

app = mcp.streamable_http_app()

async def authenticate(request, call_next):
    supplied = request.headers.get("authorization", "").encode()
    expected = ("Bearer " + TOKEN).encode()
    if not secrets.compare_digest(supplied, expected):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)

app.add_middleware(BaseHTTPMiddleware, dispatch=authenticate)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8766)
