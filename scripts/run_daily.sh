#!/bin/zsh
set -eu

REPO_ROOT="/Users/hanwha/Documents/GitHub/cryptonewsbot"
LOG_DIR="$REPO_ROOT/logs"

mkdir -p "$LOG_DIR"
cd "$REPO_ROOT"

export PYTHONPATH="$REPO_ROOT/src"

exec /usr/bin/env python3 -m cryptonewsbot.main run
