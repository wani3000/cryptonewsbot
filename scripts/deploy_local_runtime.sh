#!/bin/zsh
set -eu

SOURCE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME_ROOT="${CRYPTO_NEWSBOT_RUNTIME_ROOT:-$HOME/bots/cryptonewsbot}"

mkdir -p "$(dirname "$RUNTIME_ROOT")"
mkdir -p "$RUNTIME_ROOT"

/usr/bin/rsync -a \
  --delete \
  --exclude '.git/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude 'logs/*.log' \
  "$SOURCE_ROOT/" "$RUNTIME_ROOT/"

cd "$RUNTIME_ROOT"
/bin/chmod +x scripts/run_daily.sh scripts/install_launchd.sh scripts/deploy_local_runtime.sh
./scripts/install_launchd.sh

echo "Local runtime deployed to $RUNTIME_ROOT"
