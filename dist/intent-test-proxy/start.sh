#!/usr/bin/env bash
set -euo pipefail

fail() {
    printf 'Proxy startup configuration error: %s\n' "$1" >&2
    exit 1
}

if [ ! -f .env ]; then
    cp .env.example .env
    fail ".env was created from .env.example; replace all placeholders before retrying"
fi

env_value() {
    key="$1"
    awk -F= -v expected="$key" '$1 == expected {print substr($0, index($0, "=") + 1)}' .env | tail -n 1
}

for key in INTENT_PROXY_TOPOLOGY INTENT_PROXY_TOKEN INTENT_PUBLIC_ORIGIN \
    OPENAI_API_KEY OPENAI_BASE_URL MIDSCENE_MODEL_NAME MAIN_APP_URL; do
    value="$(env_value "$key")"
    [ -n "$value" ] || fail "missing required key $key"
    case "$value" in
        your-api-key-here|replace-with-*) fail "$key still contains a placeholder" ;;
    esac
done

[ "$(env_value INTENT_PROXY_TOPOLOGY)" = "local-host" ] || \
    fail "INTENT_PROXY_TOPOLOGY must be local-host in the native package"

command -v node >/dev/null 2>&1 || fail "Node.js 18-22 is required"
command -v npm >/dev/null 2>&1 || fail "npm is required"
node_major="$(node -p 'Number(process.versions.node.split(".")[0])')"
[ "$node_major" -ge 18 ] && [ "$node_major" -lt 24 ] || \
    fail "Node.js 18-22 is required"

node -e '
const value = process.argv[1];
let parsed;
try { parsed = new URL(value); } catch { process.exit(1); }
const loopback = new Set(["localhost", "127.0.0.1", "[::1]"]);
if (parsed.protocol !== "http:" || parsed.origin !== value || !loopback.has(parsed.hostname)) process.exit(1);
' "$(env_value INTENT_PUBLIC_ORIGIN)" || \
    fail "INTENT_PUBLIC_ORIGIN must be an exact loopback HTTP origin"
token_bytes="$(printf %s "$(env_value INTENT_PROXY_TOKEN)" | wc -c | tr -d ' ')"
[ "$token_bytes" -ge 32 ] || fail "INTENT_PROXY_TOKEN must contain at least 32 UTF-8 bytes"

if [ ! -d node_modules ]; then
    npm ci --omit=dev --no-audit --no-fund
fi
npx playwright install chromium
exec node midscene_server.js
