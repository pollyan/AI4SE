# E11 Prompt/template 版本管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让每个 New Agents stage 都有可审计的 prompt/template 版本和回归样例，并在系统提示中暴露当前版本。

**Architecture:** `workflow_manifest.json` 继续作为 stage metadata 事实源，新增 `promptTemplateVersion` 和 `regressionSampleIds`。`tools/new-agents/prompt_regression_samples.json` 保存共享样例 registry。前端 prompt builder 注入版本标识，后端 sync tests 校验每个 stage 的版本、样例引用和容器打包。

**Tech Stack:** JSON manifest, TypeScript 5.x, Vitest, Python pytest, Vite build, existing New Agents shared Agent Runtime contracts.

---

## File Structure

- Create: `tools/new-agents/prompt_regression_samples.json`
  - 每个 stage 一个短输入样例、预期关注点和验收检查。
- Modify: `tools/new-agents/workflow_manifest.json`
  - 每个 stage 增加 `promptTemplateVersion` 和 `regressionSampleIds`。
- Modify: `tools/new-agents/frontend/src/core/workflowRegistry.ts`
  - 扩展 stage metadata 类型。
- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - 扩展 `WorkflowStage` 类型，使 `WORKFLOWS` stage 暴露版本和样例 ids。
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`
  - 当前 stage 注入 `Prompt/template 版本：<version>`。
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`
  - 增加版本注入测试。
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
  - 增加 version/sample sync tests 和 Docker/Compose packaging tests。
- Modify: `tools/new-agents/docker/Dockerfile`, `tools/new-agents/backend/docker/Dockerfile`, `docker-compose.dev.yml`, `docker-compose.dev-cn.yml`
  - 打包/挂载 prompt regression samples。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - 将 E11 标记为已完成待合回。

## Task 1: RED Frontend Prompt Version Test

**Files:**
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`

- [x] **Step 1: Add failing version injection test**

Append inside `describe('buildSystemPrompt', () => { ... })`:

```ts
    it('injects the current prompt template version for the active stage', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentArtifact: '# 测试策略蓝图',
        });

        expect(prompt).toContain('【Prompt/template 版本】');
        expect(prompt).toContain('当前阶段版本：2026.06.24.1');
    });
```

- [x] **Step 2: Run frontend RED check**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: FAIL because `buildSystemPrompt()` does not inject prompt/template version yet.

## Task 2: RED Backend Version and Sample Sync Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

- [x] **Step 1: Add failing sync helpers and tests**

Add near constants:

```python
PROMPT_REGRESSION_SAMPLES = NEW_AGENTS_ROOT / "prompt_regression_samples.json"
PROMPT_TEMPLATE_VERSION_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.\d+$")
```

Add `import re` at the top.

Add helper:

```python
def _prompt_regression_samples() -> dict:
    return json.loads(PROMPT_REGRESSION_SAMPLES.read_text(encoding="utf-8"))
```

Add tests after professional method sync tests:

```python
def test_workflow_manifest_declares_prompt_template_versions_for_every_stage():
    manifest = _workflow_manifest()

    for workflow_id, workflow in manifest["workflows"].items():
        for stage in workflow["stages"]:
            version = stage.get("promptTemplateVersion")
            assert isinstance(version, str), f"{workflow_id}/{stage['id']} missing promptTemplateVersion"
            assert PROMPT_TEMPLATE_VERSION_RE.match(version), (
                f"{workflow_id}/{stage['id']} has invalid promptTemplateVersion: {version}"
            )


def test_workflow_manifest_declares_regression_samples_for_every_stage():
    known_sample_ids = {
        sample["id"]
        for sample in _prompt_regression_samples()["samples"]
    }
    manifest = _workflow_manifest()

    for workflow_id, workflow in manifest["workflows"].items():
        for stage in workflow["stages"]:
            sample_ids = stage.get("regressionSampleIds")
            assert isinstance(sample_ids, list) and sample_ids, (
                f"{workflow_id}/{stage['id']} missing regressionSampleIds"
            )
            for sample_id in sample_ids:
                assert sample_id in known_sample_ids, (
                    f"{workflow_id}/{stage['id']} references unknown regression sample {sample_id}"
                )


def test_prompt_regression_samples_reference_known_workflow_stages():
    workflow_stages = _workflow_manifest_stages()
    samples = _prompt_regression_samples()["samples"]

    for sample in samples:
        workflow_id = sample["workflowId"]
        stage_id = sample["stageId"]
        assert workflow_id in workflow_stages
        assert stage_id in workflow_stages[workflow_id]
        assert sample["input"].strip()
        assert sample["expectedFocus"]
        assert sample["acceptanceChecks"]
