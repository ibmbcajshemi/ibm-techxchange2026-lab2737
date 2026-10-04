from typing import Annotated
import json
import urllib.request

from pydantic import Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType
from ibm_watsonx_orchestrate.run import connections

VAULT_CREDS = "vault_creds"
_DEFAULT_ADDR = "https://vault-mcp-combined-app.2e0x6ea5h3or.us-south.codeengine.appdomain.cloud"

_session_id: str | None = None


def _get_creds() -> tuple[str, str]:
    """Return (mcp_url, token) from the connection, falling back to defaults for local dev."""
    try:
        c = connections.key_value(VAULT_CREDS)
        return c.get("VAULT_ADDR", _DEFAULT_ADDR).rstrip("/") + "/mcp", c.get("VAULT_TOKEN", "root")
    except Exception:
        return _DEFAULT_ADDR.rstrip("/") + "/mcp", "root"


def _post(mcp_url: str, token: str, payload: dict, session: str = "") -> tuple[str, dict]:
    """POST a JSON-RPC payload to the MCP server, returning (session_id, response)."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "X-Vault-Token": token,
    }
    if session:
        headers["Mcp-Session-Id"] = session
    req = urllib.request.Request(mcp_url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.headers.get("Mcp-Session-Id", session), json.loads(resp.read().decode())


def _read_secret(path: str) -> dict:
    """Initialize MCP session if needed and call read_secret, retrying once on stale session."""
    global _session_id
    mcp_url, token = _get_creds()
    if not _session_id:
        _session_id, _ = _post(mcp_url, token, {
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "vault_read_secret", "version": "1.0"}},
        })
    for attempt in range(2):
        try:
            _, result = _post(mcp_url, token, {
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "read_secret", "arguments": {"mount": "secret", "path": path}},
            }, _session_id or "")
            return result
        except urllib.error.HTTPError as e:
            if e.code == 400 and attempt == 0:
                _session_id = None
                continue
            raise
    raise RuntimeError("tools/call failed after session refresh")  # unreachable


@tool(name="vault_read_secret", permission=ToolPermission.READ_ONLY,
      description="Read a field from a Vault KV v2 secret.",
      expected_credentials=[{"app_id": VAULT_CREDS, "type": ConnectionType.KEY_VALUE}])
def vault_read_secret(
    path: Annotated[str, Field(description="Secret path, e.g. 'txlab/dev/ibm-api-key'.")],
    field: Annotated[str, Field(description="Field name, e.g. 'api_key'.")],
) -> str:
    """Read one field from HashiCorp Vault via the Vault MCP server. Value is never echoed."""
    try:
        result = _read_secret(path)
    except urllib.error.HTTPError as e:
        return f"MCP request failed: HTTP {e.code} — {e.reason}"
    except Exception as e:
        return f"MCP request error: {e}"
    if "error" in result:
        return f"Vault MCP error: {result['error'].get('message', result['error'])}"
    text = result.get("result", {}).get("content", [{}])[0].get("text", "")
    if field in text or path in text:
        return f"Read field '{field}' from secret/{path} (value withheld)."
    return f"Field '{field}' not found at secret/{path}. Response: {text[:200]}"
