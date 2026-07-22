# QG-020 New Agents 真实链路功能测试重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **完成记录（2026-07-20）：** 本计划已全部执行并归档。最终确定性门禁为 runner/contracts 107、LiveStack 18、frontend 947、backend 1247 全部通过；真实门禁严格按 `pr → nightly → release` 获得 2/2、25/25、7/7 PASS；Code 与 Security 独立复审均为零遗留。

> **路径替代（2026-07-22）：** 本文件保留原实施时的文件名作为历史证据。现行 deterministic E2E 已由 QG-023 收口为 [`test_deterministic_live_stack.py`](../../tests/e2e/new_agents_real/test_deterministic_live_stack.py) 与 [`test_live_stack_contracts.py`](../../tests/e2e/new_agents_real/test_live_stack_contracts.py)，入口见 [`new_agents_deterministic_e2e.py`](../../scripts/test/new_agents_deterministic_e2e.py)。

**Goal:** 建立一个无头、功能型、失败关闭的 New Agents 测试入口，使开发内环、无 secret 自动 PR、受保护 Nightly 与发布分别获得真实程度和成本匹配的格式、SSE 流式、DOM、持久化与阶段流转证据。

**Architecture:** 用 `scope + workflow + stage` 作为统一深模块接口；matrix 从 manifest 派生，live stack 隐藏 Vite/Flask/SQLite/Chromium 生命周期，SSE observer 与 assertions 只消费脱敏结构化 trace。相同 provider seam 在开发内环接 deterministic OpenAI-compatible adapter，在真实门禁接 DeepSeek，两个证据层级独立记账。

**Tech Stack:** Python 3.11、pytest、Python Playwright、Flask/SQLite、Vite/React 19、typed SSE、OpenAI-compatible streaming、GitHub Actions。

## Global Constraints

- 只改 New Agents 测试体系及其 runner、CI、稳定测试文档和 owning todo；禁止改动 intent-tester 业务/测试。
- 禁止触碰或暂存 `tools/intent-tester/test-results/proxy/junit.xml`。
- 所有 workflow/stage 必须继续复用共享 `/api/agent/runs/stream`、runtime、SSE、frontend store/UI 和服务端持久化。
- 真实 scope 禁止 `page.route`、替换生产 fetch、mock snapshot/artifact/handoff、截图基线和像素 diff。
- API key 只能进入 backend/test process；不得进入 Vite/browser、argv、stdout、报告或 Git。
- 缺凭证必须产生 `NOT_RUN` 且进程非零退出；skip、mock 或低层证据不能替代真实模型 `PASS`。
- 内部 Task 不是独立切片、commit 或交付点；按 Goal Mode Playbook 在厚切片完成后只做一次正式 Spec/Standards 审查和一个 QG-020 聚焦 commit。

---

## 文件结构与 ownership

### 新建

- `scripts/test/new_agents_functional.py`：统一 scope/selection/preflight/子命令编排的深模块。
- `scripts/test/new-agents-functional.sh`：只选择仓库 Python 并转发参数的 shell adapter。
- `tests/test_new_agents_functional_runner.py`：runner 参数、manifest selection、缺配置和 secret 隔离单测。
- `tests/e2e/new_agents_real/__init__.py`：真实链路测试包。
- `tests/e2e/new_agents_real/config.py`：根 `.env` 安全读取和 `RealLlmConfig`。
- `tests/e2e/new_agents_real/matrix.py`：manifest-derived `StageCase`/`WorkflowCase`。
- `tests/e2e/new_agents_real/real_llm_scenarios.json`：7 个 workflow 的合成业务背景和 PR 关键标记。
- `tests/e2e/new_agents_real/reporting.py`：递归脱敏、错误分类和 JSON evidence writer。
- `tests/e2e/new_agents_real/stream_observer.py`：原生 fetch clone SSE 旁路观察脚本和 trace 解析。
- `tests/e2e/new_agents_real/assertions.py`：SSE/DOM/metadata/persistence/transition 不变量。
- `tests/e2e/new_agents_real/live_stack.py`：Flask/Vite/Chromium/SQLite 生命周期。
- `tests/e2e/new_agents_real/fake_provider.py`：仅供 evidence level 3 的本地 OpenAI-compatible streaming adapter。
- `tests/e2e/new_agents_real/workflow_runner.py`：独立 stage probe 与顺序 workflow journey。
- `tests/e2e/new_agents_real/conftest.py`：live stack fixtures 与动态 case selection。
- `tests/e2e/new_agents_real/test_contracts.py`：matrix、trace、report、secret 和失败语义的确定性测试。
- `tests/e2e/new_agents_real/test_live_stack.py`：deterministic provider 的真实 frontend/backend/SQLite/browser tracer。
- `tests/e2e/new_agents_real/test_real_agent_workflows.py`：真实 DeepSeek stage/workflow cases。
- `tools/new-agents/frontend/devServerProxy.ts`：可测试的 Vite proxy seam。
- `tools/new-agents/frontend/devServerProxy.test.ts`：proxy target/rewrite/disabled tests。

