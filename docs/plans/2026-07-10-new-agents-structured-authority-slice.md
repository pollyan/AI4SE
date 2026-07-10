# New Agents 结构化权威链路闭环实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Lisa CASES 测试资产和前端阶段推进只消费结构化的权威输入，消除 Markdown 与聊天文案对状态语义的反向影响。

**Architecture:** 服务端将已持久化的 `artifactData` 作为 TEST_DESIGN/CASES 导出的首选输入，使用明确的字段映射生成既有测试资产 payload；仅缺少该数据的历史 artifact 才允许使用 Markdown 兼容解析。前端继续验证 typed `stage_action` 的目标阶段，但不再从 `chat` 文案推断推进状态。

**Tech Stack:** Python 3.11、Flask、pytest、TypeScript 5.x、Vitest。

---

## 目标承接检查

### 事实源快照

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/todos/2026-07-10-new-agents-architecture-refactor.md`、`backend/test_assets.py`、`backend/test_asset_parsing.py`、`backend/run_persistence.py`、`backend/artifact_data_renderers.py`、对应 pytest/Vitest 测试。
- 当前代码：artifact version 已持久化并恢复 `artifactData`；`export_lisa_test_assets()` 仍无条件解析 Markdown；`llm.ts` 的 `shouldInferNextStageActionFromChat()` 仍可产生 `NEXT_STAGE`。
- 基线：backend `test_test_assets.py` 与 `test_test_asset_parsing.py` 为 32 passed；frontend `llm.test.ts` 为 79 passed。
- 工作区：在 `codex/new-agents-architecture-slice-1` 隔离 worktree 执行；未接触 `tools/intent-tester/`。前端依赖通过本地忽略的 `node_modules` 符号链接复用主工作区，未变更依赖版本。

### 能力包与选择

| 候选 | 工程信任闭环 | 本轮决定 |
| --- | --- | --- |
| 结构化权威链路 | 下游测试资产不依赖渲染后的 Markdown；前端阶段动作不依赖自然语言；错误有明确来源 | 本轮执行 |
| Workflow contract 机械同步 | 新增 workflow 时由 manifest/contract/renderer 测试发现漏配 | 保留为 todo 切片 2 |

切片 1 通过厚度门禁：调用方入口是已完成 CASES artifact 或 `/api/agent/runs/stream` 的 `agent_turn`；系统处理为结构化资产转换和 typed stage action；结果是可导出的资产或明确失败/无推进；状态承接为服务端 artifact version 和既有前端 action；证据为 pytest 与 Vitest。它不是单个 parser 或单个正则调整，而是收紧同一条权威输入边界。

本轮用户故事：作为消费 Lisa 测试资产或继续工作流的调用方，当 CASES artifact 已有服务端持久化的结构化结果时，我可以获得不依赖 Markdown 文案的测试资产，并且只有有效 typed SSE 阶段动作才会显示推进入口，从而避免格式变化和自然语言误判改变系统状态。

### 自问自答设计

- **Visual Companion Decision：** 不需要。本轮不改变可视化布局或视觉资产，只收紧数据与状态协议。
- **输入权威性：** 已有 `artifactData` 时，不能在其无效后静默退回 Markdown；这会掩盖持久化或 contract 损坏。只有 `artifactData` 缺失的历史版本可声明为 legacy Markdown source。
- **兼容策略：** 返回 `sourceFormat` 表示 `artifact_data` 或 `legacy_markdown`，让调用方和排障记录能够识别兼容路径；不新建 endpoint 或持久化表。
- **数据转换位置：** 在 `test_asset_parsing.py` 增加 `build_lisa_test_assets_from_artifact_data()`，复用既有 coverage、risk、issue 和 intent-tester draft 生成器，避免在 `test_assets.py` 复制派生逻辑。
- **阶段推进：** `stage_action` 已有 schema 和目标阶段校验，chat 只能是呈现内容；删除 chat 正则推断，保留截断/门禁抑制逻辑。
- **不选方案：** 不移除 Markdown parser，因为历史 run 没有 `artifactData`；不修改 Runtime/SSE event shape，因为该切片只收紧其消费者。

## 文件边界

- Modify: `tools/new-agents/backend/test_asset_parsing.py` — 将 CASES `artifactData` 映射为现有测试资产 payload，并在字段无效时抛出可诊断错误。
- Modify: `tools/new-agents/backend/test_assets.py` — 根据 `artifactData` 是否存在选择结构化路径或历史 Markdown 路径，并返回来源标记。
- Modify: `tools/new-agents/backend/tests/test_test_asset_parsing.py` — 锁定结构化数据映射与字段校验。
- Modify: `tools/new-agents/backend/tests/test_test_assets.py` — 锁定结构化优先、legacy 标记和无静默 fallback。
- Modify: `tools/new-agents/frontend/src/core/llm.ts` — 删除 chat 正则状态推断，仅消费 typed `stage_action`。
- Modify: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts` — 锁定“建议进入下一阶段”的 chat 在缺少 `stage_action` 时不产生动作。
- Modify: `docs/todos/2026-07-10-new-agents-architecture-refactor.md` — 完成后写入实际证据并勾选切片 1。

## TDD 实施任务

