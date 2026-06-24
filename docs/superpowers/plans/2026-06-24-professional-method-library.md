# E10 专业方法库配置 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 New Agents workflow stage 可以通过共享配置声明专业方法包，并在系统提示中稳定注入方法说明。

**Architecture:** 新增 `tools/new-agents/professional_methods.json` 作为共享方法库；`workflow_manifest.json` 的 stage 通过 `methodIds` 引用方法；前端 prompt builder 读取 `WORKFLOWS` 的 stage method ids 并注入“专业方法参考”；后端同步测试校验 manifest 引用合法、容器配置会打包方法库。

**Tech Stack:** JSON manifest, TypeScript 5.x, Vitest, Python pytest, existing New Agents shared runtime contracts.

---

## File Structure

- Create: `tools/new-agents/professional_methods.json`
  - 共享专业方法 registry，包含 `id`、`name`、`description`、`guidance`。
- Create: `tools/new-agents/frontend/src/core/professionalMethods.ts`
  - TypeScript 读取方法库并构造 prompt section；未知 id 直接抛错。
- Modify: `tools/new-agents/workflow_manifest.json`
  - 在代表性 stage 上新增 `methodIds`。
- Modify: `tools/new-agents/frontend/src/core/workflowRegistry.ts`
  - 把 stage 类型扩展为可选 `methodIds`。
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`
  - 当前 stage 有 method ids 时注入“专业方法参考”。
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`
  - 增加 RED/GREEN prompt 注入测试和未知 id 测试。
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
  - 增加 registry 和 manifest 引用同步测试；增加 Docker/Compose packaging 断言。
- Modify: `tools/new-agents/docker/Dockerfile`, `tools/new-agents/backend/docker/Dockerfile`, `docker-compose.dev.yml`, `docker-compose.dev-cn.yml`
  - 确保容器环境能读取共享方法库。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - 将 E10 标记为已完成待合回，保留 E11。

## Task 1: RED Frontend Prompt Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`

- [x] **Step 1: Add failing tests**

Append these tests inside `describe('buildSystemPrompt', () => { ... })`:

```ts
    it('injects professional method guidance for configured Lisa strategy stages', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentArtifact: '# 测试策略蓝图',
        });

        expect(prompt).toContain('【专业方法参考】');
        expect(prompt).toContain('FMEA 失效模式与影响分析');
        expect(prompt).toContain('测试金字塔');
        expect(prompt).toContain('风险优先级');
    });

    it('injects product discovery methods for configured Alex journey stages', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'VALUE_DISCOVERY',
            stageIndex: 2,
            currentArtifact: '# 用户旅程分析',
        });

        expect(prompt).toContain('【专业方法参考】');
        expect(prompt).toContain('JTBD 任务理论');
        expect(prompt).toContain('RICE 优先级评分');
        expect(prompt).toContain('Kano 需求分层');
    });

    it('does not inject an empty professional method section for stages without method ids', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 需求分析文档',
        });

        expect(prompt).not.toContain('【专业方法参考】');
    });
```

- [x] **Step 2: Run frontend RED check**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: FAIL because `buildSystemPrompt()` does not inject professional method guidance yet.

Actual: failed with 2 assertion failures because `【专业方法参考】` was missing from Lisa strategy and Alex journey prompts. A temporary worktree `node_modules` symlink to the main workspace dependency tree was used only to run Vitest.

## Task 2: RED Backend Manifest Sync Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

- [x] **Step 1: Add failing sync tests**

Add near the manifest helper functions:

```python
PROFESSIONAL_METHODS = NEW_AGENTS_ROOT / "professional_methods.json"


def _professional_methods() -> dict:
    return json.loads(PROFESSIONAL_METHODS.read_text(encoding="utf-8"))
```

Add tests after `test_shared_workflow_manifest_stage_keys_match_frontend_prompt_templates`:

