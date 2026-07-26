#!/bin/bash
# Hermes State → GitHub Backup Template
# Customize: set REPO_URL with your PAT and target repo
# Deploy: copy to ~/.hermes/scripts/, chmod +x, create cron job with no_agent=True
# Cron: cronjob(action='create', name='hermes-backup', schedule='every 12h', script='hermes-backup.sh', no_agent=True, deliver='origin')

set -euo pipefail

# === CONFIGURATION ===
HERMES_DIR="${HERMES_DIR:-$HOME/.hermes}"
REPO_URL="${REPO_URL:?Set REPO_URL with embedded PAT}"  # e.g. https://ghp_xxx@github.com/user/repo.git
BACKUP_REPO_DIR="/tmp/hermes-backup-repo"
BACKUP_BRANCH="main"
STAGING_DIR="/tmp/hermes-backup-staging"
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

cleanup() { rm -rf "$BACKUP_REPO_DIR" "$STAGING_DIR" 2>/dev/null || true; }
trap cleanup EXIT

# === Clone or update repo ===
log "📦 Setting up backup repo..."
rm -rf "$BACKUP_REPO_DIR"
git clone --depth 1 "$REPO_URL" "$BACKUP_REPO_DIR" 2>/dev/null || {
    log "⚠️ Clone failed, initializing fresh repo..."
    mkdir -p "$BACKUP_REPO_DIR"
    cd "$BACKUP_REPO_DIR"
    git init && git remote add origin "$REPO_URL" && git checkout -B "$BACKUP_BRANCH"
}
cd "$BACKUP_REPO_DIR"
git checkout -B "$BACKUP_BRANCH" 2>/dev/null || true

# === Create staging ===
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

# === Copy critical data ===
log "💾 Backing up memories..."
cp -r "$HERMES_DIR/memories/"* "$STAGING_DIR/memories/" 2>/dev/null || true
mkdir -p "$STAGING_DIR/memories"

log "🧠 Backing up skills..."
rsync -a --exclude='*.lock' "$HERMES_DIR/skills/" "$STAGING_DIR/skills/" 2>/dev/null || \
cp -r "$HERMES_DIR/skills" "$STAGING_DIR/skills" 2>/dev/null || true

for f in SOUL.md config.yaml state.db channel_directory.json gateway_state.json; do
    cp "$HERMES_DIR/$f" "$STAGING_DIR/" 2>/dev/null || true
done

mkdir -p "$STAGING_DIR/sessions" "$STAGING_DIR/cron"
cp "$HERMES_DIR/sessions/sessions.json" "$STAGING_DIR/sessions/" 2>/dev/null || true
cp "$HERMES_DIR/cron/executions.db" "$STAGING_DIR/cron/" 2>/dev/null || true
cp "$HERMES_DIR/cron/ticker_heartbeat" "$STAGING_DIR/cron/" 2>/dev/null || true
cp "$HERMES_DIR/cron/ticker_last_success" "$STAGING_DIR/cron/" 2>/dev/null || true

# === Commit and push ===
cd "$BACKUP_REPO_DIR"
rm -rf backup/
mv "$STAGING_DIR" backup/
git add -A
git config user.email "hermes-backup@bot.local"
git config user.name "Hermes Backup Bot"

if git diff --cached --quiet; then
    log "✅ No changes detected."
    exit 0
fi

git commit -m "🔄 Automated backup: $TIMESTAMP"
git push origin "$BACKUP_BRANCH" 2>&1 || git push --force origin "$BACKUP_BRANCH" 2>&1

log "✅ Backup completed! ($TIMESTAMP)"
