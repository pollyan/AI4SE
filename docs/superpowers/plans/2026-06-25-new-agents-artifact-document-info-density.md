# New Agents Artifact Document Info Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move low-value document/review information tables out of the first screen for affected New Agents artifacts while preserving metadata as a traceable appendix.

**Architecture:** Update shared workflow/template/contract/renderer surfaces for the affected stages. Keep existing artifact_data schemas and shared renderers; no workflow-specific UI or runtime branch is introduced.

**Tech Stack:** Python artifact renderers and Pydantic contracts, JSON workflow manifest, TypeScript prompt templates, pytest.

---

### Task 1: Red Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`

- [x] **Step 1: Add order assertions for CLARIFY**

In `test_render_clarify_artifact_data_is_deterministic_and_contract_valid`, assert that the core first section precedes the document info appendix:

```python
markdown = first.artifact_update.markdown
assert markdown.index("## 1. 需求事实清单") < markdown.index("## 附录：文档信息")
```

- [x] **Step 2: Add order assertions for DELIVERY**

In `test_render_delivery_artifact_data_is_deterministic_and_contract_valid`, assert that the executive summary precedes the document info appendix and the change log is section 9:

```python
markdown = first.artifact_update.markdown
assert "## 9. 变更记录" in markdown
assert markdown.index("## 1. 执行摘要") < markdown.index("## 附录：文档信息")
```

- [x] **Step 3: Add order assertions for BLUEPRINT**

In `test_render_value_blueprint_artifact_data_is_deterministic_and_contract_valid`, assert that product overview precedes the document info appendix:

```python
markdown = first.artifact_update.markdown
assert markdown.index("## 1. 产品概述") < markdown.index("## 附录：文档信息")
```

- [x] **Step 4: Add order assertions for REQ_REVIEW REVIEW**

In `test_render_req_review_artifact_data_is_deterministic_and_contract_valid`, assert that business review sections precede the review information appendix:

```python
markdown = first.artifact_update.markdown
assert markdown.index("## 需求质量总览") < markdown.index("## 附录：评审信息")
```

- [x] **Step 5: Run focused renderer tests and verify red**

```bash
cd tools/new-agents/backend && ../../../.venv/bin/python -m pytest tests/test_artifact_data_renderers.py -q
```

Expected before implementation: appendix order assertions fail because renderers still output `## 文档信息` / `## 1. 文档信息` / `## 评审信息` at the top.

### Task 2: Shared Contract and Template Update

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/frontend/src/core/prompts/test_design/clarify.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/test_design/delivery.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/value_discovery/blueprint.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/req_review/review.ts`

- [x] **Step 1: Update required headings**

Replace affected required headings with `## 附录：文档信息` or `## 附录：评审信息`; for DELIVERY, renumber core headings from `执行摘要` through `变更记录` to `## 1` through `## 9`.

- [x] **Step 2: Update prompt templates**

Move the document/review info table to the end of each affected template and title it `## 附录：文档信息` or `## 附录：评审信息`. Keep the same metadata fields.

### Task 3: Renderer Update

**Files:**
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`

- [x] **Step 1: Rename shared document info renderer heading**

Change `_render_document_info()` and `_render_blueprint_document_info()` to return `## 附录：文档信息`.

- [x] **Step 2: Move CLARIFY document info to the end**

In `render_test_design_clarify_markdown()`, move `_render_document_info(data.document_info)` after `_render_stage_gate(data.stage_gate)`.

- [x] **Step 3: Move BLUEPRINT document info to the end**

In `render_value_discovery_blueprint_markdown()`, move `_render_blueprint_document_info(data.document_info)` after `_render_blueprint_stage_gate(data.stage_gate)`.

- [x] **Step 4: Move DELIVERY document info to the end and renumber core headings**

In `render_test_design_delivery_markdown()`, move `_render_delivery_document_info(...)` after `_render_delivery_change_log(data.change_log)`. Update delivery section renderer headings so summary starts at `## 1. 执行摘要` and change log becomes `## 9. 变更记录`; make `_render_delivery_document_info()` return `## 附录：文档信息`.

- [x] **Step 5: Move REQ_REVIEW REVIEW info to the end**

In `render_req_review_review_markdown()`, move `_render_req_review_info(data.review_info)` after `_render_req_review_stage_gate(data.stage_gate)`, and make `_render_req_review_info()` return `## 附录：评审信息`.

### Task 4: Verify and Archive

- [x] **Step 1: Run focused renderer tests**

```bash
cd tools/new-agents/backend && ../../../.venv/bin/python -m pytest tests/test_artifact_data_renderers.py -q
```

- [x] **Step 2: Run backend contract/runtime tests**

```bash
cd tools/new-agents/backend && ../../../.venv/bin/python -m pytest tests/test_agent_contracts.py tests/test_agent_runtime.py -q
```

Also run workflow sync after manifest/contract edits:

```bash
cd tools/new-agents/backend && ../../../.venv/bin/python -m pytest tests/test_workflow_contract_sync.py -q
```

- [x] **Step 3: Run frontend prompt/config tests**

```bash
cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

- [x] **Step 4: Run broad verification**

Run `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all` from repo root. If optional LLM judge is enabled in the ambient environment, record any external-model-only failure separately.

Verification record:
- `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all` passed; Browser E2E reported 3 passed / 3 skipped.

- [x] **Step 5: Archive todo**

Move `docs/todos/refactor/2026-06-25-new-agents-artifact-document-info-density.md` to `docs/todos/archive/2026-06-25-new-agents-artifact-document-info-density.md`, add a completion record, and update `docs/todos/refactor/README.md`.
