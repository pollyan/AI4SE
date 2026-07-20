# AI Coding Loop 自动化测试与质量保障改进

- 状态：`ARCHIVED` — `QS-01` 至 `QS-04` 的完成证据保留；2026-07-16 用户取消 `QS-05` 至 `QS-08` 及其他旧 backlog；`QG-017` 至 `QG-020` 已在后继能力包完成并归档
- 创建日期：2026-07-10
- 事实版本：`b5a2db738495e6f3daccc6238ab3d2a1ced5d5b5`
- 当前分支：`master`
- 历史发现：19 项（P0 7 / P1 6 / P2 5 / P3 1）；当前活跃项：0
- 厚切片：8 个（`QS-01` 至 `QS-08`）
- 唯一目标：让 AI Coding Loop 获得安全、诚实、分层、可诊断且成本匹配风险的自动化证据
- 归档边界：`QS-01` 至 `QS-04` 的实现与证据见下方执行记录；未完成旧项均按用户决定取消，不再恢复；`QG-017` 至 `QG-020` 的完成定义与最终证据见 [`2026-07-16-new-agents-streaming-and-artifact-ux.md`](2026-07-16-new-agents-streaming-and-artifact-ux.md)

## 背景与需求

AI Coding Loop 的安全性不取决于“有多少测试文件”，而取决于需求、代码变更、可执行验证、失败诊断和发布结果能否形成可信闭环。AI Agent 会高频重复运行测试并依据退出码继续修改代码；一旦测试能在零收集、依赖缺失、真实服务未启动或数据库绑定错误时仍给出绿色结果，自动化速度会放大而不是降低风险。

本次扫描确认仓库已经具备较强的 New Agents manifest / contract / renderer / typed SSE 正向保障，也有 Intent Tester API 测试、前端类型检查、Compose 和部署脚本。但关键风险面同时存在以下信任断点：

1. 部分入口会把 `NOT_RUN`、零测试或工具自身失败表达为成功。
2. Intent Tester 测试数据库 fixture 会绑定默认或环境数据库，随后执行 `drop_all()`；本次扫描中的一次完整运行后，默认开发库已出现表被清空的匹配证据。
3. Intent Tester 的前端、Node 代理和 Flask 持久化链路使用不同 execution ID 和不同回调前缀，而当前“集成测试”没有运行生产代理代码。
4. New Agents 的单轮成功路径由多次独立提交组成，数据库失败可能留下半持久化状态；前端又会把缺少终态事件的 EOF 当成正常结束。
5. 生产发布先覆盖 live 目录再备份，回滚不恢复上一镜像；健康检查没有证明 New Agents 前端、数据库读写或共享 stream 主路径可用。
6. 确定性 contract 测试不能替代语义质量。当前浏览器套件实际触发的 Alex LLM judge 得分 77，低于门槛 80。
7. New Agents 的 artifact-data 阶段把 `artifact_data` 排在 `chat` 前，右侧可先收到连续的可渲染增量；左侧自然对话只能在 `artifact_data` 之后开始提取，可能显著延后。用户现场观察为右侧完成前后左侧才出现内容；现有测试没有保护双栏的可见进度顺序。

本 todo 的目的不是增加泛化的“覆盖率”，而是逐项恢复这些工程信任能力，使后续目标模式能够按风险纵向交付独立可验收的质量增量。

## 目标态

全部整改完成后，仓库应同时具备以下能力：

1. 任一测试入口都能区分 `PASS`、`FAIL`、`NOT_RUN`、`BLOCKED`、`TIMEOUT` 和 `FLAKY`；零收集、缺环境、工具错误、子进程异常退出或未收到协议终态不得成为绿色。
2. 测试进程只能连接显式声明的测试数据库；初始化前完成配置，拒绝生产/开发数据库，且 fixture 清理不会删除非测试数据。
3. AI Agent 可以从一份机械可验证的入口映射中选择聚焦、模块、跨层、全量和外部质量门，并知道每个入口证明与不证明什么。
4. New Agents 的所有 workflow 继续复用共享 `/api/agent/runs/stream`、typed SSE、持久化和 UI 基础设施；每一轮对 run/message/artifact/version/metric 的成功或失败都有原子、幂等、可恢复的结果。
5. 合法 Agent 流必须以明确终态结束；取消、断流、重试、重复请求、并发版本竞争、无效事件和持久化失败都有后端与前端负向证据，不能保存部分产物为正常版本。
6. Intent Tester 的“选择用例 → 创建执行 → 本地代理执行 → 回调进度/结果 → 停止/恢复 → 持久化查看”使用一个 canonical execution ID，并由真实 Flask HTTP 与生产 Node app 的组合测试保护。
7. Intent Tester 的访问模型被明确；未经授权的写入被拒绝，持久化用户字段在真实浏览器中不能形成 XSS，代理的来源、凭证和本机边界有机械保护。
8. 至少一条真实组合路径使用生产前后端、Nginx 路由和 PostgreSQL，并仅在 LLM / Playwright 等外部边界使用可控 fake；mock 层明确声明其证据边界。
9. 发布以不可变版本为单位，状态目录不被代码同步删除；切换前有可验证备份，失败时确实启动上一版本，并重新验证页面、API、数据库和 stream 主路径。
10. 确定性 schema / artifact contract / renderer、真实模型 smoke 和 LLM judge 分层清楚；judge 记录场景、rubric、模型、维度分、问题与归因，能区分模型、prompt、runtime 和 renderer 问题。
11. 失败输出有 suite / workflow /用户路径 /风险 ID，关键门禁产生机器可读结果并保留首次失败；warning、open handle、React `act` 警告和环境漂移不再淹没根因。
12. 重复测试或资产只有在确认验证相同风险、失败模式和边界后才移除；命令矩阵、stage 矩阵、静态资产和发布物有单一 owner 或机械同步保护。
13. 聚焦反馈无需安装依赖，模块与跨层入口有预算，CI 有缓存、取消/互斥、超时和基于风险的条件执行；优化不能通过少跑关键风险换取速度。
14. 对所有共享 runtime workflow，左侧首个非占位的自然工作对话或明确可行动进度先于右侧首个可见产出物；双栏均单调流式更新，任一栏不会因另一栏的生成而长期饥饿。
15. 右侧产出物优先展示业务正文；低价值且重复工作区上下文的文档元信息不得以首屏大型表格占据正文空间，应在不丢失持久化与导出语义的前提下统一收口为尾部轻量附录或独立轻量元信息区。

## 范围与非目标

### 纳入范围

- 稳定文档与事实源：`AGENTS.md`、`docs/index.md`、`docs/TESTING.md`、Goal Mode Playbook、架构、API、数据、集成、开发和部署文档。
- 入口与门禁：根 `pytest.ini`、模块 pytest/Jest/Vitest 配置、package scripts、`scripts/test/**`、`scripts/validation/**`、`.github/workflows/deploy.yml`。
- 关键系统：`tools/frontend/`、`tools/intent-tester/`、`tools/new-agents/`、`tools/shared/`、`tests/`。
- 运行与发布边界：Docker Compose、Dockerfile、Nginx、数据库配置、部署与健康检查。
- 测试层级：单元、组件、契约、集成、浏览器 E2E、smoke、health、真实模型和 LLM judge。
- 质量属性：失败传播、数据隔离、幂等/并发、可恢复性、安全、flaky、环境等价、诊断、效率、冗余和文档可导航性。

### 非目标

- 不复制 Goal Mode 的设计、TDD、子智能体、提交、验证或归档流程。
- 不预先写死逐文件修改步骤；后续执行只引用 `AGENTS.md` 与 Goal Mode Playbook。
- 不在扫描阶段修复任何发现，也不添加 mock、fallback、skip 或兼容路径制造通过。
- 不创建新的 agent 专属 endpoint、store、SSE path、renderer 或 UI pipeline；New Agents 继续遵守共享运行时架构。
- 不把 Alex ready story 改成技术实现计划，也不在本 todo 定义尚不存在的 AI Coding 产品 workflow。
- 不把外部模型、生产环境或远端 CI 的不可用状态写成 `PASS`。
- 不恢复 `docs/todos/archive/**` 的历史任务，不吸收已有 P3 migration ownership。
- 不恢复、stage 或改写扫描开始前已有的 `.agent/**`、`.claude/**` 删除。

## 扫描基线与可信度

### Git 与工作区事实

| 项目 | 扫描事实 | 影响 |
|---|---|---|
| 分支 / HEAD | `master` / `b5a2db738495e6f3daccc6238ab3d2a1ced5d5b5` | 所有代码与配置结论基于该事实版本。 |
| Upstream | 本地 tracking ref 为 `origin/master`；`HEAD...@{upstream}` 为 ahead 10 / behind 0 | 10 个本地提交为 Goal Mode / todo 文档与合流记录，没有发现尚未合流的业务实现；不重复登记另一分支能力。远端实时状态仍未知。 |
| 未合流分支 | `git branch --no-merged HEAD` 无输出 | 没有发现会改变扫描结论的本地未合流实现。 |
| Staged | 扫描开始与完成前均为 0 | 未 stage 用户改动或本 todo。 |
| 既有 dirty diff | 84 个未暂存 tracked 删除，全部位于 `.agent/workflows/**` 与 `.claude/commands/**` | 视为用户已有改动；未读取其业务意图、未修改、未恢复，也未把它们纳入质量结论。 |
| 本轮事实组合 | `HEAD` + 当前工作树；质量判断排除上述 84 个无关删除 | 目标 todo 是本轮唯一新增的 tracked-scope 文件。 |
| 远端证据 | `gh auth status` 返回 token invalid | 最近 Actions、required checks、branch protection 和实时 remote HEAD 为 `BLOCKED`，不能声称远端绿色。 |

### 扫描边界事件

本轮发生了两项非预期副作用，均违反“只运行安全、不改变外部状态的诊断”边界；它们是扫描结论的一部分，不能被测试进程的 exit code 掩盖：

| 事件 | 实际命令与确认事实 | 未知 / 用户处置边界 |
|---|---|---|
| Intent 默认开发库 DDL | `cwd=<repo>; PYTHONPATH="$PWD:$PWD/tools/intent-tester" .venv/bin/python -m pytest -o addopts='' tools/intent-tester/tests -q`。进程报 294 passed；运行后 `tools/intent-tester/instance/local.db` 为 0 tables，mtime `2026-07-10T18:12:49+0800`，与测试运行吻合。fixture 因果由独立 memory/temp probe 确认。 | 没有 pre-run DB snapshot，因此只能确认 schema 已被清空，无法证明此前有多少用户行、能否恢复或全部损失范围。旧 sibling DB 仍有 8 tables，但不是经验证 backup；本轮未复制、恢复或清理。需要用户决定恢复策略，修复 fixture 前不得重跑该 suite。 |
| 外部 LLM judge 请求 | `cwd=<repo>; .venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q`。`llm_judge.py:40-60` 自动把 repo `.env` 注入进程，11 个 selected tests 中 3 个 optional judge 均发起真实请求；结果 10 pass / 1 fail，Alex artifact 77 < 80。 | 请求把 mock workflow 会话、阶段产物和最终产物发给 `.env` 配置的外部 endpoint；未记录任何 secret value。provider 侧保留策略、三次请求的实际费用与非本地副作用未知。本轮未重跑，也未再调用外部模型。 |

分支 ahead 10 不阻塞本 todo：ahead 区间只改变文档事实源，当前 HEAD 已包含所需 Playbook；没有代码能力只存在于另一未合流分支。真正需要用户处理的基线问题是 `QG-002` 的本地数据库副作用，见下文。

### 已读取的一手入口

| 类别 | 一手事实源 |
|---|---|
| 仓库规则与稳定文档 | `AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/TESTING.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/data-models.md`、`docs/integration-architecture.md`、`docs/deployment-guide.md`、`docs/development-guide.md` |
| CI / runner / 静态门禁 | `.github/workflows/deploy.yml`、`scripts/test/test-local.sh`、`scripts/test/check-docs.sh`、`scripts/test/check-architecture.sh`、`scripts/validation/new_agents_workflow_dry_run.py`、根与模块 pytest/Jest/Vitest 配置、三个 package scripts |
| 部署 / 健康 | `docker-compose.dev.yml`、`docker-compose.dev-cn.yml`、`docker-compose.prod.yml`、Intent secondary Compose、Dockerfiles、`nginx/nginx.conf`、`scripts/ci/deploy.sh`、`scripts/health/health_check.sh` |
| New Agents | manifest、workflow/stage/contract/renderer/prompt 映射、shared stream endpoint、`stream_services.py`、`run_persistence.py`、models、前端 `llm.ts` / `chatService.ts`、后端与前端测试、浏览器 E2E / judge |
| Intent / 其他模块 | testcase / execution / MidScene API、生产 Node 代理、Flask app 与 fixture、模板/静态 JS、proxy tests、Common Frontend、shared database/config、root tests |
| Todo 去重 | 当前非归档 todo、`docs/todos/refactor/README.md` 及其历史事实记录、相关 archive 和 `docs/plans/tech-debt.md`；archive 只用于边界核对 |