```

Extend packaging tests:

```python
    assert "COPY tools/new-agents/prompt_regression_samples.json /prompt_regression_samples.json" in dockerfile
```

For frontend Dockerfile also require:

```python
    assert "COPY tools/new-agents/prompt_regression_samples.json ./prompt_regression_samples.json" in dockerfile
```

For compose:

```python
    assert "./tools/new-agents/prompt_regression_samples.json:/prompt_regression_samples.json:ro" in dev_compose
    assert "./tools/new-agents/prompt_regression_samples.json:/prompt_regression_samples.json:ro" in dev_cn_compose
```

- [x] **Step 2: Run backend RED check**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

Expected: FAIL because prompt regression samples, stage versions, and packaging entries do not exist yet.

## Task 3: Implement Prompt Regression Samples

**Files:**
- Create: `tools/new-agents/prompt_regression_samples.json`

- [x] **Step 1: Create samples registry**

Create `tools/new-agents/prompt_regression_samples.json` with one sample per online stage. Use ids in the form `<workflow-slug>.<stage-id-lower>.baseline` and fields `id`, `workflowId`, `stageId`, `input`, `expectedFocus`, `acceptanceChecks`.

The registry must include all 17 stage ids:

```json
{
  "samples": [
    {
      "id": "test-design.clarify.baseline",
      "workflowId": "TEST_DESIGN",
      "stageId": "CLARIFY",
      "input": "支付功能上线前，请基于这份 PRD 梳理测试范围、业务规则和待澄清问题。",
      "expectedFocus": ["需求事实", "测试边界", "阻断问题"],
      "acceptanceChecks": ["包含需求事实清单", "标注阻断性问题", "输出阶段门禁"]
    },
    {
      "id": "test-design.strategy.baseline",
      "workflowId": "TEST_DESIGN",
      "stageId": "STRATEGY",
      "input": "基于已确认的支付需求，制定覆盖高风险链路的测试策略。",
      "expectedFocus": ["FMEA", "测试金字塔", "风险覆盖"],
      "acceptanceChecks": ["包含风险优先级", "说明测试分层", "给出覆盖建议"]
    },
    {
      "id": "test-design.cases.baseline",
      "workflowId": "TEST_DESIGN",
      "stageId": "CASES",
      "input": "请把支付需求拆成高优先级测试用例，覆盖成功、失败和边界场景。",
      "expectedFocus": ["用例分组", "覆盖追溯", "自动化候选"],
      "acceptanceChecks": ["包含用例标题", "关联测试点", "标注执行层级"]
    },
    {
      "id": "test-design.delivery.baseline",
      "workflowId": "TEST_DESIGN",
      "stageId": "DELIVERY",
      "input": "请汇总支付功能测试设计，形成可评审交付文档。",
      "expectedFocus": ["执行摘要", "覆盖地图", "交付验收"],
      "acceptanceChecks": ["包含签署确认", "列出开放风险", "包含变更记录"]
    },
    {
      "id": "req-review.review.baseline",
      "workflowId": "REQ_REVIEW",
      "stageId": "REVIEW",
      "input": "请评审会员权益 PRD 的完整性、边界和可测试性。",
      "expectedFocus": ["评审范围", "问题统计", "修订建议"],
      "acceptanceChecks": ["按维度列问题", "标注阻断性", "给出责任方"]
    },
    {
      "id": "req-review.report.baseline",
      "workflowId": "REQ_REVIEW",
      "stageId": "REPORT",
      "input": "请根据需求评审问题清单生成复审报告。",
      "expectedFocus": ["评审结论", "问题关闭", "复审条件"],
      "acceptanceChecks": ["包含判定标准", "列出关闭状态", "包含签署确认"]
    },
    {
      "id": "incident-review.timeline.baseline",
      "workflowId": "INCIDENT_REVIEW",
      "stageId": "TIMELINE",
      "input": "昨天支付失败 P1 事故影响 20 分钟，请先还原事实时间线。",
      "expectedFocus": ["事件概要", "影响量化", "事实推测隔离"],
      "acceptanceChecks": ["包含事实来源", "输出时间线", "列待补充信息"]
    },
    {
      "id": "incident-review.root-cause.baseline",
      "workflowId": "INCIDENT_REVIEW",
      "stageId": "ROOT_CAUSE",
      "input": "基于支付失败时间线，请分析根因并区分证据和假设。",
      "expectedFocus": ["5-Why", "根因证据", "鱼骨图"],
      "acceptanceChecks": ["包含根因结论", "列出排除项", "标注置信度"]
    },
    {
      "id": "incident-review.improvement.baseline",
      "workflowId": "INCIDENT_REVIEW",
      "stageId": "IMPROVEMENT",
      "input": "请把支付失败根因转成 CAPA 改进行动和复查计划。",
      "expectedFocus": ["CAPA", "防复发", "复查计划"],
      "acceptanceChecks": ["每项有 owner", "包含验收标准", "关联根因"]
    },
    {
      "id": "idea-brainstorm.define.baseline",
      "workflowId": "IDEA_BRAINSTORM",
      "stageId": "DEFINE",
      "input": "我想帮独立开发者解决变现难题，请先定义问题域。",
      "expectedFocus": ["问题假设", "目标用户", "证据状态"],
      "acceptanceChecks": ["包含反向验证", "标注约束边界", "输出阶段门禁"]
    },
    {
      "id": "idea-brainstorm.diverge.baseline",
      "workflowId": "IDEA_BRAINSTORM",
      "stageId": "DIVERGE",
      "input": "围绕独立开发者变现难题，请发散多个产品创意。",
      "expectedFocus": ["发散方法", "创意卡片", "创意来源"],
      "acceptanceChecks": ["包含搁置记录", "标注关键假设", "输出发散全景"]
    },
    {
      "id": "idea-brainstorm.converge.baseline",
      "workflowId": "IDEA_BRAINSTORM",
      "stageId": "CONVERGE",
      "input": "请对这些创意做 ICE 收敛评估，并推荐一个 MVP 方向。",
      "expectedFocus": ["ICE", "资源约束", "验证实验"],
      "acceptanceChecks": ["评分有依据", "解释淘汰理由", "给出下一步验证"]
    },
    {
      "id": "idea-brainstorm.concept.baseline",
      "workflowId": "IDEA_BRAINSTORM",
      "stageId": "CONCEPT",
      "input": "请把推荐创意整理成一页产品概念简报。",
      "expectedFocus": ["定位声明", "Lean Canvas", "MVP 范围"],
      "acceptanceChecks": ["包含不可做范围", "列出决策记录", "输出阶段门禁"]
    },
    {
      "id": "value-discovery.elevator.baseline",
      "workflowId": "VALUE_DISCOVERY",
      "stageId": "ELEVATOR",
      "input": "我们想做 AI 测试用例生成工具，请梳理价值定位。",
      "expectedFocus": ["目标用户", "痛点证据", "差异化"],
      "acceptanceChecks": ["包含价值评分", "列未验证假设", "输出阶段门禁"]
    },
    {
      "id": "value-discovery.persona.baseline",
      "workflowId": "VALUE_DISCOVERY",
      "stageId": "PERSONA",
      "input": "请为 AI 测试用例生成工具识别核心用户画像。",
      "expectedFocus": ["用户画像", "决策链", "反画像"],
      "acceptanceChecks": ["标注证据等级", "说明痛点证据", "输出用户优先级"]
    },
    {
      "id": "value-discovery.journey.baseline",
      "workflowId": "VALUE_DISCOVERY",
      "stageId": "JOURNEY",
      "input": "请分析测试负责人从识别需求到生成用例的完整旅程。",
      "expectedFocus": ["JTBD", "RICE", "Kano"],
      "acceptanceChecks": ["包含旅程阶段", "给出机会评分", "设计验证实验"]
    },
    {
      "id": "value-discovery.blueprint.baseline",
      "workflowId": "VALUE_DISCOVERY",
      "stageId": "BLUEPRINT",
      "input": "请把 AI 测试用例生成工具整理成可交接 Lisa 的需求蓝图。",
      "expectedFocus": ["核心需求", "验收标准", "Lisa Handoff"],
      "acceptanceChecks": ["包含 MVP 范围", "列出非功能需求", "输出 handoff 输入"]
    }
  ]
}
```

## Task 4: Add Stage Metadata and Prompt Version Injection

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/frontend/src/core/workflowRegistry.ts`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`

- [x] **Step 1: Extend stage types**

In `workflowRegistry.ts`, add:

```ts
    promptTemplateVersion?: string;
    regressionSampleIds?: string[];