### 修改

- `tools/new-agents/frontend/vite.config.ts`：只在显式 backend target 时挂载 proxy；删除任何把 LLM key 注入 bundle 的 define。
- `scripts/test/test-local.sh`：mock browser 显式排除 `real_llm`，旧 `smoke` 委派统一 runner。
- `pytest.ini`：注册 `real_llm` marker。
- `tools/new-agents/backend/pytest.ini`：保持 slow marker 语义。
- `.github/workflows/deploy.yml`：拆分无 secret deterministic PR job 与受保护真实模型 job，新增 schedule、受限 manual dispatch、JSON evidence allowlist 和 deploy dependency。
- `docs/TESTING.md`：更新 New Agents evidence levels、命令、执行时机和失败关闭语义。
- `docs/todos/archive/2026-07-16-new-agents-streaming-and-artifact-ux.md`：记录 QG-020 最终状态、结果证据和归档终态。
- `.gitignore`：忽略 `test-results/new-agents-real/`（若现有规则未覆盖）。

### 删除

- `tools/new-agents/backend/tests/test_agent_real_smoke.py`：由共享真实 browser/backend/persistence harness 替代，避免单阶段 direct-runtime skip 路径继续充当真实门禁。

---

### Task 1（内部步骤，非切片）：统一选择、凭证与报告 seam

**Files:**
- Create: `scripts/test/new_agents_functional.py`
- Create: `tests/test_new_agents_functional_runner.py`
- Create: `tests/e2e/new_agents_real/config.py`
- Create: `tests/e2e/new_agents_real/matrix.py`
- Create: `tests/e2e/new_agents_real/reporting.py`
- Create: `tests/e2e/new_agents_real/real_llm_scenarios.json`
- Test: `tests/e2e/new_agents_real/test_contracts.py`

**Interfaces:**
- Produces: `parse_scope(argv) -> FunctionalScope`、`load_real_llm_config(root, environ) -> RealLlmConfig`、`select_cases(scope, manifest, workflow_id=None, stage_id=None) -> tuple[TestCase, ...]`、`write_report(path, evidence) -> None`。
- Invariants: `nightly == 25 stages`，`release == 7 workflows`，`pr` 包含 Lisa/Alex；secret 永不进入 repr/report/frontend env。

- [x] **Step 1: 写 runner/matrix/config/report 的失败测试**

```python
def test_manifest_scopes_are_complete():
    assert len(select_cases(FunctionalScope.NIGHTLY, MANIFEST)) == 25
    assert len(select_cases(FunctionalScope.RELEASE, MANIFEST)) == 7
    assert {case.agent_id for case in select_cases(FunctionalScope.PR, MANIFEST)} == {"lisa", "alex"}

def test_missing_real_config_is_not_run_and_fails_closed(tmp_path):
    result = plan_execution(FunctionalScope.PR, root=tmp_path, environ={})
    assert result.status == "NOT_RUN"
    assert result.exit_code != 0

def test_report_recursively_redacts_canary_secret(tmp_path):
    secret = "sk-qg020-canary"
    path = tmp_path / "report.json"
    write_report(path, {"authorization": f"Bearer {secret}", "nested": {"message": secret}})
    assert secret not in path.read_text()
```

- [x] **Step 2: 运行 RED 并保存预期失败**

Run: `.venv/bin/python -m pytest -o addopts='' tests/test_new_agents_functional_runner.py tests/e2e/new_agents_real/test_contracts.py -q`

Expected: FAIL，原因是 selection/config/report 接口尚不存在；不得因 collection error 以外的环境问题失败。

- [x] **Step 3: 最小实现 manifest selection、严格配置和脱敏报告**

