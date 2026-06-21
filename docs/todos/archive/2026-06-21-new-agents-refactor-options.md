# New Agents 智能体重构方案设计

## 状态

- 类型：第二轮方案设计
- 输入：`docs/todos/refactor/2026-06-21-new-agents-refactor-scan.md`
- 当前状态：方案设计完成
- 产出目标：基于第一轮扫描结果，比较 2-3 套可执行重构方案，并给出推荐路线；不进入实施计划和编码

## 设计原则

- 本轮只做方案设计，不修改代码、配置、测试或业务文档。
- 方案必须继承第一轮扫描结论，不能重新假设系统边界。
- 保留 `/api/agent/runs/stream` typed Agent Runtime 主链路。
- 不新增 agent-specific runtime、transport、state store、SSE/API path 或 bespoke rendering pipeline。
- Lisa、Alex 和未来 Agent 的差异优先通过配置、prompt/template、artifact contract、visualization contract 和 handoff contract 表达。
- 所有方案必须包含测试策略、迁移边界、兼容性说明和回滚策略。

## 第二轮方案设计提示词

```text
请基于第一轮扫描报告设计 New Agents 智能体全面重构方案，不要修改代码、配置、测试或业务文档。

输入文档：
docs/todos/refactor/2026-06-21-new-agents-refactor-scan.md

请只更新以下文件，把完整方案设计写入“方案设计结果”章节：
docs/todos/refactor/2026-06-21-new-agents-refactor-options.md

除这个方案设计文件外，不要修改其他文件。

目标：
基于第一轮扫描中识别的风险，设计 2-3 套可落地的重构方案，并推荐一套最适合当前工程的路线。注意：本轮不是实施计划，不要拆到具体代码步骤，也不要开始编码。

必须继承的约束：
- 保留 /api/agent/runs/stream typed Agent Runtime 主链路。
- 不新增 agent-specific runtime、transport、state store、SSE/API path 或 bespoke rendering pipeline。
- 不恢复旧 /api/chat/stream 或旧文本标签协议。
- 新 workflow/agent 差异优先进入 workflow_manifest、prompt/template、artifact contract、visualization contract、handoff contract。
- 不引入隐藏 fallback、生产 mock、fake success 或无诊断失败。
- 不把 Lisa test assets 过早泛化成空洞框架；如要泛化，必须证明已有至少两个真实消费者或明确迁移收益。

请设计并比较至少 3 套方案：

方案 A：保守收敛
- 重点：补强 contract sync、handoff prompt 配置化、SSE schema fixture、少量 store helper 抽取。
- 要求：最小破坏面，适合作为第一阶段。

方案 B：共享契约注册表
- 重点：建立 workflow contract registry，把 workflow/stage、artifact headings、visual contract、prompt/template 映射和 handoff contract 统一为更清晰的单一事实源或半生成机制。
- 要求：说明哪些字段迁入 manifest，哪些继续留在 Python/TS，如何分阶段迁移。

方案 C：模块边界重组
- 重点：在方案 B 的契约基础上，进一步拆分 store、routes、run_persistence、ArtifactPane、test_assets 等大模块。
- 要求：说明哪些拆分有价值，哪些暂缓；不能改变现有 URL/API/SSE 行为。

每套方案必须包含：
1. 目标和适用场景
2. 解决哪些第一轮扫描风险
3. 不解决哪些风险
4. 主要影响文件/模块
5. 数据/API/SSE 兼容性
6. 测试策略
7. 迁移顺序概览
8. 回滚策略
9. 风险等级和预计收益

然后输出：
1. 方案对比矩阵
2. 推荐方案与理由
3. 推荐的阶段划分，但只到阶段级别，不写代码级实施步骤
4. 第一阶段应包含和不应包含的范围
5. 第三轮“实施计划”应该使用的输入和问题清单

落盘要求：
- 将“当前状态”从“待执行方案设计”更新为“方案设计完成”。
- 将“方案设计结果”下的待填充小节替换为实际内容。
- 保留本提示词，方便后续追溯方案输入。
- 不要创建新的实施计划文件；第三轮实施计划会另开文档。
```

## 方案设计结果

本轮方案设计完成于 2026-06-21。设计基于第一轮扫描报告，不修改代码、配置、测试或业务文档；本文件是唯一落盘结果。

### 1. 输入摘要

