#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOOK="$PROJECT_ROOT/.githooks/pre-push"

if [ ! -f "$HOOK" ]; then
    echo "missing versioned pre-push hook: $HOOK" >&2
    exit 1
fi

git -C "$PROJECT_ROOT" config --local core.hooksPath .githooks
