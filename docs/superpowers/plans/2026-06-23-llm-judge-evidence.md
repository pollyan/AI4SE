# LLM Judge Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 New Agents 可选 E2E LLM judge 增加 evidence 记录、可读摘要和失败解释，让外部质量评审结果可追溯。

**Architecture:** 在现有 `tests/e2e/new_agents_browser/llm_judge.py` 内扩展测试证据层，不接入 New Agents runtime/API/DB。judge helper 在解析 verdict 后先写 JSON evidence，再执行 pass/score/visual 断言；pytest 失败信息包含摘要和 evidence path。默认未启用或缺 env 时继续 skip。

**Tech Stack:** Python 3.11 standard library, dataclasses, pathlib, json, pytest, requests.

---

## 文件结构

- Modify: `tests/e2e/new_agents_browser/llm_judge.py`
  - 增加 `JudgeConfigurationStatus`、`JudgeEvidenceRecord`、`judge_configuration_status()`、`write_judge_evidence()`、`format_judge_evidence_summary()`。
  - 修改 artifact/handoff judge 断言，使其记录 evidence 后再断言，并在失败信息中展示 summary/path。
- Modify: `tests/e2e/new_agents_browser/test_llm_judge.py`
  - 增加 deterministic tests：evidence JSON 写入、summary 包含 visual score、配置诊断、失败 assertion 包含 evidence path。
- Modify: `docs/todos/refactor/README.md`
  - 从剩余能力包移除 E08 LLM judge evidence，记录本轮消化结果。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - 更新 E08 状态和 Goal Mode 消化记录。

预计 commit 边界：代码+测试为一个 commit；spec/plan/todo 记录为第二个 commit，避免文档和代码混成大 diff。

## Task 1: RED - Evidence record 和 summary 测试

**Files:**
- Modify: `tests/e2e/new_agents_browser/test_llm_judge.py`

- [ ] **Step 1: 写失败测试**

在 imports 中增加：

```python
import json
```

并从 `.llm_judge` 导入新 API：

```python
    JudgeEvidenceRecord,
    format_judge_evidence_summary,
    judge_configuration_status,
    write_judge_evidence,
```

追加测试：

```python
def test_write_judge_evidence_records_structured_verdict(tmp_path) -> None:
    result = parse_judge_result(
        """
        {
          "pass": true,
          "score": 91,
          "dimension_scores": {
            "专业完整性": 90,
            "可视化质量": 92
          },
          "issues": [],
          "evidence": ["最终产物包含风险矩阵"],
          "recommendations": ["保持当前结构"]
        }
        """
    )
    record = JudgeEvidenceRecord.from_result(
        kind="artifact",
        subject="Lisa 测试策略与用例设计",
        result=result,
    )

    evidence_path = write_judge_evidence(record, tmp_path)

    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert payload["kind"] == "artifact"
    assert payload["subject"] == "Lisa 测试策略与用例设计"
    assert payload["passed"] is True
    assert payload["score"] == 91
    assert payload["dimension_scores"]["可视化质量"] == 92
    assert payload["evidence"] == ["最终产物包含风险矩阵"]
    assert payload["recommendations"] == ["保持当前结构"]
    assert evidence_path.name.startswith("artifact-lisa-")


def test_format_judge_evidence_summary_includes_score_visual_and_path(tmp_path) -> None:
    result = parse_judge_result(
        """
        {
          "pass": true,
          "score": 88,
          "dimension_scores": {
            "交互体验": 84,
            "可视化质量": 90
          },
          "issues": ["缺少少量边界说明"],
          "evidence": ["包含 traceability-matrix"],
          "recommendations": ["补充边界条件"]
        }
        """
    )
    record = JudgeEvidenceRecord.from_result(
        kind="artifact",
        subject="Alex 价值发现",
        result=result,
    ).with_evidence_path(tmp_path / "judge.json")

    summary = format_judge_evidence_summary(record)

    assert "Alex 价值发现" in summary
    assert "score=88" in summary
    assert "visual=90" in summary
    assert "缺少少量边界说明" in summary
    assert "补充边界条件" in summary
    assert str(tmp_path / "judge.json") in summary


def test_judge_configuration_status_reports_missing_environment(monkeypatch, tmp_path):
    for key in (
        "NEW_AGENTS_E2E_LLM_JUDGE",
        "NEW_AGENTS_E2E_JUDGE_API_KEY",
        "NEW_AGENTS_E2E_JUDGE_BASE_URL",
        "NEW_AGENTS_E2E_JUDGE_MODEL",
        "NEW_AGENTS_E2E_JUDGE_EVIDENCE_DIR",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("NEW_AGENTS_E2E_JUDGE_EVIDENCE_DIR", str(tmp_path))

    status = judge_configuration_status()

    assert status.enabled is False
    assert status.missing == ("NEW_AGENTS_E2E_LLM_JUDGE",)
    assert status.evidence_dir == tmp_path
    assert "NEW_AGENTS_E2E_LLM_JUDGE" in status.skip_reason
```

