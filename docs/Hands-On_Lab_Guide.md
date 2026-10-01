# Hands-On Lab Guide — Multi-Cloud Status Dashboard with IBM Bob

**Audience:** DevOps, SRE, platform, ITOps engineers, and solutions architects.
**Duration:** 90–120 minutes. **Level:** intermediate.

Conventions used below:

- `Bob ▸` — a prompt you type to Bob, in the mode named.
- Fenced blocks — commands you run in the instance terminal.
- Replace anything in `{CURLY_BRACES}` with your value. `<initials>` = your initials, lowercase.
- ✅ **Checkpoint** — verify before moving on. Do not skip.

---

## 1. What you will build

A minimal but real **two-cloud application**, provisioned end-to-end by AI agents:

- **Frontend** — a status dashboard served as an **IBM Cloud Object Storage static website**.
- **Status API** — a public `status.json` served from an **AWS S3 website**, deployed by an agent *running inside AWS*.
- **The wiring** — the dashboard fetches live status from AWS on page load. One app, two clouds.

You drive everything through **IBM Bob** with a role-aware **infra-engineer** persona. Bob authors using **remote MCP servers** (Terraform, Vault, Ansible — three IBM Cloud Code Engine endpoints) and dispatches execution to a **watsonx Orchestrate** multi-agent system, which bridges to **AWS Bedrock AgentCore** over **A2A** with bearer-token (Cognito JWT) auth.

**Mental model:** MCP = agent-to-tool (vertical). A2A = agent-to-agent (horizontal, cross-cloud).

<img width="2080" height="1151" alt="image" src="https://github.ibm.com/user-attachments/assets/06f5782d-ad3f-4d68-90e1-b2a1cc786987" />


---

## 2. Your environment and credentials

Your pre-configured instance has: IBM Bob, the watsonx Orchestrate ADK (`orchestrate`, connected to the shared lab instance), `ibmcloud`, `aws`, Node.js 20 + `agentcore` CLI, Python 3.11 with lab libraries.

Values your instructor provides (write them down now):

| Value | Used in |
|---|---|
| `TERRAFORM_MCP_URL`, `VAULT_MCP_URL`, `ANSIBLE_MCP_URL` (+ auth header) | Phase 2 |
| `VAULT_ADDR` (Code Engine Vault URL) + `VAULT_TOKEN` | Phases 3–4 |
| `COS_CRN` (Cloud Object Storage instance CRN) | Phase 4 |
| `COGNITO_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_USER`, `COGNITO_PASS` | Phase 5 |

Credentials hygiene: AWS and IBM Cloud credentials are pre-provisioned, least-privilege, injected via environment — never typed into files or chat. Verify (no keys involved):

```bash
aws sts get-caller-identity
ibmcloud login          # uses IBMCLOUD_API_KEY from the environment
```

---

## 3. Phase 0 — Get the project and initialize Bob (5 min)

**Step 0.1 — Clone and enter the repo.** This is your working directory for the whole lab.

```bash
git clone https://github.ibm.com/amashargah/us-fsm-ce-bob-infra-engineer.git
cd us-fsm-ce-bob-infra-engineer
```

**Step 0.2 — Open in Bob and initialize.** Open the folder in IBM Bob (File → Open Folder). In the Bob chat input, run:

```
/init
```

This initializes Bob's project structure. The repo already ships the persona (`.bob/custom_modes.yaml`), rules (`.bob/rules/`, `.bob/rules-infra-engineer/`), and the skill (`.bob/skills/provision-multicloud-app/`).

**Step 0.3 — Install the WXO Agent Architect mode.** In Bob: open Modes → Marketplace / built-in modes → install **watsonx Orchestrate Agent Architect**. This adds the `wxo-agent-architect` mode plus two MCP servers: `orchestrate-adk` (create/import/list agents & tools, `chat_with_agent`) and `wxo-docs` (ADK documentation search).