第一轮扫描判断：`tools/new-agents/` 当前已经形成共享 Agent Runtime、typed SSE、共享 Zustand store 和共享 Workspace UI 的主链路，未发现 Lisa/Alex 各自独立 runtime、独立 SSE/API 主路径、独立 store 或独立 UI 渲染管线。因此全面重构不应从“重建智能体平台”开始，而应从“收敛契约、多事实源治理和边界拆分护栏”开始。

已识别的主要风险：

- P0：workflow contract 多事实源。`workflow_manifest.json`、前端 `WORKFLOWS/STAGE_CONTENT`、后端 `WORKFLOW_STAGES/REQUIRED_ARTIFACT_HEADINGS/visual contract`、prompt 文件映射和 contract sync 测试共同维护同一套 workflow 事实。
- P0：前端 `store.ts` 过宽，集中承担 workflow 切换、artifact state、handoff、snapshot restore、context summary、视觉诊断等职责。
- P1：`ArtifactPane.tsx`、`run_persistence.py`、`test_assets.py` 等大模块职责过多，但拆分风险高于契约收敛。
- P1：handoff manifest 已配置化，但 `workflow_handoffs.py` prompt 文案仍写死 Alex 语义。
- P1：typed SSE 前后端双实现，缺少共享 fixture 或 schema 对齐机制。
- P1：Lisa test assets 是明确 workflow 特化能力，不应扩散成 runtime 分支，也不宜过早抽象为空洞 asset framework。

本轮设计的共同底线：

- 保留 `/api/agent/runs/stream` typed Agent Runtime 主链路。
- 不新增 agent-specific runtime、transport、state store、SSE/API path 或 bespoke rendering pipeline。
- 不恢复旧 `/api/chat/stream` 或旧文本标签协议。
- 不用隐藏 fallback、生产 mock 或 fake success 掩盖错误。
- 所有重构方向必须可以通过 contract、runtime、frontend state、E2E 或 LLM judge 测试证明。

### 2. 方案 A：保守收敛

#### 目标和适用场景

方案 A 是最小破坏面的第一阶段方案。目标不是建立完整新抽象，而是把当前最容易漂移的契约点用测试和小配置收住，并清理少量明显的职责聚集点。

适用场景：

- 希望快速降低全面重构前的回归风险。
- 希望保留当前目录结构和大部分模块边界。
- 希望先验证“差异通过配置表达”的原则，再决定是否进入更大的 registry 或模块拆分。

#### 解决的第一轮风险

- 补强 workflow/stage/artifact heading/visual prompt/handoff prompt 的同步护栏。
- 将 Alex -> Lisa handoff 的硬编码 prompt 文案迁到显式 handoff contract 或模板映射，避免未来新增 handoff 时出现分支压力。
- 增加 typed SSE schema fixture 或 cross-language contract fixture，降低前后端双实现漂移风险。
- 从 `store.ts` 抽出少量纯 helper 或 selector，例如 snapshot restore、persisted state cleanup、workflow URL 校验相关逻辑，但不改变 Zustand store 对外 API。

#### 不解决的风险

- 不彻底消除 workflow contract 多事实源，只是把漂移变成更容易被测试发现的失败。
- 不拆 `ArtifactPane.tsx`、`run_persistence.py`、`test_assets.py` 这类大模块。
- 不建立完整 workflow contract registry。
- 不改变 prompt/template 目前主要由 TS 模块承载的事实。

#### 主要影响文件/模块

- `tools/new-agents/workflow_manifest.json`
- `tools/new-agents/backend/workflow_handoffs.py`
- `tools/new-agents/backend/sse_schemas.py`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- `tools/new-agents/backend/tests/test_sse_encoder.py`
- `tools/new-agents/frontend/src/core/llm.ts`
- `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
- `tools/new-agents/frontend/src/store.ts`
- `tools/new-agents/frontend/src/__tests__/store.test.ts`

#### 数据/API/SSE 兼容性

- URL、API path、request body、typed SSE event shape、snapshot API 全部保持兼容。
- Handoff 输出内容语义保持兼容；只改变 prompt/template 来源，不改变持久化结构。
- SSE fixture 只作为验证机制，不要求立刻生成前后端代码。
- Store helper 抽取不改变 persisted state shape；如果触及旧 `lisa-storage` 迁移逻辑，必须保留旧数据读取能力。

#### 测试策略

- 后端 contract sync：验证 manifest stage、backend `WORKFLOW_STAGES`、artifact headings、visual contract、prompt/template 映射一致。
- Handoff：验证 manifest handoff 引用、target agent、template/template id 与输出 prompt 内容。
- SSE：增加一个最小 typed event fixture，前端 parser 和后端 encoder 分别消费同一语义样本。
- Frontend state：覆盖 snapshot restore、workflow 切换、artifact rollback/currentRunId 等 helper 抽取后的行为。

建议命令：

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_sse_encoder.py`
- `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/__tests__/store.test.ts`

