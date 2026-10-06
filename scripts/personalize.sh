#!/usr/bin/env bash
# =============================================================================
# scripts/personalize.sh
# Adds student initials suffix to all tool, agent, and connection names
# so shared-instance imports do not overwrite each other.
#
# Usage:
#   bash scripts/personalize.sh
#   bash scripts/personalize.sh ckg        # pass initials directly
# =============================================================================
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Get initials ──────────────────────────────────────────────────────────────
if [[ -n "${1:-}" ]]; then
  INITIALS="${1}"
else
  read -rp "Enter your initials (e.g. ckg): " INITIALS
fi

# Lowercase and strip anything that is not a-z or 0-9
INITIALS=$(echo "$INITIALS" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9')

if [[ -z "$INITIALS" ]]; then
  echo "ERROR: initials cannot be empty." >&2; exit 1
fi

echo -e "${CYAN}Using initials: ${INITIALS}${NC}"
echo ""

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ── Patch helper ──────────────────────────────────────────────────────────────
# Idempotent: anchors both grep and sed to end-of-line so an already-suffixed
# value (e.g. secrets_agent_ajs) does not match the bare search term
# (secrets_agent) and receive a second suffix on re-run.
patch_file() {
  local file="$1" search="$2" replace="$3"
  if grep -qE "${search}$" "$file"; then
    sed -i "s|${search}$|${replace}|g" "$file"
    echo -e "  ${GREEN}patched${NC}  $(basename "$file")  ($search → $replace)"
  else
    echo -e "  ${YELLOW}skip${NC}     $(basename "$file")  ('$search' not found — already patched?)"
  fi
}

# ── tools/vault_read_secret.py ────────────────────────────────────────────────
echo "--- tools/vault_read_secret.py"
F="$REPO_DIR/tools/vault_read_secret.py"
patch_file "$F" 'name="vault_read_secret",'       "name=\"vault_read_secret_${INITIALS}\","
patch_file "$F" "VAULT_CREDS = \"vault_creds\"" "VAULT_CREDS = \"vault_creds_${INITIALS}\""

# ── tools/deploy_frontend.py ──────────────────────────────────────────────────
echo "--- tools/deploy_frontend.py"
F="$REPO_DIR/tools/deploy_frontend.py"
patch_file "$F" 'name="deploy_frontend"'          "name=\"deploy_frontend_${INITIALS}\""
patch_file "$F" 'CLOUD_CREDS = "cloud_creds"'     "CLOUD_CREDS = \"cloud_creds_${INITIALS}\""

# ── agents/secrets_agent.yaml ─────────────────────────────────────────────────
echo "--- agents/secrets_agent.yaml"
F="$REPO_DIR/agents/secrets_agent.yaml"
patch_file "$F" 'name: secrets_agent'             "name: secrets_agent_${INITIALS}"
patch_file "$F" 'using vault_read_secret.'        "using vault_read_secret_${INITIALS}."
patch_file "$F" '  - vault_read_secret'           "  - vault_read_secret_${INITIALS}"

# ── agents/provisioning_agent.yaml ───────────────────────────────────────────
echo "--- agents/provisioning_agent.yaml"
F="$REPO_DIR/agents/provisioning_agent.yaml"
patch_file "$F" 'name: provisioning_agent'        "name: provisioning_agent_${INITIALS}"
patch_file "$F" 'deploy_frontend tool.'           "deploy_frontend_${INITIALS} tool."
patch_file "$F" '  - deploy_frontend'             "  - deploy_frontend_${INITIALS}"

# ── agents/infra_supervisor.yaml ─────────────────────────────────────────────
# Patch both the collaborators list AND the instructions prose
echo "--- agents/infra_supervisor.yaml"
F="$REPO_DIR/agents/infra_supervisor.yaml"
patch_file "$F" 'name: infra_supervisor'          "name: infra_supervisor_${INITIALS}"
patch_file "$F" 'to provisioning_agent,'          "to provisioning_agent_${INITIALS},"
patch_file "$F" 'reads to secrets_agent,'         "reads to secrets_agent_${INITIALS},"
patch_file "$F" 'to aws_infra_agent.'             "to aws_infra_agent_${INITIALS}."
patch_file "$F" '  - provisioning_agent'          "  - provisioning_agent_${INITIALS}"
patch_file "$F" '  - secrets_agent'               "  - secrets_agent_${INITIALS}"
patch_file "$F" '  - aws_infra_agent'             "  - aws_infra_agent_${INITIALS}"

# ── agents/aws_infra_agent.yaml ───────────────────────────────────────────────
echo "--- agents/aws_infra_agent.yaml"
F="$REPO_DIR/agents/aws_infra_agent.yaml"
patch_file "$F" 'name: aws_infra_agent'           "name: aws_infra_agent_${INITIALS}"
patch_file "$F" 'title: aws_infra_agent'          "title: aws_infra_agent_${INITIALS}"

# ── Print Phase 4 commands with initials substituted ─────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Phase 4 commands — copy-paste ready (initials: ${INITIALS})${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}# Step 4.2 — cloud_creds connection${NC}"
cat <<EOF
orchestrate connections add -a cloud_creds_${INITIALS}

orchestrate connections configure \\
  -a cloud_creds_${INITIALS} --env draft --type team --kind key_value

orchestrate connections set-credentials -a cloud_creds_${INITIALS} --env draft \\
  -e "IBM_COS_API_KEY=\$IBMCLOUD_API_KEY" \\
  -e "IBM_COS_INSTANCE_ID=\$COS_CRN" \\
  -e "IBM_COS_ENDPOINT=https://s3.us-south.cloud-object-storage.appdomain.cloud"

EOF
echo -e "${YELLOW}# Step 4.2 — vault_creds connection${NC}"
cat <<EOF
orchestrate connections add -a vault_creds_${INITIALS}

orchestrate connections configure \\
  -a vault_creds_${INITIALS} --env draft --type team --kind key_value

orchestrate connections set-credentials -a vault_creds_${INITIALS} --env draft \\
  -e "VAULT_TOKEN=root" \\
  -e "VAULT_ADDR=https://vault-mcp-combined-app.2e0x6ea5h3or.us-south.codeengine.appdomain.cloud"

EOF
echo -e "${YELLOW}# Step 4.3 — import tools${NC}"
cat <<EOF
orchestrate tools import -k python \\
  -f tools/vault_read_secret.py \\
  --requirements-file tools/vault_requirements.txt \\
  -a vault_creds_${INITIALS}

orchestrate tools import -k python \\
  -f tools/deploy_frontend.py \\
  --requirements-file tools/cloud_requirements.txt \\
  -a cloud_creds_${INITIALS}

orchestrate tools list
EOF
echo ""
echo -e "${GREEN}Done. Files patched and commands printed above.${NC}"