```

In `types.ts`, extend the workflow stage type used by `WorkflowDef.stages` with the same optional fields. If the stage type is inline, add these fields there.

- [x] **Step 2: Add metadata to every manifest stage**

For every stage in `workflow_manifest.json`, add:

```json
"promptTemplateVersion": "2026.06.24.1",
"regressionSampleIds": ["<matching sample id>"]
```

Use the sample ids from Task 3.

- [x] **Step 3: Inject prompt/template version**

In `buildSystemPrompt.ts`, after `const professionalMethodSection = ...`, add:

```ts
    const promptTemplateVersionSection = currentStage.promptTemplateVersion
        ? `\n【Prompt/template 版本】\n当前阶段版本：${currentStage.promptTemplateVersion}\n`
        : '';
```

Add `${promptTemplateVersionSection}` after `${professionalMethodSection}` in the returned prompt.

## Task 5: Container and Sync Test Updates

**Files:**
- Modify: `tools/new-agents/docker/Dockerfile`
- Modify: `tools/new-agents/backend/docker/Dockerfile`
- Modify: `docker-compose.dev.yml`
- Modify: `docker-compose.dev-cn.yml`

- [x] **Step 1: Add frontend Docker copies**

In `tools/new-agents/docker/Dockerfile`, add after professional method copies:

```dockerfile
COPY tools/new-agents/prompt_regression_samples.json ./prompt_regression_samples.json
COPY tools/new-agents/prompt_regression_samples.json /prompt_regression_samples.json
```

- [x] **Step 2: Add backend Docker copy**

In `tools/new-agents/backend/docker/Dockerfile`, add:

```dockerfile
COPY tools/new-agents/prompt_regression_samples.json /prompt_regression_samples.json
```

- [x] **Step 3: Add compose mounts**

In both dev compose files, under `new-agents-backend.volumes`, add:

```yaml
      - ./tools/new-agents/prompt_regression_samples.json:/prompt_regression_samples.json:ro
