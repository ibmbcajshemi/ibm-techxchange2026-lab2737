# Basic Workspace Rules

Apply to EVERY Bob conversation in this project, in all modes.

## Security (highest priority)
- Never write a secret, password, API key, token, private key, or cert body into any file. Reference HashiCorp Vault instead.
- If you encounter a literal secret, stop and warn the user. Do not echo it back in full.
- Treat .env, *.tfvars with real values, *.pem, *.key, secrets/ as sensitive.
- Follow least privilege: request only the permissions a task needs.

## Output discipline
- Prefer the smallest correct change. No unrequested scaffolds.
- Show what you will do before doing it; summarize what changed after.
- End infra-code tasks with a short human review checklist.

## This is a conference lab
- Favor clarity and teachability, never at the expense of the security rules.
- Use small, cheap, easily-destroyed resources. Label assumptions explicitly.