**Step 0.4 — Confirm bidirectional handoff.** Open `.bob/custom_modes.yaml` and confirm the `infra-engineer` mode's `groups:` list includes `modes` (it does, as shipped). If the installed `wxo-agent-architect` entry has a `groups:` list, confirm it also includes `modes`. Without this, Bob cannot switch modes for you and every handoff becomes manual.

**Step 0.5 — Reload Bob** (Command Palette → "Reload Window", or restart Bob).

✅ **Checkpoint 0:** the mode dropdown (bottom-left of the chat input) shows **Infrastructure Engineer** and **WXO Agent Architect**.

---

## 4. Phase 1 — Verify the persona (5 min)

Select **Infrastructure Engineer** from the mode dropdown. Run all four tests:

**Test 1 — identity.**
> Bob ▸ `Who are you and what are you optimized for?`

Expected: describes a senior infrastructure practitioner across DevOps/SRE/platform/ITOps/SA, multi-cloud (IBM Cloud + AWS), Terraform/Ansible/Vault, MCP + A2A.

**Test 2 — secure-by-default authoring.**
> Bob ▸ `Draft a tiny Terraform snippet that uses a database password.`

Expected: the password comes from a **Vault provider data source** — never a literal or a default-valued variable — and the answer ends with an engineer review checklist.

**Test 3 — skill activation.**
> Bob ▸ `Provision a small app across IBM Cloud and AWS, store secrets in Vault.`

Expected: the `provision-multicloud-app` skill activates — Bob restates scope in 2–3 lines, lists assumptions, asks up to 3 clarifying questions.

**Test 4 — handoff rule.**
> Bob ▸ `Create a new watsonx Orchestrate agent for provisioning.`

Expected: Bob proposes switching to `wxo-agent-architect`, citing the handoff rule.

✅ **Checkpoint 1:** all four behave as described. If Test 2 inlines a password, the rules didn't load — confirm `.bob/rules-infra-engineer/` exists and reload Bob.

---

## 5. Phase 2 — Connect the remote MCP servers (10 min)

The three MCP servers run on **IBM Cloud Code Engine** — remote HTTPS endpoints. No local containers, no Docker/Podman on your instance.

**Step 2.1 — Add the three servers in Bob.** Open Bob → Settings → MCP Servers → Add server. For each, choose **Remote (streamable HTTP)** and enter:

| Name | URL | Header |
|---|---|---|
| `terraform-mcp` | `{TERRAFORM_MCP_URL}` | `Authorization: Bearer {MCP_LAB_TOKEN}` |
| `vault-mcp` | `{VAULT_MCP_URL}` | `Authorization: Bearer {MCP_LAB_TOKEN}` |
| `ansible-mcp` | `{ANSIBLE_MCP_URL}` | `Authorization: Bearer {MCP_LAB_TOKEN}` |

If your Bob build uses a JSON MCP config instead, the equivalent entry per server is:

```json
{ "terraform-mcp": { "type": "streamable-http",
    "url": "{TERRAFORM_MCP_URL}",
    "headers": { "Authorization": "Bearer {MCP_LAB_TOKEN}" } } }
```

**Step 2.2 — Enable the servers for the infra-engineer mode** (Bob → MCP → toggle each server on for the current project).

**Step 2.3 — Exercise one server end-to-end.**
> Bob ▸ `Using the terraform-mcp server, look up the latest version of the IBM Cloud provider and list two of its data sources for Cloud Object Storage.`

Expected: a real registry answer (current version number + data source names) — proof the remote MCP path works.

✅ **Checkpoint 2:** all three servers show connected in Bob's MCP panel, and the Terraform lookup returns live registry data.

---

## 6. Phase 3 — Store the lab secrets in Vault (5 min)

Vault runs on Code Engine (shared, dev-mode, lab token). Two ways — do **A** (through Bob, the agentic way); **B** is the CLI fallback.