#### 迁移顺序概览

1. 先新增或强化 contract sync 测试，明确当前事实源必须一致。
2. 再把 handoff prompt 从硬编码文案调整为显式 template/config 入口。
3. 增加 SSE schema fixture，让前后端协议漂移可被单测发现。
4. 最后抽取 `store.ts` 中低风险纯 helper，保持外部 API 和持久化 shape 不变。

#### 回滚策略

- Handoff template 配置可回滚为原硬编码文案，测试继续保护当前行为。
- SSE fixture 是测试护栏，可独立移除，不影响 runtime。
- Store helper 抽取如出现问题，可将 helper 内联回 `store.ts`，不涉及数据迁移。

#### 风险等级和预计收益

- 风险等级：低到中。
- 预计收益：短期收益高，能快速降低后续大重构的漂移风险。
- 局限：只能“收住风险”，不能从根上减少多事实源维护成本。

### 3. 方案 B：共享契约注册表

#### 目标和适用场景

方案 B 是推荐的主路线。目标是建立 New Agents workflow contract registry，把 workflow/stage、artifact headings、visual contract、prompt/template 映射、handoff contract 等统一成更清晰的事实源体系。它不要求所有内容都塞进一个 JSON，而是定义“哪些事实属于 manifest，哪些事实属于语言侧实现，哪些事实必须由 registry 统一导出或校验”。

适用场景：

- 准备长期支持 Lisa、Alex 和更多未来 workflow/agent。
- 希望新增 workflow 时不再依赖人工同步多个散落常量。
- 希望在不改变 runtime/API/SSE 的前提下提高配置化能力。

#### 解决的第一轮风险

- 从根上治理 workflow contract 多事实源。
- 降低新增 workflow/stage 时遗漏 prompt、artifact heading、visual contract、handoff contract 的风险。
- 为后续拆分 store/routes/persistence/UI 提供稳定契约边界。
- 让“差异通过配置表达”具备可执行载体，而不是只靠开发纪律。

#### 不解决的风险

- 不直接减少 `ArtifactPane.tsx`、`run_persistence.py`、`test_assets.py` 的文件体量。
- 不直接解决前端 store 职责过宽，除非同时包含方案 A 中的小 helper 抽取。
- 不自动消除所有 Python/TS 双实现；typed SSE schema 仍建议先用 fixture 护栏，而不是马上引入复杂生成链。

#### 主要影响文件/模块

