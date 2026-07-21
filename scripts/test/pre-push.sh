#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT_PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [ "$#" -ne 0 ]; then
    echo "usage: ./scripts/test/pre-push.sh" >&2
    exit 2
fi

if [ ! -x "$PROJECT_PYTHON" ]; then
    printf '%s\n' '{"suiteId":"pre-push-preflight","status":"BLOCKED","collected":0,"executed":0,"skipped":0,"reason":"project .venv/bin/python is required"}' >&2
    exit 1
fi

exec "$PROJECT_PYTHON" "$PROJECT_ROOT/scripts/test/pre_push.py"
