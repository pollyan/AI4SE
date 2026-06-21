# INCIDENT_REVIEW 产出物专业化实施计划

## 目标

完成 `INCIDENT_REVIEW` workflow 下 `TIMELINE`、`ROOT_CAUSE`、`IMPROVEMENT` 三个 stage artifact 的专业化升级，并同步 workflow manifest、backend artifact contract、contract sync tests、frontend typed runtime fixture 和本轮 spec/plan。

## 文件范围

- `tools/new-agents/workflow_manifest.json`
- `tools/new-agents/frontend/src/core/prompts/incident_review/timeline.ts`
- `tools/new-agents/frontend/src/core/prompts/incident_review/root_cause.ts`
- `tools/new-agents/frontend/src/core/prompts/incident_review/improvement.ts`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/backend/tests/test_agent_contracts.py`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
- 本轮 spec/plan

## TDD 步骤

### 1. Contract RED

更新 `test_agent_contracts.py`：

- 要求 `TIMELINE` 包含影响量化、事实来源、事实/推测隔离、阻断性、阶段门禁，并要求 `timeline` Mermaid。
- 要求 `ROOT_CAUSE` 包含根因证据表、证据强度、置信度、可行动性、排除项、未验证原因、阶段门禁，并要求 `mindmap` 和 `cause-map`。
- 要求 `IMPROVEMENT` 包含根因覆盖检查、复查计划、遗留风险与风险接受、组织学习、阶段门禁，并要求 `pie` 和 `action-board`。

预期：先失败，因为 contract 和模板仍是旧目标。

### 2. 实现 Contract / Manifest

- 扩展 `agent_contracts.py` 中三个 `INCIDENT_REVIEW` stage 的 required headings / key fields。
- 保留现有 visual contract：`TIMELINE timeline`、`ROOT_CAUSE mindmap + cause-map`、`IMPROVEMENT pie + action-board`。
- 同步 `workflow_manifest.json` 的 `artifactContract.requiredHeadings`，避免共享配置表面和 backend contract 分裂。

### 3. 实现 Prompt / Template

- `TIMELINE`：新增影响量化、事实来源、事实/推测隔离、待补充信息阻断性、阶段门禁。
- `ROOT_CAUSE`：新增根因证据表、证据强度、置信度、可行动性、排除项、未验证原因、阶段门禁。
- `IMPROVEMENT`：新增根因覆盖检查、复查计划、遗留风险与风险接受、组织学习、阶段门禁。

### 4. 更新 Fixture

- 更新 `frontend/src/core/__tests__/llm.test.ts` 中 `INCIDENT_REVIEW/TIMELINE` 的 typed artifact fixture，使其体现新结构。
- 如 backend fixture 因 contract 扩展受影响，同步更新对应样例。

### 5. 验证

最小后端验证：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py
```

前端聚焦验证：

```bash
npm run test -- --run src/core/__tests__/llm.test.ts
./node_modules/.bin/tsc --noEmit --allowImportingTsExtensions --moduleResolution Bundler --module ESNext --target ES2022 --jsx react-jsx --resolveJsonModule --esModuleInterop --strict src/core/workflows.ts
```

辅助验证：

```bash
git diff --check
```

## 风险与取舍

- Contract 仍以章节、字段和 visual 存在性为主，无法判断 RCA 因果链是否真正严谨；后续需要 LLM judge。
- 本轮不改复盘 runtime，也不新增前端可视化组件。
- 当前工作区有无关 zip 改动，提交时不得 stage。

## 每轮提交规则

完成验证后形成聚焦 commit，并在远端权限可用时 push 到 Git。只提交本轮 `INCIDENT_REVIEW` 相关文件和本轮文档。

## 执行记录

### 本轮完成范围

- 完成 `INCIDENT_REVIEW` 下 `TIMELINE`、`ROOT_CAUSE`、`IMPROVEMENT` 三个 artifact 的专业化增强。
- `TIMELINE` 补齐影响量化、事实来源、事实/推测隔离、阻断/非阻断待补充信息和阶段门禁，保留第一阶段 Mermaid `timeline`。
- `ROOT_CAUSE` 补齐 5-Why 证据强度、置信度、可行动性、根因证据表、排除项、未验证原因和阶段门禁，保留 Mermaid `mindmap` 与 `cause-map`。
- `IMPROVEMENT` 补齐根因覆盖检查、复查计划、遗留风险与风险接受、组织学习和阶段门禁，保留 Mermaid `pie` 与 `action-board`。
- 同步更新 `workflow_manifest.json`、backend contract、backend contract tests、frontend runtime fixture 和本轮 spec/plan。

### 验证结果

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py
```

结果：`94 passed in 0.21s`。

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

- 当前 contract 能约束章节、关键字段、Mermaid 和 `ai4se-visual` 类型存在，但不能判断 RCA 因果链是否跳跃、证据强度是否真实或行动是否真正可落地；需要后续 LLM judge。
- 本轮未新增复盘专用前端控件，所有结构化可视化仍复用已有通用表格渲染。
- 本轮未改变 Agent Runtime、typed SSE、workflow state、API path 或渲染管线。

### 下一轮建议

- 建议下一轮处理 `IDEA_BRAINSTORM`，完成最后一个 workflow 的 artifact 专业化闭环。
- 当前总体进度：`4/5` 个 workflow 完成，剩余 `IDEA_BRAINSTORM`。
