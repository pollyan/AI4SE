#!/bin/bash

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROJECT_PYTHON="$PROJECT_ROOT/.venv/bin/python"
if [ ! -x "$PROJECT_PYTHON" ]; then
    PROJECT_PYTHON="python3"
fi

exec "$PROJECT_PYTHON" "$PROJECT_ROOT/scripts/test/new_agents_functional.py" "$@"