### Task 1: 锁定 CASES 的结构化导出优先级

**Files:**
- Modify: `tools/new-agents/backend/tests/test_test_assets.py`
- Modify: `tools/new-agents/backend/tests/test_test_asset_parsing.py`

- [x] **Step 1: 写入结构化优先的失败测试。** 创建含 `VALID_CASES_ARTIFACT_DATA` 但 Markdown 内容不含表格的 CASES artifact；断言 `export_lisa_test_assets()` 返回两个 case、正确 coverage，并返回 `sourceFormat == "artifact_data"`。现有实现会尝试解析无效 Markdown 而失败。
- [x] **Step 2: 写入无静默 fallback 的失败测试。** 创建有合法 Markdown、但 `artifactData` 为缺少 `case_groups` 或 `coverage_trace` 的对象的 artifact；断言导出抛出 `ValueError`，而不是退回 Markdown。
- [x] **Step 3: 更新历史兼容断言。** 现有 Markdown-only fixture 应继续导出成功，并断言 `sourceFormat == "legacy_markdown"`；同时将 intent-tester draft 文案从“Markdown 用例”改为不依赖来源格式的“Lisa 测试用例”。
- [x] **Step 4: 运行 RED。**

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_test_assets.py tools/new-agents/backend/tests/test_test_asset_parsing.py -q
```

Expected: 至少结构化优先、来源标记和无 fallback 测试因当前 Markdown-only 实现失败。

### Task 2: 实现结构化 CASES 资产转换

**Files:**
- Modify: `tools/new-agents/backend/test_asset_parsing.py`
- Modify: `tools/new-agents/backend/test_assets.py`

- [x] **Step 1: 实现 `build_lisa_test_assets_from_artifact_data(artifact_data)`。** 读取 `case_groups` 与 `coverage_trace`，将 snake_case CASES 字段映射为既有 camelCase test asset 字段；复用 `build_coverage_summary()`、`build_risk_matrix()`、`_build_asset_issues()` 和 `build_intent_tester_drafts()`。
- [x] **Step 2: 为缺失/错误的结构化字段抛出带字段路径的 `ValueError`。** `artifactData` 存在但不是有效 CASES 结构时不得调用 Markdown parser。
- [x] **Step 3: 在 `export_lisa_test_assets()` 中选择来源。** `artifactData is not None` 时调用结构化转换并返回 `sourceFormat: "artifact_data"`；仅为 `None` 时调用 `parse_lisa_test_asset_markdown()` 并返回 `sourceFormat: "legacy_markdown"`。
- [x] **Step 4: 运行 GREEN。** 使用 Task 1 命令，期望全部通过。

### Task 3: 移除 chat 驱动的阶段状态推断

**Files:**
- Modify: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
- Modify: `tools/new-agents/frontend/src/core/llm.ts`

- [x] **Step 1: 修改现有“建议确认进入下一阶段”测试。** 保留 chat 文案与 `stage_action: null`，但断言最终 `action` 为空字符串；当前实现应失败，因为它返回 `NEXT_STAGE`。
- [x] **Step 2: 删除 `shouldInferNextStageActionFromChat()`。** `getAgentTurnAction()` 只在 `output.stage_action` 存在且未被截断/门禁警告阻止时返回 `NEXT_STAGE`；同步更新三个 streaming mapper 调用点。
- [x] **Step 3: 运行 GREEN。**

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts
```

Expected: 所有 stream parser 测试通过，且已有 `stage_action` 目标阶段校验仍有效。

### Task 4: 回归、记录与提交边界

**Files:**
- Modify: `docs/todos/2026-07-10-new-agents-architecture-refactor.md`

- [x] **Step 1: 运行后端与前端定向回归。**

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_test_assets.py tools/new-agents/backend/tests/test_test_asset_parsing.py -q
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts
git diff --check
```

- [x] **Step 2: 更新 todo 的切片 1 执行记录。** 只记录实际文件、命令、结果与遗留风险；将第 2 切片保留为下一轮。
- [x] **Step 3: 审查本切片 diff。** 仅允许本计划列出的 backend/frontend/test/doc 文件及此前已确认的 `AGENTS.md`、todo 索引进入提交；不触碰 `tools/intent-tester/`。

## 执行结果

- RED：backend 4 项失败，分别证明当前缺少来源标记、仍反解析 Markdown、会在损坏 `artifactData` 时静默使用 Markdown、且没有结构化转换器；frontend 1 项失败，证明 chat 文案仍产生 `NEXT_STAGE`。
- GREEN：定向 backend 为 35 passed，frontend 为 79 passed；扩展 backend 为 116 passed。
- 完整模块回归：`./scripts/test/test-local.sh new-agents` 通过，frontend 851 passed，backend 889 passed、4 deselected。
- 已知基线：`npm run lint` 在主工作区与本 worktree 均失败于未触碰的 StructuredVisual/export/docx union narrowing 错误；本切片不包含该修复，且不会据此 push。

## 自检

- 结构化优先、历史兼容、无 silent fallback、typed stage action 四个需求均由上面的任务覆盖。
- 未定义新的 API、SSE event、数据库字段或 agent-specific 基础设施。
- 切片 2 至 6 未进入本计划；没有 `1A/1B` 式内部批次。