- `tools/new-agents/workflow_manifest.json`
- `tools/new-agents/backend/workflow_manifest.py`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/backend/workflow_handoffs.py`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tools/new-agents/frontend/src/core/workflows.ts`
- `tools/new-agents/frontend/src/core/prompts/**`
- `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- `tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py`
- `tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`

#### 字段归属建议

建议迁入或显式加入 `workflow_manifest.json` 的字段：

- `workflowId`、`agentId`、`slug`、`label`、`description`、`stage order`：继续保留。
- `stages[].id`、`stages[].label`、`stages[].description`：继续保留并作为 UI 和 backend stage 校验基础。
- `stages[].artifactContract.requiredHeadings`：适合迁入 manifest，作为后端 artifact heading 校验的数据源。
- `stages[].visualContract.requiredTypes`：适合迁入 manifest，例如 `mermaid`、`ai4se-visual`、required diagram roles。
- `stages[].promptTemplateId` 或 `promptModuleKey`：适合迁入 manifest，但不建议把完整 prompt 文本立即迁入 JSON。
- `handoffs[]` 的 `sourceWorkflowId/sourceStageId/targetWorkflowId/targetStageId/targetAgentId/templateId`：适合迁入或补齐 manifest。

建议继续留在 Python 的字段或逻辑：

- Pydantic/runtime request schema。
- Artifact 内容解析、required heading 校验实现、visual schema 校验实现。
- SSE encoder 和 error event schema。
- 数据库持久化模型与 repository 实现。

建议继续留在 TypeScript 的字段或逻辑：

- React 组件渲染逻辑。
- Prompt 模块的具体长文本和 template 组装代码，至少第一阶段保留。
- Frontend workflow card 展示和路由映射派生逻辑。
- Stream parser 运行时类型保护。

建议由 registry 统一导出或统一校验的内容：

- workflow/stage/agentId/slug/listing。
- stage -> prompt template id/module key。
- stage -> artifact required headings。
- stage -> visual contract。
- handoff source/target/template id。
- E2E prompt quality 和 artifact contract 的引用清单。

#### 数据/API/SSE 兼容性

- API path、request schema、SSE event shape 不变。
- Manifest 扩展必须向后兼容现有字段；新增字段先由测试读取，不立即删除旧常量。
- 后端可以先从 manifest-derived registry 读取 contract，再保留旧常量作为迁移期间的断言对照；迁移完成后删除重复常量。
- 前端 `WORKFLOWS` 仍可从 manifest 派生，prompt 文本先通过 `promptTemplateId` 映射到现有 TS 模块。

#### 测试策略

- Registry unit tests：验证 manifest 能生成完整 workflow contract registry，且每个 stage 都有 prompt template、artifact headings、visual contract。
- Backend contract tests：验证后端 `WORKFLOW_STAGES` 或替代结构来自 registry，未知 workflow/stage 仍显式失败。
- Frontend config tests：验证 `WORKFLOWS`、slug maps、agent workflow listings 从 registry/manifest 派生一致。
- Handoff tests：验证每个 handoff 都有有效 template id，target agent 与 target workflow 一致。
- E2E smoke：Lisa TEST_DESIGN 和 Alex VALUE_DISCOVERY 仍走 `/api/agent/runs/stream` typed runtime。

建议命令：

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_request_schemas.py tools/new-agents/backend/tests/test_agent_contracts.py`
- `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/__tests__/llm.test.ts`
- `.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`

#### 迁移顺序概览

1. 定义 registry 字段边界和读取模型，先让测试证明当前 manifest + 旧常量能被一致解释。
2. 扩展 manifest，加入 artifact/visual/prompt/handoff template metadata。
3. 后端 contract 从 registry 读取一类低风险字段，例如 `WORKFLOW_STAGES` 或 handoff template id。
4. 再迁移 artifact headings 和 visual contract metadata，同时保留测试证明输出行为不变。
5. 前端 prompt/template 映射改为通过 `promptTemplateId` 解析现有 TS 模块，避免一次性迁移 prompt 文本格式。

#### 回滚策略

- Manifest 新字段可保持但暂不启用，后端回到旧 Python 常量读取。
- Registry 读取层可在一两个入口切换，不涉及数据库和外部 API。
- 如果 promptTemplateId 映射失败，可回滚到当前 `STAGE_CONTENT` 显式映射。
- 回滚不影响已有 run/snapshot，因为 runtime request 和 persistence shape 不变。

#### 风险等级和预计收益

- 风险等级：中。
- 预计收益：最高，能从根上减少新增 Agent/workflow 的同步成本，并为后续模块拆分建立稳定边界。
- 局限：需要更严谨的字段归属设计，否则容易把 manifest 变成臃肿配置泥球。

### 4. 方案 C：模块边界重组

#### 目标和适用场景

方案 C 是在方案 B 契约稳定后的结构性整理。目标是拆分过大的共享模块，让 runtime、store、routes、persistence、artifact UI、test assets 各自拥有更清晰的边界，但不改变现有 URL/API/SSE 行为。

适用场景：

- Contract registry 已经稳定，后续改动能依赖统一契约。
- 团队准备持续扩展 artifact 协作、导出、handoff、observability 或 test assets。
- 大文件已经明显拖慢测试定位、代码评审和功能迭代。

#### 解决的第一轮风险

- 降低 `store.ts`、`ArtifactPane.tsx`、`run_persistence.py`、`test_assets.py` 的维护复杂度。
- 将 `routes.py` 中通用 runtime endpoints 和 Lisa test assets endpoints 进行文件级分组，减少 workflow 特化能力污染主路由的趋势。
- 为未来新增 asset consumer 或 artifact tool 提供边界，但不提前制造独立 runtime。

#### 不解决的风险

