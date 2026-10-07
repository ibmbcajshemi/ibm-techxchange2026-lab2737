# Hands-On Lab Guide — Multi-Cloud Status Dashboard with IBM Bob
## Student Edition

**Audience:** DevOps, SRE, platform, ITOps engineers, and solutions architects.
**Duration:** 90–120 minutes. **Level:** intermediate.

Conventions used below:

- `Bob ▸` — a prompt you type to Bob, in the mode named.
- Fenced blocks — commands you run in the instance terminal.
- Replace anything in `{CURLY_BRACES}` with your value. `<initials>` = your initials, lowercase, no separators (e.g. `joe`).
- ✅ **Checkpoint** — verify before moving on. Do not skip.
- If something goes wrong, consult **Section 11 — Troubleshooting** before asking for help.

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

**Step 0.1 — Clone and enter the repo.**

```bash
git clone https://github.com/ibmbcajshemi/ibm-techxchange2026-lab2737.git
cd ibm-techxchange2026-lab2737
```

**Step 0.2 — Activate the ADK virtual environment.** The Orchestrate CLI lives in a dedicated venv that must be active for every `orchestrate` command in this lab:

```bash
source .venv-wxo/bin/activate
```

**Step 0.3 — Open in Bob and initialize.** Open the folder in IBM Bob (File → Open Folder). In the Bob chat input, run:

```
/init
```

This initializes Bob's project structure. The repo already ships the persona (`.bob/custom_modes.yaml`), rules (`.bob/rules/`, `.bob/rules-infra-engineer/`), and the skill (`.bob/skills/provision-multicloud-app/`).

**Step 0.4 — Install the WXO Agent Architect mode.** In Bob: open Modes → Marketplace / built-in modes → install **watsonx Orchestrate Agent Architect**. This adds the `wxo-agent-architect` mode plus two MCP servers: `orchestrate-adk` (create/import/list agents & tools, `chat_with_agent`) and `wxo-docs` (ADK documentation search).

**Step 0.5 — Confirm bidirectional handoff.** Open `.bob/custom_modes.yaml` and confirm the `infra-engineer` mode's `groups:` list includes `modes` (it does, as shipped). If the installed `wxo-agent-architect` entry has a `groups:` list, confirm it also includes `modes`. Without this, Bob cannot switch modes for you.

**Step 0.6 — Reload Bob** (Command Palette → "Reload Window", or restart Bob).

✅ **Checkpoint 0:** the mode dropdown (bottom-left of the chat input) shows **Infrastructure Engineer** and **WXO Agent Architect**.

---

## 4. Phase 1 — Verify the persona (5 min)

Select **Infrastructure Engineer** from the mode dropdown. Run all four tests:

**Test 1 — identity.**
> Bob ▸ `Who are you and what are you optimized for?`

Expected: describes a senior infrastructure practitioner across DevOps/SRE/platform/ITOps/SA, multi-cloud (IBM Cloud + AWS), Terraform/Ansible/Vault, MCP + A2A.

**Test 2 — secure-by-default authoring.**
> Bob ▸ `Draft a tiny Terraform snippet that uses a database password.`

Expected: the password comes from a **Vault `data "vault_kv_secret_v2"` data source** — never a literal or a default-valued variable — and the answer ends with an engineer review checklist. The Vault path will follow the project convention: `secret/{project}/{env}/{key}`.

**Test 3 — skill activation.**
> Bob ▸ `Provision a small app across IBM Cloud and AWS, store secrets in Vault.`

Expected: the `provision-multicloud-app` skill activates — Bob restates scope in 2–3 lines, lists assumptions, asks up to 3 clarifying questions.

**Test 4 — handoff rule.**
> Bob ▸ `Create a new watsonx Orchestrate agent for provisioning.`

Expected: Bob proposes switching to `wxo-agent-architect`, citing the mode boundary rule.

✅ **Checkpoint 1:** all four behave as described. If Test 2 inlines a password, the rules didn't load — confirm `.bob/rules-infra-engineer/` exists and reload Bob.

---

## 5. Phase 2 — Connect the remote MCP servers (10 min)

The three MCP servers run on **IBM Cloud Code Engine** — remote HTTPS endpoints. No local containers needed.

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

Expected: a real registry answer — e.g. `IBM-Cloud/ibm v2.x.x` with data sources `ibm_cos_bucket` and `ibm_cos_bucket_object`.

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

