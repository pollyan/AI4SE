# QG-022 可信生产发布事务与完整 Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for inline task-by-task execution. Steps use checkbox (`- [ ]`) syntax for tracking. 本仓库 Goal Mode 将整份计划作为一个厚切片；内部 Task 不是独立交付、commit 或 push。

**Goal:** 以 immutable SHA release、构建前预检、受控切换、可证明 rollback 和完整 New Agents readiness 替代生产环境的原地覆盖、先停服构建与浅健康检查。

**Architecture:** GitHub package 携带 SHA 与内容摘要 manifest；远端的 `release_transaction.py` 在锁内 materialize 不可变 release、生成私有 env、记录 source/config/image identity，并在不影响 current 时 build/preflight。只有 candidate 准备完成后才原子换 `current` 并重建唯一 Compose 项目；任一切换/readiness 失败以 previous identity 重建并复验。New Agents backend 提供 DB-backed JSON readiness 与一帧 SSE probe，release runner 从 gateway 验证页面/upstream/DB/SSE，再把安全 state 写回 release directory。

**Tech Stack:** Python 3.11 standard library (`fcntl`、`hashlib`、`subprocess`、`urllib`)、Bash invocation、Docker Compose v2、GitHub Actions、Flask/SQLAlchemy、Nginx、PostgreSQL、pytest。

## Global Constraints

- 只发布 protected GitHub SHA；release ID 必须为 40 位小写 hexadecimal，manifest source digest 必须由 remote 重算。
- 所有 production transaction 输出只能含 SHA、hash、phase、service 名与安全错误码；不得写入或打印 `.env`、provider/LLM 值、SSH 凭据、完整 HTTP body 或 Docker logs。
- `current` 必须是指向有 `release-state.json` 的可信 release symlink；缺可信 previous 时只允许 prepare，禁止切换。
- candidate build/config/image preflight 不得运行 `down`、按名称扫描删除容器/network/image，或写入 current；所有 mutation 只针对 `ai4se` Compose project。
- activation 与 rollback 必须使用相同 release 的 Compose directory、private env、recorded image IDs，并在完成后执行同一 readiness；rollback command 成功不是成功条件。
- GitHub `concurrency.cancel-in-progress` 必须为 `false`；remote 再通过 `flock` 阻止手工或异常重试重叠。
- New Agents readiness 不调用真实模型、不写业务数据、不返回 credential；SSE probe 使用既有 typed `run_started` event + `[DONE]`，并使用 `text/event-stream`、`Cache-Control: no-cache`、`X-Accel-Buffering: no`。
- 不读取、修改、暂存、清理或提交 `tools/intent-tester/test-results/proxy/junit.xml`。
- 本轮结束前以当前 HEAD 在隔离干净检出执行 `./scripts/test/pre-push.sh`；不 push，不执行真实生产发布。

---

## 文件所有权与接口冻结

| 路径 | 责任 |
| --- | --- |
| `scripts/ci/release_transaction.py` | manifest、锁、immutable release、Compose command、identity、activation/rollback/readiness 的唯一 production transaction owner |
| `tests/test_release_transaction.py` | fake command/http runner 下的 deterministic release transaction 与故障 mutation |
| `tools/new-agents/backend/routes.py` | safe DB-backed JSON/SSE readiness HTTP contract |
| `tools/new-agents/backend/tests/test_readiness_endpoint.py` | readiness DB 成功/失败与 SSE header/body contract |
| `docker-compose.prod.yml` | release-tagged build image and production service contract |
| `.github/workflows/deploy.yml` | protected SHA package manifest、unique staging、concurrency 与 remote transaction invocation |
| `scripts/ci/deploy.sh` | 保留 local/dev 行为；production legacy path fail-closed，不能成为 transaction bypass |
| `scripts/health/health_check.sh` | 退役为 local/dev diagnostics，不再是 production release verdict |
| `tests/test_ci_deploy_hardening.py` | workflow/Compose/legacy deployment fail-closed static contracts |
| `docs/deployment-guide.md` | production operator layout、trusted bootstrap、success/rollback evidence 与 no-secret observability |

### 高风险契约冻结检查点（仅一次，非切片）