```python
def test_professional_method_registry_has_required_fields():
    methods = _professional_methods()["methods"]

    assert {method["id"] for method in methods} >= {
        "fmea",
        "test_pyramid",
        "jtbd",
        "rice",
        "kano",
        "capa",
        "ice",
    }
    for method in methods:
        assert method["id"].strip()
        assert method["name"].strip()
        assert method["description"].strip()
        assert method["guidance"].strip()


def test_workflow_manifest_professional_method_ids_are_known():
    known_method_ids = {method["id"] for method in _professional_methods()["methods"]}
    manifest = _workflow_manifest()

    for workflow_id, workflow in manifest["workflows"].items():
        for stage in workflow["stages"]:
            for method_id in stage.get("methodIds", []):
                assert method_id in known_method_ids, f"{workflow_id}/{stage['id']} references unknown method {method_id}"


def test_representative_stages_declare_professional_methods():
    manifest = _workflow_manifest()

    expected = {
        ("TEST_DESIGN", "STRATEGY"): {"fmea", "test_pyramid"},
        ("INCIDENT_REVIEW", "IMPROVEMENT"): {"capa"},
        ("VALUE_DISCOVERY", "JOURNEY"): {"jtbd", "rice", "kano"},
        ("IDEA_BRAINSTORM", "CONVERGE"): {"ice"},
    }

    for (workflow_id, stage_id), method_ids in expected.items():
        stage = next(
            stage
            for stage in manifest["workflows"][workflow_id]["stages"]
            if stage["id"] == stage_id
        )
        assert set(stage.get("methodIds", [])) >= method_ids
```

Extend packaging tests with assertions for `professional_methods.json`:

```python
    assert "COPY tools/new-agents/professional_methods.json /professional_methods.json" in dockerfile
```

and:

```python
    assert "./tools/new-agents/professional_methods.json:/professional_methods.json:ro" in dev_compose
    assert "./tools/new-agents/professional_methods.json:/professional_methods.json:ro" in dev_cn_compose
```

- [x] **Step 2: Run backend RED check**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

Expected: FAIL because `professional_methods.json`, manifest `methodIds`, and container packaging entries do not exist yet.

Actual: failed with 5 expected failures covering missing `professional_methods.json`, missing representative stage `methodIds`, and missing Docker/Compose packaging entries.

## Task 3: Implement Shared Method Registry

**Files:**
- Create: `tools/new-agents/professional_methods.json`
- Create: `tools/new-agents/frontend/src/core/professionalMethods.ts`
- Modify: `tools/new-agents/frontend/src/core/workflowRegistry.ts`

- [x] **Step 1: Create method registry JSON**

Create `tools/new-agents/professional_methods.json`:

```json
{
  "methods": [
    {
      "id": "fmea",
      "name": "FMEA 失效模式与影响分析",
      "description": "识别失效模式、影响、原因和现有控制，按严重度、发生概率和可探测性判断风险优先级。",
      "guidance": "用于测试策略和风险分析阶段；要求把高风险项连接到测试覆盖、缓解措施和验收门禁。"
    },
    {
      "id": "test_pyramid",
      "name": "测试金字塔",
      "description": "按单元、服务、集成、端到端等层级规划自动化覆盖和反馈速度。",
      "guidance": "用于测试策略阶段；要求说明每层覆盖目标、适用风险、取舍和不自动化原因。"
    },
    {
      "id": "jtbd",
      "name": "JTBD 任务理论",
      "description": "围绕用户要完成的任务、触发情境、阻力和期望结果识别真实价值。",
      "guidance": "用于价值发现和用户旅程阶段；要求把用户场景、痛点证据和机会点连接到任务进展。"
    },
    {
      "id": "rice",
      "name": "RICE 优先级评分",
      "description": "用覆盖人数、影响力、信心和工作量对机会或需求排序。",
      "guidance": "用于机会排序阶段；要求标注评分依据、证据强度和对优先级结论的影响。"
    },
    {
      "id": "kano",
      "name": "Kano 需求分层",
      "description": "区分基本型、期望型、兴奋型和无差异需求，辅助产品范围取舍。",
      "guidance": "用于需求分层和旅程机会分析；要求说明每类需求的用户满意度影响和验证方式。"
    },
    {
      "id": "capa",
      "name": "CAPA 纠正预防措施",
      "description": "把事故改进拆成纠正措施、预防措施、验证方法和追踪机制。",
      "guidance": "用于故障复盘改进阶段；要求每个行动项关联根因、owner、期限、验收标准和复查机制。"
    },
    {
      "id": "ice",
      "name": "ICE 收敛评分",
      "description": "用影响力、信心和实施难度对创意或方案做轻量排序。",
      "guidance": "用于创意收敛阶段；要求评分有证据依据，并解释推荐、淘汰和验证实验。"
    }
  ]
}
```