The path follows the project convention: `secret/{project}/{env}/{key}` (e.g. `secret/txlab/dev/ibm-api-key`). Note: Vault KV v2 inserts `/data/` internally — so the policy path is `secret/data/txlab/dev/ibm-api-key`, not `secret/txlab/dev/ibm-api-key`.

✅ **Checkpoint 3:** the path `secret/txlab/dev/ibm-api-key` exists and is readable; no value was printed to chat.

---

## 7. Phase 4 — Build the Orchestrate side (25 min)

### Step 4.0 — Personalize your resource names

You share one Orchestrate instance with all lab participants. Run this script **once** — it stamps your initials on the **tool, agent, and connection names registered inside the files**. The filenames themselves (`deploy_frontend.py`, `vault_read_secret.py`, `secrets_agent.yaml`, etc.) are never renamed:

```bash
bash scripts/personalize.sh
```

Enter your initials when prompted (e.g. `joe`). The script patches tool/agent/connection names in-place across `tools/` and `agents/` and prints your copy-paste ready Phase 4 commands.

> **Use the commands printed by the script for Steps 4.2 and 4.3 — not the generic names shown below.**

Before running any `orchestrate tools import`, verify both files are patched:

```bash
# Check — both must show your initials suffix
grep '@tool(name=' tools/vault_read_secret.py
grep '@tool(name=' tools/deploy_frontend.py
```

### Step 4.1 — Review the Vault tool

Open `tools/vault_read_secret.py` and read it. There are three occurrences of `vault_read_secret` in the file:

| Line | What it is | Needs initials? |
|---|---|---|
| `"clientInfo": {"name": "vault_read_secret"}` | JSON-RPC handshake label to the MCP server — ignored for routing | ❌ No |
| `@tool(name="vault_read_secret_<initials>", …)` | **Orchestrate registration name** — what agents reference | ✅ Yes — must match |
| `def vault_read_secret(` | Python function name — Orchestrate never reads it | ❌ No |

The Vault URL and token are injected at runtime through the `vault_creds` connection created in Step 4.2 — no manual URL substitution needed.

### Step 4.2 — Create the connections

This injects credentials into the tools as key-value dictionaries — the secure alternative to hardcoding.

```bash
source .venv-wxo/bin/activate
orchestrate env activate {LAB_ENV_NAME}     # the shared lab environment, per instructor

# cloud_creds — for the COS deploy tool
orchestrate connections add -a cloud_creds_<initials>
orchestrate connections configure -a cloud_creds_<initials> --env draft --type team --kind key_value
orchestrate connections set-credentials -a cloud_creds_<initials> --env draft \
  -e "IBM_COS_API_KEY=$IBMCLOUD_API_KEY" \
  -e "IBM_COS_INSTANCE_ID=$COS_CRN" \
  -e "IBM_COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud"

# vault_creds — for the Vault read tool
orchestrate connections add -a vault_creds_<initials>
orchestrate connections configure -a vault_creds_<initials> --env draft --type team --kind key_value
orchestrate connections set-credentials -a vault_creds_<initials> --env draft \
  -e "VAULT_TOKEN={VAULT_TOKEN}" \
  -e "VAULT_ADDR={VAULT_ADDR}"
```

Expected output for each command: `Successfully created connection` / `Configuration successfully created` / `Credentials successfully set`.

### Step 4.3 — Import the two tools

The tool module is parsed **locally at import time**, so its libraries must exist in the ADK's Python environment. The `--requirements-file` flag (long form) is required — `-r` is the short form:

```bash
pip install boto3 ibm-cos-sdk
orchestrate tools import -k python \
  -f tools/vault_read_secret.py \
  --requirements-file tools/vault_requirements.txt \
  -a vault_creds_<initials>

orchestrate tools import -k python \
  -f tools/deploy_frontend.py \
  --requirements-file tools/cloud_requirements.txt \
  -a cloud_creds_<initials>

orchestrate tools list   # expect: vault_read_secret_<initials>, deploy_frontend_<initials>
```

### Step 4.4 — Import the agents

Import using the original filenames — they are never renamed. `personalize.sh` only edits the `name:` values inside the files. Import order matters (tools → leaf agents → supervisor):

```bash
# Filenames are unchanged — personalize.sh patched the name values inside each file
orchestrate agents import -f agents/secrets_agent.yaml
orchestrate agents import -f agents/provisioning_agent.yaml
orchestrate agents import -f agents/infra_supervisor.yaml
orchestrate agents list
```

Or via Bob (switch to **WXO Agent Architect** mode first):
> Bob ▸ `Using the orchestrate-adk MCP server: first list existing agents and tools. Then import these agents from the agents/ folder, in this order: secrets_agent, provisioning_agent, infra_supervisor. Do NOT import aws_infra_agent yet (its token comes in Phase 5). Confirm the result with list_agents.`