在 Task 1 GREEN 后冻结 `ReleaseManifest`、`ReleaseState`、`ReleasePaths`、`ReleaseFailure` 和 `CommandRunner` 接口。后续 workflow、Compose 和 readiness 只能消费这些公开字段，不得再创建第二套 release identity 或绕过 `ReleaseTransaction.run()` 的 activation path。

## 内部 Task 1：Release identity 与 transaction 核心（非切片）

**Files:**

- Create: `scripts/ci/release_transaction.py`
- Create: `tests/test_release_transaction.py`

**Interfaces:**

- Produces `ReleaseManifest.load_and_verify(root: Path, release_id: str) -> ReleaseManifest`，验证 `release-manifest.json` 的 `schemaVersion == 1`、`releaseId` 和 `sourceDigest`。
- Produces `tree_digest(root: Path) -> str`，按 UTF-8 relative path + file SHA-256 的排序列表计算，忽略 `release-manifest.json`、`.env`、`release-state.json`。
- Produces `ReleaseState(release_id, source_digest, compose_digest, env_digest, image_ids, phase)` 和 `ReleaseState.load(path) -> ReleaseState`。
- Produces `ReleasePaths.from_root(root, release_id, upload_dir) -> ReleasePaths`，目录固定为 `uploads/`、`releases/`、`current`、`.release.lock`。
- Produces `ReleaseFailure(code: str)`；错误码仅可为 `INVALID_MANIFEST`、`UNTRUSTED_PREVIOUS`、`LOCKED`、`PREPARE_FAILED`、`ACTIVATION_FAILED`、`READINESS_FAILED`、`ROLLBACK_FAILED`、`IDENTITY_MISMATCH`。

- [x] **Step 1: Write the failing identity tests**

```python
def test_manifest_rejects_sha_or_content_digest_mismatch(tmp_path):
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "app.txt").write_text("candidate", encoding="utf-8")
    write_manifest(upload, release_id="a" * 40, source_digest="0" * 64)

    with pytest.raises(ReleaseFailure, match="INVALID_MANIFEST"):
        ReleaseManifest.load_and_verify(upload, "a" * 40)


def test_untrusted_previous_stops_before_any_compose_command(tmp_path):
    runner = RecordingRunner()
    transaction = ReleaseTransaction.for_test(
        root=tmp_path, release_id="a" * 40, runner=runner
    )

    with pytest.raises(ReleaseFailure, match="UNTRUSTED_PREVIOUS"):
        transaction.run()

    assert runner.commands == []
```

- [x] **Step 2: Run the tests to verify RED**

Run: `pytest tests/test_release_transaction.py -q`

Expected: FAIL because `scripts.ci.release_transaction` and the frozen interfaces do not exist.

- [x] **Step 3: Implement the minimal identity model and lock**

```python
RELEASE_ID = re.compile(r"[0-9a-f]{40}\Z")

class ReleaseFailure(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)

@dataclass(frozen=True)
class ReleaseManifest:
    release_id: str
    source_digest: str

    @classmethod
    def load_and_verify(cls, root: Path, release_id: str) -> "ReleaseManifest":
        if RELEASE_ID.fullmatch(release_id) is None:
            raise ReleaseFailure("INVALID_MANIFEST")
        payload = json.loads((root / "release-manifest.json").read_text())
        manifest = cls(payload["releaseId"], payload["sourceDigest"])
        if manifest.release_id != release_id or manifest.source_digest != tree_digest(root):
            raise ReleaseFailure("INVALID_MANIFEST")
        return manifest
```

Implement `flock` with `fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)`; convert `BlockingIOError` to `ReleaseFailure("LOCKED")`. `trusted_previous()` must resolve `current`, reject non-symlink/missing state/env/image IDs, and never infer an identity from a legacy live directory.

- [x] **Step 4: Run GREEN and freeze the contract**

Run: `pytest tests/test_release_transaction.py -q`

Expected: PASS; test double records no Docker command for every identity/lock failure.

## 内部 Task 2：Prepare、activation、identity rollback（非切片）

**Files:**

- Modify: `scripts/ci/release_transaction.py`
- Modify: `tests/test_release_transaction.py`

**Interfaces:**