### 实际验证账本

状态按证据结果记录；命令退出 0 不自动等于本表的 `PASS`。下表中的 `<repo>` 为 `/Users/anhui/Documents/myProgram/AI4SE`；`cwd`、环境前缀、可执行文件和参数均按实际调用记录。

| 状态 | 实际命令 | 实际结果 | 证据边界 |
|---|---|---|---|
| `PASS` | `cwd=<repo>/tools/new-agents/backend; ../../../.venv/bin/python -m pytest -m 'not slow' -q` | 893 passed / 4 deselected，20.56s | Python 3.12.13；证明当前确定性后端 suite，不证明 PostgreSQL、并发或未覆盖的 persistence fault。 |
| `PASS` | `cwd=<repo>/tools/new-agents/frontend; npm run test` | 60 files / 870 tests passed，18.48s | 有 React `act(...)` warning；证明 jsdom / mock 边界，不证明真实服务组合。 |
| `PASS` | `cwd=<repo>/tools/frontend; npm run lint`；`cwd=<repo>/tools/new-agents/frontend; npm run lint` | 两者 exit 0 | New Agents `lint` 为 `tsc --noEmit`；Common 为 ESLint。 |
| `PASS` | `cwd=<repo>/tools/frontend; npm run build`；`cwd=<repo>/tools/new-agents/frontend; npm run build` | 两者 exit 0；New Agents 有 >500kB chunk warning，Common 有陈旧 Browserslist warning | 证明本机现有依赖下可构建；New Agents build 当前不在其 CI test job，也不含 typecheck。 |
| `PASS` | `cwd=<repo>; PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/validation/new_agents_workflow_dry_run.py` | 94 checks passed | 保护 manifest、stage、contract、renderer、handoff 与 packaging 同步；由 backend suite 间接执行。 |
| `UNSAFE / FAIL` | `cwd=<repo>; .venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q` | 1 failed / 10 passed / 10 deselected，139.34s；3 次外部 judge请求；Alex artifact 77 < 80 | 浏览器/Vite真实，HTTP/SSE为 mock；repo `.env` 自动启用 judge。失败包含缺非功能、验收、路线图章节及过早完成；费用/外部保留未知，未重跑。 |
| `UNSAFE / FAIL` | `cwd=<repo>; PYTHONPATH="$PWD:$PWD/tools/intent-tester" .venv/bin/python -m pytest -o addopts='' tools/intent-tester/tests -q` | 进程报告 294 passed / 1109 warnings，20.46s；随后默认 `tools/intent-tester/instance/local.db` 表为空，mtime 与运行吻合 | 不能登记为 `PASS`：fixture 对已绑定默认 DB `drop_all()`。无 pre-run snapshot；旧 sibling DB 未验证为 backup，未自动恢复。 |
| `PASS（仅测试进程）` | `cwd=<repo>/tools/intent-tester; npx jest tests/proxy --runInBand --reporters=default` | 2 suites / 17 tests passed，8.331s | 不证明 production proxy：一个 suite 手写 fake server，另一个把连接失败/超时判为通过。 |
| `FAIL` | `cwd=<repo>/tools/intent-tester; npx jest --testPathPattern=definitely-not-matching --passWithNoTests --runInBand --reporters=default` | exit 0 / `No tests found` | 动态确认零测试可被门禁报绿。 |
| `FAIL` | `cwd=<repo>; .venv/bin/python -m pytest -m api --collect-only -q` | 26 deselected / 0 collected，exit 5，并生成 0% coverage 噪声 | 文档化 marker 从根运行不等于 Intent API suite。 |
| `PASS` | `cwd=<repo>; PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts='' -p no:cacheprovider tests/test_ci_deploy_hardening.py -q` | 5 passed | 该文件未进入本地 runner / workflow，且不覆盖 release identity / rollback order。 |
| `FAIL` | `cwd=<repo>; bash scripts/test/check-docs.sh` | BSD grep 对 `-P` 报错，脚本仍 exit 0 并打印全部通过 | 工具失败被 `|| true` 吞掉。 |
| `FAIL` | `cwd=<repo>; bash scripts/test/check-architecture.sh` | exit 1；把允许的跨服务导航/API 引用及 `dist` 判为违规 | 脚本当前不可作为架构门，也未接入 runner / CI。 |
| `FAIL` | `cwd=<repo>; .venv/bin/python -m flake8 --select=E9,F63,F7,F82 .`；诊断对照：`.venv/bin/python -m flake8 --select=E9,F63,F7,F82 tools scripts tests` | 第一条扫描 `.venv` 第三方代码失败；限定范围 exit 0 | 稳定文档命令不可直接使用；CI 只扫 Intent backend。 |
| `NOT_RUN` | `cwd=<repo>; ./scripts/test/test-local.sh smoke` | 缺 shell `NEW_AGENTS_SMOKE_*` 时跳过，但 runner exit 0 并汇总“未发现失败” | 状态被误表达；没有发起真实 provider smoke。 |
| `PASS` | `cwd=<repo>; docker compose -f docker-compose.dev.yml config --quiet`；同命令分别使用 `docker-compose.dev-cn.yml`、`docker-compose.prod.yml`、`tools/intent-tester/docker/docker-compose.yml` | 四条均 exit 0；dev/dev-cn/secondary 有 obsolete `version` warning | 只证明 render，不证明 bind source、image build、container startup 或 schema。 |
| `PASS` | `cwd=<repo>; for f in scripts/test/test-local.sh scripts/test/check-docs.sh scripts/test/check-architecture.sh scripts/health/health_check.sh scripts/dev/deploy-dev.sh scripts/ci/deploy.sh; do bash -n "$f"; done` | 六个脚本 exit 0 | 只证明 shell 语法。 |
| `PASS（安全诊断）` | `cwd=<repo>; PYTHONPATH="$PWD:$PWD/tools/intent-tester" DATABASE_URL='sqlite:///:memory:' .venv/bin/python -c '<CMD-PROBE-01>'` | backend UUID `pending` + proxy ID `running`；prefixed callback 200 / default callback 404 | 仅 memory DB，无真实 proxy/browser/provider；完整 `-c` source 见下。 |
| `PASS（安全诊断）` | `cwd=<repo>; PYTHONPATH="$PWD:$PWD/tools/intent-tester" DATABASE_URL='sqlite:///:memory:' .venv/bin/python -c '<CMD-PROBE-02>'` | config 改为 file URI 后 engine 仍为 `sqlite:///:memory:`；8 tables | 无文件写入；证明 post-init config 不会重绑 engine。完整 `-c` source 见下。 |
| `PASS（安全诊断）` | `cwd=<repo>; PYTHONPATH="$PWD/tools/new-agents/backend:$PWD/tools/new-agents/backend/tests" PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q -k 'artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming or runtime_raw_json_stream_turn_streams_partial_artifact_data_in_final_format'`；另执行下述 `CHAT-ARTIFACT-ORDER-PROBE` | 26 passed / 194 deselected，1.12s；内存 probe 进一步得到 `artifact_before_chat=True; partial_chat=None; partial_artifact_chars=364`。 | 不调用模型、数据库或网络；证明当前 contract 会产生无 chat 的可渲染 artifact delta，不证明现场浏览器的精确延迟毫秒数。 |

`CMD-PROBE-01` 的实际 `-c` source：

```python
from backend.app import create_app; from backend.models import db,TestCase,ExecutionHistory; app=create_app(); ctx=app.app_context(); ctx.push(); tc=TestCase(name='probe',steps='[]',is_active=True); db.session.add(tc); db.session.commit(); c=app.test_client(); a=c.post('/intent-tester/api/executions',json={'testcase_id':tc.id}); backend_id=a.get_json()['data']['execution_id']; payload={'execution_id':'exec_proxy_generated','testcase_id':tc.id,'mode':'headless'}; prefixed=c.post('/intent-tester/api/midscene/execution-start',json=payload); default=c.post('/api/midscene/execution-start',json=payload); rows=[(x.execution_id,x.status) for x in ExecutionHistory.query.order_by(ExecutionHistory.id).all()]; print('backend_id='+backend_id); print('records='+repr(rows)); print('prefixed_status='+str(prefixed.status_code)); print('default_status='+str(default.status_code)); ctx.pop()
```

`CMD-PROBE-02` 的实际 `-c` source：

```python
from backend.app import create_app; from backend.models import db; app=create_app(); app.config['SQLALCHEMY_DATABASE_URI']='sqlite:///post_init_override.db'; ctx=app.app_context(); ctx.push(); print('configured_uri='+app.config['SQLALCHEMY_DATABASE_URI']); print('bound_engine='+str(db.engine.url)); print('tables='+str(len(db.metadata.tables))); ctx.pop()
```

`CHAT-ARTIFACT-ORDER-PROBE` 的实际环境为 `cwd=<repo>` 和 `PYTHONPATH="$PWD/tools/new-agents/backend:$PWD/tools/new-agents/backend/tests"`；以下是传给 `.venv/bin/python -c` 的完整 source：

```python
import json

from agent_runtime import build_partial_agent_delta, build_structured_output_instruction
from test_artifact_data_renderers import VALID_CLARIFY_ARTIFACT_DATA

instruction = build_structured_output_instruction("TEST_DESIGN", "CLARIFY")
artifact_index = instruction.index('{\n  "artifact_data"')
chat_index = instruction.index('\n  "chat"', artifact_index)
final_json = json.dumps(
    {
        "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
        "chat": "已完成需求澄清。",
        "stage_action": None,
        "warnings": [],
    },
    ensure_ascii=False,
    separators=(",", ":"),
)
partial = final_json[: final_json.index(',"business_rules"')]
delta = build_partial_agent_delta(
    partial, workflow_id="TEST_DESIGN", current_stage_id="CLARIFY"
)
assert delta is not None and delta.chat is None
assert delta.artifact_update is not None and delta.artifact_update.markdown
print(
    f"artifact_before_chat={artifact_index < chat_index}; "
    f"partial_chat={delta.chat!r}; "
    f"partial_artifact_chars={len(delta.artifact_update.markdown)}"
)
```

### 未运行、阻塞与环境边界

| 状态 | 验证 | 原因 / 缺少的证据 |
|---|---|---|
| `NOT_RUN` | `./scripts/test/test-local.sh all` | 会安装依赖，且包含已确认不安全的 Intent fixture、Playwright install 和可能被 `.env` 启用的外部 judge；本轮禁止安装和修复。 |
| `NOT_RUN` | 真实 New Agents provider smoke | runner 所需 `NEW_AGENTS_SMOKE_*` 未导出；不为补证额外调用付费外部模型。 |
| `BLOCKED` | 精确 Python 3.11 等价回归 | 本机只有项目 Python 3.12.13 与 system Python 3.14.2，CI 固定 3.11；未安装新 runtime。 |
| `NOT_RUN` | Docker build/up、真实 PostgreSQL、Nginx 组合 smoke | 会改变本机容器/端口/数据库状态；Compose 仅做了静态 render。 |
| `NOT_RUN` | 真实 Node proxy + Flask + 浏览器 + provider 执行 | 当前 suite 没有该安全组合入口；真实 provider / 浏览器执行会产生外部或本机状态。 |
| `NOT_RUN` | 生产发布、故障注入和回滚 | 破坏性外部操作；只完成顺序与 release identity 静态审计。 |
| `BLOCKED` | 远端 Actions / branch protection / required checks | `gh` 凭证无效，没有可信远端读取权限。 |
| `NOT_RUN` | 生产健康与数据库 schema / backup restore | 无生产访问授权，不能推断运行态、备份可用性或真实 schema。 |
| `NOT_RUN` | XSS 浏览器 payload 与未授权外部访问 | 利用链由存储、返回、`innerHTML` 和暴露路由静态确认；未对真实页面执行攻击。Intent 的期望访问模型仍缺产品声明。 |
| `NOT_RUN / UNKNOWN` | secret/privacy/dependency scanner 或 audit | 当前 runner / workflow 未发现对应入口；未安装或联网运行新的扫描器。GitHub deploy会校验一组 required secrets，但 direct Compose 仍允许默认值；依赖漏洞、许可证与隐私风险现状未知。 |
| `NOT_RUN` | 并发 persistence / deployment race、flaky 多轮统计 | 没有安全的故障注入或重复运行入口；当前只确认代码与 workflow 缺少对应保护。 |

