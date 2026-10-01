---
name: provision-multicloud-app
description: Use when the user wants to provision or stand up an application across IBM Cloud and AWS using the agentic multi-cloud pattern, e.g. "deploy the status dashboard across IBM Cloud and AWS, store secrets in Vault." Do NOT use for single-cloud-only changes or plain Terraform questions.
---

# Provision a Multi-Cloud App (Agentic Pattern)

## Boundaries
- No hard-coded secrets (Vault only). No destructive cloud action without a shown plan + explicit human approval. Small, cheap resources.
- For Orchestrate agent/tool authoring, hand off to wxo-agent-architect.

## Steps
1. Restate & scope (2-3 lines; IBM vs AWS split; secrets; cost).
2. Author IaC / app config per the IaC standards. Use the Terraform MCP for current docs.
3. Wire secrets in Vault (secret/{project}/{env}/{key}); run secret-detection.
4. Build/confirm the Orchestrate agents (handoff). Discover before creating.
5. Confirm the AWS A2A agent on AgentCore (agent card discoverable).
6. Dispatch: hand the request to the supervisor; it deploys the IBM frontend, reads secrets, and delegates the AWS status API over A2A.
7. Verify: open the dashboard URL; confirm it shows live AWS status. Return a consolidated result.
8. Output an engineer review checklist.

## Protocol reminder
MCP = agent-to-tool (vertical). A2A = agent-to-agent (horizontal).

