# QS-04 Intent Tester 访问与浏览器安全边界设计

## 厚切片身份基线

- **ID / 名称**：`QS-04 — Intent Tester 访问与浏览器安全边界`。
- **完整用户任务**：让 Intent Tester 在公开只读、本地开发和受限生产三种声明模式下具有一致、可执行的访问策略；未授权或错误来源不能写入、执行或控制任务，持久化用户内容不能在浏览器中执行代码，本地 Node proxy 不能被任意网页或局域网调用，所有直接生产入口缺少必需 secret 时必须 fail-closed。
- **历史顺序基线**：[已归档的 AI Coding 测试质量改进待办](../../todos/archive/2026-07-10-ai-coding-test-quality-improvement.md#厚切片序列)。本设计当时固定承接已完成的 `QS-03` 并把 `QS-05` 作为下一项；2026-07-16 用户已取消该后续序列，不能据此恢复实施。
- **纳入边界**：Intent page/API 访问模式、单管理员 session、Origin/CSRF、session cookie、CSP 与安全响应头、持久化 TestCase/Execution 内容的安全 DOM/Jinja 渲染、production Node proxy 的显式 topology/origin/token/ticket、lifecycle callback 身份、生产 Compose 默认 secret 与直接端口、真实浏览器 exploit regression。
- **排除边界**：不建立企业级身份平台、组织/角色/租户模型或 SSO；不改变 `QS-03` canonical execution identity；不实现 `QS-05` release transaction、生产 PostgreSQL 组合或回滚；不承担 `QS-08` 的通用 secret/privacy/dependency scanner 治理；不调用真实付费 AI provider。
- **七项门禁**：入口是 Intent 页面/API，以及声明为 local-host 时浏览器到 localhost proxy；动作是登录、读取、创建/修改/删除/执行用例或连接代理；处理是 Flask 安全策略统一裁决 principal、mode、Origin、CSRF 和 proxy credential，Node 验证 topology/origin/token/ticket；可见结果是合法用户功能保持、未授权/错误来源得到明确 401/403；状态承接是签名 session、CSRF token 和绑定 execution 的短期 proxy ticket；失败反馈是稳定、脱敏错误码与 startup preflight；证据是访问矩阵、负向配置、Node contract、真实浏览器 stored-XSS/CSP 回归和生产配置 contract。
- **依赖 / 验收 / 单一交付**：依赖 `QS-01` 的安全测试隔离和 `QS-03` 的 durable execution/proxy contract；只有访问、渲染、proxy 和生产配置四条风险链及全部门禁共同闭合后，才形成一个 `QS-04` 聚焦 commit。下面所有安全模块、页面、测试和配置工作都是内部实现步骤，不是子切片。

## 目标承接检查

### 当前目标、顺序与上一轮证据

`docs/todos/2026-07-10-ai-coding-test-quality-improvement.md` 已将 `QS-01`、`QS-02`、`QS-03` 记录为完成并把 `QS-04` 设为下一 owning 厚切片。`QS-03` 的 canonical ID、Flask durable authority、production Node app 与 package 已由提交 `7a7396c5` 收口；厚切片治理提交为 `2cbb8100`。Git 工作区在设计启动时干净，分支为 `master`。远端 push 的 GitHub device authorization 已过期，留待 `DELIVER` 重试，不改变本地顺序或 QS-04 边界。

### 当前事实仍支持既定顺序

- Flask 当前没有登录、session access policy、Origin/CSRF 或安全响应头；`SECRET_KEY` 存在开发默认值。
- TestCase mutation、execution create/stop/retry/reconcile 和页面均可匿名访问；生产 Compose 还直接发布 `5001`，绕过 Nginx。
- routed `testcases.html`、`testcase_edit.html` 和 `execution.html` 将持久化字段送入 `innerHTML` 或 `steps_data | safe`；`testcases.html` 可直接形成 stored-XSS 链。
- `base_layout.html` 从 CDN 加载脚本，存在大量 inline script；routed templates 仍有 inline event handler，当前无法部署有效的 strict script CSP。
- production Node app 监听所有接口、HTTP/Socket.IO CORS 为 `*`、没有调用凭据；任意网页可探测或调用用户机器上的 `localhost:3001`。
- 真实 Chromium 已证明两条 production routed exploit：持久化 TestCase name 的 `<img onerror>` 在列表页执行，持久化 step description 在编辑页执行；两页均没有 CSP header。沙箱内浏览器首次因系统权限 `Operation not permitted` 未运行，改在本机浏览器权限上下文后复现成功，该首次结果不记为 PASS。
- Flask 仍注册旧 `/midscene/execution-start` 与 `/midscene/execution-result` 写路径；前者可绕过 `QS-03` canonical create 并新建 execution，后者可绕过统一 lifecycle 状态机。它们没有现存 production Node consumer，不能只加 auth 后继续作为第二状态路径。
- `docker-compose.prod.yml` 对数据库和 Flask secrets 使用已知默认值，并公开 PostgreSQL/Flask 端口；直接 Compose 不会 fail-closed。

这些事实与 `QG-005` 完全一致，没有新的 P0/P1 要求改变 `QS-04 → QS-05` 顺序。GitHub push 身份是外部交付阻塞，不是改薄或重排当前安全能力包的依据。

### 子智能体与旁路审查

本轮已并行派发三个只读审计：`/root/qs04_access_audit`（Flask/session/CSRF 与生产配置）、`/root/qs04_ui_security_audit`（routed UI stored-XSS/CSP）、`/root/qs04_proxy_audit`（Node proxy）。它们只提供事实和设计复核，不写文件、不提交、不拥有子切片。access/proxy 审计正常返回；UI 审计先返回完整事实消息、但 final 被环境过滤器标错，按 Playbook 缩小为“只复核 spec”后重试并得到 `CLEAN`。主 Agent 负责统一安全策略、最终设计、实现、验证、精确 staging、单一 commit 和 push。

用户已为目标模式授予常规方案与实施决策的持续自主权；依据 Goal Mode Playbook §4.3，设计问答、方案选择和 written-spec review 由主 Agent 结合仓库事实自问自答并记录在本文，不为普通批准暂停。Superpowers 默认的单独 spec commit 被本仓库“一厚切片一交付 commit”规则覆盖，本文与 implementation plan 将随完整 `QS-04` 一次提交。

## 用户、场景与成功状态

### 用户与输入

- **受限生产管理员**：以单个配置管理员账户登录，读取和修改 TestCase、创建/停止/重试 managed execution，并通过 Flask 同源 progress 查看进度；只有 native local-host 才连接同机 localhost proxy Socket。
- **公开访客**：在显式 `public-readonly` 模式读取安全 TestCase summary、版本和下载说明，不能读取 steps/execution/log/variable，也不能调用 mutation；登录后的 operator 仍可使用完整功能。
- **本地开发者**：在非 production 的 `local-dev` 模式免登录开发，但 unsafe request 仍受 same-origin 与 CSRF 保护；Host 端口只绑定 loopback。
- **production Node proxy**：以共享后端 credential 调 Flask lifecycle，以共享 token 接收 Flask HTTP 调度；只有显式 `local-host` topology 才以 execution-bound 短期 ticket 接受已授权浏览器的 Socket.IO 连接，Compose `managed` topology 的浏览器只从 Flask durable polling 获取进度。

输入包括访问模式、execution enabled、管理员密码 hash、Flask secret、唯一 public Origin、proxy topology/token、managed provider credential、HTTP/session request、TestCase/Execution 持久化字段，以及仅在 local-host 下的浏览器 localhost Socket 连接。

### 成功状态

1. production 缺少或使用默认 `SECRET_KEY`、缺 password hash/public Origin/DB credential 时，Flask 在监听前退出；启用 execution 时再条件要求 proxy topology/token 和 provider key/base/model，execution disabled 不要求付费模型。
2. `restricted` 中匿名页面跳登录，匿名 API 返回 401；登录成功后只有正确 Origin + CSRF 的 unsafe request 可执行。
3. `public-readonly` 匿名只允许显式 summary allowlist；登录 operator 的权限与 restricted 一致。匿名编辑、执行、steps/execution detail 和所有 unsafe method 均稳定返回 401/403，不能靠直接 URL 绕过。
4. `local-dev` 只允许非 production，显式要求 `INTENT_PUBLIC_ORIGIN` 且只接受 HTTP(S) loopback Origin，开发 Compose 端口绑定 `127.0.0.1`；免登录不等于免 Origin/CSRF，也不从可伪造的 Host header 推导可信 Origin。
5. 持久化 payload 在 list/edit/execution 的真实浏览器页面只作为文本显示，不创建可执行节点；strict script/style CSP 不含 `unsafe-inline`。
6. Node 不再隐式监听所有接口：native `local-host` 只监听 loopback；Docker `managed` 只监听内部 Compose network、不发布 host port并禁用 browser Socket。敏感 HTTP route 需要 backend token；local-host Socket.IO 需要 execution-bound 短期 ticket；callback 需要 Flask proxy credential。
7. production Compose 不再发布 Flask/PostgreSQL/Node 端口，不再提供已知默认 secret；合法受限 `managed` 配置仍能使用完整 QS-03 durable execution。Flask 持续协调受限 running step snapshot并由页面同源轮询，终态仍由 durable lifecycle 承接；不虚构远端 portal 能直接访问最终用户机器的 localhost。

## 失败路径与下游承接

- 缺少或无效生产配置：startup preflight 抛出固定、无 secret 值的配置错误，进程非零退出。
- 未认证：页面 302 到带安全 `next` 的 login；API 返回 `401/AUTH_REQUIRED`。
- 公开只读越权：页面/API 返回 `403/READ_ONLY_MODE`，不隐式降级成成功。
- Origin 或 CSRF 无效：返回 `403/ORIGIN_REJECTED` 或 `403/CSRF_FAILED`，不执行数据库或 proxy side effect。
- lifecycle callback 缺 proxy credential：返回 `401/PROXY_AUTH_REQUIRED`，不更新 durable record。
- Node Origin/token/ticket 无效：HTTP 401/403 或 Socket.IO `connect_error` 固定码，不回显 token、header 或上游异常。
- 持久化恶意内容：保留原文本供合法用户查看，但不经 HTML sink；CSP violation 可观测且不通过“清洗后假装成功”掩盖存储事实。
- 浏览器或 Node 真实边界不可运行：记录 `BLOCKED/NOT_RUN`，不得用 Flask test client 或 Supertest 冒充浏览器证据。

`QS-05` 只消费本切片已证明的受限入口、fail-closed config 和 proxy credential，建立 production-shaped Nginx/PostgreSQL/release smoke；`QS-08` 再把这里的局部 preflight 归入统一静态治理，不反向弱化运行时门禁。

## 方案比较

### 方案一：Flask 统一安全策略 + session + proxy credential（采用）

Flask 在 request seam 安装一个深安全模块，集中完成配置 preflight、access mode、principal、Origin/CSRF、CSP nonce/header 和 proxy callback credential；页面只消费 capability 与 nonce。Node 使用显式 local-host/managed topology 和后端 token；只有 local-host 使用严格 Origin 与短期 browser ticket。

- 优点：直接端口和 Nginx 后路径行为一致；页面/API/callback 可由同一矩阵测试；localhost proxy 也闭环；不依赖外部身份平台。
- 代价：需要登录页、routed templates 的 CSP/DOM 整改和 proxy package contract 更新。
- 选择理由：复杂度集中在一个 interface，删除该模块会把策略重新散落到所有 endpoint，具备真实 Depth、Leverage 和 Locality。

### 方案二：只使用 Nginx Basic Auth（不采用）

- 优点：配置少、无需 Flask 登录页。
- 缺点：当前直接发布的 `5001` 可绕过；Basic credential 会被浏览器自动携带，仍需 Origin/CSRF；test client 难覆盖真实 gateway；Node proxy 完全未保护；开发和 public-readonly contract 不清楚。

### 方案三：OAuth2 Proxy / 企业 IdP（不采用）

- 优点：可获得组织身份、集中会话与未来角色扩展。
- 缺点：需要外部 IdP、redirect URI、client secret 和部署组件；当前单人维护场景没有可验证的组织需求；会把 `QS-05` 部署事务和“组织级身份平台”非目标拉入本切片。

## 架构与深模块

### Flask `intent_security` 深模块

外部 interface 只暴露 `install_intent_security(app)`。调用者只需在 blueprint 注册前安装一次；模块内部隐藏：

- `AI4SE_ENV`、`INTENT_ACCESS_MODE`、`INTENT_EXECUTION_ENABLED` 与 production secret preflight；
- restricted/public-readonly/local-dev policy matrix；
- `PUBLIC`、`PUBLIC_READONLY`、`OPERATOR`、`PROXY_MACHINE` 四类 endpoint policy 与 URL-map completeness；
- login/logout、safe `next`、session rotation 与 cookie policy；
- per-session CSRF token、exact Origin/Referer 校验；
- page/API 401/403 响应选择；
- per-request CSP nonce、Jinja context、CSP/security headers；
- proxy callback bearer 校验和短期 Socket.IO ticket 签发。

所有 routed endpoint 通过同一个 request seam 受保护，不在每个 view/API 上复制鉴权实现。每个非 static endpoint 必须声明 `PUBLIC`、`PUBLIC_READONLY`、`OPERATOR` 或 `PROXY_MACHINE`；未知或未分类 route 在 startup contract test 中失败，而不是默认为公开。`created_by`、`executed_by` 等审计字段从 principal 派生，不接受客户端伪造。

机械 allowlist 如下，测试直接从同一 registry 与 Flask URL map 比较：

- `PUBLIC`：`/health`、Intent static、`/intent-tester/login` GET/POST，以及根路径到 `/intent-tester/testcases` 的 redirect；login POST 仍要求 pre-auth CSRF + exact Origin。
- `PUBLIC_READONLY`：`/intent-tester/testcases` list page、`GET /intent-tester/api/testcases` 的 summary projection、`/intent-tester/local-proxy` 说明页、`GET /proxy-version`、`GET /download-proxy`。它们只在 `public-readonly` 对 anonymous 开放，在 restricted 仍要求 operator。
- `OPERATOR`：TestCase detail/steps、create/edit page、全部 TestCase mutation、execution page/detail/create/retry/reconcile/stop、proxy ticket和其他敏感读取。
- `PROXY_MACHINE`：唯一 `/executions/<id>/lifecycle` callback。旧 MidScene callback 不在 registry，退役为 410。

anonymous summary 精确包含 `id`、`name`、`description`、`category`、`priority`、`tags`、`is_active`、`updated_at`，不包含 steps、created_by、created_at、execution、log、variable 或内部路径；除此之外 anonymous 默认 deny。公开 proxy version/download 的失败响应不得回显绝对路径或异常正文。

### 访问模式

| 模式 | 允许环境 | 页面/GET | unsafe method / execution | 配置要求 |
|---|---|---|---|---|
| `restricted` | production / development | 登录后允许 | 登录 + exact Origin + CSRF；execution 还要求 enabled | 显式 strong `SECRET_KEY`、admin password hash、public origin；execution enabled 时要求 proxy/provider |
| `public-readonly` | production / development | 匿名仅安全 summary；operator 登录后完整读取 | 匿名 401/403；operator + exact Origin + CSRF；execution 还要求 enabled | 显式 strong `SECRET_KEY`、admin password hash、public origin；execution enabled 时要求 proxy/provider |
| `local-dev` | 非 production | 自动 dev operator | exact Origin + CSRF | 显式 HTTP(S) loopback `INTENT_PUBLIC_ORIGIN`；开发 secret 可用；Flask Host 端口必须 loopback；execution enabled 时 topology 必须显式为 managed 或 local-host；禁止 production |

production 不为 access mode 或 execution enabled 提供隐式 fallback；缺失、未知或 `local-dev` 均启动失败。单管理员登录名固定为 `admin`，credential 只接受 Werkzeug password hash，不接受源码或 Compose 中的明文密码默认值；local-dev principal 为 `local-dev`，proxy machine principal 为 `proxy`。Flask、Node、Compose、workflow、CSP 和 package 的 Origin 唯一事实名为单值 `INTENT_PUBLIC_ORIGIN`；不再维护 `INTENT_APP_ORIGIN` / `INTENT_ALLOWED_ORIGINS` 镜像。

可执行强度规则固定如下：所有 `restricted` / `public-readonly`（包括 development）都要求 `SECRET_KEY`；production `SECRET_KEY` 与 execution-enabled `INTENT_PROXY_TOKEN` 的 UTF-8 编码至少 32 bytes，并拒绝空值及仓库已知默认值 `change_me_in_production`、`dev-secret-key-change-in-production`、`dev-secret-key-please-change-in-production`、`dev-secret-key-please-change`。`INTENT_TESTER_ADMIN_PASSWORD_HASH` 只接受能由 Werkzeug `check_password_hash` 安全解析的完整 `scrypt:` 或 `pbkdf2:` encoded hash。execution enabled 时所有环境都要求显式 topology、trim 后非空的 `OPENAI_API_KEY` / `MIDSCENE_MODEL_NAME` 和 absolute HTTP(S)、无 userinfo 的 `OPENAI_BASE_URL`；production API key 还拒绝 `change_me_in_production`、`your-api-key-here`、`sk-your-api-key-here`，production topology 只允许 managed，production base URL 必须 HTTPS。execution disabled 不要求 topology/token/provider。合法模型名（包括 `qwen-vl-max-latest`）不作为 secret placeholder。`INTENT_PUBLIC_ORIGIN` 在所有 mode 下必须显式配置为无 userinfo/path/query/fragment 的 HTTP(S) origin，production 用 HTTPS，local-dev host 只允许 `localhost`、`127.0.0.1` 或 `::1`，port 可选。production 最终数据库 URI 必须非 SQLite、包含非空 username/password 且不能包含已知默认 credential；preflight 错误只列配置 key，不打印 value。

### Browser 渲染与 CSP

- Jinja 保持 autoescape；结构化步骤以 `tojson` 输出，不使用 `|safe` 拼入 executable script source。
- routed 页面中的持久化字段只进入 `textContent`、`value`、安全 attribute 或显式 DOM factory；event handler 使用 `addEventListener` 和 `data-*`，不拼接 `onclick`。
- `innerHTML` 只允许与运行时用户数据无关的编译期 literal；持久化 TestCase/Execution/step/report/variable 字段不得进入该 sink。通用 DOM builder 只提供 text、enum class、button listener 和 allowlisted URL，不提供“万能 escape + innerHTML”。
- Axios 与 Socket.IO client 改为仓库拥有的静态 vendor asset，不再从任意 CDN 加载。
- 每个 inline script/style block 带 per-request nonce；routed templates 清除 inline event 与 inline style attribute，动态显示/布局改用预定义 class、受限 enum 或原生 progress。CSP 至少包含：`default-src 'none'`、`script-src 'self' 'nonce-…'`、`script-src-attr 'none'`、`style-src 'self' 'nonce-…'`、`style-src-attr 'none'`、`object-src 'none'`、`base-uri 'none'`、`frame-ancestors 'none'`、`form-action 'self'`、受限的 `connect-src`（self；仅 local-host capability 增加精确 loopback proxy）、`img-src 'self' data:`、`font-src 'self'`。不允许 script/style `unsafe-inline`、`unsafe-eval` 或 wildcard；不使用 `upgrade-insecure-requests` 破坏显式 local proxy HTTP/WS。
- 同时返回 `X-Content-Type-Options: nosniff`、`Referrer-Policy: same-origin`、`X-Frame-Options: DENY` 和最小 `Permissions-Policy`。这里不能用 `no-referrer`：真实 Chromium 的 basic form POST 会因此发送 `Origin: null`，与登录和 mutation 必须精确匹配 canonical Origin 的 CSRF 不变量冲突；`same-origin` 保留同源表单的可验证来源，同时不向跨源发送 Referer。

### Production Node proxy topology

- `INTENT_PROXY_TOPOLOGY=local-host`：适用于 native Flask + Node 同主机，Node 只监听 `127.0.0.1`；浏览器可在创建 canonical execution 后申请 ticket 并连接同一 localhost Socket。
- `INTENT_PROXY_TOPOLOGY=managed`：适用于 Flask 与 Node 同处 Compose。Node 可监听容器网络地址，但服务不发布 host port，只在 owning network 被 Flask 调用；browser Socket 强制关闭，页面只轮询 Flask durable API。所有 production access mode（`restricted` 与 `public-readonly`）在 execution enabled 时都只支持该 topology。
- 旧 `host-bridge`（Flask 容器主动访问宿主 Node）不再作为 production 支持路径；dev 可迁移到 managed，或退出 Compose 后使用 native local-host。未来若需要远端 portal 控制最终用户机器，必须另建由本地代理主动发起的配对出站通道，不能恢复隐式 `0.0.0.0`。
- `public-readonly` 的匿名 principal 不允许 execution 或 proxy ticket；operator 是否可执行仍由 endpoint policy 和 topology 共同裁决。
- `INTENT_PUBLIC_ORIGIN` 是唯一 canonical browser Origin；local-host HTTP CORS 与 Socket.IO CORS 精确匹配，managed backend HTTP 不依赖 CORS 作为鉴权且拒绝 browser Socket。
- `INTENT_PROXY_TOKEN` 为至少 32-byte secret。Flask `ProxyExecutionClient` 对 execute/status/stop 携带 bearer token；Node lifecycle callback 对 Flask 携带同一 proxy credential；日志、state、WebSocket 和错误响应不包含 token。
- local-host operator 仅在 Flask 已创建 canonical ID 后，通过 `POST /intent-tester/api/executions/<id>/proxy-ticket`（Origin + CSRF）取得 60 秒 HMAC ticket；ticket wire format 为 `base64url(canonical JSON).base64url(HMAC-SHA256)`，HMAC secret 为 proxy token，payload 绑定 `executionId + canonical origin + aud="intent-proxy-socket" + integer iat + exp=iat+60 + nonce`。Socket.IO handshake 验证后只加入该 execution room，所有 execution event 从 `io.emit` 改为 room emit。连接建立后发送受限 current snapshot，补齐 create response 前的早期事件；页面不接触长期 proxy token。
- `/health` 只返回固定最小状态；local-host 受 exact CORS，managed health 只在内部 network 可达。所有能改变资源、读取 execution state、生成 screenshot/report、触发 AI/browser 或 cleanup 的 HTTP route 均需 backend token；有副作用的 `GET /ai-test` 改为 POST；screenshot/report 路径由服务端生成或限制在 owning output root；status 只返回 Flask reconcile 所需投影。
- managed/local-host 共用同源 progress contract：页面对 active ID 运行可取消、同 ID 二次 guard、500ms 至 2s 有界退避的持续 reconcile；Flask 以 backend token 拉 Node 的最小 running snapshot，并用 `status IN (pending,running)` CAS 持久化 step index/description/status/time 的安全投影。terminal callback 会原子替换最终 steps，仍是唯一终态权威；progress 不持久化 logs、screenshots、params 或 raw errors。连续网络失败达到预算后停止自动轮询并显示 same-ID retry，不假成功。
- 旧 Flask `/midscene/execution-start` 与 `/midscene/execution-result` 取消注册并返回 404，production Node 只使用带 credential 的统一 lifecycle endpoint，不能保留第二 durable 状态机。仍有 consumer 的 `midscene_python.py` 必须迁移到 bearer contract，否则明确退役。
- builder、展开目录、两个 ZIP、`.env.example`、lockfile 与 package smoke 机械同步；缺 topology/token/origin、local-host 非 loopback、managed 发布 host port/启用 browser Socket均使对应 contract 失败。

### Production 配置

- `docker-compose.prod.yml` 删除 DB/Flask secret 的 `change_me_in_production` fallback；通过 `${VAR:?message}` 或应用 preflight 显式失败。production always-required 集是 `AI4SE_ENV=production`、`INTENT_ACCESS_MODE`、`INTENT_EXECUTION_ENABLED`、`INTENT_PUBLIC_ORIGIN`、`DB_PASSWORD`/`DATABASE_URL`、`SECRET_KEY`、`INTENT_TESTER_ADMIN_PASSWORD_HASH`。
- `INTENT_EXECUTION_ENABLED=true` 时条件要求 `INTENT_PROXY_TOPOLOGY`、`INTENT_PROXY_TOKEN`、`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`MIDSCENE_MODEL_NAME`；managed Node 从同一 Compose/workflow secret source 接收 provider 配置。`false` 时 execution page/endpoints/proxy ticket 返回 `403/EXECUTION_DISABLED`，Node service 不启动且不要求 proxy/provider secret。
- production 只由 Nginx 发布 80/443；PostgreSQL 和 Flask 只在 Compose network 可达，不发布 host port。
- managed Node 使用 Compose `execution` profile 和内部 service DNS；deployment 仅在 `INTENT_EXECUTION_ENABLED=true` 时启用该 profile，service 不声明 `ports`。Flask disabled 配置不尝试 health/dispatch，避免“未启动 Node”被 silent fallback 成部分成功。
- preflight 在 `db.init_app()` / `create_all()` 前运行；production 拒绝 SQLite、已知默认值、短于 32 UTF-8 bytes 的 secret、明文管理员密码、`local-dev`、非 HTTPS public/provider origin。Flask session 使用 `Secure`、`HttpOnly`、`SameSite=Lax` cookie。production container 通过 Gunicorn gthread（或等价受支持 WSGI server）启动 Flask-SocketIO，不通过 `socketio.run` / Werkzeug；直接 `python -m backend.app` / `run.py` 在 production 显式退出并指出 production server 入口，非 production 才允许 loopback debug server。
- Flask-SocketIO 未使用的开放 channel 关闭或绑定 exact origin，不能保留 wildcard transport 绕过 request policy。
- dev/dev-cn 明确 `local-dev`，显式配置 HTTP(S) loopback `INTENT_PUBLIC_ORIGIN`，Flask Host 端口绑定 `127.0.0.1`，已知 dev secret 不能在 production mode 通过 preflight；Docker 开发使用 managed Node，native 开发使用 local-host。
- standalone Intent Compose 要么明确 local-dev，要么同样使用 restricted required secrets，不能以 `FLASK_ENV=production` 搭配开发默认值。
- deploy workflow 管理完整 always-required 集，并在 execution enabled 时管理 proxy topology/token 与 provider key/base/model；缺 required GitHub secret 时在写 `.env` 和启动容器前失败。生产 public origin 必须是 HTTPS；TLS 可由 Nginx 或声明的可信上游终止，完整 TLS/Nginx/PostgreSQL 组合仍由 `QS-05` production-shaped smoke 证明。该 preflight 是本切片运行安全门，不替代 `QS-05` 的 release transaction。

## 数据流

### Restricted 页面/API

1. 匿名用户访问 Intent page；安全模块保存经过校验的相对 `next`，返回 login。
2. login GET 创建 pre-auth CSRF；POST 验证 exact Origin、CSRF 和 password hash，清空旧 session 后建立管理员 session。
3. 页面从 Jinja context 获得 CSRF、capability 和 CSP nonce；Axios unsafe request 自动发送 `X-CSRF-Token`。
4. request seam 先判 mode/auth，再判 Origin/CSRF，最后才进入业务 endpoint；失败不触发 DB/proxy。
5. logout 只能 POST + CSRF，并清空 session。

### Public read-only

1. 访客访问 allowlisted TestCase summary list/version/download/health；summary DTO 不含 steps、execution、log、variable 或审计详情。
2. 页面 capability 隐藏 create/edit/execute/delete 控件；直接 URL 和直接 API 仍由 server policy 拒绝。
3. operator 可从同一 login 进入完整功能；匿名 unsafe method、execution detail/control、非 allowlisted endpoint 返回 401/403。前端隐藏不是安全依据。

### Proxy execution/progress

1. 仅当 `INTENT_EXECUTION_ENABLED=true` 时，`restricted` 或 `public-readonly` 的已登录 operator，以及 `local-dev` 的 dev operator，才能以 CSRF request 创建 durable execution；Flask 以 bearer token 调 Node。disabled 时在创建前返回 `403/EXECUTION_DISABLED`。
2. Node 验证 token 后执行同一 canonical ID，并以 bearer token回调 Flask lifecycle。
3. local-host 页面在 canonical ID 创建后申请 execution-bound ticket 并连接该 execution room；Node 校验 Origin、aud、executionId、签名和过期，并发送受限 snapshot。managed 页面不连接 Node，而是以可取消、同 ID 防陈旧和 500ms 至 2s 有界退避的循环持续轮询 Flask。
4. 对仍为 `pending/running` 的 execution，Flask 以 backend token 拉取 Node 的最小 running snapshot，并通过 CAS 只持久化安全的 step progress 投影；页面刷新后从 durable record 恢复并继续同一 ID 的轮询。
5. terminal lifecycle callback 原子替换最终 steps，仍是唯一终态权威；durable GET/reconcile/stop/retry 始终走 Flask。Socket.IO 只加速 local-host 可见性且有同源 polling fallback，缺少 Socket 或页面断开都不能阻断 execution completion。

## 错误处理与可诊断性

- 所有安全失败使用固定 code，不返回配置值、hash、token、cookie、Origin allowlist 或异常 traceback。
- API 安全失败统一形状为 `{"code": HTTP status, "message": generic message, "error": {"code": stable code}}`，至少固定 `AUTH_REQUIRED`、`READ_ONLY_MODE`、`ORIGIN_REJECTED`、`CSRF_FAILED`、`PROXY_AUTH_REQUIRED`、`EXECUTION_DISABLED`、`PROXY_TICKET_UNAVAILABLE`；页面按 mode 返回 login redirect 或同码 403，不靠前端隐藏授权。
- 认证失败对外统一，避免区分用户是否存在；日志只记录固定事件、request path、mode 和脱敏 client category。
- CSP nonce 每 request 新建，不持久化、不写日志。
- proxy ticket 过期只要求 local-host 页面按同一 active execution 重新申请；不回退到长期 token、匿名 Socket.IO 或全局 event stream。
- production preflight 一次性列出缺失 key 名称，不打印 value；容器不得以部分安全配置继续启动。
- public-readonly 与 restricted 不做“请求失败后自动 local-dev”兼容分支。

## 测试设计

### Flask contract / TDD

- 配置矩阵：production missing/unknown mode、SQLite、weak/default/short secret、restricted/public missing hash、missing/HTTP origin、missing token、production local-dev、任一 production access mode 在 execution enabled 时使用 local-host、local-dev 缺失/非 loopback Origin、非法 topology/bind 均 RED；合法 restricted/public-readonly/local-dev GREEN，并证明 preflight 早于 DB init。
- route-policy completeness 与访问矩阵：所有 URL-map endpoint 必须归类；page/API × anonymous/operator/proxy × safe/unsafe × mode 证明 302/401/403/200 与 side-effect count，未授权请求不查询或修改 DB；审计字段来自 principal。
- CSRF/Origin：missing/wrong token、foreign/null Origin、safe canonical Origin、login/logout、safe next、session rotation、cookie flags。
- lifecycle proxy credential 与 execution-bound proxy-ticket：missing/wrong/valid/expired/tampered/execution mismatch，证明 durable record 不被未授权 callback 修改，旧 callback 不能创建第二 identity。
- headers/CSP：nonce per request、script/style policy 无 `unsafe-inline`、`script-src-attr/style-src-attr 'none'`、frame/object/base/form/header contract。

### DOM / browser exploit regression

启动真实 Flask HTTP + SQLite，使用真实 Chromium；通过已裁决的 operator/Origin/CSRF 路径持久化恶意 TestCase/steps，而不是直接 DB 注入。payload 覆盖 name/description/category、step description/action/params/output variable、`</script>`、`<img onerror>`、SVG/onload、attribute break-out、inline handler、`javascript:` 和恶意 report path。只测试真实 routed list/create/edit/execution/local-proxy，不拿未路由的 `step_editor.html` 或 redirect-only `index.html` 充数：

- payload 文本可见但 `window.__intentXss` 始终未设置；
- 没有 payload 创建的 `script/img/svg` 可执行节点；
- CSP header 可观察且浏览器拦截无 nonce script/style/attribute；所有 inline block nonce 与当次 response 一致，CDN script request 为零；
- 合法登录、创建/编辑/执行控制仍可交互；
- foreign-origin mutation 和 public-readonly 直接 URL 在浏览器/API 均失败。

真实浏览器是 stored-XSS/CSP 的不可豁免证据；template scan/test client 只提供更快定位。

### Node / package / 组合

- Jest/Supertest/Socket.IO client：local-host/managed config、listen host、browser Socket disabled in managed、allowed/disallowed Origin、missing/wrong token、valid backend token、ticket execution/aud/origin/exp valid/invalid、execution room isolation/snapshot、callback header、legacy route removal、side-effect HTTP method、path confinement、status minimal projection 和 secret non-leak。
- real HTTP Flask↔production Node：同一 ID 调度/回调在 valid credential 下完成，invalid callback 不改变 durable record。
- managed 长任务 progress：任务运行超过旧的 1.5 秒观察窗时，页面在无 Node Socket 的条件下仍持续获得 active step snapshot 并自动观察到终态；刷新页面可从 durable record 恢复同一 ID；cancel、retry 或切换新 execution 后，旧 ID 的迟到响应不能覆盖当前 UI；terminal callback 覆盖中间投影并保持唯一 durable 终态权威。
- deterministic package：展开目录与两个 ZIP hash一致，`.env.example` 包含 topology/token/origin/bind contract，clean-room 缺安全配置 fail-closed。
- Compose/deploy contract：production 无默认 secret/host DB/Flask/Node ports；required env 缺失得到非零 preflight；dev 为 local-dev 且 Flask 仅 loopback publish，Node 使用 internal managed service。

### 回归层级

先运行安全配置、access/CSRF、DOM renderer、Node auth 的聚焦 RED/GREEN；再运行 Intent Python 全量、proxy Jest、真实 HTTP、package smoke、真实浏览器 exploit；最后执行当前仓库动态 CI 等价门、critical lint/build、`git diff --check` 和双轴 code review。所有内部测试组只记为 QS-04 证据，不单独提交或交付。
