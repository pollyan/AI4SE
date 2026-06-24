# E11 Prompt/template 版本管理设计

> 日期: 2026-06-24
> Milestone: New Agents E11 Prompt/template 版本管理
> 状态: 已实现待合回

## 1. 背景与目标

New Agents 当前已经具备共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型和共享 UI。E10 已在 `codex/professional-method-library` 中把专业方法收敛为共享配置。E11 继续补齐平台化治理的最后一块：每个 stage 的 prompt/template 需要有明确版本和回归样例，避免 prompt 改动后无法追踪、无法本地复核，也避免新增 workflow 时只补 prompt 文件而漏掉质量证据。

本轮目标是建立一个轻量、可测试、配置驱动的 prompt/template 版本管理闭环：所有在线 stage 在 `workflow_manifest.json` 中声明 `promptTemplateVersion` 和 `regressionSampleIds`，共享 `prompt_regression_samples.json` 记录回归样例，前端系统提示注入当前版本标识，后端同步测试阻止漏版本、未知样例或样例指向错误。

完成后用户可观察到的能力增量是：维护者可以追踪每个 stage 当前使用的 prompt/template 版本，并有最小回归样例作为变更审计入口；后续新增或修改 workflow 不再只靠人工记忆维护 prompt 质量证据。

## 2. Superpowers 头脑风暴自问自答

### 2.1 Explore Project Context

问：E11 是否需要拆分？

答：不拆。E11 的完整能力是“每个 stage 的 prompt/template 可审计、可回归”，可以一次覆盖 metadata、回归样例、prompt 注入、同步测试和 todo 状态。

问：E11 应基于哪个代码状态？

答：基于 `codex/professional-method-library`，因为 E10 已经把 stage 配置向 manifest 收敛；E11 继续把 prompt/template version 和 regression samples 放进同一配置体系。

问：当前缺口在哪里？

答：`workflow_manifest.json` 只有 `promptTemplateId` 和 E10 的 `methodIds`；没有版本字段、没有回归样例引用、没有测试强制每个 stage 声明版本和样例，`buildSystemPrompt()` 也不暴露当前 prompt/template 版本。

### 2.2 Visual Companion Decision

问：需要视觉辅助吗？

答：不需要。本轮是配置、prompt 构造和同步测试，不涉及 UI 视觉设计。

### 2.3 Clarifying Questions

问：谁会使用这个能力？

答：维护 New Agents workflow 的开发者、做质量复盘的 reviewer，以及后续定位 LLM 输出变化的工程人员。

问：成功状态是什么？

答：每个 online stage 都有合法 `promptTemplateVersion` 和至少一个 `regressionSampleId`；所有 sample 都能反查到 workflow/stage；系统提示包含当前 prompt/template 版本；测试能阻止漏字段、未知 sample、版本格式错误。

问：输入来源是什么？

答：版本和样例来自仓库内共享配置，不来自数据库、远端 API 或用户 UI。版本初始采用日期化格式，例如 `2026.06.24.1`，保证人工可读、可排序、适合后续变更。

问：失败路径是什么？

答：新增 stage 没版本、版本格式不合法、sample id 拼错、sample 指向不存在 stage、prompt builder 漏注入版本，都应在本地测试失败，而不是等远端 CI 或模型效果退化。

问：下游如何承接？

答：未来可把 regression samples 接入 LLM judge 或 dry-run；本轮只建立元数据和本地同步门禁，不调用外部模型。

问：本轮不做什么？

答：不做 UI 版本面板、不做数据库版本历史、不做真实模型 smoke、不大改 prompt 内容、不做最终 merge/push/delete branches。

### 2.4 Approaches

方案 A：只在前端 `STAGE_CONTENT_BY_TEMPLATE_ID` 增加版本字段。

取舍：实现快，但后端 manifest sync 无法约束，新增 workflow 仍可能漏版本。不选。

方案 B：在 `workflow_manifest.json` stage 上新增 `promptTemplateVersion` 和 `regressionSampleIds`，新增共享 `prompt_regression_samples.json`，前后端同步测试校验，prompt builder 注入版本标识。

取舍：与 E10 manifest 配置化一致，能覆盖每个 stage，又不引入 API/DB。推荐。

方案 C：新增后端 prompt registry API，运行时下发版本和样例。

取舍：未来可以动态化，但当前没有在线编辑、权限、缓存需求；会扩大 runtime/API 面，不符合最小可信闭环。不选。