- Consumes Task 1’s `ReleaseManifest`/`ReleaseState`/`ReleasePaths`/`ReleaseFailure`.
- Produces `ReleaseTransaction.prepare() -> ReleaseState`, `activate(candidate, previous) -> None`, `rollback(previous) -> None`, and `run() -> ReleaseState`.
- `CommandRunner.run(command: Sequence[str], cwd: Path) -> CompletedCommand` is injected in tests; production wrapper uses `subprocess.run(..., check=False, capture_output=True, text=True)` and never includes captured body in a failure.

- [x] **Step 1: Add failing transaction mutation tests**

```python
def test_build_and_config_complete_before_current_pointer_changes(tmp_path):
    transaction, runner, paths = prepared_transaction(tmp_path)
    transaction.run()

    build_index = runner.index_of(("docker", "compose", "build"))
    switch_index = transaction.events.index(("current", paths.release_dir))
    assert build_index < switch_index
    assert not runner.contains_subsequence(("docker", "compose", "down"))


def test_readiness_failure_restores_previous_pointer_and_recorded_images(tmp_path):
    transaction, runner, paths = prepared_transaction(tmp_path, readiness=[False, True])
    active = transaction.run()

    assert active.release_id == "b" * 40
    assert transaction.current_release_id() == "b" * 40
    assert runner.compose_directories[-1] == paths.previous_dir
    assert runner.image_ids_checked == paths.previous_state.image_ids
```

- [x] **Step 2: Run RED**

Run: `pytest tests/test_release_transaction.py -q`

Expected: FAIL because prepare/activation/rollback has not been implemented.

- [x] **Step 3: Implement a single transaction path**

```python
def run(self) -> ReleaseState:
    with self.lock():
        previous = self.require_trusted_previous()
        candidate = self.prepare()
        try:
            self.point_current(candidate.release_dir)
            self.compose_up(candidate, force_recreate=True)
            self.assert_identity(candidate)
            self.readiness.assert_ready(candidate)
        except ReleaseFailure as failure:
            self.rollback(previous)
            if failure.code == "ROLLBACK_FAILED":
                raise
            raise ReleaseFailure(failure.code) from None
        return candidate
```

`prepare()` moves the verified upload only to `releases/<sha>`, writes a `0600` candidate `.env` by preserving only explicitly allowlisted unmanaged current keys and replacing managed keys from the process environment, then runs `docker compose config`, `build`, image inspect and config/env digest recording. `compose_up()` must use `--project-directory <release> --env-file <release>/.env -p ai4se -f <release>/docker-compose.prod.yml up --no-build --wait --force-recreate --remove-orphans`; do not issue `down`. `rollback()` must point `current` to previous, use that exact directory/env, assert all recorded image IDs, run the same `compose_up()`, and call readiness before returning.

- [x] **Step 4: Run GREEN and the mutation matrix**

Run: `pytest tests/test_release_transaction.py -q`

Expected: PASS for build failure, config failure, lock collision, readiness failure, image drift and rollback readiness failure. No assertion may accept only a successful command return code.

## 内部 Task 3：New Agents DB/SSE readiness seam（非切片）

**Files:**

- Modify: `tools/new-agents/backend/routes.py`
- Create: `tools/new-agents/backend/tests/test_readiness_endpoint.py`

**Interfaces:**

- Produces `GET /api/readiness` returning exactly `{"status": "ok", "service": "new-agents-backend", "database": "ok"}` on `SELECT 1`; otherwise returns `503` with `{"status": "unavailable", "service": "new-agents-backend", "database": "unavailable"}`.
- Produces `GET /api/readiness/stream` returning the same DB gate as one typed `run_started` SSE frame followed by `[DONE]`, with `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`; it must not call a model or inspect/write a credential.

- [x] **Step 1: Write failing Flask route tests**

```python
def test_readiness_requires_database_and_returns_safe_projection(client, monkeypatch):
    assert client.get("/api/readiness").get_json() == {
        "status": "ok", "service": "new-agents-backend", "database": "ok"
    }
    monkeypatch.setattr(routes.db.session, "execute", lambda _query: (_ for _ in ()).throw(SQLAlchemyError()))
    response = client.get("/api/readiness")
    assert response.status_code == 503
    assert response.get_json() == {
        "status": "unavailable", "service": "new-agents-backend", "database": "unavailable"
    }


def test_readiness_stream_is_unbuffered_typed_sse(client):
    response = client.get("/api/readiness/stream")
    assert response.headers["Content-Type"].startswith("text/event-stream")
    assert response.headers["X-Accel-Buffering"] == "no"
    assert response.get_data(as_text=True) == (
        'data: {"type": "run_started", "runId": "readiness"}\\n\\n'
        "data: [DONE]\\n\\n"
    )
```