- 如果没有先做方案 B，模块拆分无法解决多事实源问题，反而可能把同步风险扩散到更多文件。
- 不改变产品能力，不直接提升模型输出质量。
- 不建议把 Lisa test assets 泛化为通用 framework，除非出现第二个真实消费者或已明确迁移收益。

#### 主要影响文件/模块

- `tools/new-agents/frontend/src/store.ts`
- `tools/new-agents/frontend/src/pages/ArtifactPane.tsx`
- `tools/new-agents/frontend/src/services/chatService.ts`
- `tools/new-agents/backend/routes.py`
- `tools/new-agents/backend/run_persistence.py`
- `tools/new-agents/backend/test_assets.py`
- `tools/new-agents/backend/tests/test_agent_endpoint.py`
- `tools/new-agents/backend/tests/test_test_assets.py`
- `tools/new-agents/frontend/src/pages/__tests__/ArtifactPane*.test.tsx`
- `tools/new-agents/frontend/src/services/__tests__/*.test.ts`

#### 有价值的拆分

- `store.ts`：优先拆纯函数、selectors、snapshot restore helper、workflow navigation helper、artifact history helper；Zustand store 入口保持不变。
- `routes.py`：按文件分组通用 agent runtime routes、observability routes、test assets routes、utility routes；Flask blueprint URL 保持不变。
- `run_persistence.py`：按 repository 职责分出 messages、artifacts、collaboration state、metrics/context summaries 的内部 helper 或 repository 类；数据库模型不变。
- `ArtifactPane.tsx`：先拆纯 UI 子组件和 pure helpers，例如 history list、diff/merge controls、export controls、visual diagnostics；不要在同一步重写 artifact rendering pipeline。
- `test_assets.py`：保留 Lisa TEST_DESIGN/CASES 语义，先拆解析、validation、intent-tester export、persistence 查询几个内部边界。

#### 应暂缓的拆分

- 暂缓创建 `AgentRuntimeLisa`、`AgentRuntimeAlex` 或任何 workflow-specific runtime。
- 暂缓创建独立 Zustand stores，例如 `useLisaStore`、`useAlexStore`。
- 暂缓新增 `/api/lisa/*` 或 `/api/alex/*` runtime path。
- 暂缓把 `ArtifactPane` 改成多套 workflow-specific rendering pipeline。
- 暂缓把 Lisa test assets 抽象成多 Agent asset framework，除非先有第二个真实消费者。

#### 数据/API/SSE 兼容性

- URL、API path、HTTP method、request/response JSON、SSE event shape 全部保持兼容。
- Persisted store shape 和 database schema 保持不变。
- Blueprint 或文件拆分不得改变 route registration 后的外部路径。
- Artifact rendering 的 DOM 可内部变化，但用户可见功能和测试选择器需尽量保持兼容。

#### 测试策略

- 每次拆分前先锁定现有行为测试，拆分后同一测试通过。
- Store 拆分覆盖 workflow switching、snapshot restore、currentRunId、artifact history、handoff accepted state。
- Routes 拆分覆盖 `/api/agent/runs/stream`、`/api/agent/runs/{runId}`、observability、test assets endpoints。
- Persistence 拆分覆盖 run/message/artifact/context summary/metric/collaboration state。
- ArtifactPane 拆分覆盖 preview、edit、history、diff/merge、export、visual diagnostics。

#### 迁移顺序概览

1. 以方案 B 的 registry 为稳定契约边界。
2. 先拆 `store.ts` 纯 helper 和 route 文件分组，因为外部行为最容易保持。
3. 再拆 `run_persistence.py` 内部 repository 边界。
4. 再拆 `test_assets.py` 内部服务边界。
5. 最后处理 `ArtifactPane.tsx`，每次只移动一个独立 UI 区域或 pure helper。

#### 回滚策略

- 每个拆分切片保持旧入口文件重新导出或调用新模块，回滚时可内联回原文件。
- 不做 schema/data migration，因此回滚不需要数据修复。
- UI 拆分保留测试选择器和服务接口，失败时可逐个子组件撤回。

#### 风险等级和预计收益

- 风险等级：中到高。
- 预计收益：中高，主要体现在长期维护性和后续扩展速度。
- 前置条件：不建议作为第一阶段单独启动；应在方案 A/B 的契约护栏建立后进行。

### 5. 方案对比矩阵