- [x] **Step 2: Create TypeScript registry helper**

Create `tools/new-agents/frontend/src/core/professionalMethods.ts`:

```ts
import professionalMethodsData from '../../../professional_methods.json';

type ProfessionalMethod = {
    id: string;
    name: string;
    description: string;
    guidance: string;
};

const PROFESSIONAL_METHODS = professionalMethodsData.methods as ProfessionalMethod[];

export const getProfessionalMethods = (methodIds: readonly string[] = []): ProfessionalMethod[] => {
    return methodIds.map((methodId) => {
        const method = PROFESSIONAL_METHODS.find(candidate => candidate.id === methodId);
        if (!method) {
            throw new Error(`Unknown professional method id: ${methodId}`);
        }
        return method;
    });
};

export const buildProfessionalMethodPromptSection = (methodIds: readonly string[] = []): string => {
    const methods = getProfessionalMethods(methodIds);
    if (methods.length === 0) {
        return '';
    }

    const lines = methods.map(
        method => `- ${method.name}: ${method.description}${method.guidance ? ` 使用要求：${method.guidance}` : ''}`
    );

    return `\n【专业方法参考】\n${lines.join('\n')}\n`;
};
```

- [x] **Step 3: Extend workflow stage type**

In `tools/new-agents/frontend/src/core/workflowRegistry.ts`, change `WorkflowManifestStage`:

```ts
export type WorkflowManifestStage = {
    id: string;
    name: string;
    promptTemplateId: string;
    methodIds?: string[];
};
```

## Task 4: Connect Manifest and Prompt Builder

**Files:**
- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`

- [x] **Step 1: Add representative methodIds to manifest**

Add `methodIds` to these stages:

```json
{ "id": "STRATEGY", "name": "策略制定", "promptTemplateId": "test_design.strategy", "methodIds": ["fmea", "test_pyramid"] }
```

```json
{ "id": "IMPROVEMENT", "name": "改进措施", "promptTemplateId": "incident_review.improvement", "methodIds": ["capa"] }
```

```json
{ "id": "JOURNEY", "name": "用户旅程", "promptTemplateId": "value_discovery.journey", "methodIds": ["jtbd", "rice", "kano"] }
```

```json
{ "id": "CONVERGE", "name": "收敛聚焦", "promptTemplateId": "idea_brainstorm.converge", "methodIds": ["ice"] }
```

- [x] **Step 2: Inject method prompt section**

In `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`, add import:

```ts
import { buildProfessionalMethodPromptSection } from '../professionalMethods';
```

After `const currentStage = wf.stages[stageIndex];`, add:

```ts
    const professionalMethodSection = buildProfessionalMethodPromptSection(currentStage.methodIds);
```

In the returned prompt, add after `阶段目标：${currentStage.description}`:

```ts
${professionalMethodSection}
```

## Task 5: Container and Sync Test Updates

**Files:**
- Modify: `tools/new-agents/docker/Dockerfile`
- Modify: `tools/new-agents/backend/docker/Dockerfile`
- Modify: `docker-compose.dev.yml`
- Modify: `docker-compose.dev-cn.yml`

- [x] **Step 1: Add frontend Docker copy**

In `tools/new-agents/docker/Dockerfile`, add after workflow manifest copy:

```dockerfile
COPY tools/new-agents/workflow_manifest.json ./workflow_manifest.json
COPY tools/new-agents/professional_methods.json /professional_methods.json
COPY tools/new-agents/professional_methods.json ./professional_methods.json
```

Actual: added both existing root-style package copies and Vite working-directory copies. A focused packaging RED test first failed on missing `./workflow_manifest.json`, then passed after the Dockerfile update.

- [x] **Step 2: Add backend Docker copy**

In `tools/new-agents/backend/docker/Dockerfile`, add after workflow manifest copy:

```dockerfile
COPY tools/new-agents/professional_methods.json /professional_methods.json
```

Actual: added backend root copy for the shared method registry.

- [x] **Step 3: Add backend compose mounts**

In both `docker-compose.dev.yml` and `docker-compose.dev-cn.yml`, add under `new-agents-backend.volumes`:

```yaml
      - ./tools/new-agents/professional_methods.json:/professional_methods.json:ro