- [x] **Step 2: Run RED**

Run: `cd tools/new-agents/backend && ../../.venv/bin/python -m pytest tests/test_readiness_endpoint.py -q`

Expected: FAIL with 404 because neither readiness route exists.

- [x] **Step 3: Implement the two safe routes**

```python
from flask import Response
from sqlalchemy import text

def _database_ready() -> bool:
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True

@api_bp.route("/readiness", methods=["GET"])
def readiness():
    if not _database_ready():
        return jsonify(status="unavailable", service="new-agents-backend", database="unavailable"), 503
    return jsonify(status="ok", service="new-agents-backend", database="ok")
```

`/readiness/stream` must call `_database_ready()` first; on failure reuse the JSON 503 response, on success construct the fixed one-frame `Response`. Do not route readiness through default-LLM config or Agent Runtime.

- [x] **Step 4: Run GREEN and adjacent backend contracts**

Run: `cd tools/new-agents/backend && ../../../.venv/bin/python -m pytest tests/test_readiness_endpoint.py tests/test_api.py tests/test_api_auth.py -q`

Expected: PASS with no changed authentication behavior for existing sensitive endpoints.

## 内部 Task 4：Compose/CI migration and production bypass closure（非切片）

**Files:**

- Modify: `docker-compose.prod.yml`
- Modify: `.github/workflows/deploy.yml`
- Modify: `scripts/ci/deploy.sh`
- Modify: `scripts/health/health_check.sh`
- Modify: `tests/test_ci_deploy_hardening.py`

**Interfaces:**

- Consumes `release-manifest.json` generated in CI and `release_transaction.py --root /opt/intent-test-framework --release-id "$GITHUB_SHA" --upload-dir "$UPLOAD_DIR"` on remote.
- Compose build services expose stable `image: ai4se/<service>:${AI4SE_RELEASE_ID:?AI4SE_RELEASE_ID is required}` fields consumed by Task 2’s image ID recorder.
- GitHub `deploy-to-production` adds a production-only concurrency group and generates package manifest before transfer; remote staging includes `${{ github.run_id }}-${{ github.run_attempt }}-${{ github.sha }}`.

- [x] **Step 1: Write failing static contracts**

```python
def test_production_deploy_uses_unique_staging_manifest_and_serial_concurrency():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "cancel-in-progress: false" in workflow
    assert "release-manifest.json" in workflow
    assert "github.run_id" in workflow and "github.run_attempt" in workflow
    assert "/opt/intent-test-framework-upload-tmp" not in workflow
    assert "release_transaction.py" in workflow


def test_legacy_production_deploy_cannot_down_or_globally_clean_resources():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    production = script.split("prod|production|remote)", 1)[1]
    assert "release_transaction.py" in production
    assert "docker ps -a | grep" not in production
    assert " down" not in production
```

Add contracts for tagged `image`, gateway `/new-agents/api/readiness` and `/readiness/stream`, New Agents page probe, absence of static `/health` as release verdict, and required `flock`/recorded image checks.

- [x] **Step 2: Run RED**

Run: `pytest tests/test_ci_deploy_hardening.py -q`

Expected: FAIL because current workflow overwrites fixed live/upload paths and legacy script performs early `down`/global cleanup.

- [x] **Step 3: Implement the CI/Compose handoff**

```yaml
concurrency:
  group: production-release
  cancel-in-progress: false
```

In the deploy package step, use Python stdlib to write `release-manifest.json` after all candidate files are copied, with `releaseId: ${{ github.sha }}` and the deterministic tree digest used by Task 1. Transfer to `/opt/intent-test-framework/uploads/${{ github.run_id }}-${{ github.run_attempt }}-${{ github.sha }}`. The SSH script must only validate required secret presence and invoke the candidate upload’s `python3 scripts/ci/release_transaction.py`; it must not `rsync --delete` into current or reconstruct `.env` in a shared live directory.