### Step 4.5 — Prove a real secret read

> Bob ▸ (wxo-agent-architect) `Use chat_with_agent to send this to infra_supervisor_<initials>: "Read the IBM API key reference from Vault and tell me which path you used." Show me the response.`

Expected: the reply names the path `txlab/dev/ibm-api-key` and field `api_key`, **value withheld**. That is a live supervisor → secrets_agent → vault_read_secret → Vault-on-Code-Engine chain.

✅ **Checkpoint 4:** confirmed.

---

## 8. Phase 5 — Deploy the AWS agent on Bedrock AgentCore (25 min)

The AWS agent (`aws-status-agent/a2a_server.py`) is a **Strands** agent on **Amazon Nova** with two tools:
- `aws_resource_check` — returns a health string for the AWS side
- `deploy_status_api` — creates S3 bucket → disables public-access blocks → applies public-read bucket policy → sets CORS → uploads `status.json` → configures website endpoint → returns the URL. Uses `boto3.client("s3")` with **no explicit credentials** — the AgentCore execution role provides them at runtime.

### Step 5.1 — Verify Nova access

```bash
aws bedrock-runtime invoke-model --region us-east-1 \
  --model-id us.amazon.nova-lite-v1:0 \
  --body '{"messages":[{"role":"user","content":[{"text":"hi"}]}],"inferenceConfig":{"maxTokens":10}}' \
  --cli-binary-format raw-in-base64-out /tmp/nova.json && cat /tmp/nova.json
```

Expected: JSON with `"role": "assistant"` and `"stopReason": "max_tokens"`. The `"contentType": "application/json"` line printed before the JSON is a CLI header — not an error.

### Step 5.2 — Scaffold with the AgentCore CLI
> **Note:** The `--project-name` flag requires alphanumeric only (no underscores or dashes), max 23 chars. Use your initials concatenated directly (e.g. `statusagentjoe`).


```bash
cd aws-status-agent
agentcore create \
  --name statusagent<initials> \
  --project-name statusagent<initials> \
  --framework Strands \
  --protocol A2A \
  --model-provider Bedrock \
  --memory none
```

Find the scaffolded `main.py` path and replace it with the lab's agent code:

```bash
# Confirm the exact target path first
ls aws-status-agent/statusagent<initials>/app/

# Then copy — path pattern is app/<project-name>/<project-name>/main.py
cp a2a_server.py statusagent<initials>/app/statusagent<initials>/main.py
```

Verify the copy worked:

```bash
head -5 statusagent<initials>/app/statusagent<initials>/main.py
```

Expected first line: `import logging, os, json, datetime` — confirms the lab code is in place.

Optional local smoke test (requires Docker):

```bash
agentcore dev   # Ctrl-C to stop
```

### Step 5.3 — Configure JWT auth (Cognito) and deploy
Configure JWT auth by **directly editing** `agentcore.json`:


Open `aws-status-agent/statusagent<initials>/agentcore/agentcore.json` and add two fields inside the `runtimes[0]` object, after `"protocol": "A2A"`:

```json
"authorizerType": "CUSTOM_JWT",
"authorizerConfiguration": {
  "customJwtAuthorizer": {
    "discoveryUrl": "https://cognito-idp.us-east-1.amazonaws.com/{COGNITO_POOL_ID}/.well-known/openid-configuration",
    "allowedClients": ["{COGNITO_CLIENT_ID}"]
  }
}
```

Replace `{COGNITO_POOL_ID}` (format: `us-east-1_xxxxxxxxx`) and `{COGNITO_CLIENT_ID}` with your instructor-provided values **in your editor**, not in chat.

Then deploy (first deploy bootstraps and takes a few minutes):

```bash
cd statusagent<initials>
agentcore deploy
```

**Write down the runtime ARN** from the output. URL-encode it for later: replace every `:` with `%3A` and `/` with `%2F`.

### Step 5.4 — Grant the execution role the S3 permissions
> **Do not skip this step.** Without the IAM policy, `deploy_status_api` will fail when it tries to create the S3 bucket.


```bash
cd ../..   # back to repo root
ROLE=$(aws iam list-roles --query "Roles[?contains(RoleName,'AgentCore')].RoleName" --output text)
echo "$ROLE"
```

If multiple roles are returned, identify yours by the agent name (e.g. `AgentCore-statusagentjoe-…`). Then set it explicitly:

