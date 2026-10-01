# Infrastructure Engineer - IaC Standards (loaded only when infra-engineer is active)

## Terraform
- Small, composable modules; one concern per module.
- Declare required_providers and pin provider major versions.
- Name: {project}-{env}-{component}; tag: project, env, owner, managed-by = "terraform".
- Pull secrets from Vault via the vault provider data sources - never hard-coded strings.
- Before apply: fmt, validate, plan; plan output must be human-reviewed.
- Use the Terraform MCP server (registry) to confirm current docs.

## Ansible
- Idempotent tasks; prefer modules over shell (guard with changed_when/creates).
- Reference Vault via lookups; never secrets in vars/inventory.

## HashiCorp Vault
- Use the Vault MCP server to store/read secrets and manage certs.
- Show the path layout (secret/{project}/{env}/{key}) before writing.
- Never print secret values; refer to them by path.

## Multi-cloud (IBM Cloud + AWS)
- Be explicit about which cloud each resource targets and why.
- Keep cloud-specific code in separated modules/dirs. Call out cost implications.

## Protocol clarity
- MCP = agent-to-tool (vertical). A2A = agent-to-agent (horizontal).
- The Orchestrate supervisor uses A2A to delegate to the AWS AgentCore agent.

