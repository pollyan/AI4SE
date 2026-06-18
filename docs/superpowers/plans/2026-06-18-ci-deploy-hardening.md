# CI 与部署可信度加固 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补强 AI4SE 的 CI、部署脚本和 Git 索引卫生，让关键失败不再被吞掉，并让生产 `.env` 同步更稳。

**Architecture:** 以脚本文本回归测试保护 CI/deploy 不变量，再做最小 YAML/shell 修改。部署运行时不引入新依赖，不改变服务拓扑。

**Tech Stack:** GitHub Actions YAML、Bash、pytest 文本测试、Git 索引检查。

---

### Task 1: 脚本护栏回归测试

**Files:**
- Create: `tests/test_ci_deploy_hardening.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
DEPLOY_SCRIPT = ROOT / "scripts" / "ci" / "deploy.sh"


def test_new_agents_frontend_ci_runs_typecheck_before_tests():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    section = workflow.split("new-agents-frontend-test:", 1)[1].split("code-quality:", 1)[0]
    assert "npm run lint" in section
    assert section.index("npm run lint") < section.index("npm run test")


def test_critical_flake8_is_not_soft_failed():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "flake8 tools/intent-tester/backend --count --select=E9,F63,F7,F82 --show-source --statistics || true" not in workflow


def test_production_env_sync_avoids_sed_secret_rewrite_and_locks_permissions():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "sed -i" not in workflow
    assert "chmod 600 .env" in workflow
    assert "is_managed_env_key()" in workflow
    assert "mv .env.managed .env" in workflow


def test_local_deploy_uses_existing_dev_compose_file():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    local_case = script.split("local|dev|development)", 1)[1].split("prod|production|remote)", 1)[0]
    assert 'COMPOSE_FILE="docker-compose.dev.yml"' in local_case
    assert (ROOT / "docker-compose.dev.yml").exists()


def test_typescript_incremental_build_metadata_is_not_tracked():
    result = subprocess.run(
        ["git", "ls-files", "*.tsbuildinfo"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ci_deploy_hardening.py -q`

Expected: FAIL because workflow lacks `npm run lint`, soft-fails flake8, uses `sed -i`, local deploy points at `docker-compose.yml`, and `tools/new-agents/tsconfig.tsbuildinfo` is tracked.

### Task 2: 最小实现

**Files:**
- Modify: `.github/workflows/deploy.yml`
- Modify: `scripts/ci/deploy.sh`
- Remove from Git index: `tools/new-agents/tsconfig.tsbuildinfo`

- [ ] **Step 1: Update New Agents frontend CI**

In `.github/workflows/deploy.yml`, change the New Agents frontend job from:

```yaml
npm ci
npm run test
```

to:

```yaml
npm ci
npm run lint
npm run test
```

- [ ] **Step 2: Make critical flake8 a hard gate**

Remove `|| true` from the critical flake8 command.

- [ ] **Step 3: Replace sed-based env upsert**

Replace `upsert_env_var()` with a managed-file rewrite that:

```bash
is_managed_env_key() {
  case "$1" in
    DB_PASSWORD|SECRET_KEY|NEW_AGENTS_DEFAULT_LLM_API_KEY|NEW_AGENTS_DEFAULT_LLM_BASE_URL|NEW_AGENTS_DEFAULT_LLM_MODEL|NEW_AGENTS_DEFAULT_LLM_DESCRIPTION)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

write_env_var() {
  key="$1"
  value="$2"
  printf '%s=%s\n' "$key" "$value" >> .env.managed
}
```

Then copy non-managed existing lines into `.env.managed`, append managed values, `mv .env.managed .env`, and run `chmod 600 .env`.

- [ ] **Step 4: Fix local compose file**

Change the local case in `scripts/ci/deploy.sh` to:

```bash
COMPOSE_FILE="docker-compose.dev.yml"
```

- [ ] **Step 5: Remove tsbuildinfo from Git index**

Run: `git rm --cached tools/new-agents/tsconfig.tsbuildinfo`

Expected: file remains locally ignored, but no longer appears in `git ls-files '*.tsbuildinfo'`.

### Task 3: Verification

**Files:**
- Test: `tests/test_ci_deploy_hardening.py`
- Verify changed scripts and affected frontend/backend gates

- [ ] **Step 1: Run focused regression**

Run: `pytest tests/test_ci_deploy_hardening.py -q`

Expected: PASS.

- [ ] **Step 2: Run shell syntax check**

Run: `bash -n scripts/ci/deploy.sh`

Expected: exit 0.

- [ ] **Step 3: Run New Agents frontend gates**

Run from `tools/new-agents/frontend`:

```bash
npm run lint
npm run test
```

Expected: both exit 0.

- [ ] **Step 4: Run backend and lint smoke gates**

Run:

```bash
.venv/bin/python -m pytest -m "not slow" -q
.venv/bin/python -m flake8 tools/intent-tester/backend --count --select=E9,F63,F7,F82 --show-source --statistics
```

Expected: backend tests pass; flake8 reports `0`.