```python
@dataclass(frozen=True)
class RealLlmConfig:
    api_key: SecretStr
    base_url: str
    model: str

def load_real_llm_config(root: Path, environ: Mapping[str, str]) -> RealLlmConfig:
    values = dotenv_values(root / ".env") | dict(environ)
    required = ("NEW_AGENTS_SMOKE_API_KEY", "NEW_AGENTS_SMOKE_BASE_URL", "NEW_AGENTS_SMOKE_MODEL")
    missing = [name for name in required if not str(values.get(name, "")).strip()]
    if missing:
        raise RealLlmConfigurationError(tuple(missing))
    return RealLlmConfig(SecretStr(str(values[required[0]])), str(values[required[1]]), str(values[required[2]]))
```

实现禁止把 `SecretStr.get_secret_value()` 用于 backend 子进程环境以外的位置；`RealLlmConfig.__repr__` 只显示掩码。

- [x] **Step 4: 运行 GREEN 与 mutation checks**

Run: `.venv/bin/python -m pytest -o addopts='' tests/test_new_agents_functional_runner.py tests/e2e/new_agents_real/test_contracts.py -q`

Expected: PASS。随后临时向 manifest case 集增加不存在的 stage，集合相等测试必须 FAIL；恢复后再 PASS。

---

### Task 2（内部步骤，非切片）：确定性 provider 贯通真实 live stack

**Files:**
- Create: `tools/new-agents/frontend/devServerProxy.ts`
- Create: `tools/new-agents/frontend/devServerProxy.test.ts`
- Modify: `tools/new-agents/frontend/vite.config.ts`
- Create: `tests/e2e/new_agents_real/fake_provider.py`
- Create: `tests/e2e/new_agents_real/live_stack.py`
- Create: `tests/e2e/new_agents_real/stream_observer.py`
- Create: `tests/e2e/new_agents_real/assertions.py`
- Create: `tests/e2e/new_agents_real/workflow_runner.py`
- Create: `tests/e2e/new_agents_real/conftest.py`
- Test: `tests/e2e/new_agents_real/test_live_stack.py`

**Interfaces:**
- Consumes: `RealLlmConfig`、manifest `StageCase`。
- Produces: `LiveStack` context manager、`run_stage_probe(page, stack, case, prompt) -> StageEvidence`。
- Provider seam: `base_url + api_key + model`，fake 与 DeepSeek adapter 共用，无 production runtime 分支。

- [x] **Step 1: 写 proxy 与 live-stack tracer 的失败测试**

```typescript
it('rewrites only the New Agents API prefix', () => {
  const proxy = buildNewAgentsDevProxy('http://127.0.0.1:5002');
  expect(proxy['/new-agents/api'].rewrite('/new-agents/api/agent/runs/stream'))
    .toBe('/api/agent/runs/stream');
});

it('does not expose a frontend proxy without an explicit backend target', () => {
  expect(buildNewAgentsDevProxy(undefined)).toEqual({});
});
```

```python
def test_deterministic_provider_crosses_real_stack(deterministic_live_stack):
    evidence = run_stage_probe(deterministic_live_stack, StageCase("TEST_DESIGN", "CLARIFY"))
    assert evidence.level == 3
    assert evidence.stream_order[:2] == ("chat", "artifact")
    assert evidence.artifact_delta_count >= 2
    assert evidence.snapshot_artifact_versions == 1
    assert evidence.restored_from_server is True
```

- [x] **Step 2: 运行 RED**

Run: `cd tools/new-agents/frontend && npm run test -- devServerProxy.test.ts`

Run: `.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_real/test_live_stack.py -q`

Expected: 两组都因 proxy/live-stack 接口缺失而 FAIL。

- [x] **Step 3: 实现最小 Vite proxy 和 live stack**

```typescript
export const buildNewAgentsDevProxy = (target?: string) => target ? {
  '/new-agents/api': {
    target,
    changeOrigin: true,
    rewrite: (value: string) => value.replace(/^\/new-agents/, ''),
  },
} : {};
```

`LiveStack` 必须用临时 SQLite、动态 loopback 端口、`flask --app app run --no-reload`、`vite --strictPort` 和 `chromium.launch(headless=True)`；frontend env 从 allowlist 重建并显式剔除所有 key/secret/token/password 名称。

- [x] **Step 4: 实现 deterministic OpenAI-compatible stream adapter**

adapter 接收 `/chat/completions`，把现有合法 `VALID_CLARIFY_ARTIFACT_DATA` 包装为 `chat + artifact_data + stage_action` JSON，按字段边界拆成多个 OpenAI SSE delta；它不进入真实 scope，不拦截 Agent API。