```bash
ROLE="<your-role-name-from-above>"
aws iam put-role-policy --role-name "$ROLE" --policy-name TxLabStatusApi \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
   "Action":["s3:CreateBucket","s3:PutObject","s3:PutBucketPolicy","s3:PutBucketWebsite",
   "s3:PutBucketCors","s3:PutPublicAccessBlock","s3:PutBucketPublicAccessBlock"],"Resource":"*"}]}'
```

> IAM changes can take ~1 minute to propagate — wait before proceeding.

### Step 5.5 — Mint a token and verify the agent card

Export each Cognito credential as a **separate `export` statement** — keep `COGNITO_PASS` on its own line so the password does not appear alongside other values in shell history:

```bash
export COGNITO_CLIENT_ID={COGNITO_CLIENT_ID}
export COGNITO_USER={COGNITO_USER}
export COGNITO_PASS='{COGNITO_PASS}'
TOKEN=$(../scripts/mint_token.sh)
echo ${#TOKEN}     # must print ~1000; if 0, check the three vars are set
```

Verify the agent card. **The token stays in the shell variable — do not print it, copy-paste it, or embed it in any chat message:**

```bash
curl -s -H "Authorization: Bearer $TOKEN" -H "Accept: */*" \
  -H "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id: 12345678-1234-1234-1234-123456789abc" \
  "https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/{URL_ENCODED_ARN}/invocations/.well-known/agent-card.json"
```

Expected: JSON containing `"name"`, `"skills"` listing `aws_resource_check` and `deploy_status_api`.

### Step 5.6 — Register the AWS agent in Orchestrate

Inject the runtime ARN and bearer token into `agents/aws_infra_agent.yaml` using `sed` — **do not** copy-paste the token by hand, as it can end up in shell history, clipboard history, or visible in chat:

```bash
# Substitute the URL-encoded ARN
sed -i "s|{URL_ENCODED_ARN}|<your-url-encoded-arn>|" agents/aws_infra_agent.yaml

# Inject the token from the shell variable — value is never exposed as plain text
sed -i "s|token: \".*\"|token: \"${TOKEN}\"|" agents/aws_infra_agent.yaml
```

Restore `aws_infra_agent_<initials>` to the `collaborators:` list in `agents/infra_supervisor.yaml` if it was removed in Step 4.4. Then import:

```bash
orchestrate agents import -f agents/aws_infra_agent.yaml
orchestrate agents import -f agents/infra_supervisor.yaml    # refresh collaborator binding
```

✅ **Checkpoint 5:** the agent card curl returns 200 with both skills listed, and `orchestrate agents list` shows `aws_infra_agent_<initials>` under External Agents.

---

## 9. Phase 6 — Run it and validate (15 min)

**Step 6.1 — The cross-cloud health check (warm-up).**

> Bob ▸ (wxo-agent-architect) `Use chat_with_agent to send this to infra_supervisor_<initials>: "Check whether the AWS side of the lab is healthy." Show me the response.`

Expected: the supervisor delegates over A2A; the Nova agent reasons and calls `aws_resource_check`, returning "healthy".

**Step 6.2 — Deploy the app.**

> Bob ▸ `Use chat_with_agent to send this to infra_supervisor_<initials>: "Deploy the multi-cloud status dashboard. First have the AWS agent deploy the status API to bucket txlab-dev-status-<initials>. Then deploy the frontend to COS bucket txlab-dev-dashboard-<initials>, wired to the status URL the AWS agent returns." Show me the full response.`

What happens: supervisor → `aws_infra_agent` (A2A) → `deploy_status_api` creates the S3 website and returns the `status.json` URL → supervisor → `provisioning_agent` → `deploy_frontend` creates the COS website with the dashboard pointing at that URL.

