from typing import Annotated
import json
import os
import urllib.request

from pydantic import Field
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

_MCP_URL = (
    os.environ.get(
        "VAULT_ADDR",
        "https://vault-mcp-combined-app.2e0x6ea5h3or.us-south.codeengine.appdomain.cloud",
    ).rstrip("/")
    + "/mcp"
)
_TOKEN = os.environ.get("VAULT_TOKEN", "root")


@tool(name="vault_read_secret", permission=ToolPermission.READ_ONLY,
      description="Read a field from a Vault KV v2 secret.")
def vault_read_secret(
    path: Annotated[str, Field(description="Secret path under the kv mount, e.g. 'txlab/dev/ibm-api-key'.")],
    field: Annotated[str, Field(description="The field name to read, e.g. 'api_key'.")],
) -> str:
    """Read one field from HashiCorp Vault (KV v2) via the MCP server and confirm access."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "read_secret",
            "arguments": {"mount": "secret", "path": path},
        },
    }).encode()

    req = urllib.request.Request(
        _MCP_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "X-Vault-Token": _TOKEN,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return f"MCP request failed: HTTP {e.code} — {e.reason}"
    except Exception as e:
        return f"MCP request error: {e}"

    if "error" in result:
        return f"Vault MCP error: {result['error'].get('message', result['error'])}"

    text = result.get("result", {}).get("content", [{}])[0].get("text", "")
    if field in text or path in text:
        return f"Read field '{field}' from secret/{path} (value withheld)."
    return f"Field '{field}' not found at secret/{path}. MCP response: {text[:200]}"