- [x] **Step 5: 运行 GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- devServerProxy.test.ts`

Run: `.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_real/test_live_stack.py -q`

Expected: proxy tests PASS；无外部网络的真实 frontend/backend/SQLite/browser tracer PASS，报告标记 evidence level 3。

---

### Task 3（内部步骤，非切片）：真实 stage probe 与 workflow journey

**Files:**
- Modify: `tests/e2e/new_agents_real/stream_observer.py`
- Modify: `tests/e2e/new_agents_real/assertions.py`
- Modify: `tests/e2e/new_agents_real/workflow_runner.py`
- Modify: `tests/e2e/new_agents_real/conftest.py`
- Create: `tests/e2e/new_agents_real/test_real_agent_workflows.py`
- Test: `tests/e2e/new_agents_real/test_contracts.py`

**Interfaces:**
- Consumes: `select_cases()`、`LiveStack`、workflow backgrounds。
- Produces: `run_stage_probe(...) -> StageEvidence`、`run_workflow_journey(...) -> WorkflowEvidence`。
- Trace interface: request coordinates + event types/times + text lengths/hashes + snapshot summary；不包含 key 或完整 prompt。

- [x] **Step 1: 写 SSE/DOM/transition 失败测试**

```python
def test_trace_rejects_final_only_artifact():
    with pytest.raises(FunctionalAssertionError, match="partial artifact"):
        assert_stage_trace(trace(agent_turn_only=True))

def test_trace_rejects_artifact_before_natural_chat():
    with pytest.raises(FunctionalAssertionError, match="chat before artifact"):
        assert_stage_trace(trace(order=("artifact", "chat")))

def test_workflow_requires_run_id_reuse_and_immediate_transition():
    with pytest.raises(FunctionalAssertionError, match="runId"):
        assert_workflow_trace(workflow_trace(run_ids=("a", "b")))
```

- [x] **Step 2: 运行 RED**

Run: `.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_real/test_contracts.py -q`

Expected: 新增不变量测试 FAIL，原因是 assertions/runner 尚未提供相应行为。

- [x] **Step 3: 实现 fetch clone、MutationObserver 和 snapshot 对齐**

旁路脚本必须调用 `const clone = response.clone()`，读取 clone 的 `ReadableStream`，原 response 原样返回；每个 requestId 建立独立 trace。DOM observer 只记录 hash/length/heading order。Python runner 在每个 turn 后通过真实 `/agent/runs/{runId}` 核对 snapshot，并在末 turn reload URL 验证恢复。

- [x] **Step 4: 实现动态真实 case 收集**

```python
def pytest_generate_tests(metafunc):
    if "real_case" not in metafunc.fixturenames:
        return
    selection = selection_from_environment()
    metafunc.parametrize("real_case", selection.cases, ids=[case.test_id for case in selection.cases])
```

禁止通过参数化后 `pytest.skip` 过滤范围；实际 collection 数必须等于 scope 计划数。

- [x] **Step 5: 运行确定性 GREEN 和无凭证失败关闭**

Run: `.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_real/test_contracts.py tests/e2e/new_agents_real/test_live_stack.py -q`

Expected: PASS。

Run: `./scripts/test/new-agents-functional.sh pr`

Expected: 当前 `.env` 下输出 `NOT_RUN`、不显示任何 secret、exit code 非零；不启动 Chromium/provider 请求。

---

### Task 4（内部步骤，非切片）：统一命令、marker 和旧 smoke 迁移

**Files:**
- Create: `scripts/test/new-agents-functional.sh`
- Modify: `scripts/test/new_agents_functional.py`
- Modify: `scripts/test/test-local.sh`
- Modify: `pytest.ini`
- Delete: `tools/new-agents/backend/tests/test_agent_real_smoke.py`
- Modify: `.gitignore`
- Test: `tests/test_new_agents_functional_runner.py`

**Interfaces:**
- Local CLI: `inner`、`stage WORKFLOW STAGE`、`workflow WORKFLOW`、`pr`、`nightly`、`release`。
- Existing adapter: `./scripts/test/test-local.sh smoke` 等价调用 `stage TEST_DESIGN CLARIFY`；default `e2e` 明确执行 `e2e and not real_llm`。

- [x] **Step 1: 写 CLI argv、marker 和旧入口契约失败测试**

```python
@pytest.mark.parametrize("argv,scope", [
    (["inner"], "inner"),
    (["stage", "TEST_DESIGN", "CLARIFY"], "stage"),
    (["workflow", "VALUE_DISCOVERY"], "workflow"),
    (["pr"], "pr"),
    (["nightly"], "nightly"),
    (["release"], "release"),
])
def test_cli_scopes(argv, scope):
    assert parse_scope(argv).name == scope
