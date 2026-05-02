#!/usr/bin/env bash
# setup-books-agent.sh
#
# Idempotent bootstrap for the NanoClaw "books" agent on a fresh machine.
#
# Prereqs (NOT done by this script):
#   - NanoClaw v2 already installed and running this machine's `/setup` flow
#   - Telegram channel installed (`/add-telegram` skill in NanoClaw)
#   - .env has TELEGRAM_BOT_TOKEN
#   - You are the registered owner (you've DM'd the bot at least once)
#   - SSH key on this machine that can `git clone git@github.com:tmfelwu/books.git`
#     (only needed for the FIRST clone — the agent uses its own deploy key after)
#
# Usage on a fresh machine:
#   1. git clone git@github.com:tmfelwu/books.git ~/vault/books
#   2. bash ~/vault/books/scripts/setup-books-agent.sh /absolute/path/to/nanoclaw-v2
#
# Re-running is safe — every step checks current state before mutating.
#
# What lives where, and why:
#   ~/vault/books   — this repo. Backed up via GitHub. Notes + this script.
#   ~/vault/keys/   — dedicated, disposable SSH deploy key for the agent.
#                     NOT backed up on purpose (private keys never go in git).
#                     Lose it → script regenerates a new one → re-add as deploy
#                     key on GitHub (~30s). No data at risk.
#   ~/nanoclaw-v2/data/v2.db — NanoClaw's central SQLite. Holds agent groups,
#                     wiring, users, roles. Touched by this script via
#                     INSERT-OR-IGNORE / UPDATE — re-running won't duplicate.
#
# Routing model: NanoClaw's router is regex-based, not LLM-based. To send a
# message to this agent, prefix it with `!books` in your Telegram DM:
#   !books add Project Hail Mary by Andy Weir to wishlist
# Anything not starting with `!books` falls through to your general agent.

set -euo pipefail

NANOCLAW_DIR="${1:-$HOME/nanoclaw-v2}"
VAULT_DIR="$HOME/vault"
BOOKS_DIR="$VAULT_DIR/books"
KEYS_DIR="$VAULT_DIR/keys"
DEPLOY_KEY="$KEYS_DIR/books-agent"
BOOKS_REPO="git@github.com:tmfelwu/books.git"
MOUNT_ALLOWLIST="$HOME/.config/nanoclaw/mount-allowlist.json"
AGENT_GROUP_ID="${BOOKS_AGENT_GROUP_ID:-ag-books-stable}"   # override to keep id stable across machines
GROUP_FOLDER="books"
TELEGRAM_USER_ID="${TELEGRAM_USER_ID:-}"   # required: e.g. telegram:934044247

[ -d "$NANOCLAW_DIR" ] || { echo "NanoClaw dir not found: $NANOCLAW_DIR" >&2; exit 1; }
[ -f "$NANOCLAW_DIR/data/v2.db" ] || { echo "NanoClaw DB not initialized — run /setup first" >&2; exit 1; }

# 1. Vault layout + clone books repo (idempotent)
mkdir -p "$VAULT_DIR" "$KEYS_DIR"
if [ ! -d "$BOOKS_DIR/.git" ]; then
  echo "→ cloning books repo to $BOOKS_DIR"
  git clone "$BOOKS_REPO" "$BOOKS_DIR"
else
  echo "✓ books repo already at $BOOKS_DIR"
fi

# 2. Generate dedicated deploy key (idempotent)
if [ ! -f "$DEPLOY_KEY" ]; then
  echo "→ generating deploy key at $DEPLOY_KEY"
  ssh-keygen -t ed25519 -f "$DEPLOY_KEY" -N "" -C "nanoclaw-books-agent@$(hostname)" -q
  chmod 600 "$DEPLOY_KEY"
  echo
  echo "════════════════════════════════════════════════════════════════════"
  echo "ACTION REQUIRED — add this as a deploy key WITH WRITE ACCESS at:"
  echo "  https://github.com/tmfelwu/books/settings/keys/new"
  echo "════════════════════════════════════════════════════════════════════"
  cat "${DEPLOY_KEY}.pub"
  echo "════════════════════════════════════════════════════════════════════"
  read -r -p "Press ENTER once the deploy key is added… "
else
  echo "✓ deploy key already exists at $DEPLOY_KEY"
fi

# 3. Configure the books repo's local git so it uses the deploy key + bot identity.
#    These live in $BOOKS_DIR/.git/config which is NOT pushed (per-clone), so
#    every fresh machine re-applies them here. The container reads .git/config
#    straight from the mount — no env vars needed (NanoClaw's container.json
#    has no env field).
echo "→ writing $BOOKS_DIR/.git/config (sshCommand + bot identity)"
git -C "$BOOKS_DIR" config core.sshCommand "ssh -i /workspace/extra/.git-keys/books-agent -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/tmp/known_hosts_books"
git -C "$BOOKS_DIR" config user.name  "NanoClaw Books Agent"
git -C "$BOOKS_DIR" config user.email "books-agent@nanoclaw.local"