## 质量保障现状矩阵

证据层级：L1 为静态合同/配置；L2 为单元、组件或 mock；L3 为真实进程/协议/数据库组合；L4 为真实外部 provider 或生产证据。强弱只描述当前证据，不是综合百分比。

| 关键风险面 | 当前保障 | 证据层级 | 强度 | 主要缺口 | 重复 / 成本 |
|---|---|---|---|---|---|
| New Agents manifest / stage / contract / renderer 漂移 | workflow dry-run、backend sync tests、frontend mappings、artifact renderer contracts | L1-L2 | 强 | Stable docs 仍有旧 workflow / data-model 表述；独立 CLI 不在顶层命令图 | 大型手写 stage 矩阵在代码、测试和文档重复 |
| New Agents typed output / deterministic rendering | `AgentTurnOutput`、artifact_data schema、backend deterministic renderers、前端 renderer/stream tests | L2 | 强 | 不证明 DB failure、真实 HTTP 断流和 PostgreSQL 行为 | renderer / contract suite 很大，但当前没有证据表明可安全删除 |
| New Agents 单轮生命周期 / 持久化 | endpoint success test、run snapshot、message/artifact/version/context/handoff tests | L2 | 部分 | 多次 commit 非原子；无 SQLAlchemy fault、duplicate request、sequence/version race；EOF 无终态仍被前端接受 | 正向 fake persistence 覆盖多，关键负向边界缺失 |
| New Agents 双栏流式进度 | `run_started` 占位、typed `agent_delta`、ChatPane / ArtifactPane 订阅、后端 partial artifact renderer | L1-L2 | 弱 / 失序 | artifact-data contract 强制 `artifact_data → chat`；可先发 `chat=None` 的 artifact delta，左侧只能保留占位，正式自然对话延后；无真实链路的首个有效内容顺序或 non-starvation 测试 | artifact-first 由参数化测试锁定；前端 mock 流主要只证明“delta 自带 chat”时的正确更新 |
| New Agents 浏览器主路径 | 真实 Vite + Chromium，mock API/SSE，覆盖 Lisa/Alex 部分 workflow / handoff | L2-L3 | 部分 | 不启动 Flask / PostgreSQL；不进 CI；mock 可与真实 endpoint 漂移 | 每个场景重复完整 workflow，语义成本高 |
| AI / LLM 语义质量 | schema / prompt / contract 确定性门、可选真实 smoke 和 judge、judge JSON schema | L2 / 可选 L4 | 部分且当前失败 | Alex judge 77；workflow 样本窄，证据未版本化归档，归因不足 | judge 会重复完整浏览器流程和外部调用，需分频率 |
| Intent testcase CRUD / database | 294 个 pytest 用例，API/transaction/error tests | L2 | 弱 / 不安全 | fixture 可删除默认或环境数据库；仅 SQLite；宽松 status 断言多 | 1109 warnings，完整 suite 的绿色不能安全复用 |
| Intent 执行 / proxy / callback / stop | API tests + 2 个 Jest files | L2 | 虚假保障 | 双 execution ID、callback prefix 404、生产 Node app 未被 import、失败被吞、全局 browser 状态 | fake server 和 vacuous integration 重复给出绿色但不增加真实证据 |
| Intent 安全 / 数据完整性 | “XSS attempt” API test、SQLAlchemy 参数化存储 | L2 | 弱 | raw 字段进入 `innerHTML`；写 API 无 auth/CSRF；无浏览器安全断言/CSP | 安全测试名称与真实断言不一致，维护价值低 |
| Common Frontend / Intent UI 行为 | Common lint/build；Intent server-rendered templates | L1-L2 | 弱 | Common 无 test script；Intent smart-variable test 不被 Jest 收集；关键导航/编辑/渲染无 owner | 两处相同 test 文件，目标 source 已漂移 |
| Shared config / PostgreSQL / schema | shared env config、Compose postgres health、`create_all()` | L1 | 弱 | 无真实 PostgreSQL contract / migration upgrade / startup order 证据；test config 绑定错误 | migration 机制已有独立 P3 ownership，不能重复建项 |
| 本地入口 / CI 等价 | `test-local.sh`、workflow 5 个前置 jobs、文档命令 | L1-L3 | 弱 | Python / selection / coverage / build / E2E 范围不同；部分状态 false green | 命令矩阵在文档、shell、workflow、package scripts 多处复制 |
| 静态门禁 | frontend lint/build、critical flake8、docs/architecture scripts、workflow dry-run；deploy required-secret preflight | L1-L2 | 部分；安全/隐私/依赖为未知 | Python scope 狭窄；docs gate fail-open；architecture gate false-red；root hardening未接入；direct Compose允许默认 secret；未发现 secret/privacy/dependency audit入口，也未外加扫描器 | 每个入口各自维护路径规则，易漂移；未知项不能被现有 lint/build 宣称覆盖 |
| 发布 / 回滚 / readiness | Compose health、deploy health script、root hardening tests | L1-L2 | 弱 / 虚假保障 | live 先覆盖后备份、回滚不恢复旧镜像、状态目录可能删除、健康未证明 UI/DB/stream | 每次 master push 全量重建部署；并发 run 无互斥 |
| 可诊断性 / flaky / 资源隔离 | 部分 timeout、JUnit reporter、错误 diagnostic、Playwright 动态端口 | L1-L2 | 部分 | JUnit 大多不上传；warning/open handles 被压制或 forceExit；无 suite 风险映射和多轮 flaky 证据 | 日志噪声高，CI 反复安装/构建，首次失败不易定位 |

## 完整发现清单

每个 P0/P1 只绑定一个 owning 厚切片。P2 若进入切片也只登记一个 owner；P3 在延后登记中有明确 owner 与激活条件。

