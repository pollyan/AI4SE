# New Agents Workflow Contract 机械同步闭环实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 workflow 的纯声明性契约从手工镜像收口为 manifest 派生数据，并为剩余代码注册表建立直接的漂移门禁。

**Architecture:** `workflow_manifest.json` 继续是 workflow/stage、artifact heading 和 visual requirement 的声明式入口。后端 `agent_contracts.py` 在模块初始化时通过既有 `workflow_contract_registry.py` 派生兼容的公共常量，保持其现有消费者不变；Pydantic schema、renderer 和 runtime 示例等行为实现继续留在代码中。前端从 manifest 类型派生 `WorkflowType`，并以当前 stage 的 `artifactDataContract` 判断结构化模式，移除手工阶段集合。

**Tech Stack:** Python 3.11、pytest、TypeScript 5.x、Vitest、Vite JSON module imports。

---

## 目标承接检查

### 事实源快照

- 已读取：`AGENTS.md`、活跃 todo、切片 1 实施记录、`workflow_contract_registry.py`、`agent_contracts.py`、`buildSystemPrompt.ts`、`types.ts`、相关 pytest/Vitest 测试。
- 基线：backend `test_workflow_contract_registry.py`、`test_workflow_contract_sync.py`、`test_artifact_data_renderers.py`、`test_agent_runtime.py` 为 426 passed；frontend `workflows.test.ts` 与 `buildSystemPrompt.test.ts` 为 116 passed。
- 当前问题：后端已经有 manifest registry，但 `agent_contracts.py` 仍手工复制 stage、artifact heading 和 visual contract；前端仍手工定义 online workflow union 和全部 artifact-data stage 集合。
- 固定边界：不改 `/api/agent/runs/stream`、typed SSE event、run persistence 或 agent-specific 基础设施；不将 Pydantic schema、renderer implementation、runtime 结构化示例迁入 JSON；不修改 `tools/intent-tester/`。

### 方案比较与选择

| 候选 | 结论 |
| --- | --- |
| 每次消费时直接遍历 manifest | 可行但会改变多个既有公共 map 的使用方式，增加调用期错误面。 |
| 模块初始化时通过 registry 派生既有公共 map | **采用。** 消除手工值，同时保持 runtime/persistence 现有消费 API 和失败语义不变。 |
| 将 schema、renderer 和 runtime 示例全部迁入 manifest | 不采用。它们属于行为实现和强类型验证，不是纯声明元数据。 |

切片 2 的工程闭环：新增或修改 workflow/stage 时，manifest 驱动的 backend contract、frontend type/registry 和 prompt mode 一起变化；若删回手工镜像或漏掉 renderer/runtime/handoff/regression 其中任一注册，现有同步测试和本轮新增的直接 guard 会失败。

## 文件边界

- Modify: `tools/new-agents/backend/agent_contracts.py` - 从 registry 派生声明性 backend contract maps，保留 schema 和 validation 行为。
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_registry.py` - 证明公共 contract maps 的定义直接调用 manifest registry，而非复制字面量。
- Modify: `tools/new-agents/frontend/src/core/types.ts` - 从 manifest 类型派生 online `WorkflowType`。
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts` - 用当前 stage 的 manifest contract 选择 artifact-data prompt mode。
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts` - 固定 workflow type 的 manifest 派生边界。
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts` - 固定 artifact-data mode 不再维护 workflow/stage 手工集合。
- Modify: `docs/todos/2026-07-10-new-agents-architecture-refactor.md` - 完成后记录切片 2 的证据、遗留质量门和下一入口。

## TDD 实施任务

### Task 1: 后端声明性 contract map 必须由 registry 派生

**Files:**
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_registry.py`
- Modify: `tools/new-agents/backend/agent_contracts.py`

- [x] **Step 1: 写入失败的定义来源测试。** 使用 `ast` 读取 `agent_contracts.py`，断言 `WORKFLOW_STAGES`、`REQUIRED_ARTIFACT_HEADINGS`、`REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` 和 `REQUIRED_ARTIFACT_STRUCTURED_VISUALS` 分别由对应 `get_*` registry helper 的调用赋值。
- [x] **Step 2: 运行 RED。**

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_registry.py -q
```

Expected: 新测试因为目标常量仍是字面量 `dict` 而失败。

