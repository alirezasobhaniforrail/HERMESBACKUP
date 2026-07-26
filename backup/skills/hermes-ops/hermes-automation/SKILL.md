---
name: hermes-automation
description: "Cron scripts, scheduled backups, and maintenance for Hermes."
version: 1.0.0
author: Hermes Agent (curator-created)
license: MIT
metadata:
  hermes:
    tags: [hermes, cron, automation, backup, maintenance, scheduled]
    related_skills: [hermes-agent]
---

# Hermes Automation

Reusable patterns for scheduled tasks, automated backups, and maintenance scripts that run via Hermes cron. Covers script placement, the `no_agent` zero-token pattern, and Hermes state structure for backup planning.

**See also:** `hermes-agent` skill → `references/background-systems.md` for cron fundamentals (schedules, knobs, invariants).

## Critical Pitfall: Script Path for Cron Jobs

When creating a cron job with `no_agent=True` and a `script` parameter:

1. The script **MUST** live in `~/.hermes/scripts/`
2. Reference it by **filename only** (relative path), NOT an absolute path
3. Absolute paths (`/data/hermes-backup.sh`) or home-relative paths (`~/hermes-backup.sh`) are **rejected** with an error

```
# ❌ WRONG — will fail
cronjob(action='create', script='/data/my-script.sh', no_agent=True)
cronjob(action='create', script='~/my-script.sh', no_agent=True)

# ✅ CORRECT
# First: cp my-script.sh ~/.hermes/scripts/
cronjob(action='create', script='my-script.sh', no_agent=True)
```

This constraint exists because the scheduler resolves scripts relative to `~/.hermes/scripts/` only.

## The `no_agent=True` Pattern

Use `no_agent=True` for deterministic, zero-token script execution:

- **Script IS the job** — stdout is delivered verbatim as the message
- **No LLM involved** — no model, no reasoning, no token cost
- **Empty stdout = SILENT** — nothing sent (design scripts to stay quiet when nothing to report)
- **Non-zero exit / timeout** — sends an error alert
- **`prompt` and `skills` are ignored** when `no_agent=True`

```
cronjob(
    action='create',
    name='my-watchdog',
    schedule='every 2h',
    script='my-script.sh',       # in ~/.hermes/scripts/
    no_agent=True,
    deliver='origin'             # or omit for same-chat delivery
)
```

When to use `no_agent=True`:
- Watchdog scripts (disk, memory, GPU monitoring)
- Fixed-format notifications (CI status, API polls)
- Deterministic data collection with no reasoning needed

When NOT to use it (use default LLM-driven cron instead):
- Summarizing feeds or content
- Anything requiring conditional logic on data
- Drafting reports that need human-like phrasing

## Hermes State Structure (for Backup Planning)

Critical directories and files in `~/.hermes/`:

| Path | Contents | Backup Priority |
|------|----------|-----------------|
| `memories/USER.md` | User profile + preferences | **Critical** |
| `skills/` | All installed skills (8.5M+) | **Critical** |
| `SOUL.md` | Agent personality/identity | **Critical** |
| `config.yaml` | Settings (not secrets) | **Critical** |
| `sessions/sessions.json` | Gateway routing index | High |
| `cron/executions.db` | Cron job definitions | High |
| `state.db` | Canonical session store | High |
| `channel_directory.json` | Platform routing | Medium |
| `gateway_state.json` | Gateway runtime state | Low (ephemeral) |

Files to **exclude** from backups:
- `.env` — secrets (API keys, tokens)
- `auth.json` — OAuth tokens
- `*.lock` / `*.pid` — ephemeral locks
- `logs/` — not durable
- `cache/` / `audio_cache/` / `image_cache/` — rebuildable
- `bin/` — binaries, not user data
- `models_dev_cache.json` / `provider_models_cache.json` — rebuildable

## Example: Automated GitHub Backup

A common pattern — back up Hermes state to a GitHub repo via HTTPS + PAT (when SSH is unavailable):

```bash
#!/bin/bash
set -euo pipefail

HERMES_DIR="$HOME/.hermes"
REPO_URL="https://<PAT>@github.com/user/repo.git"
STAGING="/tmp/hermes-backup-staging"

# Clone or init
rm -rf /tmp/hermes-backup-repo
git clone --depth 1 "$REPO_URL" /tmp/hermes-backup-repo

# Copy critical data (exclude secrets, caches, logs)
rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -r "$HERMES_DIR/memories" "$STAGING/"
cp -r "$HERMES_DIR/skills" "$STAGING/"
cp "$HERMES_DIR/SOUL.md" "$STAGING/"
cp "$HERMES_DIR/config.yaml" "$STAGING/"
cp "$HERMES_DIR/state.db" "$STAGING/"
# ... other critical files

# Commit and push
cd /tmp/hermes-backup-repo
rm -rf backup/ && mv "$STAGING" backup/
git add -A
git diff --cached --quiet && exit 0  # no changes
git commit -m "🔄 Automated backup: $(date '+%Y-%m-%d_%H-%M-%S')"
git push origin main
```

**Tip:** Embed PAT in the repo URL for HTTPS push when port 22 is blocked. For production use, prefer SSH keys or credential helpers over embedded tokens.

## Templates & Scripts

- `scripts/hermes-backup.sh` — Copy-paste-ready backup template with env-var configuration (`REPO_URL`), logging, and cleanup. Deploy by copying to `~/.hermes/scripts/` and creating a cron job.

## Checklist: Setting Up a New Automated Task

1. Write the script with `set -euo pipefail` and proper logging
2. Copy to `~/.hermes/scripts/` and make executable (`chmod +x`)
3. Test manually: `bash ~/.hermes/scripts/my-script.sh`
4. Create cron job with `no_agent=True` (for scripts) or LLM-driven (for reasoning tasks)
5. Verify with `cronjob(action='list')` and optionally `cronjob(action='run', job_id='...')`
6. Set `deliver='origin'` to send results back to the originating chat
