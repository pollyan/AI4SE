# IDEA_BRAINSTORM 产出物专业化实施计划

## 目标

完成 `IDEA_BRAINSTORM` workflow 下 `DEFINE`、`DIVERGE`、`CONVERGE`、`CONCEPT` 四个 stage artifact 的专业化升级，并同步 workflow manifest、backend artifact contract、contract sync tests、frontend typed runtime fixture 和本轮 spec/plan。

## 文件范围

- `tools/new-agents/workflow_manifest.json`
- `tools/new-agents/frontend/src/core/prompts/idea_brainstorm/define.ts`
- `tools/new-agents/frontend/src/core/prompts/idea_brainstorm/diverge.ts`
- `tools/new-agents/frontend/src/core/prompts/idea_brainstorm/converge.ts`
- `tools/new-agents/frontend/src/core/prompts/idea_brainstorm/concept.ts`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/backend/tests/test_agent_contracts.py`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
- 本轮 spec/plan

## TDD 步骤

### 1. Contract RED

更新 `test_agent_contracts.py`：

- 要求 `DEFINE` 包含证据与验证状态、证据等级、验证动作、阶段门禁。
- 要求 `DIVERGE` 包含发散方法说明、创意来源与假设、搁置/排除记录、关键假设、状态理由、阶段门禁。
- 要求 `CONVERGE` 包含资源约束、敏感性分析、验证实验、证据来源、用户确认状态、阶段门禁。
- 要求 `CONCEPT` 包含核心假设、验证路线、不可做范围、决策记录、owner、状态、阶段门禁。

预期：先失败，因为 contract 和模板仍是旧目标。

### 2. 实现 Contract / Manifest

- 扩展 `agent_contracts.py` 中四个 `IDEA_BRAINSTORM` stage 的 required headings / key fields。
- 保留现有 visual contract：`DEFINE mindmap`、`CONVERGE quadrantChart`、`CONCEPT mvp-map`。
- 同步 `workflow_manifest.json` 的 `artifactContract.requiredHeadings`。

### 3. 实现 Prompt / Template

- `DEFINE`：新增证据与验证状态、阶段门禁，强化问题真实性和不可做边界。
- `DIVERGE`：新增发散方法说明、创意来源与假设、搁置/排除记录、阶段门禁。
- `CONVERGE`：新增资源约束、敏感性分析、验证实验、阶段门禁。
- `CONCEPT`：新增核心假设、验证路线、不可做范围、决策记录、阶段门禁。

### 4. 更新 Fixture

- 更新 `frontend/src/core/__tests__/llm.test.ts` 中 `IDEA_BRAINSTORM/DEFINE` 的 typed artifact fixture。

### 5. 验证

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py
```

```bash
npm run test -- --run src/core/__tests__/llm.test.ts
./node_modules/.bin/tsc --noEmit --allowImportingTsExtensions --moduleResolution Bundler --module ESNext --target ES2022 --jsx react-jsx --resolveJsonModule --esModuleInterop --strict src/core/workflows.ts
git diff --check
```

## 风险与取舍

- Contract 仍无法判断创意质量、评分是否真的合理或概念是否足够有商业洞察；后续需要 LLM judge。
- 本轮不新增创意或 MVP 专属前端控件。
- 当前工作区有无关 zip 改动，提交时不得 stage。

## 每轮提交规则

完成验证后形成聚焦 commit，并在远端权限可用时 push 到 Git。只提交本轮 `IDEA_BRAINSTORM` 相关文件和本轮文档。

## 执行记录

### 本轮完成范围

- 完成 `IDEA_BRAINSTORM` 下 `DEFINE`、`DIVERGE`、`CONVERGE`、`CONCEPT` 四个 artifact 的专业化增强。
- `DEFINE` 补齐证据与验证状态、问题真实性、不可做边界和阶段门禁，保留第一阶段 Mermaid `mindmap`。
- `DIVERGE` 补齐发散方法说明、创意来源与假设、关键假设、风险、状态理由、搁置/排除记录和阶段门禁。
- `CONVERGE` 补齐评分证据来源、资源约束、敏感性分析、验证实验、用户确认状态和阶段门禁，保留 Mermaid `quadrantChart`。
- `CONCEPT` 补齐核心假设、验证路线、不可做范围、决策记录、下一步行动 owner/状态和阶段门禁，保留 `mvp-map`。
- 同步更新 `workflow_manifest.json`、backend contract、backend contract tests、frontend runtime fixture 和本轮 spec/plan。

### 验证结果

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py
```

结果：`95 passed in 0.19s`。

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

- 当前 contract 能约束章节、关键字段和 visual 类型存在，但不能判断创意质量、评分依据是否真实或概念是否具备商业洞察；需要后续 LLM judge。
- 本轮未新增创意、决策矩阵或 MVP 地图专属前端控件，仍复用现有 Markdown、Mermaid 和通用 `ai4se-visual` 渲染。
- 本轮未改变 Agent Runtime、typed SSE、workflow state、API path 或渲染管线。

### 总体进度

- `TEST_DESIGN`、`REQ_REVIEW`、`VALUE_DISCOVERY`、`INCIDENT_REVIEW`、`IDEA_BRAINSTORM` 五个 workflow 均已完成第一轮 artifact 专业化重构。
- 后续建议进入跨 workflow 的 LLM judge 样例集设计，优先覆盖：测试设计澄清、需求评审问题清单、价值发现蓝图、故障 RCA、创意收敛决策。
