#!/bin/zsh
set -eu

REPO_ROOT="/Users/hanwha/Documents/GitHub/cryptonewsbot"
TEMPLATE_PATH="$REPO_ROOT/deploy/com.chainbounty.cryptonewsbot.daily.plist.template"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PATH="$TARGET_DIR/com.chainbounty.cryptonewsbot.daily.plist"

mkdir -p "$TARGET_DIR"
mkdir -p "$REPO_ROOT/logs"

/usr/bin/env python3 - <<'PY'
from pathlib import Path

repo_root = Path("/Users/hanwha/Documents/GitHub/cryptonewsbot")
template_path = repo_root / "deploy" / "com.chainbounty.cryptonewsbot.daily.plist.template"
target_path = Path.home() / "Library" / "LaunchAgents" / "com.chainbounty.cryptonewsbot.daily.plist"

content = template_path.read_text(encoding="utf-8").replace("__REPO_ROOT__", str(repo_root))
target_path.write_text(content, encoding="utf-8")
PY

/bin/chmod 644 "$TARGET_PATH"
/bin/launchctl bootout "gui/$(id -u)" "$TARGET_PATH" >/dev/null 2>&1 || true
/bin/launchctl bootstrap "gui/$(id -u)" "$TARGET_PATH"
/bin/launchctl enable "gui/$(id -u)/com.chainbounty.cryptonewsbot.daily"
/bin/launchctl kickstart -k "gui/$(id -u)/com.chainbounty.cryptonewsbot.daily"

echo "Installed LaunchAgent at $TARGET_PATH"
echo "Schedule: daily at 09:00 local time"