```

- [x] **Step 2: 运行 RED**

Run: `.venv/bin/python -m pytest -o addopts='' tests/test_new_agents_functional_runner.py -q`

Expected: FAIL，显示尚未接线的命令/marker 契约。

- [x] **Step 3: 最小实现 shell adapter 与子命令执行计划**

`inner` 先运行 matrix/contracts、deterministic live-stack tracer、受影响 backend contract/runtime tests、frontend stream/parser/store tests；没有显式 workflow/stage 时可以运行当前 New Agents deterministic 全量。真实 scope 统一走 `real_llm` marker，并把计划收集数传给报告断言。

- [x] **Step 4: 删除旧 direct-runtime smoke 并同步选择规则**

删除后确认仓库不再有“真实模型缺配置时 pytest skip”的测试路径；现有可选 LLM judge 不属于本 scope，可继续 skip 但文档必须明确它不提供真实 Agent Runtime 证据。

- [x] **Step 5: 运行 GREEN**

Run: `.venv/bin/python -m pytest -o addopts='' tests/test_new_agents_functional_runner.py tests/e2e/new_agents_real/test_contracts.py -q`

Run: `./scripts/test/new-agents-functional.sh inner`

Run: `./scripts/test/test-local.sh e2e`

Expected: runner/contracts PASS；inner PASS；mock browser + deterministic live-stack PASS 且不收集 `real_llm`。

---

### Task 5（内部步骤，非切片）：CI 分层、稳定文档和终态记录

**Files:**
- Modify: `.github/workflows/deploy.yml`
- Modify: `docs/TESTING.md`
- Modify: `docs/todos/archive/2026-07-16-new-agents-streaming-and-artifact-ux.md`
- Modify: `docs/superpowers/plans/2026-07-16-qg020-real-agent-functional-e2e.md`
- Test: `tests/test_new_agents_functional_runner.py`

**Interfaces:**
- CI scope mapping: PR→无 secret deterministic gate，受保护 master schedule→`nightly`，受保护 master push→`release`，受审核 master dispatch→显式 scope。
- Deploy dependency: production deploy 必须 `needs` 真实 release gate。
- Secret source: 只使用两个受保护 environment 内的三个同名 secrets，禁止 repository/organization 层同名 secret。

- [x] **Step 1: 写 CI 静态契约失败测试**

```python
def test_ci_isolates_pr_from_real_model_secrets_and_blocks_deploy():
    workflow = load_workflow(".github/workflows/deploy.yml")
    assert "schedule" in workflow["on"]
    deterministic_job = workflow["jobs"]["new-agents-functional-deterministic-test"]
    assert "NEW_AGENTS_SMOKE" not in repr(deterministic_job)
    real_job = workflow["jobs"]["new-agents-real-functional-test"]
    assert "pull_request" not in real_job["if"]
    assert "refs/heads/master" in real_job["if"]
    assert "github.ref_protected == true" in real_job["if"]
    assert "new-agents-real-manual" in real_job["environment"]["name"]
    assert "env" not in real_job
    real_step = next(
        step for step in real_job["steps"]
        if step["name"] == "🤖 Run headless real-model functional gate"
    )
    assert set(real_step["env"]) == {
        "NEW_AGENTS_REAL_SCOPE",
        "NEW_AGENTS_SMOKE_API_KEY",
        "NEW_AGENTS_SMOKE_BASE_URL",
        "NEW_AGENTS_SMOKE_MODEL",
    }
    assert "new-agents-real-functional-test" in workflow["jobs"]["deploy-to-production"]["needs"]
    upload = next(step for step in real_job["steps"] if "Upload sanitized" in step["name"])
    assert upload["with"]["path"] == "test-results/new-agents-real/*.json"