- [x] **Step 3: 最小实现。** 在 `agent_contracts.py` 导入四个 registry helper，以相同公共常量名调用它们；删除重复的 stage、heading、Mermaid 和 structured visual 字面量。保留 `REQUIRED_ARTIFACT_H1_KEYWORDS` 与 `STRUCTURED_VISUAL_SCHEMA_PROMPTS`。
- [x] **Step 4: 运行 GREEN。** 重跑 Step 2 命令，期望所有测试通过。

### Task 2: 前端 workflow 与 artifact-data mode 从 manifest 派生

**Files:**
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`

- [x] **Step 1: 写入失败的前端架构 guard。** 测试读取 `types.ts`，断言 `WorkflowType` 使用 `keyof typeof workflowManifestData.workflows`，且不再有手工 union；读取 `buildSystemPrompt.ts`，断言不含 `ARTIFACT_DATA_STAGE_IDS`，并使用 `Boolean(currentStage.artifactDataContract)` 作为 mode 开关。
- [x] **Step 2: 运行 RED。**

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

Expected: 新的 source guard 因旧手工 union 和 stage set 失败。

- [x] **Step 3: 最小实现。** 在 `types.ts` 增加 JSON manifest 的 type-only import 并派生 `WorkflowType`；删除 `ARTIFACT_DATA_STAGE_IDS` 与 helper，令 `usesArtifactData` 直接读取 `currentStage.artifactDataContract`。
- [x] **Step 4: 运行 GREEN。** 重跑 Step 2 命令，期望 workflow/prompt 行为和新 guard 一起通过。

### Task 3: 扩展同步回归、记录与提交

**Files:**
- Modify: `docs/todos/2026-07-10-new-agents-architecture-refactor.md`

- [x] **Step 1: 运行后端完整契约回归。**

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest \
  tools/new-agents/backend/tests/test_workflow_contract_registry.py \
  tools/new-agents/backend/tests/test_workflow_contract_sync.py \
  tools/new-agents/backend/tests/test_artifact_data_renderers.py \
  tools/new-agents/backend/tests/test_agent_runtime.py -q
```

- [x] **Step 2: 运行前端定向回归与类型检查。**

```bash
cd tools/new-agents/frontend && npm run test -- --run \
  src/core/config/__tests__/workflows.test.ts \
  src/core/prompts/__tests__/buildSystemPrompt.test.ts
npm run lint
```

Expected: 定向 Vitest 通过；`npm run lint` 的既有 `StructuredVisual.tsx`、`artifactExport.ts`、`docxExport.ts` 联合类型错误如仍存在，必须记录为切片 6 基线，不在本切片混修。

- [x] **Step 3: 更新活跃 todo。** 仅记录实际变更、验证结果、遗留质量门并勾选切片 2；不改后续切片的范围和顺序。
- [x] **Step 4: 审查并提交。** 运行 `git diff --check`、检查 diff 和状态；提交仅包含本计划的 source/test/doc 文件，且不包含前端 `node_modules` 符号链接。

## 自检

- 后端 map 派生、前端 type 派生与 prompt mode 派生都有 RED 测试和 GREEN 回归。
- runtime instruction、renderer registry、regression sample、handoff template 的完整性继续由既有 contract sync/renderer/runtime 测试覆盖。
- 不创建 agent-specific runtime、transport、store、API 或 renderer；不会把尚未完成的后续文件边界重构带入本切片。

## 执行结果

- RED：backend 新 guard 因 `agent_contracts.py` 使用字面量 map 失败；frontend 两个 guard 分别因手工 union 和 `ARTIFACT_DATA_STAGE_IDS` 失败。机械删除后，guard 还捕获 Mermaid/structured visual map 的重复赋值并阻止其覆盖派生结果。
- GREEN：`test_workflow_contract_registry.py` 为 5 passed；扩展 backend contract/runtime/renderer suite 为 427 passed；frontend 定向 suite 为 118 passed。
- 完整回归：`./scripts/test/test-local.sh new-agents` 通过，frontend 853 passed，backend 890 passed、4 deselected。
- 已知基线：`npm run lint` 仍在未触碰的 `StructuredVisual.tsx`、`artifactExport.ts` 和 `docxExport.ts` 失败于 `MatrixStructuredVisual | NodeEdgeStructuredVisual` 的 `columns/rows` 访问；本切片未修复也未扩大范围。
