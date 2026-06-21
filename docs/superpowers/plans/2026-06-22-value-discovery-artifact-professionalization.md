# VALUE_DISCOVERY 产出物专业化实施计划

## 目标

完成 `VALUE_DISCOVERY` workflow 下 `ELEVATOR`、`PERSONA`、`JOURNEY`、`BLUEPRINT` 四个 stage artifact 的专业化升级，并同步 backend artifact contract、contract sync tests、frontend typed runtime fixture 和 handoff 相关测试样例。

## 文件范围

- `tools/new-agents/frontend/src/core/prompts/value_discovery/elevator.ts`
- `tools/new-agents/frontend/src/core/prompts/value_discovery/persona.ts`
- `tools/new-agents/frontend/src/core/prompts/value_discovery/journey.ts`
- `tools/new-agents/frontend/src/core/prompts/value_discovery/blueprint.ts`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/backend/tests/test_agent_contracts.py`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- `tools/new-agents/backend/tests/test_agent_endpoint.py`
- `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
- 本轮 spec/plan

## TDD 步骤

### 1. Contract RED

更新 `test_agent_contracts.py`：

- 要求 `VALUE_DISCOVERY/ELEVATOR` 包含价值结构图、痛点证据、未验证假设、阶段门禁、证据等级、验证动作、状态，并要求 `flowchart` Mermaid。
- 要求 `PERSONA` 包含画像摘要、行为与场景、决策链、痛点证据、反画像、阶段门禁、证据等级、验证状态。
- 要求 `JOURNEY` 包含机会评分、验证实验、阶段门禁、验证状态。
- 要求 `BLUEPRINT` 包含非功能需求、验收标准、可测试性等级、阶段门禁、owner、状态。

预期：先失败，因为 contract 仍是旧目标。

### 2. 实现 Contract

更新 `agent_contracts.py`：

- 扩展四个 `VALUE_DISCOVERY` stage 的 required headings / key fields。
- 为 `ELEVATOR` 增加 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` 的 `flowchart`。
- 保留 `ELEVATOR score-matrix`、`JOURNEY journey-map`、`BLUEPRINT roadmap`。

### 3. 实现 Prompt / Template

- `ELEVATOR`：新增价值结构图、痛点证据、未验证假设、阶段门禁。
- `PERSONA`：新增决策链、痛点证据、反画像、验证状态、阶段门禁。
- `JOURNEY`：新增机会评分、验证实验、阶段门禁，强化 journey-map 字段。
- `BLUEPRINT`：新增非功能需求、验收标准、可测试性等级、阶段门禁，强化 P0/P1/P2 需求表字段。

### 4. 更新 Fixture

- 更新 `frontend/src/core/__tests__/llm.test.ts` 中 `VALUE_DISCOVERY/ELEVATOR` 的 typed artifact fixture。
- 更新 `backend/tests/test_workflow_handoffs.py` 和可能相关 endpoint fixture，使蓝图样例满足新的 contract / handoff 语义。

### 5. 验证

最小验证命令：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py
```

前端聚焦验证：

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts
cd tools/new-agents/frontend && ./node_modules/.bin/tsc --noEmit --allowImportingTsExtensions --moduleResolution Bundler --module ESNext --target ES2022 --jsx react-jsx --resolveJsonModule --esModuleInterop --strict src/core/workflows.ts
```

辅助验证：

```bash
git diff --check
```

## 风险与取舍

- 后端 contract 仍以标题、字段和 visual 存在性为主，语义质量需要后续 LLM judge。
- 本轮不改 handoff runtime，只让蓝图 artifact 更适合被现有 handoff 消费。
- 当前工作区有无关 zip 改动，提交时不得 stage。

## 每轮提交规则

完成验证后形成聚焦 commit，并在远端权限可用时 push 到 Git。只提交本轮 `VALUE_DISCOVERY` 相关文件和本轮文档。

## 执行记录

### 本轮完成范围

- 完成 `VALUE_DISCOVERY` 下 `ELEVATOR`、`PERSONA`、`JOURNEY`、`BLUEPRINT` 四个 artifact 的模板专业化增强。
- `ELEVATOR` 增加第一阶段必需的 Mermaid `flowchart` 价值结构图，并补齐目标用户与场景、痛点证据、差异化价值、商业可行性、未验证假设、60 秒电梯演讲和阶段门禁。
- `PERSONA` 补齐画像摘要、核心画像字段、行为与场景、决策链、痛点证据、反画像、用户优先级排序和阶段门禁。
- `JOURNEY` 强化结构化旅程地图字段，补齐关键阶段分析、痛点优先级排序、机会评分、产品切入策略、验证实验和阶段门禁。
- `BLUEPRINT` 强化 P0/P1/P2 需求表字段，新增非功能需求、验收标准、路线图、风险评估、Lisa Handoff 输入和阶段门禁。
- 同步更新 backend artifact contract、Mermaid contract、backend fixtures、frontend typed runtime fixture 和本轮 spec/plan。

### 验证结果

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_workflow_handoffs.py tools/new-agents/backend/tests/test_agent_endpoint.py
```

结果：`149 passed in 1.96s`。

```bash
npm run test -- --run src/core/__tests__/llm.test.ts
```

结果：`69 passed`。

```bash
./node_modules/.bin/tsc --noEmit --allowImportingTsExtensions --moduleResolution Bundler --module ESNext --target ES2022 --jsx react-jsx --resolveJsonModule --esModuleInterop --strict src/core/workflows.ts
```

结果：通过，无输出。

```bash
git diff --check
```

结果：通过，无输出。

### 剩余风险

- 当前 contract 能约束章节、关键字段和 Mermaid 类型存在，但不能判断内容是否真正具有商业洞察、用户证据质量或产品可落地性；需要后续 LLM judge 评审覆盖。
- 本轮复用现有 markdown、Mermaid 和 `ai4se-visual` 通用结构化渲染能力，没有新增可视化组件。
- 本轮未改变 runtime、transport、state store、SSE/API path 或 bespoke rendering pipeline。
- 全量前端 lint 未在本轮重跑；此前已知存在与本轮无关的 `artifactMerge.test.ts` `"context"` 类型问题，后续应单独清理。

### 下一轮建议

- 建议下一轮处理 `INCIDENT_REVIEW`，因为它面向故障复盘和改进闭环，专业度依赖时间线证据、根因分析严谨性、行动项 owner/验收标准/跟踪状态，适合继续按 workflow 薄切片推进。
- 当前总体进度：`3/5` 个 workflow 完成，剩余 `INCIDENT_REVIEW`、`IDEA_BRAINSTORM`。