```

- [x] **Step 2: 运行 RED**

Run: `.venv/bin/python -m pytest -o addopts='' tests/test_new_agents_functional_runner.py -q`

Expected: FAIL，原因是 CI job/schedule/dependency 尚不存在。

- [x] **Step 3: 实现 CI 与 PR secret 隔离**

自动 PR（同仓与 fork）只运行无 secret deterministic job，不收集真实 job，且 `master` ruleset 必须把该 job 设为 required check。真实 job 只接受 `github.ref_protected == true` 的 `master` push/schedule，或同样受保护的 `master` 上经 `new-agents-real-manual` required reviewers 审核的 `workflow_dispatch`。两个 environment 的 deployment branch 只允许 `master`，manual environment 还必须 prevent self-review 且禁止管理员 bypass，三个真实模型 secrets 不存在于 repository/organization 层。如果 GitHub 套餐不支持 required reviewers，manual environment 不配置 secrets，只保留受保护 push/schedule 路径。报告上传使用 JSON 文件 allowlist，上传前要求至少一份 evidence，扫描文件名/内容中的 API key 原值并拒绝其他目录项。

- [x] **Step 4: 更新稳定文档和 todo**

`docs/TESTING.md` 记录命令、evidence levels、headless、执行时机、credential/fork 语义和无截图边界。只有真实 DeepSeek 门禁实际 PASS 后才把 QG-020 标记 `DONE`；若 key 仍缺失，todo 保持 `IN_PROGRESS/BLOCKED` 并记录恢复触发器。

- [x] **Step 5: 运行文档与静态 GREEN**

Run: `.venv/bin/python -m pytest -o addopts='' tests/test_new_agents_functional_runner.py -q`

Run: `git diff --check`

Run: `rg -n 'test_agent_real_smoke|pytest.skip.*DeepSeek|NEW_AGENTS_SMOKE' docs scripts tools/new-agents tests .github`

Expected: CI contract PASS；旧 smoke 执行入口已消失；所有剩余引用都符合统一 runner/凭证语义。

---

## 正式审查与验证门禁

### 厚切片正式审查

- Spec reviewer：逐条对照本 spec 的 stage/workflow scope、真实链路、QG-017/018/019、持久化、失败关闭和 secret 边界。
- Standards reviewer：检查共享 runtime 架构、进程清理、SSE observer 是否只旁路、报告脱敏、CI fork 安全、测试可维护性和无 intent-tester 越界。
- Critical/Important 必须修复并复审；Minor 必须有明确风险、owner 和去向。

### 聚焦与必要跨层验证

- `.venv/bin/python -m pytest -o addopts='' tests/test_new_agents_functional_runner.py tests/e2e/new_agents_real/test_contracts.py -q`
- `cd tools/new-agents/frontend && npm run test -- devServerProxy.test.ts`
- `.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_real/test_live_stack.py -q`
- `./scripts/test/new-agents-functional.sh inner`
- `./scripts/test/test-local.sh e2e`
- `./scripts/test/new-agents-functional.sh pr`：有 key 时必须 PASS；计划执行早期无 key 时准确返回 `NOT_RUN` 且非零，最终受控凭证可用后获得 2/2 PASS。

### 完成型全量与 CI 等价

- `./scripts/test/test-local.sh new-agents`
- `cd tools/new-agents/frontend && npm run lint && npm run build`
- `cd tools/new-agents/backend && ../../../.venv/bin/python -m pytest -m 'not slow' -q`
- `./scripts/test/test-local.sh`
- `.venv/bin/python -m flake8 --select=E9,F63,F7,F82 scripts/test tests/e2e/new_agents_real tools/new-agents/backend`
- `.venv/bin/python -m black --check scripts/test/new_agents_functional.py tests/test_new_agents_functional_runner.py tests/e2e/new_agents_real`
- YAML/JSON 解析、`git diff --check`、staged ownership。

### 交付边界

- 只有全部不可豁免 deterministic/live-stack/CI contract 门禁和真实 `pr` scope 通过，才能将 QG-020 标记 DONE、完成 owning todo 归档事务、形成单一聚焦 commit 并 push。
- 若实现完成但 key 仍缺失：保存 `WAIT` 记录，列出已通过的 evidence level 1–3、真实门禁 `BLOCKED/NOT_RUN`、责任方为用户提供凭证、恢复触发器为三个环境变量可用；不得 commit/push 完成型交付，也不得启动其他 todo。

## Plan 自审

- Spec 的统一入口、stage/workflow 两类场景、真实栈、失败分类、secret、CI 和证据层级均有对应 Task。
- 所有 production/harness 行为都先有具体 RED 命令和预期失败，再有最小实现与 GREEN。
- `RealLlmConfig`、`select_cases`、`LiveStack`、`StageEvidence` 和 `WorkflowEvidence` 的名称在上下游一致。
- Task 是内部纵向 tracer 步骤；首次真实跨层证据位于 Task 2，没有把 E2E 推迟到最后。
