# QS-04 Intent Tester 访问与浏览器安全边界 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 [QS-04 设计](../specs/2026-07-11-qs04-intent-access-browser-security-design.md) 一次性交付 Intent Tester 的访问控制、浏览器渲染、Node proxy 与生产配置安全闭环。

**Architecture:** Flask 通过唯一公开入口 `install_intent_security(app)` 安装 production preflight、route policy、session、Origin/CSRF、CSP 与 proxy credential；业务 endpoint 只声明策略，不复制安全判断。Node 只运行在显式 `local-host` 或 `managed` topology，长期 token 只在后端间流动，浏览器只在 local-host 使用短期 execution ticket；Flask durable record 与 terminal lifecycle 继续作为状态权威。

**Tech Stack:** Python 3.11、Flask、Flask-SQLAlchemy、Werkzeug、pytest、Playwright/Chromium、Node.js 20、Express、Socket.IO、Jest/Supertest、Docker Compose、GitHub Actions。

## Global Constraints

- 厚切片身份、纳入/排除边界、七项门禁和单一交付以 [设计中的“厚切片身份基线”](../specs/2026-07-11-qs04-intent-access-browser-security-design.md#厚切片身份基线) 为唯一事实；顺序以 [QS 厚切片序列](../../todos/2026-07-10-ai-coding-test-quality-improvement.md#厚切片序列) 为唯一事实。
- 本文所有 Task 都是“内部实现步骤（非切片）”；不得改名为 QS-04A/QS-04B、单独验收、计算厚切片进度、commit、push 或交付。
- 用户要求直接在 `master` 单工作区完成；不创建 branch/worktree。每个内部步骤保留 RED/GREEN 证据，但只在全部 QS-04 门禁通过后形成一个聚焦 commit。
- production 唯一 browser Origin 配置名是单值 `INTENT_PUBLIC_ORIGIN`；不新增同义配置镜像。
- production access mode 仅允许 `restricted` / `public-readonly`；execution enabled 时 topology 仅允许 `managed`。
- `local-dev` 仅允许非 production，显式 Origin 仅允许 HTTP(S) loopback；不能从 Host header 推导可信 Origin。
- production always-required：`AI4SE_ENV=production`、`INTENT_ACCESS_MODE`、`INTENT_EXECUTION_ENABLED`、`INTENT_PUBLIC_ORIGIN`、`DB_PASSWORD`/`DATABASE_URL`、`SECRET_KEY`、`INTENT_TESTER_ADMIN_PASSWORD_HASH`。
- execution enabled conditional-required：`INTENT_PROXY_TOPOLOGY`、至少 32-byte `INTENT_PROXY_TOKEN`、`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`MIDSCENE_MODEL_NAME`。
- production `SECRET_KEY` 与 execution-enabled `INTENT_PROXY_TOKEN` 的 UTF-8 编码至少 32 bytes，并拒绝空值及 `change_me_in_production`、`dev-secret-key-change-in-production`、`dev-secret-key-please-change-in-production`、`dev-secret-key-please-change`；管理员 hash 只接受 Werkzeug `scrypt:` / `pbkdf2:`。
- execution enabled 时所有环境要求 trim 后非空 provider key/model 和 absolute HTTP(S)、无 userinfo 的 base URL；production API key 还拒绝 `change_me_in_production`、`your-api-key-here`、`sk-your-api-key-here`，provider base URL 必须 HTTPS；合法模型名不按默认值拒绝。production 最终 DB URI 非 SQLite 且不能包含已知默认 credential。
- `INTENT_PUBLIC_ORIGIN` 是无 userinfo/path/query/fragment 的 absolute HTTP(S) origin；production HTTPS，local-dev host 只允许 `localhost`、`127.0.0.1`、`::1`，port 可选。
- 所有 restricted/public-readonly 环境都显式要求 strong `SECRET_KEY`；admin hash 必须能由 Werkzeug 安全解析。execution disabled 不要求 topology/token/provider；enabled local-dev 允许 explicit managed 或 local-host，enabled production 只允许 managed。production DB URI 还必须包含非空 username/password。
- production container 使用 Gunicorn gthread 受支持入口；`backend.app` / `run.py` 的 direct production main 显式退出，不调用 Werkzeug。只有非 production 使用 loopback debug server。
- 不添加 silent fallback、production mock、假成功、第二 execution identity、第二终态权威、长期 browser token、wildcard CORS 或 `unsafe-inline` / `unsafe-eval`。
- 每次写入前确认 `git status --short` 只有本轮文件；子智能体 writer 只能修改计划明确授权且互不重叠的路径，主 Agent 负责共享配置、最终 diff、验证、staging、commit 和 push。

## 纵向执行偏差与校正记录

本计划最初的 Task 1–6 按 config → policy → UI/CSP → Node → progress → deploy/package 技术层排队，首次完整浏览器证据推迟到 Task 7；这违反当前 Playbook §4.3，不能把“内部 Task”或“同属一个厚切片”当作纵向合规。以下已完成 checkbox 保留为真实历史 TDD ledger，不追溯伪装成 tracer task，也不作为后续计划模板。

在 Task 8 首轮整片 review 后，剩余修复改由下列真实 tracer 旅程驱动并逐条形成跨边界证据：

1. restricted operator：登录 → exact Origin/CSRF 写入 → SQLite → 嵌套 step/action/params/output 编辑保存 → CSP/DOM 安全渲染 → 受控执行失败与 same-ID retry；
2. public-readonly anonymous：operator 创建 → 匿名 summary → 敏感投影/详情/mutation 被拒；
3. local-host execution：canonical ID → 页面取 Flask ticket → 跨语言 HMAC → production Node Socket.IO → execution room；
4. production gateway：required config/workflow transaction → Compose internal topology → Nginx `/intent-tester/static` 与 health → fail-closed；
5. native package：解压配置 → side-effect 前校验 → exact loopback Node runtime → `/health` 或脱敏非零失败。

首轮整片 review 正是通过这些旅程发现 ticket 签名输入不一致、页面未取票、静态命名空间冲突、5001 health 漂移、report stored-XSS、access mode fallback 与 local-host Origin 漂移；所有发现必须在同一个 QS-04 commit 前关闭。

---

## 文件结构与责任锁定

**新增安全深模块**

- `tools/intent-tester/backend/intent_security/__init__.py`：唯一公开 interface `install_intent_security(app)` 与 endpoint policy 标注 helper。
- `tools/intent-tester/backend/intent_security/config.py`：强类型配置、production/local-dev preflight；不访问数据库。
- `tools/intent-tester/backend/intent_security/policy.py`：`EndpointPolicy` registry、URL-map completeness、principal/mode access matrix。
- `tools/intent-tester/backend/intent_security/web.py`：login/logout、safe next、Origin/CSRF、nonce/security headers、proxy bearer、HMAC ticket。

**新增/扩展测试**

- `tools/intent-tester/tests/security/test_security_config.py`：配置矩阵与 DB 初始化前 fail-closed。
- `tools/intent-tester/tests/security/test_access_policy.py`：机械 route registry 与匿名/operator/proxy 访问矩阵。
- `tools/intent-tester/tests/security/test_origin_csrf.py`：login/session/Origin/CSRF/audit principal/ticket。
- `tools/intent-tester/tests/security/test_csp_contract.py`：headers、nonce、inline attribute/CDN 静态 contract。
- `tools/intent-tester/tests/e2e/test_stored_xss_csp.py`：真实 HTTP + SQLite + Chromium exploit 回归。
- `tools/intent-tester/tests/deployment/test_intent_secure_compose.py`：production/dev Compose 与 workflow required-env contract。
- 扩展 `tools/intent-tester/tests/api/test_execution_api.py`、`test_execution_page_contract.py`、`tests/frontend/test_durable_execution_control.js`、`tests/proxy/*.test.js`、`tests/integration/*.py`。

**修改运行时**

- `tools/intent-tester/backend/app.py`、`run.py`、`backend/extensions.py`、`backend/views.py`、`backend/api/{__init__,testcases,executions,midscene,proxy}.py`。
- `tools/intent-tester/backend/services/proxy_execution_client.py` 与 `database_service.py`。
- `tools/intent-tester/frontend/templates/{base_layout,testcases,testcase_edit,execution,local_proxy,login}.html`。
- `tools/intent-tester/frontend/static/js/{intent-security,safe-dom,durable-execution-control}.js` 及 routed page-owned JS；`frontend/static/css/intent-security.css`；本地 vendor Axios/Socket.IO client。
- `tools/intent-tester/browser-automation/midscene_server.js`、`browser-automation/midscene_python.py`、`proxy_templates/{.env.example,start.sh,start.bat}`。
- `docker-compose.prod.yml`、`docker-compose.dev.yml`、`docker-compose.dev-cn.yml`、`tools/intent-tester/docker/docker-compose.yml`、`.github/workflows/deploy.yml`、`scripts/ci/build-proxy-package.js`、两份生成 ZIP/展开目录。

---

### Task 1（内部实现步骤，非切片）：配置 preflight 与安全模块安装 seam

**Files:**

- Create: `tools/intent-tester/backend/intent_security/__init__.py`
- Create: `tools/intent-tester/backend/intent_security/config.py`
- Create: `tools/intent-tester/tests/security/test_security_config.py`
- Modify: `tools/intent-tester/backend/app.py`
- Modify: `tools/intent-tester/backend/extensions.py`
- Modify: `tools/intent-tester/run.py`
- Modify: `tools/intent-tester/requirements.txt`
- Modify: `tools/intent-tester/docker/Dockerfile`
- Modify: `tools/intent-tester/tests/conftest.py`
- Modify: `tools/intent-tester/tests/test_app_factory_database_isolation.py`

**Interfaces:**

- Produces: `IntentSecurityConfigurationError`；`IntentSecurityConfig.from_mapping(mapping) -> IntentSecurityConfig`；`validate_startup_config(config, database_uri) -> None`；`install_intent_security(app: Flask) -> None`。
- Produces app config: `INTENT_SECURITY_CONFIG`、`INTENT_ACCESS_MODE`、`INTENT_EXECUTION_ENABLED`、`INTENT_PUBLIC_ORIGIN`、`INTENT_PROXY_TOPOLOGY`。
- Constraint: `validate_startup_config` 必须在 `db.init_app(app)` 和 `db.create_all()` 前执行。
- Task 1 exit seam: install 只 parse/store canonical config 到 `app.extensions["intent_security"]`、执行 DB 前 preflight，并用 canonical Origin 初始化 Flask-SocketIO exact CORS；request auth hooks 与 URL-map completeness 必须等 Task 2 先写 RED 后再扩展同一个 install，不能在本 Task 做 no-op 假实现。production container 由 Gunicorn gthread 启动，两个 direct main 在 production fail closed。

- [x] **Step 1: 写配置矩阵 RED tests**

  在 `test_security_config.py` 参数化 production 缺失/非法 mode、execution flag、SQLite、weak/default/short secret、missing password hash、HTTP/missing Origin、local-host topology、missing/short proxy token、missing provider key/base/model；并覆盖合法 restricted/public-readonly managed、execution disabled 和 local-dev loopback。

  ```python
  @pytest.mark.parametrize("override, error_key", [
      ({"INTENT_ACCESS_MODE": "local-dev"}, "INTENT_ACCESS_MODE"),
      ({"INTENT_PUBLIC_ORIGIN": "http://prod.example"}, "INTENT_PUBLIC_ORIGIN"),
      ({"INTENT_PROXY_TOPOLOGY": "local-host"}, "INTENT_PROXY_TOPOLOGY"),
  ])
  def test_production_preflight_fails_before_database_init(mocker, override, error_key):
      config = valid_production_config() | override
      init = mocker.spy(db, "init_app")
      with pytest.raises(IntentSecurityConfigurationError, match=error_key):
          create_app(config)
      assert init.call_count == 0
  ```

- [x] **Step 2: 运行 RED 并保存首个失败原因**

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/security/test_security_config.py -q`

  Expected: collection FAIL because `backend.intent_security` does not exist；不得通过修改 fixture 绕过生产 preflight。

- [x] **Step 3: 实现强类型 config 与无副作用 preflight**

  ```python
  @dataclass(frozen=True)
  class IntentSecurityConfig:
      environment: Literal["development", "test", "production"]
      access_mode: Literal["restricted", "public-readonly", "local-dev"]
      execution_enabled: bool
      public_origin: str
      proxy_topology: Literal["managed", "local-host"] | None
      proxy_token: str | None = field(repr=False, compare=False)
      secret_key: str | None = field(repr=False, compare=False)
      admin_password_hash: str | None = field(repr=False, compare=False)
      provider_api_key: str | None = field(repr=False, compare=False)
      provider_base_url: str | None = field(repr=False, compare=False)
      provider_model: str | None = field(repr=False, compare=False)

  def validate_startup_config(config: IntentSecurityConfig, database_uri: str) -> None:
      errors: list[str] = []
      # accumulate key names only; never include secret values
      if errors:
          raise IntentSecurityConfigurationError(
              "Invalid Intent Tester configuration: " + ", ".join(sorted(errors))
          )
  ```

  `create_app` 的 Task 1 顺序固定为：load config → apply `test_config` → isolated-test guard → register routes → `install_intent_security(app)` 完成 config/preflight/SocketIO exact Origin → `db.init_app` → `create_all`。Task 2 再以 RED tests 把 auth hooks 与完整 URL-map 校验装入同一个 install，不新增第二入口。Testing fixture 和 isolation test config 明确使用 `AI4SE_ENV=test`、`INTENT_ACCESS_MODE=local-dev`、loopback Origin、execution disabled，不能用 production fallback。

- [x] **Step 4: 关闭 unsafe server 与 Socket.IO wildcard**

  `backend/app.py` 和 `run.py` 的 `__main__` 仅在非 production 使用 loopback debug；production direct main 显式退出并指向 Docker 的 Gunicorn entrypoint，禁止 `allow_unsafe_werkzeug=True`。`requirements.txt` 加入锁定 Gunicorn，Docker `CMD` 使用 `gunicorn --worker-class gthread --threads 100 --bind 0.0.0.0:5001 'backend.app:create_app()'`。`extensions.py` 不在全局构造 wildcard CORS，改为在安装后从 canonical Origin 初始化。

- [x] **Step 5: 运行 GREEN 与既有 app isolation tests**

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/security/test_security_config.py tools/intent-tester/tests/test_app_factory_database_isolation.py -q`

  Expected: PASS；错误消息只出现 key，不出现测试 secret 值。

---

### Task 2（内部实现步骤，非切片）：机械 route policy、session、Origin/CSRF 与 principal

**Files:**

- Create: `tools/intent-tester/backend/intent_security/policy.py`
- Create: `tools/intent-tester/backend/intent_security/web.py`
- Create: `tools/intent-tester/frontend/templates/login.html`
- Create: `tools/intent-tester/tests/security/test_access_policy.py`
- Create: `tools/intent-tester/tests/security/test_origin_csrf.py`
- Modify: `tools/intent-tester/backend/intent_security/__init__.py`
- Modify: `tools/intent-tester/backend/views.py`
- Modify: `tools/intent-tester/backend/api/__init__.py`
- Modify: `tools/intent-tester/backend/api/testcases.py`
- Modify: `tools/intent-tester/backend/api/executions.py`
- Modify: `tools/intent-tester/backend/api/midscene.py`
- Modify: `tools/intent-tester/backend/api/proxy.py`
- Modify: `tools/intent-tester/backend/models/models.py`
- Modify: `tools/intent-tester/tests/conftest.py`
- Modify: `tools/intent-tester/tests/api/test_execution_api.py`
- Modify: `tools/intent-tester/tests/api/test_midscene_api.py`
- Modify: `tools/intent-tester/tests/api/test_testcase_api.py`
- Modify: `tools/intent-tester/tests/api/test_proxy_api.py`

**Interfaces:**

- Consumes: `IntentSecurityConfig` from Task 1.
- Produces: `EndpointPolicy = PUBLIC | PUBLIC_READONLY | OPERATOR | PROXY_MACHINE`；`intent_policy(policy)` decorator；`current_intent_principal() -> IntentPrincipal`；`require_valid_origin_and_csrf()`；`require_proxy_bearer()`；`issue_proxy_ticket(execution_id) -> str`。
- Produces Jinja context：`csrf_token`、`intent_principal`、`intent_capabilities`、`intent_public_origin`；capabilities 至少含 `can_read_full`、`can_mutate`、`can_execute`、`can_use_local_proxy`，并由 principal + execution enabled + topology 计算，供 Task 3 隐藏控件但不替代 server policy。
- Invariant: every Flask URL-map endpoint（包括 `static`）恰有一个 policy；未分类 endpoint 在 `install_intent_security` 中于 DB init 前失败。
- Exact endpoint registry：
  - `PUBLIC`：`static`、`health_check`、`root_redirect`、`views.index`、`views.login`。login endpoint 的 GET 安全，POST 仍走 pre-auth Origin + CSRF。
  - `PUBLIC_READONLY`：`views.testcases`、`views.local_proxy`、`testcases.get_testcases`、`proxy.proxy_version`、`proxy.download_proxy`。只在 public-readonly 对 anonymous 开放；restricted 仍要求 operator。
  - `PROXY_MACHINE`：唯一 `executions.record_execution_lifecycle`。
  - `OPERATOR`：`views.create_testcase`、`views.edit_testcase`、`views.view_execution`、`views.logout`；除 `get_testcases` 外所有 `testcases.*`；除 lifecycle 外所有 `executions.*`（包含新增 `executions.issue_proxy_ticket`）。
  - `midscene.midscene_execution_start/result` 从 URL map 移除并由 tests 证明 404；不得把它们归类成 PUBLIC 来保留第二 durable 写路径。
- Stable JSON error shape 以认证失败为例是 `{"code": 401, "message": "Authentication required", "error": {"code": "AUTH_REQUIRED"}}`；其他失败保持同一字段结构和实际 HTTP status。至少固定 `AUTH_REQUIRED`、`READ_ONLY_MODE`、`ORIGIN_REJECTED`、`CSRF_FAILED`、`PROXY_AUTH_REQUIRED`、`EXECUTION_DISABLED`、`PROXY_TICKET_UNAVAILABLE`，不含 secret/header/origin allowlist/traceback。

- [x] **Step 1: 写 route registry/access matrix RED tests**

  从 `app.url_map.iter_rules()` 构造真实 endpoint 集并与 policy registry 比较；逐项验证 `PUBLIC`、`PUBLIC_READONLY`、`OPERATOR`、`PROXY_MACHINE` 在三种 mode 下的 page/API 状态和零 side effect。

  ```python
  def test_every_routed_endpoint_has_one_policy(app):
      endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}
      assert endpoints == set(app.extensions["intent_security"].route_policies)

  def test_public_readonly_anonymous_projection_excludes_sensitive_fields(public_client):
      response = public_client.get("/intent-tester/api/testcases")
      assert response.status_code == 200
      assert set(response.json["data"]["items"][0]) == {
          "id", "name", "description", "category", "priority",
          "tags", "is_active", "updated_at"
      }
  ```

- [x] **Step 2: 写 login/session/Origin/CSRF/principal RED tests**

  登录 principal 固定为 `admin`，local-dev principal 固定为 `local-dev`，proxy principal 固定为 `proxy`。覆盖 pre-auth CSRF、wrong password 统一错误、只允许 `/intent-tester` 范围内的 safe relative `next`、external/scheme-relative next 拒绝、session clear + CSRF rotation、logout 仅 POST、missing/foreign/null Origin、missing/wrong CSRF、production cookie Secure/HttpOnly/SameSite=Lax、`created_by`/`executed_by` 忽略客户端伪造值。

- [x] **Step 3: 运行 RED**

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/security/test_access_policy.py tools/intent-tester/tests/security/test_origin_csrf.py -q`

  Expected: FAIL with missing policies/login/CSRF enforcement, and existing anonymous mutations returning success.

- [x] **Step 4: 实现 policy registry 与 request seam**

  ```python
  class EndpointPolicy(StrEnum):
      PUBLIC = "public"
      PUBLIC_READONLY = "public-readonly"
      OPERATOR = "operator"
      PROXY_MACHINE = "proxy-machine"

  def intent_policy(policy: EndpointPolicy):
      def decorate(view):
          view.__intent_policy__ = policy
          return view
      return decorate
  ```

  request seam 顺序固定为 mode/capability → authentication/proxy bearer → execution enabled → Origin → CSRF → view。restricted 页面未认证 302 到 `/intent-tester/login`，API 返回 JSON `401/AUTH_REQUIRED`；public-readonly anonymous 访问非 allowlist 返回 `403/READ_ONLY_MODE`；execution disabled 为 `403/EXECUTION_DISABLED`。所有 unsafe session request 要求 header `Origin` 精确等于 canonical Origin 与 `X-CSRF-Token`（HTML form 可用同名 hidden field）；`PROXY_MACHINE` 只验 bearer，不验 session CSRF。

- [x] **Step 5: 实现登录与 principal-derived audit**

  login form 只接受固定 username `admin` 与 password；使用 `werkzeug.security.check_password_hash`，失败统一为同一文案。login 成功先 `session.clear()` 再写 operator principal 与新 CSRF。`testcases.py` 和 `executions.py` 不再接受 `created_by`/`executed_by`，统一从 `current_intent_principal().name` 取得。operator 读取 TestCase 列表仍得到现有完整 DTO；public anonymous 只得到上述八字段 summary。公开 proxy 下载/version 错误不得返回绝对路径或异常正文。测试 fixture 新增 `anonymous_client`、`public_client`、`proxy_client` 与完成真实 login/CSRF 的 `operator_client`；既有 `client`/`api_client` 显式复用 operator fixture（默认 test app 为 restricted + execution enabled +完整 test-only proxy/provider config），不能全局关闭鉴权。

- [x] **Step 6: 退役旧 durable 写路径并实现 proxy auth/ticket**

  `/midscene/execution-start`、`/midscene/execution-result` 不再注册并返回 404，不能创建/更新 ExecutionHistory。唯一 lifecycle route 标为 `PROXY_MACHINE`，bearer 用 `secrets.compare_digest` 对 canonical proxy token。新增 `POST /intent-tester/api/executions/<id>/proxy-ticket`：仅 execution-enabled + local-host operator + Origin + CSRF，且 canonical execution 已存在；managed 返回 `403/PROXY_TICKET_UNAVAILABLE`。ticket 是 `base64url(canonical JSON).base64url(HMAC-SHA256)`，HMAC secret 为 proxy token，payload 固定含 `executionId`、canonical `origin`、`aud="intent-proxy-socket"`、integer `iat`、`exp=iat+60`、随机 `nonce`；response 只返回 ticket、execution_id、expires_in=60。

- [x] **Step 7: 运行 GREEN 与完整 API 回归**

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/security tools/intent-tester/tests/api -q`

  Expected: all PASS；现有 tests 通过明确登录 helper 进入 operator 状态，而不是关闭安全 seam。

---

### Task 3（内部实现步骤，非切片）：strict CSP 与 routed 页面安全 DOM

**Files:**

- Create: `tools/intent-tester/frontend/static/js/intent-security.js`
- Create: `tools/intent-tester/frontend/static/js/safe-dom.js`
- Create: `tools/intent-tester/frontend/static/css/intent-security.css`
- Create: `tools/intent-tester/tests/security/test_csp_contract.py`
- Modify: `tools/intent-tester/frontend/templates/{base_layout,testcases,testcase_edit,execution,local_proxy,login}.html`
- Modify: routed page-owned files under `tools/intent-tester/frontend/static/js/`
- Vendor: exact Axios and Socket.IO client versions from `tools/intent-tester/package-lock.json` into `tools/intent-tester/frontend/static/vendor/`

**Interfaces:**

- Consumes: per-request `csp_nonce`, `csrf_token`, `intent_capabilities`, `INTENT_PUBLIC_ORIGIN` from security context.
- Produces: `window.IntentSecurity.csrfHeaders(method)`；`window.IntentSafeDom.text(tag, value)`、`button(label, handler)`、`safeUrl(value, allowedProtocols)`、`replaceChildren(target, children)`。
- Constraint: untrusted TestCase/Execution/step/report/variable content never enters `innerHTML`, script source, inline event handler, style attribute or `javascript:` URL.

- [x] **Step 1: 写 CSP/template RED contract**

  ```python
  ROUTED_TEMPLATES = {"base_layout.html", "testcases.html", "testcase_edit.html",
                      "execution.html", "local_proxy.html", "login.html"}

  def test_routed_pages_have_strict_nonce_csp(operator_client):
      response = operator_client.get("/intent-tester/testcases")
      csp = response.headers["Content-Security-Policy"]
      assert "unsafe-inline" not in csp
      assert "script-src-attr 'none'" in csp
      assert "style-src-attr 'none'" in csp
  ```

  静态扫描 routed templates：零 `onclick=` 等 inline handler、零 `style=`、零 CDN URL、零 `|safe`；所有 inline script/style 带当次 nonce。

- [x] **Step 2: 运行 RED**

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/security/test_csp_contract.py -q`

  Expected: FAIL on missing CSP, CDN scripts, `steps_data | safe`, inline handlers/styles and unsafe DOM sinks.

- [x] **Step 3: 实现 nonce headers 与本地 vendor**

  `web.py` 每 request 用 `secrets.token_urlsafe(24)` 生成 nonce并注入 Jinja；after-request 设置设计中的完整 CSP、nosniff、no-referrer、DENY 和最小 Permissions-Policy。复制 lockfile 已锁版本的浏览器 bundle，不通过 CDN 或运行时下载。

- [x] **Step 4: 重写 routed template 与 DOM builder**

  `steps_data` 使用 `tojson` 数据节点或 `application/json` script + nonce，读取后只通过 DOM factory 创建节点。所有事件使用 `addEventListener`，动态 show/hide 用 class，进度用 `<progress>`；`innerHTML` 只允许无运行时变量的编译期 literal。

  ```javascript
  function text(tagName, value) {
      const node = document.createElement(tagName);
      node.textContent = value == null ? '' : String(value);
      return node;
  }
  ```

- [x] **Step 5: 运行 GREEN 与 routed page contract 回归**

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/security/test_csp_contract.py tools/intent-tester/tests/api/test_execution_page_contract.py -q`

  Expected: PASS；未路由 `step_editor.html` 与 redirect-only `index.html` 不冒充浏览器安全证据，但若仍被 build/scan 发现的公共 sink 不得新增风险。

---

### Task 4（内部实现步骤，非切片）：Node topology、backend bearer、ticket 与 execution room

**Files:**

- Modify: `tools/intent-tester/browser-automation/midscene_server.js`
- Modify: `tools/intent-tester/browser-automation/midscene_python.py`
- Modify: `tools/intent-tester/backend/services/proxy_execution_client.py`
- Modify: `tools/intent-tester/tests/proxy/midscene-server-api.test.js`
- Modify: `tools/intent-tester/tests/proxy/midscene-integration.test.js`
- Modify: `tools/intent-tester/tests/api/test_execution_api.py`

**Interfaces:**

- Consumes: `INTENT_PROXY_TOPOLOGY`、`INTENT_PROXY_TOKEN`、`INTENT_PUBLIC_ORIGIN`、provider key/base/model。
- Produces Node config: `{topology, bindHost, browserSocketEnabled, publicOrigin, proxyToken}`；Flask `ProxyExecutionClient(base_url, timeout, session, token)` 给每个 request 添加 bearer `Authorization` header。
- Produces local-host Socket handshake: `auth.ticket` verified against execution ID + origin + audience + expiry, then joins room `execution:<id>`.

**高风险契约冻结检查点：** 本步骤是 QS-04 唯一的正式审查前检查点，只针对 Node / Flask 的 topology、bearer、ticket、execution room 与 artifact ownership 安全边界。它不形成独立验收、commit、交付或厚切片进度，也不替代 Task 8 的完整 QS-04 双轴审查。

- [x] **Step 1: 写 Node security RED tests**

  覆盖 missing/short token、非法 topology/bind、local-host 非 loopback、managed browser Socket disabled、foreign Origin、HTTP missing/wrong/valid bearer、ticket tamper/expiry/aud/origin/execution mismatch、room isolation/current snapshot、health minimal、secret non-leak。

- [x] **Step 2: 写 method/path/legacy RED tests**

  证明有副作用 `GET /ai-test` 不存在而 POST 受 auth；screenshot/report path 被 owning output root 约束；legacy callback/midscene Python 不能绕过 bearer；status 只返回 execution ID、status、safe step progress、callback code，不返回 logs/params/screenshot/raw error。

- [x] **Step 3: 运行 RED**

  Run: `cd tools/intent-tester && npx jest tests/proxy/midscene-server-api.test.js tests/proxy/midscene-integration.test.js --runInBand`

  Expected: FAIL because routes and Socket currently accept anonymous/wildcard access and emit globally.

- [x] **Step 4: 实现 fail-closed Node config 与 bearer middleware**

  ```javascript
  function requireBackendToken(req, res, next) {
    const supplied = parseBearer(req.get('authorization'));
    if (!timingSafeEqualSecret(supplied, runtimeConfig.proxyToken)) {
      return res.status(401).json({ success: false, code: 'PROXY_AUTH_REQUIRED' });
    }
    return next();
  }
  ```

  `local-host` bind `127.0.0.1`；`managed` 可 bind container network address但 browser Socket 直接 `connect_error/BROWSER_SOCKET_DISABLED`。`/health` 无 secret/config details。

- [x] **Step 5: 实现 ticket/room 与路径边界**

  验证 Flask HMAC ticket；连接只加入 `execution:<id>`；所有 execution event 改为 `io.to(room).emit` 并在连接后发送受限 current snapshot。所有 artifact path 以 `path.resolve(outputRoot, executionId, serverName)` 生成并验证仍位于 owning root。

- [x] **Step 6: Flask client 双向 bearer 与旧 client 退役**

  `_ProxySession.get/post` protocol 增加 `headers`；`ProxyExecutionClient` 不再默认 `http://localhost:3001` 于 production，base URL/token 从 validated config 注入。`midscene_python.py` 若仍被 package 调用则携 bearer；无 consumer 时从 package/build contract 移除并由测试证明。

- [x] **Step 7: 运行 GREEN**

  Run: `cd tools/intent-tester && npx jest tests/proxy --runInBand`

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/api/test_execution_api.py -q`

  Expected: both PASS；测试日志/JSON/event 不含 canary token。

---

### Task 5（内部实现步骤，非切片）：managed 持续 progress 与唯一 durable terminal authority

**Files:**

- Modify: `tools/intent-tester/backend/api/executions.py`
- Modify: `tools/intent-tester/backend/services/database_service.py`
- Modify: `tools/intent-tester/frontend/static/js/durable-execution-control.js`
- Modify: `tools/intent-tester/frontend/templates/execution.html`
- Modify: `tools/intent-tester/tests/api/test_execution_api.py`
- Modify: `tools/intent-tester/tests/api/test_execution_page_contract.py`
- Modify: `tools/intent-tester/tests/frontend/test_durable_execution_control.js`
- Modify: `tools/intent-tester/tests/integration/test_durable_execution_loop.py`

**Interfaces:**

- Consumes Node safe running projection: `{executionId, status, steps:[{index,description,status,start_time,end_time,duration}]}`.
- Produces `DatabaseService.apply_execution_progress(execution_id, steps) -> outcome` with `pending/running` CAS.
- Produces JS `startContinuousReconciliation({expectedExecutionId, signal})` / `cancelContinuousReconciliation()` with 500ms→2s bounded backoff and failure budget；首次 restore 可 GET durable record，active 循环每轮都 POST 同源 `/reconcile` 并携 CSRF，让 Flask 拉 Node progress。
- Invariant: running progress cannot write logs/screenshots/params/raw errors or terminal status; terminal lifecycle atomically replaces final steps.

- [x] **Step 1: 写 progress CAS RED tests**

  覆盖 pending/running safe projection、terminal no-op、invalid status/duplicate index、concurrent terminal race、terminal callback replacing intermediate steps、network failure preserving durable state。

- [x] **Step 2: 写 JS long-running/stale/cancel RED tests**

  ```javascript
  test('continuous reconciliation survives the old 1.5 second window', async () => {
      const outcome = await control.startContinuousReconciliation({
          expectedExecutionId: 'run-1', signal: controller.signal
      });
      assert.equal(outcome.kind, 'terminal');
      assert.ok(clock.elapsed >= 1500);
  });
  ```

  另测页面恢复同一 ID、retry/new ID 后旧 response 不 apply、abort 后不再请求、连续失败达到预算后返回 `retry_required` 而非 terminal。

- [x] **Step 3: 运行 RED**

  Run: `node --test tools/intent-tester/tests/frontend/test_durable_execution_control.js`

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/api/test_execution_api.py tools/intent-tester/tests/api/test_execution_page_contract.py -q`

  Expected: FAIL on old finite-attempt exhaustion and absent running step persistence.

- [x] **Step 4: 实现 safe progress CAS 与 reconcile**

  `_reconcile_execution_from_proxy` 对 running projection 调 `apply_execution_progress`；SQL update/transaction 只在 owning execution 状态 active 时生效。若 terminal 已先落盘，progress 返回 `terminal_noop`，不能复活 execution。

- [x] **Step 5: 实现可取消持续轮询**

  JS 每轮先后两次检查 current ID；delay 序列从 500ms 递增到 2s 并保持上限；terminal 结束，AbortController/ID 变化返回 `cancelled/stale`，failure budget 用尽返回 `retry_required`。local-host Socket 只触发提前 reconcile，仍保留同源 polling fallback。

- [x] **Step 6: 运行 GREEN 与 real HTTP loop**

  Run: `node --test tools/intent-tester/tests/frontend/test_durable_execution_control.js`

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/api/test_execution_api.py tools/intent-tester/tests/api/test_execution_page_contract.py tools/intent-tester/tests/integration/test_durable_execution_loop.py -q`

  Expected: PASS；长任务在无 Socket 情况下自动观察中间进度和终态，终态刷新后仍与 DB 一致。

---

### Task 6（内部实现步骤，非切片）：三条部署与启动用户旅程

**Files:**

- Create: `tools/intent-tester/tests/deployment/test_intent_secure_compose.py`
- Modify: `docker-compose.prod.yml`
- Modify: `docker-compose.dev.yml`
- Modify: `docker-compose.dev-cn.yml`
- Modify: `tools/intent-tester/docker/docker-compose.yml`
- Modify: `.github/workflows/deploy.yml`
- Modify: `tools/intent-tester/proxy_templates/.env.example`
- Modify: `tools/intent-tester/proxy_templates/start.sh`
- Modify: `tools/intent-tester/proxy_templates/start.bat`
- Modify: `scripts/ci/build-proxy-package.js`
- Modify: `scripts/ci/deploy.sh`
- Modify/generated: `dist/intent-test-proxy/`、`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`
- Modify: `tools/intent-tester/tests/integration/test_proxy_package_smoke.py`

**纵向场景边界：**

- Production managed：发布者提供 secrets 与 execution 开关 → workflow 在替换 `.env` / deploy 前完成事务式校验 → Compose 只经 Nginx 暴露服务并以 service DNS 连接 managed Node → 缺任一条件 secret 时可观察地 fail-closed。
- Development managed：开发者启动任一开发 Compose → Flask 只在 loopback 暴露，DB/Node 保持内部并以 service DNS 连通 → rendered Compose 可直接证明没有 host bridge 或公开 DB/Node 端口。
- Native local-host：操作者解压确定性代理包并填写 `.env` → 启动脚本在安装/启动副作用前校验全部配置 → 合法 loopback 配置真实启动 `/health`，非法配置稳定非零退出且不泄露 secret。

下面每个步骤都以一条上述旅程的输入、跨边界动作和可观察结果为闭环；Compose、workflow、脚本和 package 只是旅程所经过的实现层，不再作为独立执行单元。

- [x] **Step 1: 生产 managed 启动旅程 RED**

  在 `test_intent_secure_compose.py` 写一个完整 production scenario：只有 Nginx 发布端口；Postgres、Flask、Node 不发布端口；DB/Flask secret 使用 `${VAR:?message}`；无 `host.docker.internal`；Flask 通过 `http://intent-execution-proxy:3001` 调用带 `profiles: [execution]` 的 managed Node。同步断言 workflow 的 `envs`、`require_secret`、managed-key filter 与 `.env.managed` writer 完整，并且缺失条件 secret 时失败发生在 `mv .env.managed .env` 和 deploy 之前。

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/deployment/test_intent_secure_compose.py -q`

  Expected: FAIL on production secret fallback、host ports/bridge、缺失 managed service 与不完整 workflow transaction。

- [x] **Step 2: 生产 managed 启动旅程 GREEN**

  只修改 `docker-compose.prod.yml`、`.github/workflows/deploy.yml` 与 `scripts/ci/deploy.sh` 闭合上述 scenario。`INTENT_EXECUTION_ENABLED=false` 不要求 provider/proxy secret且普通 Compose 启动；`true` 才验证并使用 `--profile execution`。完成后重跑 Step 1，必须 PASS，才进入开发路径。

- [x] **Step 3: 开发 managed 启动旅程 RED→GREEN**

  先增加 dev/dev-cn/模块 Compose scenario：Flask 唯一 host publish 为 `127.0.0.1:5001:5001`，显式 `AI4SE_ENV=development`、`INTENT_ACCESS_MODE=local-dev`、loopback Origin；Docker 内执行使用 managed service DNS，DB 与 Node 不发布 host port且无 host bridge。运行测试确认 RED 后，仅修改三个开发 Compose 文件并重跑到 GREEN。

- [x] **Step 4: native local-host 包启动旅程 RED**

  扩展 `test_proxy_package_smoke.py`：clean-room 分别验证 missing token/topology/origin/provider 非零退出；合法 local-host loopback 配置能真实启动；`.env.example` 明确 topology/token/origin/provider/callback；server、lock、env、start scripts 与 expanded package 同步；两 ZIP 与 expanded tree byte-identical。

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/integration/test_proxy_package_smoke.py -q`

  Expected: FAIL on package 缺少完整安全配置和旧隐式默认。

- [x] **Step 5: native local-host 包启动旅程 GREEN**

  修改 `.env.example`、`start.sh`、`start.bat` 与 `build-proxy-package.js`，让启动脚本在任何安装/启动副作用前验证 `.env` 的完整 local-host contract；重建 expanded tree 与两个 ZIP。合法配置真实启动 `/health`，缺失任一必需项稳定非零退出且不打印 secret。

- [x] **Step 6: 三条用户旅程联合门禁**

  Run: `node scripts/ci/build-proxy-package.js`

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/deployment/test_intent_secure_compose.py tools/intent-tester/tests/integration/test_proxy_package_smoke.py -q`

  Expected: PASS；production managed、dev managed 与 native local-host 三条真实启动路径分别闭环；两 ZIP 同一 SHA-256，expanded tree 与 archive 完全一致。

---

### Task 7（内部实现步骤，非切片）：两条真实浏览器安全用户旅程

**Files:**

- Create: `tools/intent-tester/tests/e2e/conftest.py`
- Create: `tools/intent-tester/tests/e2e/test_stored_xss_csp.py`
- Modify as defects demand: only QS-04 files owned by Tasks 1–6

**纵向场景边界：**

- Restricted operator：操作者在真实 Chromium 登录 → 通过 canonical Origin + CSRF 的真实 API 写入覆盖各字段的攻击文本 → SQLite 持久化 → 打开列表、编辑、执行与 local-proxy 页面并保留合法交互 → CSP、DOM、网络、dialog 与 exfil 证据共同证明文本未执行；foreign Origin 写入被拒绝。
- Public-readonly anonymous：operator 先通过同一真实入口创建用例 → 匿名浏览器读取公开摘要 → API 投影不含步骤和创建者 → 直接详情 URL 与 mutation 都以声明的只读错误失败。
- 两条旅程共用 real Flask HTTP/random loopback/isolated SQLite/real Playwright Chromium harness；harness 是支撑 seam，不单独算完成步骤或证据。

- [x] **Step 1: 建立最小可诊断浏览器 seam，立即由 restricted 旅程消费**

  启动 Werkzeug test server thread/random port，使用 fixture 创建 hashed admin password和 restricted config；Chromium 缺 executable/OS permission 时明确 `BLOCKED` 并给出恢复命令，不能 skip 成 PASS。

- [x] **Step 2: restricted operator 写入到安全渲染旅程 RED→GREEN**

  payload 覆盖 TestCase name/description/category、step action/description/params/output_variable、`</script><script>`、`<img onerror>`、SVG/onload、attribute break-out、inline handler、`javascript:`、恶意 report path；逐一经真实 mutation path 持久化并打开 routed list/edit/execution/local-proxy。

  ```python
  assert page.locator("text=<img src=x onerror=window.__intentXss=1>").count() == 1
  assert page.evaluate("window.__intentXss") is None
  assert exploit_requests == []
  assert dialogs == []
  ```

- [x] **Step 3: public-readonly operator 创建到匿名只读旅程 RED→GREEN**

  operator 通过真实浏览器创建用例；匿名浏览器能够看到公开摘要，但服务端投影无 `steps` / `created_by`，直接编辑 URL 与 mutation 都返回 `READ_ONLY_MODE`。同时在 restricted 旅程断言 CSP nonce 每 response 不同、无 unsafe-inline/eval/wildcard、零 inline event/style attribute、零 CDN request，且登录、创建、编辑和 execution control 仍可交互。

- [x] **Step 4: 两条浏览器旅程与 execution 承接联合门禁**

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/e2e/test_stored_xss_csp.py -q`

  Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tools/intent-tester/tests/integration/test_durable_execution_loop.py -q`

  Expected: PASS；若首次 sandbox browser 权限失败，保留该原始 BLOCKED 证据并在允许的本机上下文重跑，只有真实 Chromium 通过才离开本步骤。

---

### Task 8（内部实现步骤，非切片）：全量验证、双轴审查、记录与 QS-04 单一交付

**Files:**

- Modify: `docs/todos/2026-07-10-ai-coding-test-quality-improvement.md`
- Keep: `docs/superpowers/specs/2026-07-11-qs04-intent-access-browser-security-design.md`
- Keep: `docs/superpowers/plans/2026-07-11-qs04-intent-access-browser-security.md`
- Review: all QS-04 diff only

**Interfaces:**

- Consumes all RED/GREEN evidence from Tasks 1–7.
- Produces one QS-04 completion record, one exact staged set, one commit, and a push decision; no internal-step commit.

- [x] **Step 1: 主 Agent 做厚切片身份与 diff ownership 审计**

  Run: `git status --short`

  Run: `git diff --name-status`

  Run: `git diff --check`

  Expected: only QS-04 planned paths plus generated proxy artifacts；无 4A/4B、checkpoint commit、unrelated user file、secret 或 runtime log。

- [x] **Step 2: 运行聚焦与模块全量**

  Run: `python3 -m pytest -p no:cacheprovider tools/intent-tester/tests -q --cov=tools/intent-tester/backend --cov-report=term`

  Run: `node --test tools/intent-tester/tests/frontend/test_durable_execution_control.js tools/intent-tester/tests/frontend/test_enhanced_editor_controller.js tools/intent-tester/tests/frontend/test_variable_validation_security.js`

  Run: `cd tools/intent-tester && npm run test:proxy -- --runInBand`

  Result: Python `510 passed`（coverage 模式 `1573 warnings`）；frontend Node `59/59`；proxy Jest `40/40`。真实浏览器、real HTTP、package smoke 的独立结果均可定位。不得禁用 pytest plugin autoload；该做法会错误禁用仓库所需的 `pytest-asyncio`。

- [x] **Step 3: 运行动态 CI 等价与仓库回归**

  Run: `./scripts/test/test-local.sh`

  Run: `flake8 --select=E9,F63,F7,F82 tools/intent-tester/backend`

  Run: `node scripts/ci/build-proxy-package.js`

  Run: `git diff --check`

  Result: `test-local.sh all` 在受限执行上下文中如实为 `NOT_PASS`：Intent/proxy 子进程绑定回环端口得到 `EPERM`，后续无条件 `playwright install chromium` 停滞后由主 Agent 中止；同一产品子门禁在本机权限上下文分别以 Python `510/510`、proxy `40/40`、Chromium `2/2` 重跑通过，脚本在该环境下的重复安装/权限适配由 `QS-07/QG-007/QG-014` owning。critical flake8、生成物重建、ZIP identity、Node/shell syntax 和 `git diff --check` PASS。该 runner 结果不改写为 PASS。

- [x] **Step 4: 执行一次厚切片级 Standards 与 Spec 双轴 review**

  生成一份 QS-04 审查包，包含 spec / plan 链接、`HEAD` 后完整 diff、ownership、关键契约风险、聚焦/跨层/全量证据及已知缺口。使用 `code-review`/Superpowers requesting-code-review，让 Standards 与 Spec 两个只读 reviewer 并行读取同一份审查包；它们属于同一轮厚切片审查。任一 Critical / Important 发现返回 IMPLEMENT 修复并重跑受影响验证；复审默认只读取原发现、修复 delta、相邻影响面和新增证据，直到两轴均 `CLEAN/READY`。

- [x] **Step 5: 更新 owning todo 的 QS-04 终态与下一入口**

  只有访问、Origin/CSRF、CSP/真实浏览器、Node topology/auth/ticket/room、managed progress、production fail-closed、package/Compose/workflow 和全量门禁都有当前证据时，才把 QS-04 标为完成并将下一 owning 厚切片保持为 QS-05。记录命令、pass counts、ZIP hash、review 结论与未消除风险。

- [x] **Step 6: 精确 staging 并形成唯一 QS-04 commit**

  先把 `git diff --name-only` 与 Task 1–7 ownership 逐项核对，再只运行以下显式路径的 staging；若实现审查删去某个候选文件，该路径不存在时从命令移除并在交付记录说明，不能用目录级 `git add` 扩大范围。

  ```bash
  git add -- \
    .github/workflows/deploy.yml \
    docker-compose.prod.yml docker-compose.dev.yml docker-compose.dev-cn.yml \
    scripts/ci/build-proxy-package.js scripts/ci/deploy.sh \
    docs/ARCHITECTURE.md docs/TESTING.md docs/api-contracts.md \
    docs/strategy/goal-mode-playbook.md \
    docs/todos/2026-07-10-ai-coding-test-quality-improvement.md \
    docs/superpowers/specs/2026-07-11-qs04-intent-access-browser-security-design.md \
    docs/superpowers/plans/2026-07-11-qs04-intent-access-browser-security.md \
    tools/intent-tester/backend/app.py tools/intent-tester/backend/extensions.py \
    tools/intent-tester/backend/views.py tools/intent-tester/run.py \
    tools/intent-tester/requirements.txt tools/intent-tester/docker/Dockerfile \
    tools/intent-tester/backend/intent_security/__init__.py \
    tools/intent-tester/backend/intent_security/config.py \
    tools/intent-tester/backend/intent_security/policy.py \
    tools/intent-tester/backend/intent_security/web.py \
    tools/intent-tester/backend/api/__init__.py \
    tools/intent-tester/backend/api/testcases.py \
    tools/intent-tester/backend/api/executions.py \
    tools/intent-tester/backend/api/midscene.py \
    tools/intent-tester/backend/api/proxy.py \
    tools/intent-tester/backend/models/models.py \
    tools/intent-tester/backend/services/database_service.py \
    tools/intent-tester/backend/services/proxy_execution_client.py \
    tools/intent-tester/browser-automation/midscene_server.js \
    tools/intent-tester/browser-automation/midscene_python.py \
    tools/intent-tester/frontend/templates/base_layout.html \
    tools/intent-tester/frontend/templates/testcases.html \
    tools/intent-tester/frontend/templates/testcase_edit.html \
    tools/intent-tester/frontend/templates/execution.html \
    tools/intent-tester/frontend/templates/local_proxy.html \
    tools/intent-tester/frontend/templates/login.html \
    tools/intent-tester/frontend/static/js/intent-security.js \
    tools/intent-tester/frontend/static/js/safe-dom.js \
    tools/intent-tester/frontend/static/js/enhanced-editor-controller.js \
    tools/intent-tester/frontend/static/js/durable-execution-control.js \
    tools/intent-tester/frontend/static/js/button-protection.js \
    tools/intent-tester/frontend/static/js/components/EnhancedStepEditor.js \
    tools/intent-tester/frontend/static/js/list-components.js \
    tools/intent-tester/frontend/static/js/smart-variable-input.js \
    tools/intent-tester/frontend/static/js/utils/variableValidation.js \
    tools/intent-tester/frontend/static/css/intent-security.css \
    tools/intent-tester/frontend/static/vendor/axios-1.13.2.min.js \
    tools/intent-tester/frontend/static/vendor/socket.io-client-4.8.1.min.js \
    tools/intent-tester/proxy_templates/.env.example \
    tools/intent-tester/proxy_templates/start.sh \
    tools/intent-tester/proxy_templates/start.bat \
    tools/intent-tester/docker/docker-compose.yml \
    tools/intent-tester/tests/security/test_access_policy.py \
    tools/intent-tester/tests/security/test_csp_contract.py \
    tools/intent-tester/tests/security/test_origin_csrf.py \
    tools/intent-tester/tests/security/test_security_config.py \
    tools/intent-tester/tests/e2e/conftest.py \
    tools/intent-tester/tests/e2e/test_stored_xss_csp.py \
    tools/intent-tester/tests/deployment/test_intent_secure_compose.py \
    tools/intent-tester/tests/conftest.py \
    tools/intent-tester/tests/intent_test_config.py \
    tools/intent-tester/tests/test_app_factory_database_isolation.py \
    tools/intent-tester/tests/api/test_execution_api.py \
    tools/intent-tester/tests/api/test_execution_page_contract.py \
    tools/intent-tester/tests/api/test_midscene_api.py \
    tools/intent-tester/tests/frontend/test_durable_execution_control.js \
    tools/intent-tester/tests/frontend/test_enhanced_editor_controller.js \
    tools/intent-tester/tests/frontend/test_variable_validation_security.js \
    tools/intent-tester/tests/proxy/midscene-server-api.test.js \
    tools/intent-tester/tests/proxy/midscene-integration.test.js \
    tools/intent-tester/tests/integration/test_durable_execution_loop.py \
    tools/intent-tester/tests/integration/test_proxy_package_smoke.py \
    nginx/nginx.conf scripts/health/health_check.sh \
    dist/intent-test-proxy dist/intent-test-proxy.zip \
    tools/intent-tester/frontend/static/intent-test-proxy.zip
  ```

  Run: `git diff --cached --name-status`

  Run: `git diff --cached --check`

  Expected: staged set 与本计划 ownership 精确一致，没有其他用户改动。

  Commit: `git commit -m "fix(intent): 收口访问与浏览器安全边界"`

  Expected: exactly one new QS-04 commit after `7a7396c5`；spec、plan、实现、生成物、todo 记录同属该 commit。

  Result: ownership 审计后精确暂存 82 个 QS-04 文件；无 unstaged/untracked 漏项，cached diff check PASS；secret scan 仅命中两处测试 canary。唯一 commit 由紧随本计划更新的交付命令形成。

- [ ] **Step 7: 推送 master 或记录真实外部阻塞**

  Run: `git push origin master`

  Expected: push exact local `master` succeeds；若 GitHub device authorization/credential 仍阻塞，保留 stderr、当前 ahead count 与恢复触发器，不创建新 branch、不重写 commit、不把 push 阻塞伪装成 QS-04 工程门禁通过。

---

## 执行与审查分工

- 采用 Superpowers subagent-driven 方式，但受用户“一厚切片一 commit”覆盖：worker 不 commit/push，不创建 branch/worktree。
- 主 Agent 先执行/集成 Task 1–2 的共享安全 seam；之后可把无重叠 writer 分为 UI/CSP、Node、deploy/package 三条 ownership，managed progress 由主 Agent 串行接线。
- 每个 writer 返回文件清单、RED/GREEN 命令和原始结果；主 Agent 检查 `git status`、允许路径 diff 与最小测试后才采信。
- Task 1–3 已完成的历史独立审查证据保留但不重复；Task 4 执行本计划声明的唯一高风险契约冻结检查点；Task 5–7 不再各自生成正式审查包或派发完整代码审查，只执行 TDD、聚焦验证、ownership 与主 Agent diff 复核。
- Task 7 真实浏览器证据可由只读 verifier 采集；Task 8 的 Standards / Spec reviewer 并行读取同一份厚切片审查包。reviewer 不修改、commit 或 push。
- 任何内部步骤发现新 P0/P1 都留在同一 QS-04 修复；只有完整 CGA 证明切片身份失效才允许回到 ASSESS，不能因工作量、文件数或测试耗时拆薄。

## Plan Self-Review 记录

- **Spec coverage:** 设计中的 access modes、机械 allowlist、session/Origin/CSRF、principal、strict CSP/safe DOM、local-host/managed topology、bearer/ticket/room、managed progress、terminal authority、production preflight、Compose/workflow/package、真实浏览器与交付门禁分别映射到 Tasks 1–8，无缺口。
- **完整性检查:** 没有未决标记、泛化“补错误处理”或未命名测试；所有行为步骤给出 exact file、interface、命令和可观察预期。
- **Type consistency:** `IntentSecurityConfig`、`EndpointPolicy`、`IntentPrincipal`、`ProxyExecutionClient(token)`、`apply_execution_progress`、`startContinuousReconciliation` 在首次定义和后续消费处名称一致。
- **Scope check:** 四条风险链共享同一未授权执行/stored-XSS/open-proxy/production-default 用户安全目标和同一运行链，单独交付任一条都不能闭合 QS-04 七项门禁，因此保持一个厚切片、一个 plan、一个 commit。
