#!/usr/bin/env bash

# Local development deployment helper. Production releases are owned by the
# immutable transaction in scripts/ci/release_transaction.py.

set -euo pipefail

environment="${1:-local}"

case "$environment" in
  local|dev|development)
    compose_file="docker-compose.dev.yml"
    ;;
  prod|production|remote)
    printf '%s\n' 'Production deployment requires scripts/ci/release_transaction.py.' >&2
    exit 2
    ;;
  *)
    printf 'Unknown deployment environment: %s\n' "$environment" >&2
    exit 2
    ;;
esac

if [[ -f scripts/ci/build-proxy-package.js ]] && command -v node >/dev/null 2>&1; then
  node scripts/ci/build-proxy-package.js
fi

docker compose -f "$compose_file" build
docker compose -f "$compose_file" up -d
bash scripts/health/health_check.sh "$environment"