| ID | 类型 / 优先级 / 置信度 | 风险与失败模式 | 当前保障及不足 | 证据 | 目标状态 | Owning 厚切片 |
|---|---|---|---|---|---|---|
| `QG-001` | 虚假保障 / 门禁失真；**P0**；高 | AI Coding Agent 可在 smoke 未运行、Jest 零收集或 docs 工具自身失败时得到 exit 0，继续交付未经验证的变更。受影响边界是所有本地/CI verdict。 | runner 有 `set -e` 和汇总，但 smoke 显式 `return 0`，proxy 带 `--passWithNoTests`，docs 检查吞掉 grep 错误；没有机器可读非 PASS 状态或最小收集数。 | `scripts/test/test-local.sh:247-279,369-380`；`.github/workflows/deploy.yml:155-159`；`scripts/test/check-docs.sh:21-72`；动态结果：smoke skip exit 0、zero Jest exit 0、docs grep error exit 0。 | 每个 gate 声明 suite ID、状态、收集/执行/skip 数和原因；零收集、工具错误、缺 required env、超时和未收到终态均非 PASS，父 runner 原样传播。 | `QS-01` |
| `QG-002` | 虚假保障 / 数据完整性；**P0**；高 | Intent pytest 在应用已绑定默认或 `DATABASE_URL` 后才把 config 改为 memory，teardown 对真实 engine `drop_all()`；AI 高频回归可删除开发或更高环境数据。本次默认本地库很可能已被该运行清空。 | 文档声称全部使用 memory SQLite，fixture 也设置该字符串；但设置发生在 `db.init_app()` / `create_all()` 后，没有 engine 身份断言或外部 DB fail-closed。 | `tools/intent-tester/backend/app.py:25-39`；`tools/intent-tester/tests/conftest.py:29-43`；`tools/shared/database/__init__.py:3-9`；`docs/TESTING.md:29-33`。`CMD-PROBE-02` 证明 post-init config 不重绑 engine；扫描后 `tools/intent-tester/instance/local.db` 0 tables，mtime `2026-07-10T18:12:49+0800`。旧 sibling DB 仍有 8 tables，但不是经验证 backup。 | test config 在初始化前生效；只接受可证明的临时 test DB，非测试 URI 立即拒绝；fixture 用 transaction/savepoint 或隔离库清理，并用 sentinel 证明不会改变外部 DB。 | `QS-01` |
| `QG-003` | 覆盖缺口 / 共享运行时契约；**P0**；高 | New Agents 一轮在 user message、assistant message、artifact version 和 metric 间分别 commit；中途 DB 失败可留下不完整 durable history并在 HTTP 200 后断流。前端把 EOF 当正常结束，可能保留“正在生成”或把 partial artifact 记为正常版本；重复/并发请求可争用 `max+1` sequence/version。 | typed SSE、schema/visual error、abort、成功 persistence 和 artifact rollback 测试较强；但没有 SQLAlchemy fault、正常 partial 后 EOF、request idempotency、并发 sequence/version 竞争证据。 | `tools/new-agents/backend/run_persistence.py:115-142,248-300`；`tools/new-agents/backend/stream_services.py:395-465,466-610`；`tools/new-agents/backend/models.py:108-185`；`tools/new-agents/frontend/src/core/llm.ts:998-1143`；`tools/new-agents/frontend/src/services/chatService.ts:491-681`；`tools/new-agents/backend/tests/test_stream_services.py:231-357`。 | 一轮有明确 transaction / outcome boundary、request identity 和幂等语义；所有 DB fault 产生 sanitized typed error 或可恢复状态；客户端只在合法 `agent_turn` + protocol terminal 后完成并持久化版本。 | `QS-02` |
| `QG-004` | 虚假保障 / 跨服务契约漂移；**P0**；高 | Intent UI 先创建 backend UUID，却不传给 proxy；proxy 再生成 ID，默认 callback 又指向不存在的 `/api`。结果是原记录永久 pending、第二记录 running/缺失、UI 与 durable history 分裂；stop/retry/restart 不能可靠恢复。 | API tests 验证已匹配 ID；Jest 报告 17 passed。但一个 suite 自建 fake server，另一个在连接失败/超时使用 15 处 no-op true；生产 `midscene_server.js` 未被组合执行，callback 失败只记日志。发布包启动脚本还引用缺失 `.env.example`。 | `tools/intent-tester/backend/api/executions.py:33-80`；`tools/intent-tester/frontend/templates/execution.html:822-888`；`tools/intent-tester/browser-automation/midscene_server.js:81-84,139-142,203-284,1593-1644`；`tools/intent-tester/backend/api/__init__.py:16-25`；`tools/intent-tester/backend/api/midscene.py:54-60,181-219`；`tools/intent-tester/tests/api/test_midscene_api.py:256-275`；`tools/intent-tester/tests/proxy/midscene-integration.test.js:15-136`；`tools/intent-tester/tests/proxy/midscene-server-api.test.js:94-195`；`tools/intent-tester/tests/proxy/setup.js:65-77`；`tools/intent-tester/proxy_templates/start.sh:161-170`；`CMD-PROBE-01`。 | 前端、Flask、proxy、WebSocket 和 DB 使用一个 canonical execution ID；生产 Node app 可被测试导入；callback/stop/retry 幂等且失败可见；真实 HTTP 组合只 fake AI/Playwright 外部 adapter，代理包有可启动 smoke。 | `QS-03` |
| `QG-005` | 安全 / 虚假保障；**P0**；高 | 生产暴露 Intent 写 API；未认证 create/update/delete 可持久化 name/description/category，列表页直接插入 `innerHTML`，`img onerror` / `svg onload` 可形成 stored XSS。访问模型未定义使爆炸半径未知；直接 Compose 还允许默认 DB/Flask secrets。 | SQLAlchemy 防 SQL 注入；GitHub deploy 会 `require_secret`。但 XSS test 只断言非空，未经过 DOM；没有 auth/CSRF/Origin contract 或 CSP，直接 `docker compose` 配置不是 fail-closed。 | `docker-compose.prod.yml:12-13,32-45,92,109-125`；`.github/workflows/deploy.yml:303-335`；`nginx/nginx.conf:69-83`；`backend/api/testcases.py:157-214,236-308`；`backend/models/models.py:39-48`；`frontend/templates/testcases.html:227-235,267-308`；`tests/api/test_error_scenarios.py:345-381`。 | 明确公开/受限访问策略；写路径具备身份与来源保护；所有生产入口拒绝默认 secrets；持久化用户字段按上下文安全渲染并有 CSP；真实浏览器 payload 回归证明代码不执行。 | `QS-04` |
| `QG-006` | 虚假保障 / 发布可恢复性；**P0**；高 | CI `rsync --delete` 先覆盖 live 且可删除 `.env`、日志、截图，再由 deploy script 备份新版本；“回滚”不选择上一镜像。健康检查可在 New Agents frontend、真实 DB 或 stream 失败时成功，生产发布可能假成功；失败发布也可能无法恢复。并发 master runs 还可争抢同一服务器。 | 五个 CI jobs、Compose health、health script 和 5 个 hardening tests存在；但备份/回滚 identity 未测，Nginx `/health` 固定 200，Intent / New Agents health 静态，生产跳过容器检查，页面漏 `/new-agents/`，Docker health 不检查 HTTP error。 | `.github/workflows/deploy.yml:3-8,164-171,267-296,438-445`；`scripts/ci/deploy.sh:94-148,170-220`；`scripts/health/health_check.sh:73-113,118-157,163-231,279-307`；`docker-compose.prod.yml:55-60,69-124`；`nginx/nginx.conf:120-125`；`tests/test_ci_deploy_hardening.py:10-58`。 | 不可变 release/image、状态与代码隔离、切换前可验证备份、原子切换和上一版本恢复；同环境部署互斥；readiness 验证所有容器/页面、DB 读写、关键 API/stream，回滚后重新验证 release identity。 | `QS-05` |
| `QG-007` | 门禁失真 / 环境漂移；**P1**；高 | 文档、root pytest、module configs、本地 runner 和 CI 对 `api` / `all` / New Agents 的含义不同；Agent 可能选择错误 suite。Python 3.12/3.14 本地与 CI 3.11、coverage threshold、slow、lint/build/E2E 范围也不等价。 | 各模块命令可单独运行；runner 自称模拟 Actions。但 root `pytest` 只收集 root tests，本地 Intent 没 CI coverage threshold，本地 New Agents 不跑 lint/build，CI 不跑 browser E2E / New Agents build，官方 flake8 命令不可用。 | `pytest.ini:4-37`；`tools/intent-tester/pytest.ini:1-7`；`scripts/test/test-local.sh:4-15,60-88,157-242,281-360`；`.github/workflows/deploy.yml:14-166`；动态 `pytest -m api` 为 0 / exit 5；版本为 3.12.13 / 3.14.2 vs CI 3.11。 | 一份机械命令图定义 focus/module/cross/full/external 层级、环境、选择器、预期收集与 CI 映射；本地等价差异必须显式且可测试。 | `QS-07` |
| `QG-008` | 覆盖缺口 / mock 边界；**P1**；高 | 真实部署由 Common UI、Intent Flask/Node proxy、New Agents UI/backend、Nginx 和 PostgreSQL 组成，但没有一条自动化在真实组合上验证路由、schema、启动顺序、SSE 和持久化；单模块绿色可在集成时逃逸。 | Compose 可 render，New Agents browser 用真实 Chromium，模块 tests 很多；但 DB 主要 SQLite，browser 拦截所有 API，proxy tests 不运行 production app，health 是浅探测。 | `tests/e2e/new_agents_browser/conftest.py:65-120` 及 route mocks；`docker-compose.prod.yml:4-141`；`scripts/health/health_check.sh:118-273`；`tools/intent-tester/backend/app.py:25-39`；当前无 PostgreSQL / Nginx / full HTTP composition job。 | 建立可重复的 production-shaped cross-service smoke：真实构建/进程/路由/PostgreSQL，只 fake 外部模型和浏览器自动化 adapter；证明启动、读写、stream、callback、重启恢复和失败暴露。 | `QS-05` |
| `QG-009` | 覆盖缺口 / 无 ownership 测试；**P1**；高 | Common portal 导航/Profile 和 Intent 编辑/静态组件可在 lint/build 通过时行为回归；两个 `smart-variable-input.test.js` 不属于任何 Jest match，AI Agent 无法选择它们。 | Common 有 ESLint + TypeScript build；Intent 有 server API tests。Common 无 test script，Intent Jest 只匹配 `tests/proxy/**`。 | `tools/frontend/package.json:6-10`；`tools/intent-tester/jest.config.js:9-13`；`tools/intent-tester/frontend/static/js/smart-variable-input.test.js:1` 与 `tools/frontend/public/static/js/smart-variable-input.test.js:1` hash 相同且无 runner 引用；对应 source hash 已不同。 | 为关键 portal / Intent UI 行为建立明确 owner、可执行 component/browser 入口和最小场景；未执行测试必须被收集审计发现。 | `QS-07` |
| `QG-010` | AI 语义质量 / 可诊断性；**P0**；高 | 当前事实源启用了 80 分 judge 门，Alex browser judge 77 < 80，按 Playbook 是当前 P0 改道；确定性 contract 全绿不能替代专业完整性。judge 只覆盖 TEST_DESIGN、VALUE_DISCOVERY / handoff；STORY_BREAKDOWN、REQ_REVIEW、INCIDENT_REVIEW、IDEA_BRAINSTORM、PRD_REVIEW 没有语义质量样本。 | judge 有结构化 JSON、维度分、可视化最低分和 timeout；真实 smoke 可选。证据依赖 repo `.env`、固定 mock artifact 和单次模型评分，没有版本化 baseline / 重跑策略 / model/prompt/runtime/renderer 归因。 | `docs/strategy/goal-mode-playbook.md:276-289`；`tools/new-agents/workflow_manifest.json:117,384,547,776,1037,1318,1624`；`tests/e2e/new_agents_browser/llm_judge.py:40-60,67-100,234-377`；`test_lisa_test_design_workflow.py`、`test_alex_value_discovery_workflow.py`、`test_alex_user_story_breakdown_workflow.py`；实际 77 分，差距为缺少非功能、验收、路线图章节与过早完成。model identity与完整 dimension scores未在首次失败日志中保留，当前为未知。 | 先收口当前低于门线的失败维度、期望/实际差距、修复位置、重跑方式与结果/阻塞；再建立按 workflow 风险分层的语义样本、版本化元数据和问题归因。 | `QS-06` |
| `QG-011` | 静态门禁 / 契约与文档漂移；**P1**；高 | manifest 之外的 Python、docs、architecture、data model、Compose source、安全/隐私/secret 和依赖一致性没有可信统一门禁；Agent 可依赖过时文档或忽略未执行脚本。 | New Agents workflow dry-run 很强，前端 lint/build、CI critical flake8和 deploy `require_secret` 存在；但 docs gate fail-open、architecture gate false-red、flake8 只覆盖 Intent backend，root hardening未接入，未发现 CI/runner secret scan、dependency audit 或 privacy gate。 | `scripts/test/check-docs.sh:21-69` / `scripts/test/check-architecture.sh:23-62` 动态结果；`.github/workflows/deploy.yml:103-123,303-335`；`.coveragerc:3-18,83-88`；`docs/integration-architecture.md:89-96`；`docs/data-models.md:186-195`；`docs/development-guide.md:276-288`；workflow dry-run 94 pass。 | portable、fail-closed、与允许架构边界一致的静态 gate 覆盖 owning Python、manifest/schema/config/docs/Compose source，并明确 secret/privacy/dependency gate 的范围或 NOT_RUN 边界；稳定文档由权威配置派生或有 drift test。 | `QS-08` |
| `QG-012` | 可诊断性 / 可靠性；**P2**；高 | 失败日志难映射风险：Intent 一次运行 1109 warnings，New Agents frontend 有 React `act` warnings；Jest 配置 JUnit 但 CI 不上传，pytest/Vitest 无统一 machine result；`forceExit` / suppressed unhandled errors 可隐藏资源泄漏。 | 后端 typed diagnostics 和部分 timeout 已有；coverage.xml 仅 Intent 上传。 | Intent pytest 实际 warning 数；`tools/intent-tester/tests/proxy/setup.js:65-90`；`tools/intent-tester/jest.config.js:68-93`；`.github/workflows/deploy.yml:41-45,155-159`；Vitest output。 | 每个 gate 产出统一 machine summary、JUnit/诊断附件和风险映射；warning / open handle 有 budget 与 owner，首次失败保留，超时指出阶段和资源。 | `QS-07` |
| `QG-013` | 冗余 / 契约漂移；**P2**；高 | 同一个 unowned `smart-variable-input` 测试被复制到两个静态资产树，两个 test 完全相同而对应 production source 已漂移；Agent 修改任一 source 都得不到测试反馈。 | 两份测试都不被当前 Jest match 收集，因此重复没有提供纵深证据；其他相似静态资产尚未证明消费者、失败模式和边界相同，本发现不建议删除它们。 | `tools/intent-tester/frontend/static/js/smart-variable-input.test.js:1` 与 `tools/frontend/public/static/js/smart-variable-input.test.js:1` SHA1 均 `e2cd...`；对应 `smart-variable-input.js:1` SHA1 为 `9848...` vs `4a3c...`；`tools/intent-tester/jest.config.js:9-13`。 | 先建立唯一 test/source owner和真实 runner；仅在证明相同消费者、风险与失败边界后合并副本，必要纵深防御保留。 | `QS-08` |
| `QG-014` | 效率 / 反馈循环；**P2**；高 | 高频 AI Coding 入口会重复安装依赖、Playwright browser、全量构建；CI 无 dependency cache、path risk selection、job timeout或旧 run cancellation，docs-only master push也会全量测试并部署，反馈慢且可并发争用生产。 | 模块命令可单跑，New Agents backend/frontend本机各约 20s；CI jobs 已并行。 | `scripts/test/test-local.sh:71-74,139-145,164-169,189-204,221-236,296-316`；`.github/workflows/deploy.yml:3-8,14-190` 无 `concurrency` / `timeout-minutes` / cache；当前 workflow 对 master push部署。 | 无安装的 focused/module入口，基于风险的 path selection，缓存、超时、取消/互斥、可量化预算；任何 skip 都保留理由且不能漏关键跨层风险。 | `QS-07` |
| `QG-015` | 文档 / 治理成本；**P2**；高 | 已终结的超长 todo 仍在 active navigation，AI Agent 可能把历史候选重新当作未完成工作，重复扫描或重复建项。 | Playbook 已定义 todo lifecycle，archive 记录完整；但 `2026-07-08-new-agents-structured-artifact-failure-reduction.md` 自称 P0/P1 收口且无 unchecked item，仍有 3512 行留在 active。稳定文档/矩阵 drift 只由 `QG-011` owning，不在此重复计数。 | `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md:1-17,3456-3491`；当前文件 3512 行且无 unchecked checkbox。 | 终态 todo 从活跃导航面收口，并保留可追溯 archive / successor；active 只承载真实未完成 ownership。 | `QS-08` |
| `QG-016` | 覆盖缺口（未知 / 待验证）/ dormant 契约；**P3**；中 | 两个 Intent legacy release surface 缺 consumer/owner 证据：secondary Compose 引用缺失 source，conditional Langfuse migration 调用缺失脚本；被重新触发时可能失败，立即修复也可能维护死路径。 | 主 Compose 可 render，当前稳定文档只引导根 Compose；没有找到这两个 legacy surface 的当前执行者。New Agents startup ALTER TABLE P3 是不同 ownership，明确排除。 | `tools/intent-tester/docker/docker-compose.yml:27-74`；`.github/workflows/deploy.yml:398-419`；缺失 `scripts/migrate_langfuse_to_local.sh`；`docs/todos/refactor/README.md:21-33` 仅描述 New Agents migration。 | `DB/LEGACY-P3` 先分别确认 secondary Compose 与 Langfuse branch 的消费者；活跃者进入对应 release/schema contract并有 smoke，无消费者者明确退役。 | 延后登记 `DB/LEGACY-P3`，不进入当前切片 |
| `QG-017` | 覆盖缺口 / 共享运行时流式编排；**P1**；高 | 用户已复现：右侧产出物按段落持续更新，左侧自然对话直到右侧接近或完成后才出现。artifact-data 阶段机械要求 `artifact_data` 先于 `chat`；partial parser 因而可先发出 `chat=None`、但含可渲染 artifact 的 `agent_delta`。前端保留“正在生成...”占位并立即应用右侧更新；`chat` 字段只有在 `artifact_data` 之后才可提取。若模型把 `chat` 放在完整数据之后，左侧自然对话会显著滞后，`agent_turn` 仅负责最终收敛。用户无法从左侧获得同步的判断、假设和下一步，容易误以为对话卡死。 | `run_started` 与 typed delta 已存在；`chatService` 对同一已收到 chunk 会先写 chat 再写 artifact，故没有证据表明根因是 React 提交顺序。但现有 backend test 明确锁定 artifact-first，前端 test 主要覆盖 delta 自带 chat 时的渐进更新；浏览器 E2E mock 不发送真实的 delayed `agent_delta` 序列。 | `tools/new-agents/backend/agent_runtime.py:146-202,394-451,618-639,779-800`；`tools/new-agents/backend/tests/test_agent_runtime.py:86-96,4708-4735`；`tools/new-agents/backend/stream_services.py:414-465`；`tools/new-agents/frontend/src/core/llm.ts:902-951,1013-1067`；`tools/new-agents/frontend/src/services/chatService.ts:496-606`；`tools/new-agents/frontend/src/core/__tests__/llm.test.ts:532-612,796-856`；本轮安全诊断输出 `artifact_before_chat=True; partial_chat=None; partial_artifact_chars=364`。 | 共享协议明确双栏可见进度不变量：首个非占位 chat 或明确可行动进度先于首个可渲染 artifact；chat 与 artifact 各自单调更新、互不饥饿；任一 workflow 不得用延迟右侧来伪造顺序。对 artifact-data-first、慢 token、断流和最终收敛建立共享后端→SSE→store→DOM 证据。 | `QS-02` |
| `QG-018` | 覆盖缺口 / 全工作流 artifact 分段流式一致性；**P1**；高 | 用户观察到不同 workflow、甚至同一 workflow 的不同 stage，右侧产出物增量渲染行为不一致。`TEST_DESIGN/CLARIFY` 能随已完成的顶层结构按段落/章节逐步更新，但其他阶段可能等完整 `artifact_data` 可校验后才整体出现或表现出不同粒度。 | 全量静态盘点确认 manifest 共有 7 个 workflow / 25 个在线 stage，25 个阶段都有完整 `artifactDataContract` 与 final renderer；但 `render_partial_artifact_data_markdown()` 只对 `TEST_DESIGN/CLARIFY` 分派 partial renderer，其余 24 个阶段明确返回 `None`。现有 partial streaming 回归也只锁定 CLARIFY，没有机械覆盖所有 manifest stage 的增量渲染矩阵。 | `tools/new-agents/workflow_manifest.json`；`tools/new-agents/backend/artifact_data_renderers.py:2320-2419`；`tools/new-agents/backend/agent_runtime.py:621-795`；`tools/new-agents/backend/tests/test_agent_runtime.py:4760`；盘点结果：`TEST_DESIGN/CLARIFY` 1 个基准阶段有 partial renderer，其余 24/25 阶段无 partial renderer。 | 以 `TEST_DESIGN/CLARIFY` 的用户可见行为为基准：所有 stage 在已收到完整、可校验、可确定渲染的章节/结构块时立即更新右侧，并单调收敛为与 final deterministic renderer 一致的完整 Markdown。视觉块、表格或引用未完整时不伪造成功；不允许工作流/阶段专属 runtime、SSE、store 或渲染管线。用 manifest 全阶段矩阵门禁、后端 partial/final 收敛测试和每个 workflow 至少一条真实 DOM 流式证据验收。 | 未启动 backlog；恢复时回到 `ASSESS` 形成新同级厚切片 |
| `QG-019` | UX / 产出物信息层级与空间效率；**P2**；高 | 用户观察到右侧产出物首段经常是“文档信息”，并以大型两列表格占据有限首屏；Artifact 名称、Workflow、Stage、状态等内容多与当前工作区上下文重复，正文价值低，却会成为用户最先看到、流式阶段最先占空间的区块。 | 共享结构化契约中的 `document_info` 应继续保留，但展示层级不统一：`TEST_DESIGN/CLARIFY`、`TEST_DESIGN/DELIVERY`、`VALUE_DISCOVERY/BLUEPRINT` 与四个 `PRD_REVIEW` 阶段的 deterministic renderer 都把元信息表放在标题之后；CLARIFY partial renderer 还会把它作为首个有效增量。与此同时，对应的 CLARIFY、DELIVERY、BLUEPRINT 前端模板已把文档信息写成尾部“附录”，形成 prompt/template 与 renderer 顺序漂移；其他 workflow 还使用 `review_info`、报告概要等相邻概念，需全阶段区分业务摘要与纯元信息。 | `tools/new-agents/backend/artifact_data_renderers.py:2304-2419,2580-2594,2683-2703,2705-2759,2997-3004,4812-4828,5469-5476`；`tools/new-agents/frontend/src/core/prompts/test_design/clarify.ts:91`；`tools/new-agents/frontend/src/core/prompts/test_design/delivery.ts:118`；`tools/new-agents/frontend/src/core/prompts/value_discovery/blueprint.ts:160`；`tools/new-agents/frontend/src/components/ArtifactMarkdownPreview.tsx:40-95`。 | 所有 workflow/stage 先展示可行动的业务正文，纯文档元信息不得再以首段重表格出现。恢复时先用全阶段矩阵划分“纯元信息”与“业务摘要”，再在两种共享方案中定案：默认候选为文末紧凑附录；若独立元信息区能在窄屏、滚动、导出和流式状态下保持轻量且不遮挡正文，也可采用右下角/折叠区。无论方案如何，结构化 `document_info`、持久化与导出语义必须保留，QG-018 的首个右侧增量不得被低价值元信息占据。 | 未启动 backlog；恢复时回到 `ASSESS`，与 `QG-018` 协同但独立验收 |