**A — via Bob and the Vault MCP:**
> Bob ▸ `Using the vault-mcp server, store a secret at secret/txlab/dev/ibm-api-key with a field named api_key set to the placeholder value lab-placeholder-key. Then list the path to confirm it exists — do not print the value.`

**B — via the Vault CLI:**

```bash
export VAULT_ADDR={VAULT_ADDR}
export VAULT_TOKEN={VAULT_TOKEN}
vault kv put secret/txlab/dev/ibm-api-key api_key=lab-placeholder-key
vault kv get -field=api_key secret/txlab/dev/ibm-api-key >/dev/null && echo "secret readable"
```

✅ **Checkpoint 3:** the path `secret/txlab/dev/ibm-api-key` exists and is readable; no value was printed to chat.

---

## 7. Phase 4 — Build the Orchestrate side (25 min)

### Step 4.1 — Point the Vault tool at the Code Engine Vault

Open `tools/vault_read_secret.py`. Find the line:

```python
addr = os.environ.get("VAULT_ADDR", "https://VAULT_CE_URL_HERE")
```

Replace `https://VAULT_CE_URL_HERE` with your `{VAULT_ADDR}`. Save. (The tool reads a KV v2 field via `hvac` and confirms access **without echoing the value** — open the file and read it; it's 20 lines.)

### Step 4.2 — Create the cloud_creds connection

This injects COS credentials into the frontend tool as a key-value dictionary — the secure alternative to hardcoding.

```bash
orchestrate env activate {LAB_ENV_NAME}     # the shared lab environment, per instructor
orchestrate connections add -a cloud_creds
orchestrate connections configure -a cloud_creds --env draft --type team --kind key_value
orchestrate connections set-credentials -a cloud_creds --env draft \
  -e "IBM_COS_API_KEY=$IBMCLOUD_API_KEY" \
  -e "IBM_COS_INSTANCE_ID={COS_CRN}" \
  -e "IBM_COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud"
```

Expected output for each command: `Successfully created connection` / `Configuration successfully created` / `Credentials successfully set`.

### Step 4.3 — Import the two tools

The tool module is parsed **locally at import time**, so its libraries must exist in the ADK's Python environment too:

```bash
pip install hvac boto3 ibm-cos-sdk
orchestrate tools import -k python -f tools/vault_read_secret.py -r tools/vault_requirements.txt
orchestrate tools import -k python -f tools/deploy_frontend.py -r tools/cloud_requirements.txt -a cloud_creds
orchestrate tools list        # expect: vault_read_secret, deploy_frontend
```

Note the `-a cloud_creds` on the second import — that flag binds the tool to the connection you created in 4.2.

### Step 4.4 — Let Bob create the agents

Switch to **WXO Agent Architect** mode (or ask infra-engineer to hand off). Then:

> Bob ▸ `Using the orchestrate-adk MCP server: first list existing agents and tools. Then import these agents from the agents/ folder, in this order: secrets_agent, provisioning_agent, infra_supervisor. Do NOT import aws_infra_agent yet (its token comes in Phase 5). Confirm the result with list_agents.`

Bob runs the `import_agent` MCP operations and reports. CLI fallback if you prefer:

```bash
orchestrate agents import -f agents/secrets_agent.yaml
orchestrate agents import -f agents/provisioning_agent.yaml
orchestrate agents import -f agents/infra_supervisor.yaml
orchestrate agents list
```

(The supervisor lists `aws_infra_agent` as a collaborator that doesn't exist yet — if your ADK version rejects the import for that reason, temporarily remove that line from `agents/infra_supervisor.yaml`, import, and re-add + re-import after Phase 5.)

### Step 4.5 — Prove a real secret read

> Bob ▸ (wxo-agent-architect) `Use chat_with_agent to send this to infra_supervisor: "Read the IBM API key reference from Vault and tell me which path you used." Show me the response.`

✅ **Checkpoint 4:** the reply names the real path `secret/txlab/dev/ibm-api-key` and field `api_key`, **value withheld**. That is a live agent → tool → Vault-on-Code-Engine read.

---

## 8. Phase 5 — Deploy the AWS agent on Bedrock AgentCore (25 min)

The AWS agent (`aws-status-agent/a2a_server.py`) is a **Strands** agent on **Amazon Nova** with two tools: `aws_resource_check` (health) and `deploy_status_api` (deploys the AWS half of the app using the **execution role's** credentials — no keys cross clouds). Open the file and read the `deploy_status_api` tool: create bucket → public-read policy → CORS → upload `status.json` → website config → return the URL.

### Step 5.1 — Verify Nova access (one command)

```bash
aws bedrock-runtime invoke-model --region us-east-1 \
  --model-id us.amazon.nova-lite-v1:0 \
  --body '{"messages":[{"role":"user","content":[{"text":"hi"}]}],"inferenceConfig":{"maxTokens":10}}' \
  --cli-binary-format raw-in-base64-out /tmp/nova.json && cat /tmp/nova.json
```

Expected: a short JSON completion. (Nova enables on first use — no access form. This is why the lab uses Nova.)

### Step 5.2 — Scaffold with the AgentCore CLI

```bash
cd aws-status-agent
agentcore create --name status_agent --framework Strands --protocol A2A --model-provider Bedrock
```

This scaffolds an AgentCore project (config + `app/` folder). Replace the generated agent code with the lab's `a2a_server.py` content (same file, our tools + Nova model). Optional local smoke test:

```bash
agentcore dev        # Ctrl-C to stop
```

### Step 5.3 — Configure JWT auth (Cognito) and deploy

Configure the agent's inbound auth as a **custom JWT authorizer** pointing at the lab Cognito pool — per the CLI's identity configuration (see `agentcore add --help` / the project's `agentcore.json`), supplying:

```
discoveryUrl:   https://cognito-idp.us-east-1.amazonaws.com/{COGNITO_POOL_ID}/.well-known/openid-configuration
allowedClients: ["{COGNITO_CLIENT_ID}"]
```

Then deploy (first deploy bootstraps and takes a few minutes):

```bash
agentcore deploy
```

**Write down the runtime ARN** from the output. URL-encode it for later: replace every `:` with `%3A` and `/` with `%2F`.

### Step 5.4 — Grant the execution role the S3 permissions

```bash
ROLE=$(aws iam list-roles --query "Roles[?contains(RoleName,'AgentCore')].RoleName" --output text)
echo "$ROLE"
aws iam put-role-policy --role-name "$ROLE" --policy-name TxLabStatusApi \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
   "Action":["s3:CreateBucket","s3:PutObject","s3:PutBucketPolicy","s3:PutBucketWebsite",
   "s3:PutBucketCors","s3:PutPublicAccessBlock"],"Resource":"*"}]}'
```

If a later tool call returns **AccessDenied**, this role/policy is the fix (IAM can take ~1 min to propagate).

### Step 5.5 — Mint a token and verify the agent card

```bash
export COGNITO_CLIENT_ID={COGNITO_CLIENT_ID} COGNITO_USER={COGNITO_USER} COGNITO_PASS='{COGNITO_PASS}'
TOKEN=$(../scripts/mint_token.sh)
curl -s -H "Authorization: Bearer $TOKEN" -H "Accept: */*" \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: 12345678-1234-1234-1234-123456789abc" \
  "https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{URL_ENCODED_ARN}/invocations/.well-known/agent-card.json"
```

Expected: JSON containing `"name"`, `"skills"` listing `aws_resource_check` and `deploy_status_api`.

### Step 5.6 — Register the AWS agent in Orchestrate

Edit `agents/aws_infra_agent.yaml`: set `api_url` with your `{URL_ENCODED_ARN}` and paste the `$TOKEN` value into `auth_config.token` (keep the quotes, one line). Then:

```bash
cd ..
orchestrate agents import -f agents/aws_infra_agent.yaml
orchestrate agents import -f agents/infra_supervisor.yaml    # refresh collaborator binding
```

✅ **Checkpoint 5:** the agent card curl returns 200 with both skills, and `orchestrate agents list` shows `aws_infra_agent` under External Agents.

> ⏱ **Tokens expire in ~1 hour.** Any later 401 on the A2A hop = re-mint, update the YAML token, re-import `aws_infra_agent`, and **fully restart** the chat session.

---

## 9. Phase 6 — Run it and validate (15 min)

**Step 6.1 — The cross-cloud health check (warm-up).**

> Bob ▸ (wxo-agent-architect) `Use chat_with_agent to send this to infra_supervisor: "Check whether the AWS side of the lab is healthy." Show me the response.`

Expected: the supervisor delegates over A2A; the Nova agent reasons and answers "healthy". No error banner.

**Step 6.2 — Deploy the app.**

> Bob ▸ `Use chat_with_agent to send this to infra_supervisor: "Deploy the multi-cloud status dashboard. First have the AWS agent deploy the status API to bucket txlab-dev-status-<initials>. Then deploy the frontend to COS bucket txlab-dev-dashboard-<initials>, wired to the status URL the AWS agent returns." Show me the full response.`

What happens: supervisor → `aws_infra_agent` (A2A) → `deploy_status_api` creates the S3 website and returns the `status.json` URL → supervisor → `provisioning_agent` → `deploy_frontend` creates the COS website with the dashboard pointing at that URL.

**Step 6.3 — Validate the running app.** From the response, copy:

1. The **status URL** — open it: raw JSON, `"status": "healthy"` with a timestamp. That is AWS.
2. The **dashboard URL** — open it: the styled page renders **"AWS component: healthy — deployed <timestamp>"**, fetched live from AWS by your browser. That page is served by IBM Cloud.

✅ **Checkpoint 6 (final):** the dashboard shows live AWS status. One request → a running application spanning both clouds, with MCP and A2A each visibly doing their job.

---

## 10. Cleanup

```bash
aws s3 rb s3://txlab-dev-status-<initials> --force
# Delete the COS dashboard bucket in the IBM Cloud console (Storage → your instance → bucket → Delete)
aws iam delete-role-policy --role-name "$ROLE" --policy-name TxLabStatusApi
cd aws-status-agent && agentcore remove agent --name status_agent   # then tear down deployed resources per CLI docs
```

Instructors additionally: revoke the Service ID key, rotate the Cognito lab password, remove per-seat resources.

---

## 11. Troubleshooting

| Symptom | Cause → fix |
|---|---|
| A2A call returns **401** | Cognito token expired (~1 h). Re-mint (`scripts/mint_token.sh`), update `auth_config.token`, re-import `aws_infra_agent`, restart the chat. |
| AWS tool returns **AccessDenied** | Execution role missing an S3 action → re-run Step 5.4; wait ~1 min for IAM. |
| AWS agent replies **empty** | Model access → re-run the Nova test (Step 5.1). If Strands defaulted to a Claude model, that requires a use-case form — the lab's code pins Nova; confirm your `a2a_server.py` kept the `BedrockModel(... nova-lite ...)` line. |
| Dashboard shows **unreachable** | CORS/public policy on the AWS bucket → open `status.json` directly; if it loads but the dashboard fails, re-run `deploy_status_api` (it reapplies CORS). |
| `tools import` fails: **No module named …** | Install the library in the ADK Python env (`pip install hvac boto3 ibm-cos-sdk`) — tools are parsed locally at import time. |
| Agent import fails: **collaborator not found** | Import order — specialists and the external agent before the supervisor. |
| Agent narrates a **"plan"** instead of a result | Re-import the agent YAMLs as shipped — their instructions say "report the tool result exactly; do not present it as a plan." |