| 维度 | 方案 A：保守收敛 | 方案 B：共享契约注册表 | 方案 C：模块边界重组 |
| --- | --- | --- | --- |
| 核心目标 | 用测试和小配置降低漂移 | 建立 workflow contract 的清晰事实源体系 | 拆分过大模块和职责边界 |
| 主要收益 | 快速、安全、回归面小 | 长期收益最高，支撑新增 workflow/agent | 降低维护成本，提高模块可测试性 |
| 主要风险 | 多事实源仍存在 | registry 边界设计不好会变成大配置泥球 | 没有稳定契约时容易扩散风险 |
| API/SSE 兼容 | 完全兼容 | 完全兼容 | 完全兼容 |
| 数据迁移 | 无 | 无，最多 manifest 字段扩展 | 无 |
| 测试重点 | contract sync、handoff、SSE fixture、store helper | registry、manifest-derived contracts、frontend/backend sync | behavior lock tests、route/store/persistence/UI tests |
| 适合作为第一阶段 | 是 | 是，但应从 A 的护栏起步 | 否 |
| 对新增 Agent 的帮助 | 中 | 高 | 中 |
| 对大文件治理的帮助 | 低 | 间接 | 高 |
| 推荐度 | 高，作为第 1 阶段 | 最高，作为主路线 | 中，作为第 3 阶段 |

### 6. 推荐方案

推荐采用“方案 A 起步，方案 B 作为主路线，方案 C 后置”的组合路线。

理由：

- 当前系统最大风险不是 runtime 分叉，而是 contract 多事实源和配置同步成本。直接拆大文件无法解决这个根因。
- 方案 A 能用最小破坏面先补齐护栏，让后续 registry 迁移有明确安全网。
- 方案 B 是最符合仓库高优先级原则的长期方向：不同 Agent/workflow 的差异通过 manifest、prompt/template、artifact contract、visualization contract、handoff contract 表达，而不是通过 runtime/API/store/UI 分支表达。
- 方案 C 有价值，但它依赖稳定契约。若先拆 `ArtifactPane.tsx`、`run_persistence.py` 或 `test_assets.py`，很容易把现有隐式耦合拆散到更多文件里，短期可读性提升但系统一致性没有提升。

推荐目标架构不是“所有内容都塞进 `workflow_manifest.json`”，而是“manifest + registry + language-side validators”的分层事实源：

| 层 | 负责内容 | 不负责内容 |
| --- | --- | --- |
| `workflow_manifest.json` | workflow/stage/agent/slug/listing、artifact/visual metadata、prompt template id、handoff declaration | 长 prompt 文本、runtime implementation、UI rendering |
| Backend registry/validators | request stage validation、artifact heading validation、visual contract validation、handoff template resolution | Agent-specific runtime branch、fake fallback |
| Frontend registry adapter | `WORKFLOWS`、slug maps、agent listings、prompt template id 到 TS prompt module 的映射 | 多套 store、多套 rendering pipeline |
| Tests/fixtures | contract sync、SSE schema fixture、E2E workflow proof | 替代真实错误处理或生产 mock |

### 7. 推荐阶段划分

#### 阶段 1：契约护栏和低风险收敛

目标：让现有多事实源的漂移尽早失败，并清理最明显的硬编码。

范围：

- 强化 contract sync 测试。
- Handoff prompt template 配置化。
- typed SSE schema fixture 或协议 fixture。
- 少量 `store.ts` 纯 helper 抽取，不改变外部 API。

#### 阶段 2：共享契约注册表

目标：建立 manifest-derived workflow contract registry，让新增 workflow/stage 的必备事实被统一发现、读取和校验。

范围：

- 扩展 manifest 字段。
- 定义 backend registry 读取模型。
- 定义 frontend registry adapter。
- 迁移低风险字段，例如 handoff template id、stage prompt template id。
- 再迁移 artifact headings 和 visual contract metadata。

#### 阶段 3：模块边界重组

目标：在稳定 contract 边界上拆分大模块。

范围：

- `store.ts` helpers/selectors/slices 内部整理。
- `routes.py` route 文件分组，外部 URL 不变。
- `run_persistence.py` repository/helper 边界整理。
- `test_assets.py` 内部能力分层。
- `ArtifactPane.tsx` 子组件和 pure helper 拆分。

#### 阶段 4：质量回归和可选 E2E/LLM judge

