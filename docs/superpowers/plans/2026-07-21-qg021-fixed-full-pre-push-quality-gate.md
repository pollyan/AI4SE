# QG-021 固定全量 Pre-push 质量门禁 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:executing-plans` for inline execution. 本计划的内部步骤不得拆成独立切片、独立交付、独立 commit 或 push。

**Goal:** 让任意 GitHub push 前都由一个固定、fail-closed 的本地命令验证当前 `HEAD`：全仓确定性门禁、隔离 production-shaped Compose、部署栈真实 DeepSeek 7-workflow E2E、脱敏证据和工作区清理全部通过才允许 push。

**Architecture:** 新增 Python canonical runner 负责前置检查、固定 suite registry、结果/evidence、工作区基线和最终裁决；shell 与 Git hook 只调用它。独立 Compose harness 以 project name、loopback 端口、临时 env/volume/network 启动 `docker-compose.prod.yml` 的叠加形态；真实模型 runner 增加一个只能访问该本地 Nginx target 的 `DeployedStack`，沿用既有 7/25 workflow 断言与脱敏报告，不复制 Agent Runtime、SSE 或浏览器断言逻辑。

**Tech Stack:** Python 3.11、pytest、Playwright Chromium、Docker Compose、PostgreSQL 15、Gunicorn、Nginx、React/Vite、Vitest、Jest、Git hooks。

## 全局约束