## 厚切片序列

执行顺序：`QS-01 → QS-02 → QS-03 → QS-04 → QS-05 → QS-06 → QS-07 → QS-08`。前六个切片先收口 P0，再进入 P1/P2 反馈与治理优化。

### QS-01 — 诚实且不伤数据的验证结果

- **解决的风险**：AI Agent 不能信任退出码，且运行测试本身可能删除数据。
- **能力增量**：完成后，每个 gate 都能给出机器可读的真实状态，所有数据库测试都在可证明的隔离环境中运行；“执行验证”不再是一项数据风险。
- **承接发现**：`QG-001`、`QG-002`。
- **目标态**：零收集、缺 required env、工具错误、timeout、skip-only 和子命令失败均非 PASS；Intent test app 在 DB 初始化前接收 test config，并对非 test URI fail-closed。
- **纳入范围**：runner outcome contract、pytest/Jest 收集门禁、smoke 状态、子工具失败传播、Intent app factory / fixture / database sentinel。
- **排除范围**：不修 Intent 业务执行链、不定义 LLM judge 策略、不恢复本地数据库。
- **架构边界**：shell / package runner → test framework → app factory → database engine → result summary。
- **可观察验收证据**：故障矩阵证明 zero/skip/tool-error/timeout 分别得到正确状态；临时/非测试 DB probe 证明外部 sentinel 与 schema 不变；重复运行结果一致；本地默认 DB 不被打开或清理。
- **依赖 / 阻塞**：无；这是所有后续切片可信执行的前置。用户需先决定是否恢复扫描中受影响的默认本地库，但恢复不属于本切片扫描记录。
- **与其他切片边界**：`check-docs.sh` 的 portability / path 规则由 `QS-08` owning；本切片只用模拟 child-tool failure 证明父级 outcome 传播。`QS-07` 组织“跑哪些测试”。
- **记录要求**：完成时记录 outcome schema、隔离证据和受影响库的用户处置结论；取消时记录依据、残余风险和 backlog owner；替换或迁移时记录 successor、移交的 `QG-*` 与证据位置。

### QS-02 — Shared Agent Runtime 单轮原子性、流式编排与终态协议

- **解决的风险**：共享 runtime 在 DB fault、断流、重复或并发请求下留下半成功 durable state，前端把 partial/EOF 当成功；或右侧 artifact 持续可见而左侧自然对话长期只剩占位，用户无法判断 Agent 是否卡住。
- **能力增量**：完成后，每个 workflow 的一轮请求都具有统一 request identity、原子持久化结果、双栏非饥饿的流式可见进度和必需协议终态；失败可诊断、可重试且不会重复消息/版本。
- **承接发现**：`QG-003`、`QG-017`。
- **目标态**：run/user/assistant/artifact/version/metric 的一致性不变量明确；左侧首个非占位 chat 或明确可行动进度先于右侧首个可渲染 artifact，双方单调更新；所有 persistence phase fault、合法/非法 EOF、disconnect、cancel、retry、duplicate 和 sequence/version race 有共享后端/前端证据。
- **纳入范围**：共享 `/api/agent/runs/stream`、partial JSON 字段顺序与 `agent_delta` 编排、typed SSE terminal contract、persistence transaction/idempotency、frontend parser/state/version completion、双栏可见进度与 sanitized diagnostics。
- **排除范围**：不创建 workflow/agent 专属 runtime 分支；不处理 judge 专业质量；不实现生产 deployment。
- **架构边界**：HTTP request → shared runtime → provider adapter → DB → typed SSE → frontend reducer/store/version history。
- **可观察验收证据**：每个 persistence 注入点的 fault test；premature EOF 不完成也不保存正常版本；artifact-data-first、慢 token、无 chat delta、断流和最终收敛的后端→SSE→store→DOM 测试证明左侧首个非占位 chat 或明确可行动进度先于右侧首个可见 artifact，双方单调更新；重复 request 只有一组 durable records；并发版本冲突显式；所有当前 workflow 仍通过同一 endpoint / event types。
- **依赖 / 阻塞**：依赖 `QS-01` 提供可信、安全的测试结果；阻塞 `QS-05` 的真实 shared stream readiness和 `QS-06` 的完整 trace。
- **与其他切片边界**：`QS-06` 判断产物是否“好”，本切片只判断一轮是否“完整且一致”。
- **记录要求**：完成时记录不变量、fault matrix、双栏时序证据、协议兼容性和跨 workflow 共享证据；取消时记录依据、残余 shared-runtime 风险和 backlog owner；替换或迁移时记录 successor、移交的 `QG-003/QG-017` 与证据位置。

### QS-03 — Intent Tester 真实执行与持久化闭环

- **解决的风险**：用户看到代理执行，但服务端历史永久 pending、重复或缺失，stop/retry/restart 不能恢复同一任务。
- **能力增量**：完成后，Intent 从创建、代理执行、回调、停止、重试到恢复使用一个 durable identity，生产 Node app 与 Flask contract 有真实组合证据。
- **承接发现**：`QG-004`。
- **目标态**：真实 Flask 与可导入的 production Node app形成可控组合；callback prefix/schema/idempotency/scoped stop受契约保护；代理失败进入显式 durable 终态。
- **纳入范围**：execution ID、callbacks、WebSocket/status、scoped stop/recovery、production proxy app和下载 package smoke。
- **排除范围**：不要求真实付费 AI provider；不处理认证/XSS/CSP；不重写 New Agents runtime。
- **架构边界**：Intent page → Flask API/DB → localhost Node proxy → fake Playwright/AI adapter → callback/WebSocket → page/history。
- **可观察验收证据**：real HTTP test只产生一个 execution record并完成同一 ID；callback失败/重试/重复不造新步骤；restart/stop状态可解释；production package在 clean-room 配置下启动。
- **依赖 / 阻塞**：依赖 `QS-01`；其 durable path 是 `QS-05` cross-service smoke 的前置。
- **与其他切片边界**：`QS-04` 独立处理 Intent access/browser security；`QS-05` 验证部署组合，不在此定义 release transaction。
- **记录要求**：完成时记录 canonical identity、fake/real 边界和 recovery evidence；取消时记录依据、残余 pending/duplication 风险和 backlog owner；替换或迁移时记录 successor、移交的 `QG-004` 与证据位置。

### QS-04 — Intent Tester 访问与浏览器安全边界

- **解决的风险**：未授权写入和不安全 DOM 渲染可形成 stored XSS，默认生产 secrets 又可让直接 Compose 以不安全配置启动。
- **能力增量**：完成后，Intent 有明确访问模型、fail-closed 的生产配置和真实浏览器安全证据，持久化用户内容不能执行代码。
- **承接发现**：`QG-005`。
- **目标态**：身份、Origin/CSRF/CORS、proxy loopback/token、output encoding、CSP 和 production secret 要求彼此一致；公开与受限部署分别有可执行 contract。
- **纳入范围**：testcase mutation/read/render、gateway/API访问策略、local proxy source boundary、CSP、默认 secrets 和浏览器 exploit regression。
- **排除范围**：不修 execution ID/callback；不定义组织级身份平台；不把安全 scanner 是否接入的治理归到本切片。
- **架构边界**：外部 browser/origin → Nginx → Flask write API/DB → server-rendered page/DOM；网页 → localhost proxy；Compose / secret source。
- **可观察验收证据**：未授权或错误来源写入按声明策略失败；合法内容功能不回归；存储 payload 在真实浏览器不执行；缺 required secret 的所有生产入口 fail-closed；CSP/headers可观测。
- **依赖 / 阻塞**：依赖 `QS-01` 的安全测试环境；访问模型未裁决时该切片不能完成。
- **与其他切片边界**：`QS-03` owning execution identity，`QS-08` owning secret/privacy/dependency 静态扫描策略；本切片 owning 运行时 exploit chain和直接生产配置。
- **记录要求**：完成时记录访问模型、exploit regression和 secret preflight；取消时记录依据、暴露面、残余安全风险和 backlog owner；替换或迁移时记录 successor、移交的 `QG-005` 与证据位置。