目标：证明重构没有改变主链路行为，也没有降低 workflow 输出质量。

范围：

- Backend contract/runtime/persistence tests。
- Frontend config/parser/store/UI tests。
- Lisa 和 Alex 浏览器 E2E。
- 影响 prompt/artifact quality 时启用显式 LLM judge。

#### 建议执行轮次

本推荐方案不适合一次 Superpowers 流程直接完成。建议从当前状态起拆成 1 个实施计划轮和 6 个目标模式执行轮。每一轮都应先做 Current State Gap Analysis，再产出中文 spec、implementation plan、TDD 实现、验证证据和记录更新；前一轮验收完成后再进入下一轮。

| 轮次 | 类型 | Milestone 名称 | 目标边界 | 主要验收证据 | 不纳入本轮 |
| --- | --- | --- | --- | --- | --- |
| 第三轮 | Superpowers 文档计划 | 阶段 1 实施计划 | 只把阶段 1 拆成 TDD 任务和验证命令，不写代码 | 实施计划文件、任务边界、预计验证命令、回滚点 | 不实施阶段 1；不设计阶段 2/3 细节 |
| 目标模式第 1 轮 | 工程信任闭环 | Workflow 契约漂移可检测闭环 | 让 manifest、backend stages、artifact headings、visual contract、prompt/template 映射、handoff metadata 的漂移能被测试发现 | contract sync tests、frontend workflow config tests | 不迁移全部 contract；不拆大模块 |
| 目标模式第 2 轮 | 工程信任闭环 | Handoff 与 typed SSE 协议护栏闭环 | Handoff prompt template 配置化；建立 typed SSE fixture 或等价双端协议样本 | handoff tests、SSE encoder/parser tests、runtime 主链路 targeted tests | 不改 SSE event shape；不引入 schema 生成硬依赖 |
| 目标模式第 3 轮 | 工程信任闭环 | Workspace 状态恢复与承接稳定闭环 | 只抽取低风险 `store.ts` pure helpers，并锁定 snapshot restore、workflow switching、artifact history、currentRunId 行为 | store tests、chatService targeted tests、snapshot restore 验证 | 不拆独立 store；不改 persisted state shape |
| 目标模式第 4 轮 | 架构收敛闭环 | 共享 workflow contract registry 最小闭环 | 扩展 manifest metadata；建立 backend registry 读取模型和 frontend registry adapter；先迁移低风险字段 | registry unit tests、request schema tests、frontend config tests | 不一次性迁移长 prompt 文本；不动 ArtifactPane |
| 目标模式第 5 轮 | 架构收敛闭环 | Artifact 与 visual contract 注册表闭环 | 将 artifact headings、visual contract metadata 纳入 registry 驱动或半生成机制，并删除已被替代的重复事实源 | agent contract tests、workflow contract sync tests、Lisa/Alex workflow smoke | 不改变 runtime API/SSE；不改变数据库 schema |
| 目标模式第 6 轮 | 模块边界闭环 | 大模块边界重组第一批 | 在 registry 稳定后拆分 routes、run_persistence、test_assets、store 内部边界中最安全的一批 | backend endpoint tests、persistence tests、test_assets tests、frontend state tests | 暂不拆 `ArtifactPane.tsx` 主渲染结构 |
| 后续可选轮 | UI 结构闭环 | ArtifactPane 渲染与协作模块化 | 单独处理 `ArtifactPane.tsx` 子组件和 pure helpers 拆分 | ArtifactPane tests、导出/协作/visual diagnostics tests、必要截图 | 不与 backend registry 或 persistence 重构同轮进行 |

执行口径：

- 第三轮适合用一次 Superpowers 计划流程完成，因为它只生成阶段 1 的实施计划。
- 目标模式第 1 到第 3 轮共同完成原“阶段 1：契约护栏和低风险收敛”，不要把它们压缩成一次大改。
- 目标模式第 4 到第 5 轮完成原“阶段 2：共享契约注册表”。
- 目标模式第 6 轮开始进入原“阶段 3：模块边界重组”；`ArtifactPane.tsx` 建议作为后续可选轮单独处理。
- 每一轮都必须保持 `/api/agent/runs/stream`、typed SSE event shape、snapshot API、test assets API 兼容。
- 任一轮如果发现需要 agent-specific runtime、transport、store、SSE/API path 或 UI rendering pipeline，应停止并重新进入方案评审，而不是顺手实现。