# Sanity-check the deploy key actually has write access
if ! GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes" \
     git -C "$BOOKS_DIR" ls-remote --exit-code origin >/dev/null 2>&1; then
  echo "✗ deploy key cannot reach the books repo. Check that you added it on GitHub." >&2
  exit 1
fi
echo "✓ deploy key authenticates to GitHub"

# 4. Mount allowlist — ensure ~/vault is allowed RW
mkdir -p "$(dirname "$MOUNT_ALLOWLIST")"
if [ ! -f "$MOUNT_ALLOWLIST" ] || ! grep -q '"~/vault"' "$MOUNT_ALLOWLIST"; then
  echo "→ writing mount allowlist with ~/vault entry"
  cat > "$MOUNT_ALLOWLIST" <<'JSON'
{
  "allowedRoots": [
    {
      "path": "~/vault",
      "allowReadWrite": true,
      "description": "Personal vault: book notes (RW) and dedicated git deploy keys (RO)"
    }
  ],
  "blockedPatterns": [],
  "nonMainReadOnly": true
}
JSON
else
  echo "✓ mount allowlist already includes ~/vault"
fi

# 5. groups/books/ — container.json + CLAUDE.local.md (overwrite each run; this folder is owned by the script)
GROUP_DIR="$NANOCLAW_DIR/groups/$GROUP_FOLDER"
mkdir -p "$GROUP_DIR"
cat > "$GROUP_DIR/container.json" <<JSON
{
  "mcpServers": {},
  "packages": { "apt": ["git", "openssh-client", "python3"], "npm": [] },
  "additionalMounts": [
    { "hostPath": "~/vault/books",            "containerPath": "books",                 "readonly": false },
    { "hostPath": "~/vault/keys/books-agent", "containerPath": ".git-keys/books-agent", "readonly": true  }
  ],
  "skills": "all",
  "groupName": "Books",
  "assistantName": "Books",
  "agentGroupId": "$AGENT_GROUP_ID"
}
JSON

cat > "$GROUP_DIR/CLAUDE.local.md" <<'MD'
# Books Agent

You manage a personal book-tracking repository for the user, reachable from Telegram.

## Working directory

The user's books vault is mounted at `/workspace/extra/books`. It is a git repository (`git@github.com:tmfelwu/books.git`). Treat that directory as your working root for every book-related task — `cd /workspace/extra/books` at the start of each turn that touches the vault.

The vault ships its own `CLAUDE.md` at the repo root with the full schema, status values, filename conventions, index regeneration rules, and the validation script. **Read `/workspace/extra/books/CLAUDE.md` once at session start and follow it as the source of truth** — don't duplicate or guess at its rules from memory.

## Git workflow (NON-NEGOTIABLE)

**A change that isn't pushed to GitHub does not exist.** The user accesses this vault from multiple devices via git — anything you leave in the working tree is invisible to them.

Run these commands as a single atomic block at the END of every turn that modifies any file under `/workspace/extra/books`. Do not skip. Do not defer. Do not assume the user will do it. If any step fails, stop and tell the user the exact error.

```bash
cd /workspace/extra/books
git pull --ff-only                          # MUST be done before edits, but re-run is safe
# ... your edits already happened ...
[ -x scripts/books.py ] && python3 scripts/books.py    # regenerate index if script exists
git add -A                                   # stage everything you touched (including index.md)
git status --short                           # sanity print — should show staged changes only
git commit -m "<action> \"<title>\""         # e.g. add "Project Hail Mary" to wishlist
git push                                     # ← if you skip this, the change is LOST to other devices
git status --short                           # MUST print nothing. If it prints anything, something failed — report it.
```

Before you tell the user "done", confirm you ran `git push` successfully and `git status --short` is empty. Saying "added the book" without a push is a bug — treat it the same as not doing the work at all.

**Pull-first rule:** `git pull --ff-only` MUST run before reading or editing — the user may have edited from another device. If the pull fails (conflict, non-fast-forward), stop and surface the error to the user; do not attempt resolution.

**SSH auth:** uses a dedicated deploy key, wired via `core.sshCommand` in the repo's `.git/config`. If you see `Permission denied (publickey)`, stop and tell the user — the deploy key was not added on GitHub.

## Telegram interaction

The user reaches you with messages prefixed `!books`. After the prefix, the request is natural language — examples:

- `!books add Project Hail Mary by Andy Weir to wishlist`
- `!books mark The Goldfinch as finished, rating 4`
- `!books what am I currently reading?`
- `!books archive Material World`
- `!books recommend me something like Apple in China`

Be concise in replies. After making a change, confirm the action in one short sentence (e.g. *"Added 'Project Hail Mary' to wishlist and pushed."*) — the diff is already in the commit.