### QS-05 — 可回滚发布与 production-shaped 跨服务信心

- **解决的风险**：各模块绿色但真实组合失败，发布 verdict 与恢复承诺均不可信。
- **能力增量**：完成后，每个发布版本可以在不触碰持久状态的前提下切换、验证和恢复，并有一条 production-shaped smoke 证明关键服务共同工作。
- **承接发现**：`QG-006`、`QG-008`。
- **目标态**：不可变 release/image、状态分离、切换前备份/迁移门、上一版本恢复、同环境互斥；readiness 覆盖 Common、Intent、New Agents UI/backend、Nginx、PostgreSQL、shared stream 和 Intent callback。
- **纳入范围**：workflow deploy coordination、release identity/order、backup/rollback、Compose/Docker health、Nginx routes、real PostgreSQL cross-service smoke、failure injection。
- **排除范围**：不默认激活已有 database migration P3；不把真实 provider judge 放进每次 deploy；不访问生产机完成本 todo 的扫描。
- **架构边界**：CI artifact → remote release → images/containers → Nginx → services → PostgreSQL / state volumes → health verdict / rollback。
- **可观察验收证据**：顺序测试证明 live 不在备份前被覆盖、状态目录不进 delete scope；故障后运行版本 hash 回到上一 release；真实 Postgres读写和 stream/callback smoke；任一核心页面/DB/terminal event失败均使 deploy 非 PASS；并发部署被串行化或取消。
- **依赖 / 阻塞**：依赖 `QS-01`；完整 smoke 依赖 `QS-02`、`QS-03` 和 `QS-04` 的主路径不变量。
- **与其他切片边界**：本切片只消费明确 migration readiness / compatibility signal；New Agents migration P3 与 `DB/LEGACY-P3` 均保持独立 owner。
- **记录要求**：完成时记录 release identity、状态资产清单、fault/rollback证据和 smoke topology；取消时记录依据、当前不可回滚风险和 backlog owner；替换或迁移时记录 successor、移交的 `QG-006/QG-008` 与证据位置。

### QS-06 — AI / LLM 语义质量 P0 收口

- **解决的风险**：已启用 judge 低于当前门线，schema 合法但专业不完整的产物仍可能进入后续 handoff。
- **能力增量**：完成后，当前 77 分失败有可复现的差距、归因、重跑结果或诚实阻塞，关键 workflow 家族有分层语义证据。
- **承接发现**：`QG-010`。
- **目标态**：先满足 Playbook 对低于门线 P0 的失败维度、期望/实际差距、修复位置、重跑和新结果/阻塞记录；再明确 deterministic contract、provider smoke、artifact/browser judge 和 handoff judge 的职责。
- **纳入范围**：当前失败 scenario/rubric/artifact、workflow risk sampling、judge threshold/dimensions、evidence persistence、model/prompt/runtime/renderer attribution、external status/cost boundary。
- **排除范围**：不把 judge 设成所有本地 focused test 的默认依赖；不以 judge 替代 schema/renderer；不在本扫描轮调用更多模型。
- **架构边界**：workflow prompt/trace/artifact → deterministic contracts → browser/render → external judge → evidence/triage。
- **可观察验收证据**：当前 77 分场景达到门线或记录有效阻塞；失败维度与产物差距逐项闭合；每个高风险 workflow 家族有 semantic evidence或明确 NOT_RUN reason；重复样本的波动可解释；问题映射到 owning layer。
- **依赖 / 阻塞**：依赖 `QS-01` 的诚实 external verdict与 `QS-02` 的完整 trace/terminal；不依赖后续效率优化。
- **与其他切片边界**：本切片不改变 shared transport；transport/trace fault回流 `QS-02`，judge infrastructure与样本治理留在本切片。
- **记录要求**：完成时保存 judge元数据、维度、期望/实际差距、归因、重跑结果和成本；取消时记录依据、门线失败残余风险和 backlog owner；替换或迁移时记录 successor、移交的 `QG-010` 与证据位置。

### QS-07 — AI Coding 分层反馈、UI ownership 与诊断预算

- **解决的风险**：Agent 不知道该跑什么、运行环境不等价、关键 UI 没有 owner，失败日志又慢且难定位。
- **能力增量**：完成后，Agent 能从聚焦到全量逐层升级验证，每层有稳定入口、环境/风险映射、机器结果和时间预算。
- **承接发现**：`QG-007`、`QG-009`、`QG-012`、`QG-014`。
- **目标态**：focus/module/cross/full/external selector 和 CI mapping 机械同步；Python/Node 版本与 coverage/slow/build/E2E 差异显式；Common/Intent UI 关键场景有 owner；JUnit、warning、timeout和首次失败可用于自动定位。
- **纳入范围**：canonical command graph、environment preflight、module UI tests、CI artifacts、warning/open-handle budgets、cache/path selection/timeout/cancellation、运行时长基线。
- **排除范围**：不通过跳过 P0/P1 risk gate 换速度；不在尚未证明风险重叠时删除测试；不负责业务 bug 修复。
- **架构边界**：changed paths / risk tags → local selector → module/cross suite → CI jobs → machine-readable evidence → Agent diagnosis。
- **可观察验收证据**：代表性改动映射到唯一最小充分 suite并可升级；本地等价入口和 CI 收集数一致；Common/Intent UI 回归可执行；JUnit/summary包含 suite/risk/status；warning/open handles 达到预算；冷/热时长与 cache 命中有基线。
- **依赖 / 阻塞**：依赖 `QS-01` outcome contract；不能把远端 CI当首次验证。
- **与其他切片边界**：`QS-08` 处理源事实与重复资产，`QS-07` 只提供可执行反馈入口和诊断。
- **记录要求**：完成时记录 selector contract、风险映射、环境矩阵、预算、path-filter兜底和不运行原因；取消时记录依据、残余反馈成本和 backlog owner；替换或迁移时记录 successor、移交的 `QG-007/QG-009/QG-012/QG-014` 与证据位置。

### QS-08 — 静态事实源、重复资产与长期治理收口

- **解决的风险**：脚本存在但不可用，文档/矩阵/资产多份漂移，AI Agent 从错误事实源开始工作。
- **能力增量**：完成后，架构、配置、文档、静态资产和测试清单都有唯一 owner或机械漂移门，活跃 todo 只保留真实未完成工作。
- **承接发现**：`QG-011`、`QG-013`、`QG-015`。
- **目标态**：portable static gates fail-closed且理解允许的跨服务边界；Python owning scope、manifest/schema/Compose/docs 同步；secret/privacy/dependency gate有明确范围；重复资产按消费者证据收口；终态 todo退出活跃导航面。
- **纳入范围**：docs/architecture/config checks、critical Python scope、coverage config、manifest-derived matrices、安全/隐私/secret与dependency gate边界、static asset ownership、todo lifecycle truth。
- **排除范围**：不改变 AGENTS shared runtime architecture；不因相似名称删除必要纵深防御；不从 archive恢复任务。
- **架构边界**：authoritative config/code → generated/mirrored surfaces → static gate → stable docs / todo navigation / release assets。
- **可观察验收证据**：在 macOS/Linux同样通过或同样失败；合法集成不误报、故意 drift 必失败；不存在无人执行 test；重复副本有生成 hash或唯一源；终态 todo 已收口且稳定文档与当前 models/manifest一致。
- **依赖 / 阻塞**：排在功能性与反馈 P0/P1 后；可提前记录 owner，但删除/迁移必须基于前序切片的真实消费者证据。
- **与其他切片边界**：`QS-07` 决定运行入口与报告，本切片维护这些入口背后的单一事实源和低成本一致性；`QS-04` owning 运行时 exploit chain。
- **记录要求**：完成时记录 portable gate、drift negative test、asset ownership与todo收口证据；取消时记录依据、残余漂移/维护成本和 backlog owner；替换或迁移时记录 successor、移交的 `QG-011/QG-013/QG-015` 与证据位置。

## 全局验收标准

全部厚切片完成后，必须同时满足：

- **关键主路径**：New Agents 完整 turn/handoff、Intent execution/callback/stop/recovery、Common/Intent UI 导航、生产切换/回滚均有自动化风险证据。
- **共享架构契约**：所有 New Agents workflow 继续通过 manifest、共享 stream、typed events、共享 persistence 和 deterministic renderer；无 agent-specific bypass。
- **双栏可见进度**：对 artifact-data-first、慢 token、断流和最终收敛，左侧自然对话或明确可行动进度先于右侧首个可见 artifact 出现；两栏单调流式更新，不能以延迟右侧掩盖左侧饥饿。
- **失败传播**：zero/skip/tool error/timeout/EOF/persistence failure/child exit 均不会成为 PASS，父入口保留原始状态和首次失败。
- **安全测试隔离**：任何数据库 test 在连接前证明 test identity；非测试 DB sentinel、schema 和数据在 suite 前后不变。
- **分层入口**：聚焦、模块、跨层、全量和外部门有唯一命令、预期收集数、环境、风险范围与升级关系。
- **本地 / CI 等价**：同一 suite 在本地和 CI 的 selector、版本、threshold 和收集一致；有意差异明确且有 contract test。
- **跨层真实边界**：至少一条 production-shaped smoke 使用真实 HTTP、Nginx、服务和 PostgreSQL；fake 只位于声明的外部 adapter。
- **flaky / 环境依赖**：端口、时间、随机、共享状态、网络、资源清理和 timeout 可控；多轮证据能区分 flaky 与确定性失败，retry 不覆盖首次失败。
- **Mock / fake 边界**：每个 mock suite 说明不证明什么；production app / schema / error semantics 有 drift test，真实边界缺失时状态为 NOT_RUN/BLOCKED。
- **AI / LLM 质量门**：deterministic、smoke、judge 分层；高风险 workflow 有语义样本或诚实未运行原因，judge 元数据和归因可审计。
- **发布可信度**：状态目录不被 release sync 删除；备份发生在切换前；回滚运行上一不可变版本；readiness 覆盖页面、API、DB 和 stream。
- **可诊断性**：机器结果能映射 suite/workflow/path/risk；关键 job 有 JUnit/summary/diagnostic，warning/open handle/timeout 有 owner和预算。
- **静态安全与依赖边界**：所有生产入口对 required secrets fail-closed；secret/privacy/dependency gate 的执行范围与未知项明确，未运行扫描不得被 lint/build 替代。
- **冗余与成本**：被删除的测试均有“相同风险、相同失败模式、相同边界”证据；必要纵深防御保留；冷/热运行预算达到目标且不漏关键风险。
- **文档与治理**：稳定测试文档、manifest/models、CI/runner和 active todo 不再互相矛盾；archive 不被重新当成执行入口。

## 延后项与重新激活条件

当前 P2 `QG-012` 至 `QG-015` 已分别进入 `QS-07` / `QS-08`，没有无 owner 的 P2。唯一 P3 如下：

| Backlog owner | 发现 / 延后原因 | 当前风险 | 重新激活条件 | 处置边界 |
|---|---|---|---|---|
| 本文件 `DB/LEGACY-P3` | `QG-016`：两个 Intent legacy release surface 各自缺 consumer/owner 证据；立即修复可能延续死路径。 | secondary Compose被调用时因缺 source 失败；Langfuse conditional branch被触发时因缺脚本失败。 | 分别激活：文档/CI/用户再次调用 secondary Compose；或目标环境出现 legacy Langfuse container；任一路径在 deployment inventory 中被确认为受支持。 | 本 owner 负责先分别确认 consumer，再迁移到相应 release/schema slice或退役。`docs/todos/refactor/README.md:21-33` 只 owns New Agents startup migration，明确不 owns 这两个 Intent legacy surface。 |

## 现有 todo 与事实源去重

