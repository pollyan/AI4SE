@echo off
setlocal EnableExtensions EnableDelayedExpansion

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Proxy startup configuration error: .env was created from .env.example; replace all placeholders before retrying 1>&2
  exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in (".env") do set "%%A=%%B"
for %%K in (INTENT_PROXY_TOPOLOGY INTENT_PROXY_TOKEN INTENT_PUBLIC_ORIGIN OPENAI_API_KEY OPENAI_BASE_URL MIDSCENE_MODEL_NAME MAIN_APP_URL) do (
  if "!%%K!"=="" (
    echo Proxy startup configuration error: missing required key %%K 1>&2
    exit /b 1
  )
)
if /I not "!INTENT_PROXY_TOPOLOGY!"=="local-host" (
  echo Proxy startup configuration error: INTENT_PROXY_TOPOLOGY must be local-host in the native package 1>&2
  exit /b 1
)
where node >nul 2>nul || (
  echo Proxy startup configuration error: Node.js 18-22 is required 1>&2
  exit /b 1
)
where npm >nul 2>nul || (
  echo Proxy startup configuration error: npm is required 1>&2
  exit /b 1
)
powershell -NoProfile -Command "$value=$env:INTENT_PUBLIC_ORIGIN; try {$uri=[Uri]$value} catch {exit 1}; $loopback=@('localhost','127.0.0.1','::1','[::1]'); if ($uri.Scheme -ne 'http' -or $loopback -notcontains $uri.Host -or $uri.GetLeftPart([UriPartial]::Authority) -ne $value) {exit 1}" || (
  echo Proxy startup configuration error: INTENT_PUBLIC_ORIGIN must be a loopback HTTP origin 1>&2
  exit /b 1
)
echo !OPENAI_API_KEY! | findstr /C:"your-api-key-here" >nul && (
  echo Proxy startup configuration error: OPENAI_API_KEY still contains a placeholder 1>&2
  exit /b 1
)
echo !INTENT_PROXY_TOKEN! | findstr /C:"replace-with-" >nul && (
  echo Proxy startup configuration error: INTENT_PROXY_TOKEN still contains a placeholder 1>&2
  exit /b 1
)
powershell -NoProfile -Command "if ([Text.Encoding]::UTF8.GetByteCount($env:INTENT_PROXY_TOKEN) -lt 32) { exit 1 }" || (
  echo Proxy startup configuration error: INTENT_PROXY_TOKEN must contain at least 32 UTF-8 bytes 1>&2
  exit /b 1
)

if not exist "node_modules" call npm ci --omit=dev --no-audit --no-fund || exit /b 1
call npx playwright install chromium || exit /b 1
node midscene_server.js
exit /b !errorlevel!
