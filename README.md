# ibm-techxchange2026-lab2737
Multi-Cloud Status Dashboard with IBM Bob

IBM Bob custom mode persona of **"Infrastructure Engineer"**

## IBM Bob — Infrastructure Engineer

> A role-aware AI persona that provisions and orchestrates a real two-cloud application — frontend on IBM Cloud, status API on AWS — through a governed, multi-agent workflow (MCP + A2A).

---

## 1. What this lab is

This lab shows infrastructure practitioners — **DevOps engineers, SREs, FDEs, platform engineers, ITOps, and solutions architects** — how to use IBM Bob as an *agentic coding companion* tailored to their role, rather than a generic assistant. We achieve this with a custom Bob persona (custom mode), the **"Infrastructure Engineer"** mode, and use it to prepare infrastructure and execute agentic tasks across IBM Cloud and AWS — ending with a running application that spans both clouds.

### The big picture

Bob stops being a code-completion tool and becomes a **role-aware partner**. The engineer states an outcome in one sentence; a governed persona and a multi-agent system carry it across clouds — with standards, secret hygiene, and cross-cloud delegation built in. **roles + AI = more capability and productivity.**

### What you walk away able to do

- **Use** a Bob custom mode governed by rules and skills (and tailor one to your own role).
- **Author** infrastructure with Bob via **remote MCP servers** (Terraform, Vault, Ansible on IBM Cloud Code Engine — no local containers).
- **Stand up** a multi-agent system in watsonx Orchestrate: a supervisor delegating to specialist agents.
- **Deploy** an external agent on AWS Bedrock AgentCore that exposes itself over **A2A** with Cognito JWT auth.
- **Validate** a live multi-cloud app: an IBM Cloud-hosted dashboard rendering real-time status from AWS.

---

## 2. Why this matters

Real enterprise infrastructure is rarely single-cloud. By spanning IBM Cloud (watsonx Orchestrate) and AWS (Bedrock AgentCore) we show a pattern operations teams genuinely face. The multi-agent design — a supervisor delegating to specialists — mirrors how an engineer decomposes a problem, and it showcases both open protocols in one coherent story:

- **MCP** = agent-to-tool (**vertical**). Bob authors with the Terraform/Vault/Ansible MCP servers; Orchestrate agents use their own Python tools.
- **A2A** = agent-to-agent (**horizontal**). The supervisor delegates across clouds; the AWS agent provisions *its own cloud* with its execution role — no credentials cross the boundary.

---

## 3. Lab architecture

<img width="2080" height="1151" alt="image" src="https://github.ibm.com/user-attachments/assets/8fe9bd44-9bf9-4f39-8412-5fe0618a4b3a" />



End-to-end: Bob (with three remote MCP servers on Code Engine) is the single interface. The watsonx Orchestrate supervisor delegates — frontend deploy and secrets locally, the AWS status API over A2A. The finished dashboard (IBM COS static website) fetches live `status.json` from the AWS S3 website: one request, one running app, two clouds.

**The validation scenario — Multi-Cloud Status Dashboard:**

| Component | Cloud | Deployed by | How |
|---|---|---|---|
| Dashboard frontend | IBM Cloud (COS static website) | `provisioning_agent` → `deploy_frontend` tool | IBM COS SDK from the Orchestrate tool |
| Status API (`status.json`) | AWS (S3 website + policy + CORS) | `aws_infra_agent` → `deploy_status_api` tool | boto3 **inside AWS**, execution-role creds |
| Secrets | Vault on Code Engine | `secrets_agent` → `vault_read_secret` tool | hvac; value never echoed |

---

## 4. Prerequisites & environment

Participants use a **pre-configured instance** — everything below is already installed:

| Component | Purpose |
|---|---|
| IBM Bob | Persona host; agentic coding companion |
| watsonx Orchestrate ADK (`orchestrate`) | Agents, tools, connections (shared lab instance) |
| `ibmcloud`, `aws` CLIs | Cloud operations (least-privilege lab profiles, env-injected) |
| Node.js 20 + `agentcore` CLI (`@aws/agentcore`) | Deploy the AWS agent (current tooling; the Python starter toolkit is legacy) |
| Python 3.11 + `hvac`, `boto3`, `ibm-cos-sdk` | Orchestrate tools |

Provided by the instructor at the session: 3 MCP endpoint URLs + auth header, `VAULT_ADDR`/`VAULT_TOKEN`, the COS instance CRN, and the Cognito pool/client/user.

**Credentials best practice used here:** least-privilege pre-provisioned profiles; injected via environment, never stored in the repo or typed into chat (Bob's baseline rules flag literal secrets); short-lived bearer tokens (~1 h); rotation and revocation after the event; per-seat resource naming (`txlab-dev-*-<initials>`).

---

## 5. Lab flow (6 phases, 90–120 min)

| Phase | What you do | Time |
|---|---|---|
| 0 | Clone repo → open in Bob → `/init` → install WXO Agent Architect mode | 5 |
| 1 | Verify the infra-engineer persona (4 tests) | 5 |
| 2 | Connect the 3 remote MCP servers (Code Engine endpoints) | 10 |
| 3 | Store the lab secret in Vault (via Bob + Vault MCP) | 5 |
| 4 | Build the Orchestrate side: connection, 2 tools, 3 agents (via Bob) + real secret read | 25 |
| 5 | Deploy the AWS agent: AgentCore CLI, Cognito JWT, IAM grant, agent card, register in Orchestrate | 25 |
| 6 | Run the scenario; open the live dashboard; validate | 15 |

**→ Full baby-step instructions: [docs/Hands-On_Lab_Guide.md](docs/Hands-On_Lab_Guide.md)**

---

## 6. Repository layout

```
.bob/
  custom_modes.yaml          the infra-engineer persona (custom mode)
  rules/01-basic-rules.md    baseline rules (all modes): security, output discipline
  rules-infra-engineer/      persona rules: IaC standards, WXO handoff
  skills/provision-multicloud-app/SKILL.md
agents/                      Orchestrate agents: supervisor, provisioning, secrets, aws (external A2A)
tools/                       Python tools: vault_read_secret, deploy_frontend (+ requirements)
aws-status-agent/            AWS AgentCore agent: Strands + Amazon Nova + deploy_status_api
scripts/mint_token.sh        Cognito token helper (~1 h expiry)
docs/Hands-On_Lab_Guide.md   the full step-by-step lab guide
docs/images/architecture.png
```

---

## 7. Quick start

```bash
git clone https://github.ibm.com/amashargah/us-fsm-ce-bob-infra-engineer.git <update>
cd us-fsm-ce-bob-infra-engineer
```

Open the folder in **IBM Bob**, run `/init`, and follow **[docs/Hands-On_Lab_Guide.md](docs/Hands-On_Lab_Guide.md)**. Cloning is the recommended path for the session — the persona, rules, agents, and tools are scaffolded so you focus on wiring, deploying, and understanding. Every file doubles as reference if you prefer to rebuild your own directory step by step afterward.

---

## 8. Cleanup

See the guide's Cleanup section: delete the two buckets, remove the inline IAM policy, tear down the AgentCore runtime. Instructors: revoke keys, rotate the Cognito password.