| 记录 | 当前分类 | 与本 todo 的边界 |
|---|---|---|
| `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` | 待收口：正文声明 P0/P1 已完成、无 unchecked item，仅保留 P2历史/候选，但仍位于 active | 不恢复其中切片；当前 judge 77 是新的实际证据，由 `QG-010/QS-06` owning。该长文件退出活跃面由 `QG-015/QS-08` 处理。 |
| `docs/todos/refactor/README.md` | 活跃 P3 register / 历史索引 | 只保留 New Agents startup migration mechanism ownership；`QS-05` 仅消费 readiness signal，`DB/LEGACY-P3` 独立 owns Intent legacy surface。 |
| `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`、enhancement diagnostic、milestone ledger | 历史事实 / 待收口 | 只用于确认已存在 deterministic artifact / smoke / judge 能力，不恢复旧 checkbox。 |
| `docs/todos/archive/**` 中 Alex handoff、New Agents evolution / architecture记录 | Archive | 只提供需求输入和历史验收边界；不作为当前剩余工作来源。 |
| `docs/plans/tech-debt.md` 及历史 specs/plans | 历史证据 | 当前 workflow、runner、tests和实际命令优先；不恢复旧 plan，不把历史 PASS 当当前 PASS。 |

## 执行记录

### 2026-07-10 — QS-01：诚实且不伤数据的验证结果

- **状态**：已完成实现与本地验证；下一个 owning 厚切片为 `QS-02`。
- **解决的风险**：`QG-001`、`QG-002`。
- **实现**：新增 `scripts/test/verification_outcomes.py`，本地 runner 与 CI 对 pytest/Jest/Vitest/命令门禁输出统一 JSON outcome；零收集、skip-only、缺少 smoke 配置、超时、子命令启动或退出失败、不可解析或不一致统计均为非 PASS。Proxy 移除 `--passWithNoTests`，并修正为 Jest 支持的 `--testPathPattern`。`check-docs.sh` 不再吞没 child-tool 错误，并为测试注入工具路径。Intent app factory 在 `db.init_app()` 前接收测试配置，且只允许 `sqlite:///:memory:`；外部 SQLite sentinel 会在连接前 fail-closed。
- **TDD / 负向证据**：先观察到新 outcome 测试中 Jest skip-only 计数和不一致 pytest 计数失败；修复后 `tests/test_verification_outcomes.py` 为 17 passed。数据库隔离 sentinel 的专用回归为 2 passed。
- **独立复核**：`qs01_review` 对最终 diff 复核通过，未发现 P1/P2；已逐项确认计数不变量、Jest skip-only、fake `GREP_BIN` 负向测试和 CI 相对路径。
- **已验证的实际结果**：`./scripts/test/test-local.sh api` 为 296 passed，并输出 `intent-tester-api/PASS (296/296)`；`./scripts/test/test-local.sh new-agents` 为前端 60 files / 872 tests、后端 907 passed / 4 deselected，均输出实际计数的 PASS outcome；无 smoke 配置时 `./scripts/test/test-local.sh smoke` 输出 `new-agents-real-llm-smoke/NOT_RUN` 并以非零退出，不再假绿。
- **已知非 PASS / 归属**：真实外部 LLM smoke 因未提供 `NEW_AGENTS_SMOKE_*` 配置保持 `NOT_RUN`，并未被当作通过；macOS 默认 `grep -P` 不可用时 docs gate 现在诚实输出 `FAIL`，跨平台解析改造仍由 `QS-08/QG-011` owning。本轮未调用付费 model judge；其 77/80 P0 收口仍由 `QS-06/QG-010` owning。Intent full run 仍有大量既有 resource warnings，New Agents frontend 仍有两个 React `act(...)` warnings，诊断预算由 `QS-07/QG-012` owning。
- **边界确认**：未修改 Intent 业务执行链、New Agents shared runtime、真实生产数据库、LLM judge 或 deployment；本切片只将既有 runner/CI gate 与 Intent 测试 app factory 收口为可诊断、fail-closed 的行为。

### 2026-07-11 — QS-02：共享 run 的流式与持久化一致性

- **状态**：已完成实现与本地验证；下一 owning 厚切片为 `QS-03`。
- **解决的风险**：`QG-003`、`QG-017`。
- **共享协议不变量**：首次可见 artifact 前必先渲染非占位 progress frame，且两帧通过异步边界分离；artifact-first raw output 在后端补齐诚实进度，前端对旧式无 chat delta 仍作防御；进度不会因最终 chat 回退。成功终态被收紧为 `agent_turn` 后的 `[DONE]`，delta-only EOF 或缺少 `[DONE]` 都抛出显式协议错误。
- **持久化与重试**：assistant 消息、artifact version、context summaries 与 success metric 通过单一事务提交，metric / unique-slot 故障会回滚全部成功记录并返回 `PERSISTENCE_FAILED` 或 `PERSISTENCE_CONFLICT`。新增 durable `AgentRunTurnRequest`，以 `(runId, requestId)` 唯一约束保存 active/completed/failed terminal outcome；首轮由客户端生成并发送稳定 `(runId, requestId)`，普通重试、重试本阶段生成及 assistant-only 内部续写重试均复用两者，服务端拒绝缺失 `requestId` 而非隐式生成。首 run 的并发创建冲突会重新读取既有 run；相同 request 重放不调用模型、不重复追加消息或版本，成功和失败终态均可重放。
- **TDD / 负向证据**：artifact-first SSE、delta-only EOF、缺失 `[DONE]`、metric 写失败和唯一槽冲突均先出现稳定红灯；随后转绿。本轮评审修复的“重试本阶段生成”与 assistant-only 续写重试均先证明会生成新 identity，再收敛为同一 replay identity。端点级真实 persistence 回归证明重复 request 只执行一次模型调用并重放相同 `agent_turn` 或失败 `error`；独立 SQLAlchemy 会话的重复 identity 写入触发真实 unique constraint；两个真实 Flask/SQLite session 的同步 stale sequence 与 stale artifact-version 竞争分别证明一方完成、另一方获得 `TurnPersistenceConflictError` 且不留下部分助手历史或第二个 artifact version。
- **已验证的实际结果**：New Agents backend 全量 `926 passed, 1 skipped`；frontend 全量 `60 files / 877 tests passed`；此前本次的 `./scripts/test/test-local.sh new-agents` 已输出 frontend `876/876 PASS`、backend `922/922 PASS`（其余 4 项按 runner 选择规则 deselect），本次新增三项回归已由对应前后端全量套件覆盖；`npm run lint` 通过；关键 Python flake8 通过。Playwright E2E 在沙箱内因 macOS MachPort 权限无法启动，随后在本机权限上下文重跑并以零退出完成（6 个用例进度点）。该 E2E 使用 mock typed SSE，不能替代本切片的后端真实 persistence 端点回归。前端 `ChatPane` 的两条既有 `act(...)` warning 仍由 `QS-07/QG-012` owning。
- **设计与治理记录**：`tools/new-agents/CONTEXT.md` 记录 Run、turn request、progress frame 与 terminal outcome 的术语；ADR-0001 明确 request identity 是客户端生成的 `(runId, requestId)`，服务端以 shared durable model 处理重放，而非依赖 runId、metric JSON 或 localStorage。
- **边界确认**：所有 workflow 继续使用共享 `/api/agent/runs/stream`、typed SSE、shared persistence 与 renderer；未新增 Lisa/Alex 专属 runtime、SSE、store 或渲染管线。外部 LLM judge、生产-shaped 部署和业务 execution identity 分别留给 `QS-06`、`QS-05`、`QS-03`。

### 2026-07-11 — QS-03：Intent Tester 真实执行与持久化闭环

- **状态**：已完成实现与本地验证；下一个 owning 厚切片为 `QS-04`。
- **解决的风险**：`QG-004`。Flask `ExecutionHistory` 先创建且唯一分配 canonical `execution_id`，create、Node dispatch、started/result callback、页面进度、GET、stop、retry、reconcile 与重启恢复都复用该 ID；Node 不再生成第二身份，WebSocket 只承载同 ID 的可见进度和脱敏诊断。
- **durable / recovery 不变量**：Flask 是唯一状态权威；callback 通过条件状态转移和步骤快照事务保持幂等，终态不能回退。页面只调用 Flask durable API；有界轮询耗尽后由 Flask `reconcile` 拉取 production Node 同 ID 状态，遗漏 callback 可补偿，Node 不可用、ID 不匹配或非法响应显式 502。callback 耗尽诊断只在 pending/running 条件更新，终态提交优先并清除 active-only 告警。stop 只作用于当前 owner；pending/running retry 复用原 ID，terminal retry 显式拒绝。
- **真实组合证据**：`tests/integration/test_durable_execution_loop.py` 通过真实回环 HTTP 启动 Flask、SQLite 与 production `midscene_server.js`，只替换 Playwright / MidScene AI adapter；覆盖首次代理不可用后 same-ID retry、started/result callback、重复 result 不复制步骤、scoped stop、Flask 重启读回，以及故意把 durable 记录退回 pending 后由 production Node status 恢复同一 success 记录。全量 Intent pytest 包含该组合测试并得到 `373 passed`。
- **production package 证据**：deterministic builder 从 production Node server、lockfile 和 `.env.example` 生成展开目录与两个同步 ZIP，过滤 cache 并固定顺序、权限和时间戳；两个 ZIP 的 SHA-256 均为 `59e1c562edded7d36c39b4eeaf9d132e91887170e7b72a7978c3cbfd458123c8`。clean-room smoke 在临时目录解压，使用仓库已安装依赖边界启动 `/health`，并证明缺 `OPENAI_API_KEY` 时 fail-closed；它不证明离线 fresh `npm install`、真实 provider 或 Windows `start.bat`。
- **TDD / 审查整改**：canonical ID、非法 lifecycle、retry/reconcile、页面旧响应隔离、callback 重试、raw secret 清理、deterministic package 和 clean-room 启动均先有失败证据再转绿。标准复审发现并修复了 callback 诊断与 terminal commit 的竞态、预期及意外代理异常原文/traceback 入日志和 lifecycle endpoint 类型门禁；两批审查聚焦回归分别为 6 passed 与 5 passed。
- **双轴复核**：最终 Standards 与 Spec 两条独立复审均为 `CLEAN / READY`；确认厚切片验收、并发状态机、日志脱敏、类型门禁、真实组合边界、生成物同步和交付记录均已闭合。
- **最终验证**：Intent Python `373 passed, 1368 warnings`；durable frontend controller `50 passed`；Node production proxy 在允许绑定本机临时端口的环境中 `16 passed`；critical flake8、两个 Node `--check` 与 `git diff --check` 均通过。Node proxy 首次在受限沙箱运行因 Supertest `listen EPERM 0.0.0.0` 得到 14 个环境失败，随后以相同命令在本机端口权限环境重跑全绿；未把该首次运行表述为 PASS。
- **残余边界 / owner**：本切片没有调用真实付费 AI provider，也不处理 Intent 认证、stored XSS、CSP 或生产 secrets，这些由 `QS-04/QG-005` owning；production-shaped Compose/Nginx/PostgreSQL 组合和 release transaction 由 `QS-05/QG-006/QG-008` owning。现有 1363 条 warning 的诊断预算由 `QS-07/QG-012` owning。

### 2026-07-11 — QS-04：Intent Tester 访问与浏览器安全边界

