import os, hvac
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission

@tool(name="vault_read_secret", permission=ToolPermission.READ_ONLY,
      description="Read a field from a Vault KV v2 secret.")
def vault_read_secret(path: str, field: str) -> str:
    """Read one field from HashiCorp Vault (KV v2) and confirm access.

    Args:
        path: Secret path under the kv mount, e.g. 'bob-lab/dev/ibm-api-key'.
        field: The field name to read, e.g. 'api_key'.
    Returns:
        Confirmation that the field was read (value withheld).
    """
    addr = os.environ.get("VAULT_ADDR", "https://VAULT_CE_URL_HERE")  # Code Engine Vault URL
    client = hvac.Client(url=addr, token=os.environ.get("VAULT_TOKEN", "root"))
    if not client.is_authenticated():
        return f"Vault auth failed at {addr}."
    r = client.secrets.kv.v2.read_secret_version(path=path, mount_point="secret")
    data = r["data"]["data"]
    if field not in data:
        return f"Field '{field}' not found at secret/{path}."
    return f"Read field '{field}' from secret/{path} (value withheld)."