```

Actual: added the read-only backend mount to both dev compose files.

## Task 6: GREEN Verification

**Files:**
- Validate all implementation files.

- [x] **Step 1: Run frontend prompt tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: PASS.

Actual: PASS, 25 tests passed.

- [x] **Step 2: Run backend sync tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

Expected: PASS.

Actual: PASS, 13 tests passed.

- [x] **Step 3: Run formatting and placeholder checks**

Run:

```bash
rg "\bTB[D]\b|\bTO[D]O\b|占[位]" docs/superpowers/specs/2026-06-24-professional-method-library-design.md docs/superpowers/plans/2026-06-24-professional-method-library.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md
git diff --check
```

Expected: `rg` returns no matches; `git diff --check` exits 0.

Actual: placeholder scan returned no matches and `git diff --check` exited 0. Additional CI-equivalent frontend build was run with `cd tools/new-agents/frontend && npm run build`; it passed with the existing large chunk warning only.

## Task 7: Todo Update and Commit

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Add/Modify: all files from this plan.

- [x] **Step 1: Update E10 status**

Change E10 acceptance text to:

```markdown
已完成待合回: 专业方法库通过 `professional_methods.json` 统一配置，代表性 stage 通过 `methodIds` 引用 FMEA、测试金字塔、JTBD、RICE、Kano、CAPA、ICE，并由 prompt builder 注入系统提示；同步测试阻止未知方法引用。
```

Add or update the remaining section:

```markdown
## 当前剩余能力包

- E11 Prompt/template 版本管理。

其余 E 编号如果需要恢复，必须先通过 CGA 证明当前主线集成后仍存在回归或未验收缺口。
```

Actual: E10 now records the shared `professional_methods.json`, representative stage `methodIds`, prompt injection, and sync-test gate. The remaining section keeps E11 as the active capability package.

- [x] **Step 2: Review scope**

Run:

```bash
git status --short
git diff --stat
```

Expected: only this milestone's `tools/new-agents/`, `docker-compose*.yml`, spec, plan, and refactor todo docs are changed.

Actual: scope review shows only this milestone's `tools/new-agents/`, `docker-compose*.yml`, spec, plan, and refactor todo docs changed; temporary `node_modules` symlink was removed before scope review.

- [ ] **Step 3: Commit**

Run:

```bash
git add tools/new-agents/professional_methods.json tools/new-agents/frontend/src/core/professionalMethods.ts tools/new-agents/frontend/src/core/workflowRegistry.ts tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts tools/new-agents/workflow_manifest.json tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/docker/Dockerfile tools/new-agents/backend/docker/Dockerfile docker-compose.dev.yml docker-compose.dev-cn.yml docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/superpowers/specs/2026-06-24-professional-method-library-design.md docs/superpowers/plans/2026-06-24-professional-method-library.md
git commit -m "feat(new-agents): 配置化专业方法库"
```

## Self-Review

- Spec coverage: plan covers method registry, manifest method references, prompt injection, sync tests, container packaging, todo update, and commit.
- Placeholder scan: use explicit `\bTB[D]\b|\bTO[D]O\b|占[位]` check to avoid matching method names such as JTBD or legitimate workflow state words.
- Type consistency: method ids are strings from JSON registry, `WorkflowManifestStage.methodIds?: string[]`, prompt helper accepts `readonly string[]`.