Give every `build:` service in `docker-compose.prod.yml` an explicit `image: ai4se/<service>:${AI4SE_RELEASE_ID:?AI4SE_RELEASE_ID is required}`. Change legacy `deploy.sh production` to fail with the fixed instruction that production requires `release_transaction.py`; retain local/dev behavior. Change `health_check.sh production` to the same fail-closed instruction; local/dev diagnostics remain non-release helpers.

- [x] **Step 4: Run GREEN plus syntax/config validation**

Run: `pytest tests/test_ci_deploy_hardening.py -q && bash -n scripts/ci/deploy.sh scripts/health/health_check.sh && docker compose -f docker-compose.prod.yml config --quiet`

Expected: PASS. The last command is run with a test-only environment containing no real values; it validates Compose interpolation but never starts a service.

## 内部 Task 5：Gateway readiness runner and local Docker release simulation（非切片）

**Files:**

- Modify: `scripts/ci/release_transaction.py`
- Modify: `tests/test_release_transaction.py`
- Modify: `tests/test_pre_push_deployment.py`
- Modify: `tests/e2e/new_agents_real/test_deployed_stack.py`

**Interfaces:**

- Consumes Task 3’s `/new-agents/api/readiness` and `/new-agents/api/readiness/stream` contracts.
- Produces `GatewayReadiness.assert_ready(release: ReleaseState) -> None` with injectable `request(url, timeout)` and `CommandRunner`.
- Produces only safe codes `READINESS_FAILED`, `IDENTITY_MISMATCH` or `ROLLBACK_FAILED`; no body/log diagnostic is serialized.

- [x] **Step 1: Write failing readiness and rollback mutation tests**

```python
def test_gateway_readiness_requires_new_agents_page_json_sse_and_database_write(tmp_path):
    readiness = GatewayReadiness(fake_http({
        "/new-agents/": Response(200, b'<div id="root"></div>'),
        "/new-agents/api/readiness": Response(200, b'{"status":"ok","database":"ok"}'),
    "/new-agents/api/readiness/stream": Response(200, b'data: {"type":"run_started","runId":"readiness"}\n\ndata: [DONE]\n\n', {"Content-Type": "text/event-stream"}),
    }), RecordingRunner())
    readiness.assert_ready(release_state)


@pytest.mark.parametrize("broken_path", ["/new-agents/", "/new-agents/api/readiness", "/new-agents/api/readiness/stream"])
def test_any_gateway_readiness_mutation_causes_candidate_rollback(tmp_path, broken_path):
    transaction = prepared_transaction(tmp_path, broken_path=broken_path)
    with pytest.raises(ReleaseFailure, match="READINESS_FAILED"):
        transaction.run()
    assert transaction.current_release_id() == transaction.previous_release_id
```

- [x] **Step 2: Run RED**

Run: `pytest tests/test_release_transaction.py tests/test_pre_push_deployment.py tests/e2e/new_agents_real/test_deployed_stack.py -q`

Expected: FAIL because release readiness does not yet check gateway page/DB/SSE or bind rollback to all failed probes.

- [x] **Step 3: Implement bounded, secret-free readiness**

```python
def assert_ready(self, release: ReleaseState) -> None:
    self.require_page("/new-agents/", marker='id="root"')
    self.require_json("/new-agents/api/health", {"status": "ok"})
    self.require_json("/new-agents/api/readiness", {"status": "ok", "database": "ok"})
    self.require_sse("/new-agents/api/readiness/stream", event_type="run_started")
    self.runner.run(self.compose("exec", "-T", "postgres", "psql", "-v", "ON_ERROR_STOP=1", "-c", "CREATE TEMPORARY TABLE release_probe (id integer); INSERT INTO release_probe VALUES (1); SELECT count(*) FROM release_probe;"), cwd=release.directory)
```

`require_*` methods accept only status/headers/fixed markers, discard bodies before raising, and bind all URLs to loopback/public gateway configured by the transaction. Add deployed-stack contract tests that Nginx keeps `proxy_buffering off` for the readiness SSE path and exposes the New Agents backend response through `/new-agents/api/`.

- [x] **Step 4: Run GREEN and local production-shaped proof**