- 固定入口是 `./scripts/test/pre-push.sh`；不得接收 diff/path/Agent scope，也不得有 skip、fallback-to-green 或 retry-to-green 参数。
- 本轮是 `QG-021` 的内部实施步骤（非切片）；唯一顺序基线为 [历史待办](../../todos/archive/2026-07-21-pre-push-full-validation-and-release-safety.md)，身份基线为 [QG-021 spec](../specs/2026-07-21-fixed-full-pre-push-quality-gate-design.md#厚切片身份基线)。
- 不读取、修改、暂存或清理用户已有的 `tools/intent-tester/test-results/proxy/junit.xml`。
- canonical runner 不安装依赖、不改 lockfile、不使用系统 Python 兼容降级；缺少 `.venv`、Node modules、Docker/Compose、Chromium 或真实模型配置必须输出非 `PASS` 并返回非零。
- 生产 Compose overlay 使用 Compose `!override` 合并标签；preflight 必须要求 Docker Compose v2.24.4 或更新版本，避免旧版本把 base 的 `80:80` 端口与 loopback port 同时保留。
- 测试 artifacts 只能写入 Git ignored 的 `test-results/pre-push/<head>/`，且报告不得包含 API key、provider URL、admin/proxy key、prompt 原文、浏览器 storage 或原始日志。
- QG-021 只验证本机隔离部署；不得修改生产 rsync、线上切换、rollback 或生产 health script 的事务语义，这些是 QG-022。
- 任何新生产行为先写失败测试并观察正确失败，再写最小实现；最终只创建一个 QG-021 聚焦提交。

---

## 文件所有权与接口冻结

| 路径 | 责任 |
| --- | --- |
| `scripts/test/pre_push.py` | 固定 phase registry、前置检查、子命令执行、`HEAD`/工作区 freshness、脱敏 summary 与最终非零裁决。 |
| `scripts/test/pre_push_deployment.py` | 生成仅含临时凭证的 Compose env、隔离 project/port、`config/build/up/readiness/restart/down` 生命周期。 |
| `scripts/test/pre-push.sh`、`.githooks/pre-push`、`scripts/dev/install-git-hooks.sh` | 不含业务逻辑的 canonical CLI 与 versioned hook 安装。 |
| `docker-compose.pre-push.yml` | 覆盖 production Compose 的 container/network/volume/loopback port 与 common frontend build mount，不影响默认 production 名称。 |
| `tests/e2e/new_agents_real/deployed_stack.py` | 本地 Nginx target 的 secret-free Playwright 生命周期和受控 backend restart。 |
| `tests/e2e/new_agents_real/{config.py,conftest.py,reporting.py,workflow_runner.py}` | 选择 LiveStack 或 DeployedStack、报告根目录、恢复前 restart hook；保留同一 workflow assertion。 |
| `tests/test_pre_push_gate.py`、`tests/test_pre_push_deployment.py`、`tests/e2e/new_agents_real/test_deployed_stack.py` | 新 runner、部署隔离与 target/E2E 回归。 |
| `scripts/test/test-local.sh`、`scripts/test/new_agents_functional.py`、`tools/intent-tester/jest.config.js` | 消除重复调度并确保 JUnit/coverage 不写入 tracked 用户路径。 |
| `AGENTS.md`、`docs/TESTING.md`、`docs/deployment-guide.md`、`.github/workflows/deploy.yml` | 同步 fixed pre-push 语义、CI 关系和本地 hook 安装说明。 |

### 高风险契约冻结检查点（仅一次，非切片）

在 Task 3 的 RED/GREEN 完成后，主 Agent 审查下列不变量再继续：Compose 只能 bind loopback；临时 env 只写入受限权限的 output 目录；provider/admin/proxy 三类密钥独立且不进入 browser；overlay 不能改变默认 `docker-compose.prod.yml` 的生产 container/network/volume 名称；target URL 只能是 loopback 的 `/new-agents/` 根。若任一不成立，留在本任务修复，不以 checkpoint 形式提交或交付。

## 内部 Task 1：固定入口的 fail-closed 基线（非切片）

**Files:**

- Create: `scripts/test/pre_push.py`
- Create: `scripts/test/pre-push.sh`
- Create: `tests/test_pre_push_gate.py`

**Interfaces:**

- Produces `PrePushContext.create(root: Path, environ: Mapping[str, str]) -> PrePushContext`，包含固定 `head`, `output_dir`, `initial_status`。
- Produces `GateOutcome(phase: str, suite_id: str, status: Literal["PASS", "FAIL", "NOT_RUN", "BLOCKED", "TIMEOUT", "FLAKY"], collected: int, executed: int, reason: str)`。
- Produces `run_pre_push(root: Path, environ: Mapping[str, str]) -> int`；只接受完整固定 sequence，不接收范围参数。

- [x] **Step 1: 先写失败测试，锁定 CLI 与当前 `HEAD` 基线。**

```python
def test_pre_push_rejects_scope_arguments_and_records_the_starting_head(tmp_path, monkeypatch):
    runner = load_pre_push_module()
    monkeypatch.setattr(runner, "git_head", lambda _root: "a" * 40)

    context = runner.PrePushContext.create(tmp_path, {"PATH": "/bin"})

    assert context.head == "a" * 40
    assert context.output_dir == tmp_path / "test-results" / "pre-push" / ("a" * 40)
    with pytest.raises(SystemExit):
        runner.parse_args(["--scope", "frontend"])


def test_non_pass_or_head_change_makes_the_final_verdict_nonzero(tmp_path, monkeypatch):
    runner = load_pre_push_module()
    context = runner.PrePushContext.create(tmp_path, {"PATH": "/bin"})
    monkeypatch.setattr(runner, "git_head", lambda _root: "changed-head")

    assert runner.finalize(context, [runner.passing_outcome("static")]) == 1
```

- [x] **Step 2: 运行测试并确认 RED。**

Run: `.venv/bin/python -m pytest tests/test_pre_push_gate.py -q`

Expected: FAIL，因为 `pre_push.py`、`PrePushContext`、`finalize` 尚不存在。

- [x] **Step 3: 实现最小无范围入口。**

```python
NON_PASS = frozenset({"FAIL", "NOT_RUN", "BLOCKED", "TIMEOUT", "FLAKY"})


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(list(argv))
    return argparse.Namespace()


@dataclass(frozen=True)
class PrePushContext:
    root: Path
    head: str
    output_dir: Path
    initial_status: tuple[str, ...]

    @classmethod
    def create(cls, root: Path, environ: Mapping[str, str]) -> "PrePushContext":
        head = git_head(root)
        return cls(root, head, root / "test-results" / "pre-push" / head, git_status(root))


def finalize(context: PrePushContext, outcomes: Sequence[GateOutcome]) -> int:
    if git_head(context.root) != context.head or has_new_worktree_entries(context):
        return 1
    return int(any(outcome.status in NON_PASS for outcome in outcomes))
```

`pre-push.sh` 只执行 `exec "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/scripts/test/pre_push.py" "$@"`，并在 `.venv/bin/python` 不存在时以 `BLOCKED` 退出，不改用 `python3`。

- [x] **Step 4: 运行 GREEN 与静态检查。**

Run: `.venv/bin/python -m pytest tests/test_pre_push_gate.py -q && bash -n scripts/test/pre-push.sh`

Expected: PASS。

## 内部 Task 2：唯一 suite registry、结果 journal 与去重（非切片）

**Files:**

- Modify: `scripts/test/pre_push.py`
- Create: `docs/test_requirements/2026-07-21-qg021-suite-ownership.md`
- Modify: `scripts/test/test-local.sh`
- Modify: `scripts/test/new_agents_functional.py`
- Modify: `scripts/test/verification_outcomes.py`
- Modify: `tools/intent-tester/jest.config.js`
- Modify: `tests/test_pre_push_gate.py`
- Modify: `tests/test_new_agents_functional_runner.py`
- Modify: `tests/test_verification_outcomes.py`

**Interfaces:**

- `fixed_suites(context) -> tuple[SuiteSpec, ...]` has exactly one command owner per `suite_id` and fixed phase order `static`, `deterministic`, `deployment`, `real_e2e`, `finalize`.
- `SuiteSpec` carries `suite_id`, `phase`, `invariants`, `evidence_level`, `external_dependency`, `canonical_owner` and `disposition` (`KEEP`/`MOVE`/`MERGE`/`DELETE`); the ownership document is rendered from this registry rather than maintained as a second hand-written list.
- `run_suite(spec, context) -> GateOutcome` invokes `verification_outcomes.py run`, preserves `NOT_RUN`/`TIMEOUT`, and writes one sanitized JSON journal entry.
- `test-local.sh all` remains a developer convenience command but does not recursively invoke canonical pre-push or real-model `release`; `new_agents_functional.py inner` no longer repeats suites owned by canonical fixed registry.

- [x] **Step 1: 写失败测试，先规定 unique ownership 和非零收集。**

```python
def test_fixed_suite_registry_has_one_owner_and_full_required_coverage(tmp_path):
    runner = load_pre_push_module()
    suites = runner.fixed_suites(runner.PrePushContext.create(tmp_path, {"PATH": "/bin"}))

    assert [suite.phase for suite in suites] == ["static", "deterministic"]
    assert len({suite.suite_id for suite in suites}) == len(suites)
    assert {suite.suite_id for suite in suites} >= {
        "intent-tester-api", "intent-proxy",
        "common-frontend-lint", "common-frontend-build",
        "new-agents-frontend-lint", "new-agents-frontend-test", "new-agents-frontend-build",
        "new-agents-backend", "new-agents-runner-contracts", "new-agents-live-stack",
        "ci-deploy-hardening", "verification-outcomes", "docs-links",
    }
    assert all(suite.invariants and suite.canonical_owner for suite in suites)
    assert {suite.disposition for suite in suites} >= {"KEEP", "MOVE", "MERGE"}


def test_jest_junit_output_is_taken_from_the_pre_push_artifact_directory():
    source = (ROOT / "tools/intent-tester/jest.config.js").read_text(encoding="utf-8")
    assert "JEST_JUNIT_OUTPUT_DIR" in source
```

- [x] **Step 2: 确认 RED。**

Run: `.venv/bin/python -m pytest tests/test_pre_push_gate.py tests/test_new_agents_functional_runner.py -q`

Expected: FAIL，因为 registry、唯一 owner 和可重定向 JUnit 尚未存在。

- [x] **Step 3: 实现 registry 与无污染调度。**

`SuiteSpec` 固定使用以下真实命令（由 `run_suite` 以绝对路径、隔离 env 和显式 timeout 调用）：

```python
static = (
    command("docs-links", "command", ("bash", "scripts/test/check-docs.sh")),
    command("intent-tester-critical-lint", "command", (python, "-m", "flake8", "tools/intent-tester/backend", "--select=E9,F63,F7,F82")),
    command("intent-tester-api", "pytest", (python, "-m", "pytest", "tools/intent-tester/tests", "-q", "--cov=tools/intent-tester/backend", "--cov-fail-under=50", "--cov-report=term")),
    command("intent-proxy", "jest", ("npx", "jest", "tests/proxy", "--runInBand"), cwd="tools/intent-tester"),
    command("common-frontend-lint", "command", ("npm", "run", "lint"), cwd="tools/frontend"),
    command("common-frontend-build", "command", ("npm", "run", "build", "--", "--outDir", str(context.output_dir / "common-frontend-dist")), cwd="tools/frontend"),
    command("new-agents-frontend-lint", "command", ("npm", "run", "lint"), cwd="tools/new-agents/frontend"),
    command("new-agents-frontend-test", "vitest", ("npm", "run", "test"), cwd="tools/new-agents/frontend"),
    command("new-agents-frontend-build", "command", ("npm", "run", "build", "--", "--outDir", str(context.output_dir / "new-agents-frontend-dist")), cwd="tools/new-agents/frontend"),
    command("new-agents-backend", "pytest", (python, "-m", "pytest", "-m", "not slow", "-q"), cwd="tools/new-agents/backend"),
)
```

deterministic phase 固定只调用一次 root `tests/test_new_agents_functional_runner.py`、`tests/test_verification_outcomes.py`、`tests/test_ci_deploy_hardening.py`、`tests/e2e/new_agents_real/test_contracts.py`、`tests/e2e/new_agents_real/test_live_stack.py` 和现有 mock-browser suite；从 `new_agents_functional.py inner` 移除与上述重复的 frontend/backend/LiveStack 调度，保留其作为明确的 deterministic contract entrypoint。

`run_suite` 必须设置 `COVERAGE_FILE=<output>/coverage/.coverage`、`JEST_JUNIT_OUTPUT_DIR=<output>/intent-proxy/junit`、`PYTEST_ADDOPTS=-p no:cacheprovider`，把每个 child 的 stdout/stderr 先 capture、redact，再写 `<output>/outcomes/<phase>-<suite>.json`。任何无法解析的成功测试输出、零收集、超时或子进程无法启动均产出非 `PASS`。

从 `fixed_suites` 渲染 `docs/test_requirements/2026-07-21-qg021-suite-ownership.md`：每行必须列出 suite ID、保护的不变量、证据层、真实/替身外部边界、canonical owner、耗时类别与处置。现有 Intent API/coverage、proxy、Common frontend、New Agents frontend/backend、root runner/contracts/outcomes/hardening、mock browser、LiveStack、real `release` 和 Nightly 独立 stage probe 都必须有一行。`test-local all`/`inner` 的重复调用标为 `MERGE` 并从 canonical pre-push 调度中移除；Nightly 标为 `KEEP` 但明确不是 pre-push 的第二份 release；没有独有不变量的候选只有在替代 gate mutation 已经失败后才可标为 `DELETE`。

- [x] **Step 4: 运行 GREEN 与既有回归。**

Run: `.venv/bin/python -m pytest tests/test_pre_push_gate.py tests/test_new_agents_functional_runner.py tests/test_verification_outcomes.py -q`

Expected: PASS；并且现有 `inner` 测试明确证明不再嵌套重复 frontend/backend/LiveStack。

## 内部 Task 3：隔离 production-shaped Compose 生命周期（非切片）

**Files:**

- Create: `scripts/test/pre_push_deployment.py`
- Create: `docker-compose.pre-push.yml`
- Create: `tests/test_pre_push_deployment.py`
- Modify: `scripts/test/pre_push.py`

**Interfaces:**

- `DeploymentConfig.create(context, llm_config) -> DeploymentConfig` 生成随机 `project_name`、loopback port、temporary env file、temporary output paths 和独立 provider/admin/proxy keys。
- `ProductionHarness.start()`, `.assert_ready()`, `.restart_backend()`, `.close()` 仅允许 `docker compose -p <project> -f docker-compose.prod.yml -f docker-compose.pre-push.yml --env-file <temp>`。
- `DeploymentTarget.frontend_url` 格式固定为 `http://127.0.0.1:<port>/new-agents/`。

- [x] **Step 1: 写失败测试，规定隔离和 ready 不依赖固定 `/health`。**

```python
def test_deployment_config_never_reuses_production_names_or_public_ports(tmp_path):
    deployment = load_deployment_module().DeploymentConfig.create(
        root=tmp_path, output_dir=tmp_path / "test-results", llm_config=fake_llm_config()
    )

    assert deployment.project_name.startswith("ai4se-pre-push-")
    assert deployment.gateway_port != 80
    assert deployment.frontend_url.startswith("http://127.0.0.1:")
    assert deployment.env_path.parent == deployment.output_dir


def test_readiness_requires_new_agents_page_backend_and_database_not_static_gateway(monkeypatch):
    harness = fake_harness()
    monkeypatch.setattr(harness, "request", lambda path, **_: fake_response(path))

    harness.assert_ready()

    assert "/new-agents/" in harness.checked_paths
    assert "/new-agents/api/health" in harness.checked_paths
    assert "/health" not in harness.checked_paths


def test_rendered_overlay_has_exactly_one_loopback_gateway_port():
    rendered = render_pre_push_compose(fake_deployment_config())
    assert rendered["services"]["nginx"]["ports"] == ["127.0.0.1:18080:80"]
```

- [x] **Step 2: 运行 RED。**

Run: `.venv/bin/python -m pytest tests/test_pre_push_deployment.py -q`

Expected: FAIL，因为隔离 harness 和 overlay 尚不存在。

- [x] **Step 3: 实现 overlay 与 harness。**

`docker-compose.pre-push.yml` 必须只覆盖以下 production service 运行身份：

```yaml
services:
  postgres:
    container_name: "${PRE_PUSH_PROJECT_NAME:?}-postgres"
  intent-tester:
    container_name: "${PRE_PUSH_PROJECT_NAME:?}-intent-tester"
  new-agents:
    container_name: "${PRE_PUSH_PROJECT_NAME:?}-new-agents"
  new-agents-backend:
    container_name: "${PRE_PUSH_PROJECT_NAME:?}-new-agents-backend"
  nginx:
    container_name: "${PRE_PUSH_PROJECT_NAME:?}-nginx"
    ports: !override
      - "127.0.0.1:${PRE_PUSH_GATEWAY_PORT:?}:80"
    volumes: !override
      - "${PRE_PUSH_COMMON_FRONTEND_DIST:?}:/app/tools/frontend/dist:ro"
volumes:
  postgres_data:
    name: "${PRE_PUSH_PROJECT_NAME:?}-postgres-data"
networks:
  ai4se-network:
    name: "${PRE_PUSH_PROJECT_NAME:?}-network"
```

Harness 以 `os.open(..., 0o600)` 写临时 env，填充隔离 PostgreSQL、Intent dummy 值、来自 `RealLlmConfig.backend_environment()` 的 provider 值以及独立随机 `NEW_AGENTS_CONFIG_ADMIN_API_KEY`/`PROXY_API_KEY`。它按顺序运行 `config --quiet`、`build`、`up --wait`、页面/后端/DB readiness、`restart new-agents-backend`、相同 readiness、`down --volumes --remove-orphans`；finally 永远执行 `down` 并把 cleanup failure 作为非 `PASS` 记录。Nginx readiness 必须验证 `/new-agents/` HTML、`/new-agents/api/health` JSON 和 PostgreSQL `pg_isready`，不用 `/health` 的固定 200。

- [x] **Step 4: 运行 GREEN 和契约冻结检查点。**

Run: `.venv/bin/python -m pytest tests/test_pre_push_deployment.py tests/test_ci_deploy_hardening.py -q`

Expected: PASS。随后按本计划“高风险契约冻结检查点”逐项审查 overlay、env 和 target contract，发现问题立即在本 Task 修复。

## 内部 Task 4：部署栈真实 DeepSeek E2E 与重启恢复（非切片）

**Files:**

- Create: `tests/e2e/new_agents_real/deployed_stack.py`
- Create: `tests/e2e/new_agents_real/test_deployed_stack.py`
- Modify: `tests/e2e/new_agents_real/config.py`
- Modify: `tests/e2e/new_agents_real/conftest.py`
- Modify: `tests/e2e/new_agents_real/reporting.py`
- Modify: `tests/e2e/new_agents_real/workflow_runner.py`
- Modify: `scripts/test/new_agents_functional.py`
- Modify: `tests/test_new_agents_functional_runner.py`

**Interfaces:**

- `DeploymentTarget.parse(value: str) -> DeploymentTarget` 接受且仅接受 loopback HTTP(S) URL，路径必须为 `/new-agents/`；拒绝 credentials、query、fragment、remote host 或任意非该前缀路径，并以 `DeploymentTargetError` 显式失败。
- `DeploymentControl.from_environment(root, environ) -> DeploymentControl` 只接受由 pre-push harness 写出的、位于当前 evidence root 内的 control descriptor；它用固定 compose files、project-name regex 和该 0600 env file 重建受控 backend restart，不接受任意命令或任意 env path。
- `DeployedStack(root, llm_config, target, control)` 暴露与 `LiveStack` 相同的 `root`, `llm_config`, `frontend_url`, `page`, `redaction_secrets()`、context manager；它不启动 Flask/Vite/SQLite，也不把 secret 传入 Chromium。
- `NEW_AGENTS_REAL_TARGET_URL` 为空时沿用 `LiveStack`；存在时 `release` 继续从 manifest 派生 7 个 workflow 和 25 stages，但浏览器仅访问 deployed target。
- `NEW_AGENTS_REAL_EVIDENCE_DIR` 只允许 `test-results/pre-push/<HEAD>/real-e2e` 的绝对子目录；`report_path` 在其下写入脱敏 JSON。

- [x] **Step 1: 写失败测试，规定 target 安全、真实 target 选择和 restart 后恢复。**

```python
@pytest.mark.parametrize("value", [
    "https://remote.example/new-agents/",
    "http://127.0.0.1:8080/other/",
    "http://user:secret@127.0.0.1:8080/new-agents/",
])
def test_deployment_target_rejects_non_loopback_or_non_workspace_urls(value):
    with pytest.raises(DeploymentTargetError):
        DeploymentTarget.parse(value)


def test_real_fixture_selects_deployed_stack_without_starting_live_processes(monkeypatch):
    monkeypatch.setenv("NEW_AGENTS_REAL_TARGET_URL", "http://127.0.0.1:18080/new-agents/")
    monkeypatch.setenv("NEW_AGENTS_REAL_DEPLOYMENT_CONTROL_FILE", str(control_file()))
    stack = build_real_stack(ROOT, fake_llm_config(), environ=os.environ)

    assert isinstance(stack, DeployedStack)
    assert stack.frontend_url.endswith("/new-agents/")


def test_workflow_restore_runs_after_deployed_backend_restart():
    stack = fake_deployed_stack()
    run_stage_probe(stack, fixture_case(), "prompt", restart_after_snapshot=True)

    assert stack.restart_calls == 1
    assert stack.restore_happened_after_restart is True
```

- [x] **Step 2: 运行 RED。**

Run: `.venv/bin/python -m pytest tests/e2e/new_agents_real/test_deployed_stack.py tests/test_new_agents_functional_runner.py -q`

Expected: FAIL，因为 target contract、DeployedStack 和 restart hook 尚不存在。

- [x] **Step 3: 最小实现并复用既有断言。**

`DeployedStack.__enter__` 使用 `start_secret_free_playwright(sync_playwright, os.environ)` 与 `build_secret_free_browser_environment(...)`，在 `frontend_url` 先验证页面与 `/new-agents/api/health`，然后创建 Chromium context/page 并安装既有 `stream_observer`。不复制 `run_stage_probe`、`run_workflow_journey`、`assert_stage_trace`、`assert_snapshot` 或 UI selector。

`workflow_runner` 在每个 workflow 的第一个已完成 snapshot 后，仅当 target stack 的 `DeploymentControl` 存在且 `NEW_AGENTS_REAL_VERIFY_RESTART=1` 时调用一次受控 `restart_backend()`，等待 target readiness，再执行既有清空 localStorage、`?runId=` restore 断言。control descriptor 只含 project identity、compose env file 路径和 target，不含 provider/admin/proxy secret 或 shell command。这样 release 同时证明 Nginx→Gunicorn→PostgreSQL、真实 provider、SSE、artifact persistence 与 backend restart 后恢复。

`new_agents_functional.py` 的 `release` command 只在三个 internal environment values 同时存在时启用部署 target：`NEW_AGENTS_REAL_TARGET_URL`、`NEW_AGENTS_REAL_EVIDENCE_DIR`、`NEW_AGENTS_REAL_DEPLOYMENT_CONTROL_FILE`。它们由 `ProductionHarness` 在同一 output root 中生成；普通 `stage/workflow/pr/nightly/release` 保持 LiveStack 行为，任何远程 URL、缺 control descriptor 或越界 evidence path 都显式失败。

- [x] **Step 4: 运行 GREEN。**

Run: `.venv/bin/python -m pytest tests/e2e/new_agents_real/test_deployed_stack.py tests/test_new_agents_functional_runner.py tests/e2e/new_agents_real/test_contracts.py -q`

Expected: PASS；现有 LiveStack scopes 仍通过，新的 target path 被测试证明不能泄露凭证或接受非 loopback URL。

## 内部 Task 5：把 deployment 与真实 E2E 接入一个 canonical verdict（非切片）

**Files:**

- Modify: `scripts/test/pre_push.py`
- Modify: `scripts/test/pre_push_deployment.py`
- Modify: `tests/test_pre_push_gate.py`
- Modify: `tests/test_pre_push_deployment.py`
- Modify: `tests/test_verification_outcomes.py`
- Create: `.githooks/pre-push`
- Create: `scripts/dev/install-git-hooks.sh`

**Interfaces:**

- `run_pre_push()` 固定按 `preflight → static → deterministic → deployment → real_e2e → finalization` 运行；它可以 fail-fast，但不能把未运行 phase 表示为 PASS。
- deployment phase 成功后把 `DeploymentTarget` 注入 `new-agents-functional.sh release`；任何 child 非 PASS、evidence secret scan failure、cleanup failure、`HEAD`/worktree 新增污染均令最终返回非零。
- `.githooks/pre-push` 只能 `exec ./scripts/test/pre-push.sh`；安装脚本只执行 `git config --local core.hooksPath .githooks`。

- [x] **Step 1: 写失败测试，锁定完整 phase 链和 hook。**

```python
def test_canonical_run_orders_all_phases_and_never_runs_real_e2e_before_deployment(monkeypatch, tmp_path):
    runner = load_pre_push_module()
    observed: list[str] = []
    monkeypatch.setattr(runner, "run_phase", lambda phase, *_: observed.append(phase.name) or runner.passing_outcome(phase.name))

    assert runner.run_pre_push(tmp_path, {"PATH": "/bin"}) == 0
    assert observed == ["preflight", "static", "deterministic", "deployment", "real_e2e", "finalization"]


def test_versioned_git_hook_executes_only_the_canonical_runner():
    hook = (ROOT / ".githooks/pre-push").read_text(encoding="utf-8")
    assert "scripts/test/pre-push.sh" in hook
    assert "git push" not in hook
    assert "--scope" not in hook
```

- [x] **Step 2: 运行 RED。**

Run: `.venv/bin/python -m pytest tests/test_pre_push_gate.py tests/test_pre_push_deployment.py -q`

Expected: FAIL，因为完整 phase orchestration 与 versioned hook 未实现。

- [x] **Step 3: 实现 full chain、evidence 和 cleanup。**

`run_pre_push` 在 preflight 写 `<output>/summary.json` 初稿，依次追加每个 `GateOutcome` 的 suiteId/status/count/duration；从 `ProductionHarness` 获得 target 后以 `NEW_AGENTS_REAL_SCOPE=release` 调用真实 runner。它必须在 `finally` 关闭 harness，递归读取 output 中的文本/JSON，以 `RealLlmConfig.redaction_secrets()`、临时 admin/proxy keys 及 sensitive-key schema 扫描；任何命中或无法扫描都生成 `FAIL`。最终对比 `git status --porcelain=v1 -uall` 与初始快照，只允许 output root 内的 ignored artifacts，且不触碰初始 dirty JUnit。

hook 安装脚本先验证仓库根和 hook 文件存在，再设置 local config；它不修改 global config。`pre-push.sh` 没有参数时运行完整命令，有任意参数时返回 usage error，确保 hook 和人工运行同一范围。

- [x] **Step 4: 运行 GREEN。**

Run: `.venv/bin/python -m pytest tests/test_pre_push_gate.py tests/test_pre_push_deployment.py tests/test_verification_outcomes.py -q && bash -n scripts/test/pre-push.sh .githooks/pre-push scripts/dev/install-git-hooks.sh`

Expected: PASS；mutation tests 还必须覆盖缺 `.venv`、缺 Docker、缺三个模型变量、零收集、child timeout、Compose cleanup failure、重复 suite id、secret evidence、`HEAD` 变化和新增 tracked/untracked 路径均非零。

## 内部 Task 6：文档、CI 关系与最终验证（非切片）

**Files:**

- Modify: `AGENTS.md`
- Modify: `docs/TESTING.md`
- Modify: `docs/deployment-guide.md`
- Modify: `.github/workflows/deploy.yml`
- Move: `docs/todos/2026-07-21-pre-push-full-validation-and-release-safety.md` → `docs/todos/archive/2026-07-21-pre-push-full-validation-and-release-safety.md`
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/superpowers/specs/2026-07-21-fixed-full-pre-push-quality-gate-design.md`
- Create: `docs/test_requirements/2026-07-21-qg021-validation-record.md`

**Interfaces:**

- 文档唯一声明：开发者 push 前运行 `./scripts/dev/install-git-hooks.sh` 一次，再由 `.githooks/pre-push` 调用 `./scripts/test/pre-push.sh`；CI 是远端复验和生产部署前置，不是第一次真实验证。
- CI 增加 runner/hook contract job，固定执行 QG-021 deterministic contract tests；它不把本地 Docker/真实模型 gate 静默降级成绿色。

- [x] **Step 1: 写失败文档/CI 一致性测试。**

```python
def test_repository_documents_and_ci_reference_the_fixed_pre_push_contract():
    for path in (ROOT / "AGENTS.md", ROOT / "docs/TESTING.md", ROOT / "docs/deployment-guide.md"):
        assert "scripts/test/pre-push.sh" in path.read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    assert "tests/test_pre_push_gate.py" in workflow
    assert "tests/test_pre_push_deployment.py" in workflow
```

- [x] **Step 2: 运行 RED。**

Run: `.venv/bin/python -m pytest tests/test_ci_deploy_hardening.py tests/test_pre_push_gate.py -q`

Expected: FAIL，因为文档和 CI contract job 尚未同步。

- [x] **Step 3: 同步事实源并运行完成型验证。**

更新 todo：QG-021 保持 `IN_PROGRESS` 直到下列全部 evidence 对最终 `HEAD` 为 PASS；不要将内部 Task 写成额外进度。更新 spec 以最终命令、suite owner 表与实际 evidence location 为准。验证记录必须列出每个 phase、命令、结果、时间、`HEAD`、Docker target、清理结果、真实 `release` 7/7 workflow、25/25 stage、18 transition、失败/波动策略和未运行项；不得复制 API key 或原始 prompt。

先运行聚焦测试：

```bash
.venv/bin/python -m pytest \
  tests/test_pre_push_gate.py \
  tests/test_pre_push_deployment.py \
  tests/e2e/new_agents_real/test_deployed_stack.py \
  tests/test_new_agents_functional_runner.py \
  tests/test_ci_deploy_hardening.py \
  tests/test_verification_outcomes.py -q
```

再从最终 `HEAD` 运行唯一完成型门禁：

```bash
./scripts/dev/install-git-hooks.sh
./scripts/test/pre-push.sh
```

只有该命令所有 phase PASS、Docker 资源已清理、`git diff --check` 通过、工作区相对起点无新增污染、正式审查关闭 Critical/Important 发现后，才更新 QG-021 为 `DONE`、把 QG-022 设为当前入口，并创建唯一的 QG-021 聚焦提交。此后从 `BOOTSTRAP` 重新读取生产事实，再进入 QG-022 自己的 `ASSESS/DESIGN/PLAN`；不得借用本计划直接实施 QG-022。

- [ ] **Step 4: 计划自审。**

逐条对照 QG-021 spec 第 4、5、7、8 节与活动待办验收：确认每条都映射到上述 Task；按 Writing Plans skill 的 placeholder 词表扫描本文件，发现未决占位表达即改写为明确路径、接口和命令；确认所有内部 Task 均标注“非切片”。