- **状态**：已完成实现、真实浏览器/跨语言/模块全量验证与双轴复审；本轮停止于 QS-04，不启动 QS-05。
- **访问与启动模型**：production 只允许 `restricted` / `public-readonly`，配置和 URL-map policy completeness 在数据库初始化前 fail-closed；session unsafe request 要求 exact canonical Origin + CSRF，proxy lifecycle 只接受 backend bearer。execution disabled 会清空 execution-only canonical config并在认证前关闭全部 execution surface。production access mode、Origin、secret、admin hash 与 execution 条件配置由 workflow、deploy preflight 和 Compose 同步要求，不再提供默认 secret/mode。
- **浏览器与 stored-XSS 证据**：Intent 自有资产统一走 `/intent-tester/static/**`，不与 portal `/static/**` 混用；所有 routed page 使用 response-local nonce CSP、本地固定版本 vendor、safe DOM 与 encoded server data。真实 Chromium 从 operator 登录、CSRF API 写入覆盖 testcase 与 nested step/action/params/output 的攻击文本，贯通列表、编辑修改保存、执行页和 local-proxy；payload 未产生 inline handler、dialog、外部请求或 exfil。执行按钮真实触发 proxy 不可达的受控 502，页面保留 same ID 并显示 retry。public-readonly 独立匿名浏览器只读摘要且无法打开详情或 mutation。真实浏览器还发现并修复了 `Referrer-Policy: no-referrer` 令 basic form POST 发送 `Origin: null`、导致正常登录被拒的跨策略矛盾；最终使用 `same-origin` 且继续拒绝 missing/foreign/null Origin。
- **Node / durable 安全闭环**：Node HTTP 除 `/health` 外均要求长期 bearer；local-host 只绑定 loopback 并要求 exact loopback HTTP Origin，managed 禁用 browser Socket。页面只在 canonical execution ID 存在后向 Flask 取 60 秒 HMAC ticket；Flask 对 canonical JSON bytes 签名，Node 对 decoded bytes 验签并校验 execution/origin/audience/expiry，连接只进入 `execution:<id>` room。真实 Flask endpoint → production Node → Socket.IO 跨语言测试通过。running progress 只写安全字段且 active-only CAS，terminal lifecycle 仍是唯一终态权威；报告路径限制在 owning realpath，生成 HTML 将动态值和原始报告全部转义为纯文本并附 strict CSP。
- **部署与 package 证据**：production 只有 Nginx 发布 host ports，Flask/PostgreSQL/managed Node 使用内部 service DNS；deploy/health 经 gateway 探测 Intent、使用精确容器名并在 DB 容器内运行 `pg_isready`，restricted/public-readonly 匿名状态按声明判断。开发 Compose 只 loopback 暴露 Flask。native package 在安装/启动副作用前校验 topology/token/origin/provider/callback；clean-room 合法配置真实启动 `/health`，缺任一必需项非零且不泄露 secret。两份 ZIP byte-identical，SHA-256 均为 `63815aa43acb6f37a21a18c010cb19b725a00fc1ba3a5dacf90927651e18c1c8`。
- **纵向执行纠偏**：原 Task 1–6 曾按 config → policy → UI → Node → progress → deploy 横向排队，首次完整浏览器证据晚到 Task 7；计划已诚实记录该偏差，首轮整片审查后的整改改按 restricted operator、public-readonly anonymous、local-host ticket、production gateway、native package 五条 tracer 旅程闭环。Playbook 已明确：技术重构、安全整改和基础设施变更同样必须按可观察行为/风险闭环小步 RED → 最小实现 → 聚焦回归 → 跨边界证据，不能把技术层完成当进度。
- **验证与审查**：Intent Python coverage 全量 `510 passed, 1573 warnings`；frontend Node behavior `59/59`；production proxy Jest `40/40`；real Chromium `2/2`；Flask→Node durable/ticket real HTTP `1/1`；deployment `5/5`；clean-room package `11/11`；deployment + CSP focused `25/25`；critical flake8、Node/shell syntax、ZIP identity 与 `git diff --check` 通过。`test-local.sh all` 在受限上下文因回环端口 `EPERM` 令 Intent/proxy 子门禁失败，并停在无条件 Playwright 安装；同一产品子门禁已在本机权限上下文用上述命令重跑通过，runner 权限/重复安装问题保留给 `QS-07/QG-007/QG-014`，未把该次 runner 写成 PASS。现存 warning 属于既有 SQLAlchemy/datetime/marker/连接回收诊断预算，由 `QS-07/QG-012` owning。首轮 Standards 发现 3 Critical/3 Important、Spec 发现 5 Important，全部按 delta 修复并由两轴复审确认 `CLEAN/READY`；JUnit 时间戳产物已恢复，不进入交付。
- **残余边界 / owner**：没有调用真实付费 provider；完整 production-shaped Nginx/PostgreSQL 多服务启动、不可变 release、backup/migration/rollback/failure injection 仍由 `QS-05/QG-006/QG-008` owning；组织级身份平台与 QS-08 scanner 治理未纳入本切片。下一 owning 厚切片仍为 `QS-05`，但按用户停止线先暂停并重新评估其自然纵向边界。

### 2026-07-16 — QG-017 用户复现重开：全工作流对话先于产出物

- **状态**：`REOPENED / TODO`，只记录待办，未启动调试、spec、plan、TDD 或实现。
- **用户复现**：在测试设计/测试用例生成工作流的第一阶段，右侧产出物先按段落开始流式渲染，左侧对话内容在右侧之后才出现，可见顺序与用户预期相反。
- **全工作流共享规则**：测试设计第一阶段只是复现入口，不得实现为 Lisa/该阶段专属分支。所有当前与未来 workflow/stage 都必须通过共享 `/api/agent/runs/stream`、typed SSE、shared frontend stream/state 与统一渲染基础设施遵守相同顺序。
- **用户可见不变量**：左侧必须先出现与本轮分析相关、有意义的自然对话，之后右侧才可出现第一个可见产出物增量。通用“正在生成”占位符或只描述执行状态的进度帧不等价于用户要求的左侧对话，不能用于满足该顺序验收。
- **必须保留的行为**：右侧产出物开始后继续按段落/结构单调流式渲染，不允许为了调整先后顺序而退化为等待完整 artifact 后一次性显示，也不允许通过人为延迟右侧来伪造正确顺序。
- **后续验收边界**：激活本待办后，先按用户真实复现链路完成根因调查；再用共享后端 raw/partial JSON → typed SSE → frontend parser/store → ChatPane/ArtifactPane DOM 时序证据验收。至少覆盖一个 Lisa 与一个 Alex 的代表 workflow，并使用慢 token、artifact-first provider 输出、断流和最终收敛负向样本证明全工作流统一不变量。
- **与历史 QS-02 的关系**：`QS-02` 的 request identity、原子持久化与必需终态结论保持完成；但其“progress frame 可满足左侧先行”的旧验收不能替代本次明确的自然对话顺序。未来不直接改写或伪裂 `QS-02`；需在用户显式恢复时回到 `ASSESS`，形成新的同级厚切片承接本重开项。

### 2026-07-16 — QG-018 新增：以 TEST_DESIGN/CLARIFY 统一全阶段右侧分段流式

- **状态**：`TODO / NOT_STARTED`，本轮已完成静态全量盘点与待办登记，未修改任何 renderer、runtime、SSE、frontend state 或 UI。
- **行为基准**：以 `TEST_DESIGN/CLARIFY` 右侧产出物的用户可见行为为标准。对模型已完整输出且通过局部类型校验的顶层结构，后端将其确定性渲染为章节/Markdown 并立即替换到右侧；后续结构完成后继续追加到同一累积文档。
- **静态盘点矩阵**：

  | Workflow | 阶段数 | 已有基准 partial renderer | 待统一阶段数 |
  |---|---:|---:|---:|
  | `TEST_DESIGN` | 4 | 1（`CLARIFY`） | 3 |
  | `REQ_REVIEW` | 2 | 0 | 2 |
  | `INCIDENT_REVIEW` | 3 | 0 | 3 |
  | `IDEA_BRAINSTORM` | 4 | 0 | 4 |
  | `VALUE_DISCOVERY` | 4 | 0 | 4 |
  | `STORY_BREAKDOWN` | 4 | 0 | 4 |
  | `PRD_REVIEW` | 4 | 0 | 4 |
  | **合计** | **25** | **1** | **24** |

- **根因证据边界**：当前 `render_partial_artifact_data_markdown()` 以硬编码条件只调用 `_render_partial_test_design_clarify_markdown()`，其他 stage 立即返回 `None`。共享 runtime 虽然能从 raw JSON 提取已完整顶层字段，但没有对应 partial renderer 时无法在完整 artifact 校验前生成右侧 Markdown。这是共享 renderer 注册/能力矩阵缺口，不是 React 组件或单个 workflow prompt 的局部差异。
- **全阶段不变量**：每个 manifest online stage 必须声明并通过可机械验证的 partial-rendering 能力；已完整章节不等未完成章节，右侧文档单调累积，已显示的正确内容不回退、闪烁、重复或丢失。partial 累积的最终结果必须与现有 final deterministic renderer 的完整 Markdown 一致。
- **严格失败边界**：不完整的表格行、引用、Mermaid / `ai4se-visual` 块、ID 关系或未通过局部 schema 的内容不得被伪造为可渲染成功；该严格性不得反过来阻塞其他已完整章节的渐进显示。
- **共享架构边界**：差异应以 artifact schema、章节字段顺序、partial renderer/registry 配置与 contract 表达，所有 stage 继续复用共享 raw streaming、`agent_delta`、SSE parser、store 与 ArtifactPane；禁止新增 Lisa/Alex/workflow/stage 专属 transport、endpoint、store 或渲染管线。
- **后续验收证据**：用 manifest 驱动的 25/25 stage 能力矩阵阻止新 stage 或旧 stage 漏注册；每个 stage 的 fixture 证明至少两个结构块可分步出现并收敛到 final Markdown；每个 workflow 至少一条 typed SSE → frontend state → DOM 证据验证用户可见分段流式。同时与 `QG-017` 组合验收：左侧有意义自然对话先出现，随后右侧按本项规则分段流式。
- **恢复规则**：本项不追加为已完成 `QS-02` 的内部子任务。用户后续显式恢复时先回到 `ASSESS`，由 CGA 判断 `QG-017` 与 `QG-018` 是组成一个“全工作流双栏流式一致性”厚切片，还是保持两个可独立验收的同级切片。

### 2026-07-16 — QG-019 新增：文档信息退出首屏重表格

- **状态**：`TODO / NOT_STARTED`，本轮只完成只读核对与待办登记，未修改 schema、prompt、renderer、Markdown preview、布局或样式。
- **用户问题**：右侧本就狭窄，当前产出物经常在标题后先展示占据多行的“文档信息”表格。该区块主要是 Artifact 名称、Workflow、Stage、状态、版本与生成时间等辅助信息，重要性低于正文，却优先消耗首屏和流式生成早期的注意力。
- **已确认的实现漂移**：至少 CLARIFY、DELIVERY、BLUEPRINT 和四个 PRD_REVIEW stage 的 deterministic renderer 会在标题后立即输出元信息表；CLARIFY 的 partial renderer 还会优先显示它。但 CLARIFY、DELIVERY 与 BLUEPRINT 的前端模板已将同类内容定义为文末“附录”，所以不能只改 prompt，必须统一结构化 renderer、partial renderer、预览与导出规则。
- **不得误伤的语义**：`document_info` 仍是 artifact schema、持久化、版本、handoff 或导出可消费的结构化事实，不以删除字段换取视觉空间。全量盘点时需把纯文档元信息与事件概要、评审结论、执行摘要等业务正文分开；后者不能因为标题相似而一并挪走或降级。
- **候选方案与决策规则**：默认候选是把纯元信息放到文末，改成紧凑附录、短键值行或可折叠摘要，不再使用正文级大型两列表格。备选是在 ArtifactPane 的共享布局中提供右下角、页脚或折叠元信息区；只有它在窄屏、长文滚动、编辑/预览切换、版本恢复、Markdown/PDF 导出和无障碍访问下都不遮挡正文时才采用。不得为单个 workflow/stage 创建专属 UI。
- **与流式待办的组合约束**：`QG-017` 负责左侧自然对话先行，`QG-018` 负责右侧正文按有效段落渐进显示，本项负责右侧第一块内容的价值密度。三项组合后的用户顺序应是“左侧有意义对话 → 右侧首个业务正文段落 → 后续正文持续累积 → 低权重文档元信息在尾部或独立轻量区”，不能让 `document_info` 继续充当首个可见 artifact 增量。
- **后续验收证据**：恢复时建立 25 个 manifest stage 的元信息/业务摘要分类矩阵；后端证明 partial 与 final renderer 的章节顺序一致且结构化数据未丢失；前端至少覆盖窄右栏首屏、长文滚动、流式增量、编辑/预览、版本恢复与导出；每个 workflow 至少一条 DOM 证据证明正文优先且元信息仍可发现、可读取。
- **恢复规则**：先回到 `ASSESS`，与 `QG-018` 在同一共享 artifact rendering 设计中评估，但保持独立验收，避免“分段流式已统一”掩盖首屏信息层级仍然错误。

## 本轮停止线

2026-07-16 用户明确要求只保留刚积累的 3 个待办，随后新增并批准 QG-020。`QS-01` 至 `QS-04` 的既有交付继续作为历史证据；`QS-05` 至 `QS-08`、其承接的未完成发现和本文件内其他 P2/P3 条件触发项全部取消，不再作为恢复候选。`QG-017` 至 `QG-020` 已在 [`2026-07-16-new-agents-streaming-and-artifact-ux.md`](2026-07-16-new-agents-streaming-and-artifact-ux.md) 完成并归档。未来出现新失败时必须按当前事实重新建项，不得从本归档恢复旧序列。