### 8. 第一阶段范围

第一阶段应包含：

- 强化 `test_workflow_contract_sync.py`，覆盖 manifest、backend stages、artifact headings、visual contract、frontend prompt/template 映射、handoff template metadata。
- 为 typed SSE 增加共享 fixture 或等价的双端 contract 样本，保证前端 parser 与后端 encoder 对同一事件语义一致。
- 将 `workflow_handoffs.py` 中写死 Alex 语义的 prompt 文案调整为可由 handoff contract/template id 表达。
- 从 `store.ts` 只抽取低风险纯 helper，例如 snapshot restore 数据整形、workflow/slug 校验、persisted state cleanup；保持 `useAppStore` 外部 shape 不变。
- 保持所有 runtime、API、SSE、snapshot、test assets URL 兼容。

第一阶段不应包含：

- 不拆 `ArtifactPane.tsx` 的主要渲染结构。
- 不重写 `run_persistence.py`。
- 不把所有 prompt 文本迁入 JSON/Markdown。
- 不新增 code generation 作为硬依赖，除非先有 fixture 证明收益。
- 不泛化 Lisa test assets 为通用 asset framework。
- 不调整数据库 schema。
- 不新增任何 Lisa/Alex 专属 runtime、store、SSE/API path 或 UI rendering pipeline。

第一阶段完成标准：

- 新增 workflow/stage 时，如果漏配 artifact heading、visual contract、prompt template 或 handoff template，测试必须失败。
- Lisa `TEST_DESIGN/CASES` 和 Alex `VALUE_DISCOVERY` 仍通过 `/api/agent/runs/stream` typed Agent Runtime。
- 前端恢复 run snapshot、继续对话、artifact history 和 handoff 状态行为不变。
- 不出现隐藏 fallback、生产 mock 或 fake success。

### 9. 第三轮实施计划输入

第三轮实施计划建议输入：

- 第一轮扫描报告：`docs/todos/refactor/2026-06-21-new-agents-refactor-scan.md`
- 第二轮方案设计：`docs/todos/refactor/2026-06-21-new-agents-refactor-options.md`
- 目标阶段：阶段 1，契约护栏和低风险收敛。
- 约束：保留 `/api/agent/runs/stream` typed Agent Runtime；不改变 API/SSE/persistence shape；不新增 agent-specific 基础设施。

第三轮实施计划应回答的问题：

- Handoff template metadata 放在 manifest 的哪个字段下，字段名是否与现有 `handoffs` 结构兼容？
- SSE fixture 放在哪里最合理：backend tests fixture、frontend shared fixture，还是 `tools/new-agents/contract-fixtures/` 这类新目录？
- 第一阶段是否允许新增一个 registry 读取 helper，还是只强化现有 sync tests？
- `store.ts` 第一批只抽哪些 pure helper，哪些逻辑必须留在 Zustand action 内？
- Contract sync 测试中，prompt/template 映射如何避免再形成一个新的手写多事实源？
- 第一阶段验收命令是否限定为 targeted tests，还是必须跑 New Agents 前后端完整测试集？

第三轮计划应拆成 TDD 任务，但只覆盖阶段 1：

- 先写 contract sync 失败测试，再补配置或 registry helper。
- 先写 handoff template 行为测试，再迁移 prompt 来源。
- 先写 SSE fixture/parser/encoder 测试，再接入 fixture。
- 先写 store helper 行为测试，再抽取 helper。
- 最后运行 targeted backend/frontend tests 和必要的 E2E smoke。

### 10. 开放问题

1. `workflow_manifest.json` 是否接受新增 `artifactContract`、`visualContract`、`promptTemplateId`、`handoff.templateId` 这类字段，还是希望先通过 sidecar registry 文件承载？
2. Prompt/template 长文本第一阶段是否明确继续留在 TypeScript 模块中，只把 template id 放入 manifest？
3. typed SSE 是否只需要共享 fixture，还是希望后续进入 schema 生成？本轮建议先 fixture，暂缓生成链。
4. Lisa test assets 是否保持 `TEST_DESIGN/CASES` 特化能力定位？本轮建议保持，直到出现第二个真实消费者。
5. 第一阶段是否需要跑浏览器 E2E，还是 targeted backend/frontend tests 足够？如果 handoff 或 prompt quality 受影响，建议补 E2E smoke。