- [ ] **Step 2: 运行 RED**

Run:

```bash
python3 -m pytest tests/e2e/new_agents_browser/test_llm_judge.py -q
```

Expected: FAIL，原因是 `JudgeEvidenceRecord` / `write_judge_evidence` / `judge_configuration_status` 未定义。

## Task 2: GREEN - Evidence 数据结构与写入

**Files:**
- Modify: `tests/e2e/new_agents_browser/llm_judge.py`

- [ ] **Step 1: 实现最小 API**

新增：

```python
@dataclass(frozen=True)
class JudgeConfigurationStatus:
    enabled: bool
    missing: tuple[str, ...]
    evidence_dir: Path

    @property
    def skip_reason(self) -> str:
        if not self.enabled:
            return "NEW_AGENTS_E2E_LLM_JUDGE is not enabled"
        if self.missing:
            return "missing LLM judge environment variables: " + ", ".join(self.missing)
        return ""
```

新增 `JudgeEvidenceRecord`，包含 `from_result()` 和 `with_evidence_path()`；新增 `_slugify_subject()`、`write_judge_evidence()`、`format_judge_evidence_summary()`。

证据 JSON 字段：
- `kind`
- `subject`
- `passed`
- `score`
- `dimension_scores`
- `issues`
- `evidence`
- `recommendations`

- [ ] **Step 2: 运行 GREEN**

Run:

```bash
python3 -m pytest tests/e2e/new_agents_browser/test_llm_judge.py -q
```

Expected: 新增测试通过。

## Task 3: RED/GREEN - Judge 断言失败解释

**Files:**
- Modify: `tests/e2e/new_agents_browser/test_llm_judge.py`
- Modify: `tests/e2e/new_agents_browser/llm_judge.py`

- [ ] **Step 1: 写失败路径测试**

在 `test_llm_judge.py` 追加：

```python
def test_failed_artifact_judge_message_includes_evidence_path(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("NEW_AGENTS_E2E_LLM_JUDGE", "1")
    monkeypatch.setenv("NEW_AGENTS_E2E_JUDGE_API_KEY", "key")
    monkeypatch.setenv("NEW_AGENTS_E2E_JUDGE_BASE_URL", "https://judge.example")
    monkeypatch.setenv("NEW_AGENTS_E2E_JUDGE_MODEL", "judge-model")
    monkeypatch.setenv("NEW_AGENTS_E2E_JUDGE_EVIDENCE_DIR", str(tmp_path))

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "pass": False,
                                    "score": 61,
                                    "dimension_scores": {
                                        "专业完整性": 60,
                                        "可视化质量": 75,
                                    },
                                    "issues": ["缺少风险追溯"],
                                    "evidence": ["最终产物没有风险矩阵"],
                                    "recommendations": ["补充风险到用例追溯"],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }

    def fake_post(*_args, **_kwargs):
        return FakeResponse()

    monkeypatch.setattr("tests.e2e.new_agents_browser.llm_judge.requests.post", fake_post)

    with pytest.raises(AssertionError) as exc:
        assert_llm_judges_artifact_quality(
            "Lisa 测试策略与用例设计",
            _sample_run_result(),
        )

    message = str(exc.value)
    assert "score=61" in message
    assert "缺少风险追溯" in message
    assert "补充风险到用例追溯" in message
    assert str(tmp_path) in message
    assert list(tmp_path.glob("artifact-*.json"))
```