> **Note:** This call traverses multiple hops with LLM inference at each — expect 1–3 minutes end-to-end.

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
cd aws-status-agent/statusagent<initials> && agentcore remove agent --name statusagent<initials>
```

Instructors additionally: revoke the Service ID key, rotate the Cognito lab password, remove per-seat resources.

---

## 11. Troubleshooting

| Symptom | Cause → fix |
|---|---|
| **`orchestrate` commands fail or return auth errors mid-lab** | The Orchestrate session token has expired. Re-activate the environment: `source .venv-wxo/bin/activate && orchestrate env activate {LAB_ENV_NAME}`. Then retry the failing command. |
| A2A call returns **401** | Cognito JWT expired (~1 h). Full recovery sequence: (1) re-mint: `TOKEN=$(aws cognito-idp initiate-auth --region us-east-1 --auth-flow USER_PASSWORD_AUTH --client-id "$COGNITO_CLIENT_ID" --auth-parameters "{\"USERNAME\":\"$COGNITO_USER\",\"PASSWORD\":\"$COGNITO_PASS\"}" --query 'AuthenticationResult.AccessToken' --output text)` and verify `echo ${#TOKEN}` prints ~1000; (2) re-inject: `sed -i "s\|token: \".*\"\|token: \"${TOKEN}\"\|" agents/aws_infra_agent.yaml`; (3) re-import: `orchestrate agents import -f agents/aws_infra_agent.yaml`; (4) **fully restart** the Bob chat session. |
| AWS tool returns **AccessDenied** | Execution role missing S3 permissions → re-run Step 5.4. If you lack `iam:PutRolePolicy`, ask your instructor to apply the policy; they can verify with `aws iam get-role-policy --role-name "$ROLE" --policy-name TxLabStatusApi`. Wait ~1 min for IAM to propagate. |
| `deploy_status_api` fails on `PutBucketPublicAccessBlock` | Policy is missing `s3:PutBucketPublicAccessBlock` (bucket-scoped variant) — update the inline policy to add it alongside `s3:PutPublicAccessBlock`. |
| AWS agent replies **empty** or times out | Re-run the Nova test (Step 5.1). If you got `AccessDeniedException`, open the AWS console → Bedrock → Model access → enable **Amazon Nova Lite**. If Strands defaulted to a Claude model, confirm your `a2a_server.py` kept the `BedrockModel(... nova-lite ...)` line. |
| Dashboard shows **unreachable** | CORS/public policy on the AWS bucket → open `status.json` directly; if it loads but the dashboard fails, re-run `deploy_status_api` (it reapplies CORS). |
| `tools import` fails: **No module named …** | Install the library in the ADK Python env (`pip install boto3 ibm-cos-sdk`) — tools are parsed locally at import time. |
| `tools import` via Bob MCP fails with `ibm_boto3` error | Expected — the Bob MCP sandbox doesn't have `ibm_boto3`. Run `orchestrate tools import` from the terminal with `.venv-wxo` active. |
| `personalize.sh` did not stamp initials on the `@tool(name=…)` decorator | The script has an end-of-line anchor bug. Patch manually: `sed -i "s\|name=\"vault_read_secret\",\|name=\"vault_read_secret_${INITIALS}\",\|" tools/vault_read_secret.py` and the same for `deploy_frontend.py`. Re-verify with `grep '@tool(name=' tools/*.py`, then re-import both tools. |
| A stray `deploy_frontend` (no suffix) appears in `orchestrate tools list` | The tool was imported before the `@tool` name was patched. It is safe to ignore — agents reference the suffixed name. Re-import after patching to register the correct name. |
| `agents/secrets_agent.yaml` import fails — tool not found | The `@tool(name=…)` decorator on `vault_read_secret.py` was not patched. Run the manual `sed` fix (see row above), re-import the tool, then re-import the agent. |
| Agent import fails: **collaborator not found** | Import order — leaf agents must be imported before the supervisor. If `aws_infra_agent` does not exist yet (it is created in Phase 5), temporarily remove it from `infra_supervisor.yaml` collaborators, import the supervisor, then re-add it and re-import after Phase 5. |
| Supervisor asks a clarifying question instead of routing to the AWS agent | Follow up with: `Use aws_infra_agent_<initials> to run aws_resource_check and report the result.` |
| `mint_token.sh` returns 0 (empty token) | Mint directly: `TOKEN=$(aws cognito-idp initiate-auth --region us-east-1 --auth-flow USER_PASSWORD_AUTH --client-id "$COGNITO_CLIENT_ID" --auth-parameters "{\"USERNAME\":\"$COGNITO_USER\",\"PASSWORD\":\"$COGNITO_PASS\"}" --query 'AuthenticationResult.AccessToken' --output text)` then verify `echo ${#TOKEN}` prints ~1000. Confirm all three env vars (`COGNITO_CLIENT_ID`, `COGNITO_USER`, `COGNITO_PASS`) are exported. |
| Agent narrates a **"plan"** instead of a result | Re-import the agent YAMLs as shipped — their instructions say "report the tool result exactly; do not present it as a plan." Use `style: react_core` (not `react`) to avoid the deprecation warning. |
| `orchestrate agents import` prints deprecation warning about `style: react` | Run `sed -i 's/style: react$/style: react_core/' agents/infra_supervisor.yaml` then re-import. |

