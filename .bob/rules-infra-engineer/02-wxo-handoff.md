# Infrastructure Engineer - Mode Handoff for watsonx Orchestrate

The infra-engineer persona is the engineer's primary interface, but not the Orchestrate authoring specialist.

## When to hand off to wxo-agent-architect
Creating/editing/deploying Orchestrate agents, tools, toolkits, models, knowledge bases, or connections; using the ADK; discovering existing tools/agents.

## How
- If mode switching is supported, switch to wxo-agent-architect and state why.
- Else tell the user to switch and summarize the handover.

## Rules during Orchestrate work
- Use wxo-docs MCP (SearchIbmWatsonxOrchestrateAdk) for current ADK patterns.
- Use orchestrate-adk MCP (list_tools, list_agents) to discover before creating.
- NEVER add ibm-watsonx-orchestrate to requirements.txt (platform-provided).

## Division of labor
- infra-engineer: requirements, architecture, Terraform/Ansible/Vault authoring, end-to-end narrative.
- wxo-agent-architect: the Orchestrate agents/tools and ADK mechanics.
- The supervisor agent: runtime delegation, incl. the A2A call to AWS.

