# TEST_DESIGN 产出物专业化实施计划

## 目标

完成 `TEST_DESIGN` workflow 下 `CLARIFY`、`STRATEGY`、`CASES`、`DELIVERY` 四个 stage artifact 的专业化升级，并同步必要的 backend contract、contract sync tests、stream fixture 和 test asset parser/export 测试。

## 文件范围

- `tools/new-agents/frontend/src/core/prompts/test_design/clarify.ts`
- `tools/new-agents/frontend/src/core/prompts/test_design/strategy.ts`
- `tools/new-agents/frontend/src/core/prompts/test_design/cases.ts`
- `tools/new-agents/frontend/src/core/prompts/test_design/delivery.ts`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/backend/test_asset_parsing.py`
- `tools/new-agents/backend/tests/test_agent_contracts.py`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tools/new-agents/backend/tests/test_stream_services.py`
- `tools/new-agents/backend/tests/test_test_assets.py`
- 本轮记录文档：`docs/superpowers/specs/2026-06-22-test-design-artifact-professionalization-design.md`、本文档

## TDD 步骤

### 1. Contract RED

更新 `test_agent_contracts.py`：

- 断言 `build_artifact_contract_prompt(TEST_DESIGN/CLARIFY)` 包含新增核心标题：`需求事实清单`、`业务规则与数据状态`、`阶段门禁`。
- 扩展 `test_validate_agent_turn_rejects_test_design_cases_missing_executable_fields`，要求 `CASES` 缺少 `断言`、`执行层级`、`自动化建议`、`状态` 时失败。
- 保持 `TEST_DESIGN` 四个 stage 的完整模板校验继续覆盖 Mermaid 和 `ai4se-visual`。

预期：测试先失败，因为 backend contract 还没有新增标题和字段。

### 2. Parser RED

更新 `test_test_assets.py`：

- 将 `CASES_MARKDOWN` 升级为包含新用例字段的表格。
- 断言 `export_lisa_test_assets` 的 `testCases` 包含 `assertion`、`executionLayer`、`automationSuggestion`、`status`。
- 断言 intent tester draft description 包含断言和执行层级，便于导入前人工校准。
- 保持持久化 collection 仍只验证现有核心字段，避免本轮引入数据库 schema 迁移。

预期：测试先失败，因为 parser 当前只映射旧字段。

### 3. 实现 Contract

更新 `agent_contracts.py`：

- `TEST_DESIGN/CLARIFY` required headings 增加目标章节和关键表头。
- `TEST_DESIGN/STRATEGY` required headings 增加策略摘要、资源与取舍、阶段门禁和关键风险/测试点字段。
- `TEST_DESIGN/CASES` required headings 增加目标章节和新增用例字段。
- `TEST_DESIGN/DELIVERY` required headings 增加执行摘要、覆盖地图、开放风险、签署确认、变更记录。
- 保持现有 `flowchart`、`quadrantChart`、`block-beta`、`risk-board`、`traceability-matrix`、`coverage-map` 合同。

### 4. 实现 Prompt / Template

更新四个 `test_design/*.ts`：

- `CLARIFY`：从需求分析文档升级为测试需求分析与澄清基线，补齐事实表、规则表、异常链路、问题表、质量需求、后续策略输入、阶段门禁。
- `STRATEGY`：补齐策略摘要、质量目标表、FMEA 风险明细、资源取舍和阶段门禁。
- `CASES`：补齐用例设计依据、测试数据与环境、自动化候选、开放问题、阶段门禁；用例表新增 `断言`、`执行层级`、`自动化建议`、`状态`。
- `DELIVERY`：从拼接终稿升级为交付评审文档，补齐执行摘要、开放风险、签署确认、变更记录和 coverage-map。

### 5. 实现 Parser

更新 `test_asset_parsing.py`：

- 在 `TEST_CASE_HEADERS` 中加入新增字段，让 parser 优先识别新模板。
- `_map_test_case` 输出新增字段。
- `_build_intent_tester_draft` description 纳入断言、执行层级、自动化建议和状态。
- 兼容旧字段的策略：如果只出现旧表头，仍可解析旧 artifact；但 contract 会推动新 artifact 生成新字段。

### 6. 更新测试样例

更新 `test_stream_services.py` 的 `VALID_CLARIFY_ARTIFACT`，使其满足新 `CLARIFY` contract。

必要时更新 contract prompt 断言中旧标题期望。

### 7. 验证

最小验证命令：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_test_assets.py tools/new-agents/backend/tests/test_stream_services.py
```

辅助验证：

```bash
git diff --check
```

如前端模板只被 backend sync tests 静态读取，本轮不运行完整 Vitest；若修改触发 TypeScript 语法风险，再运行：

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts
```

## 风险与取舍

- `CASES` 新增字段会被 Markdown parser 导出，但不会进入 `AgentTestCaseVersion` 数据表；这是为了避免本轮扩张到数据库迁移和前端资产中心编辑模型。
- 后端 contract 只能约束标题、关键表头和 visual 存在，不能判断正文是否真正专业；更细的语义质量应进入后续 LLM judge / E2E evidence。
- 当前工作区非隔离且已有无关 zip 改动；本轮不得触碰这些文件。

## 完成记录模板

- 完成 workflow：`TEST_DESIGN`
- 覆盖 stage：`CLARIFY`、`STRATEGY`、`CASES`、`DELIVERY`
- 修改范围：prompt/template、backend contract、parser、backend tests、spec/plan
- 验证：记录 pytest 和 diff check 结果
- 残余风险：记录数据库不持久化扩展字段、LLM judge 未新增等
- 下一轮推荐：`REQ_REVIEW`

## 每轮提交规则

每完成并验证一个 workflow 后，形成一个聚焦 commit，并在远端仓库配置和权限可用时 push 到 Git。提交只包含本轮 workflow 相关文件；当前工作区已有的无关改动，例如 intent-tester zip 产物，不得被 stage 或提交。

## 本轮完成记录

- 完成 workflow：`TEST_DESIGN`
- 覆盖 stage：`CLARIFY`、`STRATEGY`、`CASES`、`DELIVERY`
- 已修改：四个 `test_design` prompt/template、backend artifact contract、`CASES` Markdown parser、contract/runtime/endpoint/test asset 测试、本轮 spec/plan
- 验证通过：
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_test_assets.py tools/new-agents/backend/tests/test_test_asset_parsing.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_endpoint.py`
  - `./node_modules/.bin/tsc --noEmit --allowImportingTsExtensions --moduleResolution Bundler --module ESNext --target ES2022 --jsx react-jsx --resolveJsonModule --esModuleInterop --strict src/core/workflows.ts`
  - `git diff --check`
- 未通过但非本轮引入：
  - `cd tools/new-agents/frontend && npm run lint` 失败于既有 `src/core/__tests__/artifactMerge.test.ts` 类型错误：`"context"` 不属于 `"removed" | "unchanged" | "added"`。
- 残余风险：
  - `CASES` 新增扩展字段已在 Markdown 导出层和 intent tester draft 描述中保留，但没有扩展 `AgentTestCaseVersion` 数据库 schema，资产中心持久化编辑仍以旧核心字段为准。
  - 本轮未新增真实模型 LLM judge，只更新了 contract 和 smoke 提示词；语义专业度仍需要后续 judge/evidence 加强。
- 下一轮推荐：`REQ_REVIEW`，先补强需求评审入口质量，再作为 `TEST_DESIGN` 的上游输入。
- 当前全量进度：已完成 1/5 workflow。