并确保 import 中包含 `assert_llm_judges_artifact_quality`。

- [ ] **Step 2: 运行 RED**

Run:

```bash
python3 -m pytest tests/e2e/new_agents_browser/test_llm_judge.py::test_failed_artifact_judge_message_includes_evidence_path -q
```

Expected: FAIL，失败消息还不包含 evidence path 或 summary。

- [ ] **Step 3: 修改 artifact/handoff judge helper**

在 `assert_llm_judges_artifact_quality()` 与 `assert_llm_judges_handoff_quality()` 中：
- 使用 `judge_configuration_status()` 判断 skip。
- parse verdict 后构建 record。
- 调用 `write_judge_evidence()`。
- 使用 `format_judge_evidence_summary()` 构建失败信息。
- pass/score/visual assertion 都包含 summary。

- [ ] **Step 4: 运行 GREEN**

Run:

```bash
python3 -m pytest tests/e2e/new_agents_browser/test_llm_judge.py -q
```

Expected: PASS。

## Task 4: 更新 todo 记录

**Files:**
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

- [ ] **Step 1: 更新 README 剩余能力包**

剩余能力包改为：
1. Prompt/template 版本管理。
2. 专业方法库配置化。
3. DeepSeek 真实外部执行证据。

新增说明：E08 LLM judge evidence 已完成可选 judge verdict 记录、summary 展示、失败解释和本地测试证据。

- [ ] **Step 2: 更新诊断文档 E08 和消化记录**

把 E08 从“后续仅保留 LLM judge evidence”改为已消化完整 judge evidence；新增 Goal Mode 消化记录；后续 Superpowers 粒度表移除 E08。

## Task 5: 验证与提交

**Files:**
- All changed files.

- [ ] **Step 1: 运行聚焦验证**

Run:

```bash
python3 -m pytest tests/e2e/new_agents_browser/test_llm_judge.py -q
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py::test_lisa_final_artifact_passes_optional_llm_judge tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py::test_alex_final_artifact_passes_optional_llm_judge -q
python3 -m py_compile tests/e2e/new_agents_browser/llm_judge.py
git diff --check
```

Expected:
- `test_llm_judge.py` PASS。
- optional E2E judge tests SKIP when env disabled。
- py_compile and diff check exit 0。

- [ ] **Step 2: 检查 diff 粒度**

Run:

```bash
git diff --stat
git status -sb
```

Expected: 只包含 judge helper/tests、spec/plan、todo 文档。若 staged diff 超过约 800 行，拆成代码测试 commit 和文档记录 commit。

- [ ] **Step 3: 提交**

Run:

```bash
git add tests/e2e/new_agents_browser/llm_judge.py tests/e2e/new_agents_browser/test_llm_judge.py docs/superpowers/specs/2026-06-23-llm-judge-evidence-design.md docs/superpowers/plans/2026-06-23-llm-judge-evidence.md docs/todos/refactor/README.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md
git commit -m "feat(new-agents): 记录 LLM judge evidence"
```

Expected: focused commit created; split docs commit if diff size requires it。

## 自检

- Spec 覆盖：配置诊断、evidence 写入、summary、失败解释、skip 行为和 todo 更新均有任务。
- 占位扫描：无 TBD/TODO/implement later。
- CI 等价门禁：本轮不触碰 frontend TypeScript、runtime、SSE/API、artifact contract 或 persistence；验证以 deterministic pytest、optional skip check、py_compile 和 diff check 为准。