When you can't disambiguate a book by title alone (multiple matches), list the candidates and ask which.

## Out of scope

Anything that isn't book-related. Defer back to the user's general assistant if asked about other topics.
MD

echo "✓ groups/$GROUP_FOLDER/ written"

# 6. DB wiring (idempotent via INSERT OR IGNORE / UPDATE)
if [ -z "$TELEGRAM_USER_ID" ]; then
  TELEGRAM_USER_ID=$(python3 -c "
import sqlite3
db = sqlite3.connect('$NANOCLAW_DIR/data/v2.db')
row = db.execute(\"SELECT id FROM users WHERE id LIKE 'telegram:%' ORDER BY id LIMIT 1\").fetchone()
print(row[0] if row else '')
")
  [ -z "$TELEGRAM_USER_ID" ] && { echo "✗ no telegram user found in DB. DM the bot once, then re-run." >&2; exit 1; }
  echo "✓ resolved telegram user: $TELEGRAM_USER_ID"
fi

python3 <<PY
import sqlite3, datetime, secrets
db = sqlite3.connect('$NANOCLAW_DIR/data/v2.db')
now = datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%dT%H:%M:%S.%fZ')[:-4]+'Z'
AGID = '$AGENT_GROUP_ID'
USER = '$TELEGRAM_USER_ID'

tg_mg_row = db.execute("SELECT id FROM messaging_groups WHERE channel_type='telegram' AND platform_id=? LIMIT 1", (USER,)).fetchone()
if not tg_mg_row:
    raise SystemExit('✗ no telegram messaging_group for ' + USER + ' — DM the bot once, then re-run.')
TG_MG = tg_mg_row[0]

dm_ag_row = db.execute("""SELECT agent_group_id FROM messaging_group_agents
                          WHERE messaging_group_id=? AND agent_group_id != ? LIMIT 1""", (TG_MG, AGID)).fetchone()
DM_AG = dm_ag_row[0] if dm_ag_row else None

db.execute("INSERT OR IGNORE INTO agent_groups (id,name,folder,agent_provider,created_at) VALUES (?,?,?,?,?)",
           (AGID,'Books','books',None,now))

existing = db.execute("SELECT id FROM messaging_group_agents WHERE messaging_group_id=? AND agent_group_id=?",(TG_MG,AGID)).fetchone()
if not existing:
    mga_id = f'mga-{int(datetime.datetime.now(datetime.UTC).timestamp()*1000)}-{secrets.token_hex(3)}'
    db.execute("""INSERT INTO messaging_group_agents
                  (id,messaging_group_id,agent_group_id,session_mode,priority,created_at,
                   engage_mode,engage_pattern,sender_scope,ignored_message_policy)
                  VALUES (?,?,?,?,?,?,?,?,?,?)""",
               (mga_id,TG_MG,AGID,'shared',10,now,'pattern',r'^!books\b','all','drop'))
else:
    db.execute("UPDATE messaging_group_agents SET engage_pattern=?, priority=10 WHERE messaging_group_id=? AND agent_group_id=?",
               (r'^!books\b', TG_MG, AGID))

if DM_AG:
    db.execute("UPDATE messaging_group_agents SET engage_pattern=? WHERE messaging_group_id=? AND agent_group_id=?",
               (r'^(?!!books\b)', TG_MG, DM_AG))

db.execute("INSERT OR IGNORE INTO user_roles (user_id,role,agent_group_id,granted_by,granted_at) VALUES (?,?,?,?,?)",
           (USER,'admin',AGID,USER,now))
db.execute("INSERT OR IGNORE INTO agent_group_members (user_id,agent_group_id,added_by,added_at) VALUES (?,?,?,?)",
           (USER,AGID,USER,now))
db.commit()
print('✓ DB wired')
PY

# 7. Build host
echo "→ building host"
( cd "$NANOCLAW_DIR" && pnpm run build >/dev/null )

# 8. Restart service
if command -v systemctl >/dev/null && systemctl --user list-unit-files | grep -q '^nanoclaw'; then
  UNIT=$(systemctl --user list-unit-files | awk '/^nanoclaw/ {print $1; exit}')
  echo "→ restarting systemd service ($UNIT)"
  systemctl --user restart "$UNIT"
elif command -v launchctl >/dev/null; then
  echo "→ restarting launchd service"
  launchctl kickstart -k "gui/$(id -u)/com.nanoclaw" || true
else
  echo "! no service manager detected — start NanoClaw manually (pnpm run dev or your service)"
fi

cat <<'DONE'

✓ Books agent setup complete.

Test it from Telegram:
  !books what's currently in my wishlist?
  !books add Project Hail Mary by Andy Weir to wishlist

If it ever 401s on git push, re-add the deploy key at:
  https://github.com/tmfelwu/books/settings/keys
DONE