Run: `pytest tests/test_release_transaction.py tests/test_pre_push_deployment.py tests/e2e/new_agents_real/test_deployed_stack.py -q`

Expected: PASS for positive path and every negative mutation. Then run the existing isolated Docker deployment test owner: `pytest tests/test_pre_push_deployment.py tests/e2e/new_agents_real/test_deployed_stack.py -q`.

## 内部 Task 6：Documentation, review, full verification and one focused commit（非切片）

**Files:**

- Modify: `docs/deployment-guide.md`
- Move: `docs/todos/2026-07-21-pre-push-full-validation-and-release-safety.md` → `docs/todos/archive/2026-07-21-pre-push-full-validation-and-release-safety.md`
- Create: `docs/test_requirements/2026-07-21-qg022-validation-record.md`
- Review: all Task 1–5 paths

**Interfaces:**

- Documents only the public `release-manifest.json`, release layout, required trusted bootstrap, lock/prepare/activate/rollback/readiness phases, evidence locations and no-secret constraints.
- Marks `QG-022` done only after final current-HEAD full gate passes; archives the todo only when both QG entries are terminal, following the Goal Mode archive rule.

- [x] **Step 1: Write docs and documentation assertions first**

Add documentation tests/links that require the deployment guide to reference `release_transaction.py`, `releases/<sha>`, trusted bootstrap and `scripts/test/pre-push.sh`. Add a QG-022 validation record template whose PASS claim is left absent until actual commands run.

- [x] **Step 2: Run documentation RED/consistency checks**

Run: `bash scripts/test/check-docs.sh && pytest tests/test_ci_deploy_hardening.py -q`

Expected: PASS only after the docs name the implemented transaction; do not write a completed validation claim before the commands exist.

- [x] **Step 3: Perform the one thick-slice formal review**

Review the final diff against [QG-022 design](../specs/2026-07-21-qg022-trusted-production-release-design.md): source/image/config identity, no early stop/global cleanup, trusted bootstrap, lock, recovery proof, page/DB/SSE readiness, secret boundary and user dirty-file ownership. Resolve every Critical/Important finding before verification; record any Minor risk with owner and disposition in the validation record.

- [x] **Step 4: Run layered verification**

Run:

```bash
pytest tests/test_release_transaction.py tests/test_ci_deploy_hardening.py tests/test_pre_push_deployment.py tests/e2e/new_agents_real/test_deployed_stack.py -q
cd tools/new-agents/backend && ../../../.venv/bin/python -m pytest tests/test_readiness_endpoint.py tests/test_api.py tests/test_api_auth.py -q
cd ../../..
bash scripts/test/check-docs.sh
```

Expected: PASS. Record actual test counts, mutation coverage and any legitimate skips; do not claim a remote production run.

- [x] **Step 5: Commit and execute the complete fixed gate**

Precisely stage only QG-022 source/tests/docs, excluding `tools/intent-tester/test-results/proxy/junit.xml`. Create one focused local commit. In a clean isolated checkout at that exact HEAD run:

```bash
./scripts/test/pre-push.sh
```

Expected: all phases `PASS`, including production-shaped Docker deployment and real DeepSeek 7-workflow/25-stage E2E; temporary Docker resources and credential files are absent after finalization. Then update QG-022 evidence/archival records only if that verification remains current, without push.

## Plan self-review

- **Spec coverage:** Task 1 covers immutable manifest/previous trust/lock; Task 2 covers pre-build and identity rollback; Task 3 covers backend DB/SSE seam; Task 4 closes CI and unsafe legacy paths; Task 5 makes page/upstream/DB/SSE and negative recovery executable; Task 6 records, reviews and runs the required fixed full gate.
- **Placeholder scan:** no `TBD`/`TODO`/implicit error-handling task exists; every mutation has an explicit expected non-success route.
- **Type consistency:** every later task consumes Task 1’s `ReleaseState`, `ReleaseFailure`, `ReleasePaths` and injected `CommandRunner`; gateway readiness consumes only Task 3’s fixed JSON/SSE payloads.
- **Commit boundary:** individual Tasks are implementation evidence only. One QG-022 commit, then the fixed full gate, is the only release-boundary commit; no push is authorized.