```

## Task 6: GREEN Verification

**Files:**
- Validate all implementation files.

- [x] **Step 1: Run frontend prompt tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: PASS.

- [x] **Step 2: Run backend sync tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

Expected: PASS.

- [x] **Step 3: Run frontend build**

Run:

```bash
cd tools/new-agents/frontend && npm run build
```

Expected: PASS. Existing large chunk warning is acceptable if no new build error appears.

- [x] **Step 4: Run formatting and document checks**

Run:

```bash
rg "\bTB[D]\b|\bTO[D]O\b|占[位]" docs/superpowers/specs/2026-06-24-prompt-template-versioning-design.md docs/superpowers/plans/2026-06-24-prompt-template-versioning.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md
git diff --check
```

Expected: no matches; diff check exits 0.

## Task 7: Todo Update and Commit

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Add/Modify: all files from this plan.

- [x] **Step 1: Update E11 status**

Change E11 acceptance text to:

```markdown
已完成待合回: 每个 online stage 通过 `promptTemplateVersion` 记录 prompt/template 版本，并通过 `regressionSampleIds` 关联 `prompt_regression_samples.json` 中的回归样例；同步测试阻止漏版本、未知样例和样例指向错误。
```

Add or update remaining section:

```markdown
## 当前剩余能力包

功能能力包已清空；后续进入最终集成、主线验证、merge/push/删分支闭环。
```

- [x] **Step 2: Review scope**

Run:

```bash
git status --short
git diff --stat
```

Expected: only this milestone's `tools/new-agents/`, compose files, spec, plan, and refactor todo docs are changed.

- [x] **Step 3: Commit**

Run:

```bash
git add tools/new-agents/prompt_regression_samples.json tools/new-agents/workflow_manifest.json tools/new-agents/frontend/src/core/workflowRegistry.ts tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/docker/Dockerfile tools/new-agents/backend/docker/Dockerfile docker-compose.dev.yml docker-compose.dev-cn.yml docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/superpowers/specs/2026-06-24-prompt-template-versioning-design.md docs/superpowers/plans/2026-06-24-prompt-template-versioning.md
git commit -m "feat(new-agents): 增加 prompt template 版本治理"
```

## Self-Review

- Spec coverage: plan covers all stage versions, all stage regression sample ids, prompt injection, sync tests, packaging, todo update, and commit.
- Placeholder scan: use word-boundary `\bTB[D]\b|\bTO[D]O\b|占[位]` to avoid false matches.
- Type consistency: stage metadata fields are `promptTemplateVersion?: string` and `regressionSampleIds?: string[]` everywhere.