### 2.5 Presented Design

Architecture：`workflow_manifest.json` 是 stage metadata 事实源；新增 `promptTemplateVersion` 和 `regressionSampleIds`。`prompt_regression_samples.json` 存储每个 stage 的短输入样例、预期关注点和验收检查。前端类型读取 metadata，`buildSystemPrompt()` 注入“Prompt/template 版本”。后端 sync tests 校验每个 stage 版本和 sample 关系。

Components：

- `workflow_manifest.json`：每个 stage 声明 `promptTemplateVersion`、`regressionSampleIds`。
- `prompt_regression_samples.json`：共享回归样例 registry，记录 `id`、`workflowId`、`stageId`、`input`、`expectedFocus`、`acceptanceChecks`。
- `workflowRegistry.ts` / `types.ts`：扩展 stage metadata 类型。
- `buildSystemPrompt.ts`：注入当前 stage prompt/template 版本标识。
- `test_workflow_contract_sync.py`：校验版本格式、样例引用、Docker/Compose 打包。
- `buildSystemPrompt.test.ts`：校验版本标识注入。

Data flow：workflow/stage 选择 -> `WORKFLOWS` 携带 version/sample ids -> `buildSystemPrompt()` 输出当前版本标识 -> LLM 仍走共享 `/api/agent/runs/stream` -> reviewer 可从 prompt 或 tests 定位版本。

Error handling：metadata 缺失和未知 sample 在测试期失败；运行时不静默生成假版本，不改变 typed SSE/API。

Testing：先写 frontend/backend RED tests，再补 metadata/samples/helper，最后跑 Vitest、pytest sync、frontend build、文档未完成标记扫描和 `git diff --check`。

## 3. 用户故事

作为 New Agents workflow 维护者，我希望每个 stage 的 prompt/template 都有可审计版本和回归样例，这样当 prompt 或 template 变化导致输出质量波动时，我能定位变更版本，并用样例快速复核核心能力是否被破坏。

## 4. 范围

### 纳入

- 为所有在线 workflow stage 声明 `promptTemplateVersion`。
- 为所有在线 workflow stage 声明至少一个 `regressionSampleId`。
- 新增共享 prompt regression sample registry。
- 系统提示中注入当前 stage 的 prompt/template 版本标识。
- 前后端测试覆盖版本和样例同步。
- Docker/Compose 打包共享 sample registry。
- 更新 E11 todo 状态、spec 和 plan。

### 不纳入

- 真实 LLM smoke 或 LLM judge。
- Prompt 内容重写、模板大改、模型参数调优。
- UI 版本面板、数据库版本历史、远端配置 API。
- 最终 merge/push/delete branches。

## 5. 验收标准

- 所有 `workflow_manifest.json` stage 都有合法 `promptTemplateVersion`，格式为 `YYYY.MM.DD.N`。
- 所有 stage 都声明至少一个 `regressionSampleId`。
- `prompt_regression_samples.json` 中每个 sample 都指向已存在 workflow/stage，包含非空输入、预期关注点和验收检查。
- 未知 sample id、漏版本、版本格式错误会让后端 sync test 失败。
- `buildSystemPrompt()` 对当前 stage 注入 `Prompt/template 版本：<version>`。
- 没有新增 Lisa/Alex 专属 runtime、API path、store 或 renderer。

## 6. 风险与缓解

- 风险：给 17 个 stage 一次性加 metadata 容易漏字段。
  缓解：后端 sync test 遍历所有 manifest stages，逐项校验。
- 风险：回归样例太长导致配置臃肿。
  缓解：样例只记录短输入、预期关注点和验收检查，不保存完整模型输出。
- 风险：版本字段和 artifact version 混淆。
  缓解：字段命名为 `promptTemplateVersion`，只表示 prompt/template 配置版本，不表示 run artifact version。
- 风险：Docker/Vite 相对路径漏打包。
  缓解：同步测试覆盖 frontend/backend Dockerfile 和 dev compose 对 sample registry 的打包/挂载。

## 7. 验证计划

- 前端：`cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts`。
- 前端构建：`cd tools/new-agents/frontend && npm run build`。
- 后端同步：`.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q`。
- 文档/格式：`rg "\bTB[D]\b|\bTO[D]O\b|占[位]" docs/superpowers/specs/2026-06-24-prompt-template-versioning-design.md docs/superpowers/plans/2026-06-24-prompt-template-versioning.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`，以及 `git diff --check`。
