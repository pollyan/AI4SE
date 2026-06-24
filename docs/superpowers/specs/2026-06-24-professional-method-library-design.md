# E10 专业方法库配置设计

> 日期: 2026-06-24
> Milestone: New Agents E10 专业方法库配置
> 状态: 设计中

## 1. 背景与目标

当前 New Agents 已经通过共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、run persistence 和共享 UI 支撑 Lisa/Alex 多工作流。剩余活跃能力包中，E10 要解决的是专业方法散落问题：FMEA、JTBD、RICE、Kano、CAPA、ICE 等方法目前散布在 prompt、manifest、renderer 示例和 contract 文案里，缺少统一配置、引用校验和 prompt 注入路径。

本轮目标是建立一个可测试的专业方法库配置闭环：workflow stage 可以声明使用哪些专业方法，系统提示词会注入这些方法的简明说明，本地测试会阻止未知方法或漏配置进入共享运行链路。

完成后用户可观察到的能力增量是：维护者不再只能改散落 prompt 文案来调整专业方法，而可以通过共享配置声明 stage 方法包；Lisa/Alex 输出的专业方法依据也更容易被审计、扩展和回归测试保护。

## 2. Superpowers 头脑风暴自问自答

### 2.1 Explore Project Context

问：当前需求是否过大，需要拆分吗？

答：不需要拆成多个 Superpowers。E10 的用户价值是“专业方法配置化”，可以形成一个完整平台能力包：统一 registry、stage 引用、prompt 注入、同步测试和 todo 状态记录。它不包含 E11 的 prompt/template version 治理。

问：现有代码怎么组织 prompt 和 workflow？

答：`workflow_manifest.json` 声明 workflow、stage 和 `promptTemplateId`；前端 `workflows.ts` 通过 `STAGE_CONTENT_BY_TEMPLATE_ID` 手工映射 prompt/template；后端 `agent_contracts.py` 和 `test_workflow_contract_sync.py` 有 manifest、artifact contract、prompt 文件同步测试。专业方法目前是字符串散落，没有统一配置面。

问：会不会破坏共享 Agent Runtime？

答：不会。本轮只在 shared manifest、prompt 构造和同步测试层引入配置，不新增 agent-specific runtime、API path、store 或 renderer。

### 2.2 Visual Companion Decision

问：需要视觉辅助吗？

答：不需要。本轮是配置、prompt 构造和测试门禁，不涉及 UI 布局、视觉设计或交互取舍。

### 2.3 Clarifying Questions

问：目标用户是谁？

答：直接用户是维护 New Agents workflow/prompt 的开发者；间接用户是依赖 Lisa/Alex 专业输出质量的产品、测试和研发协作方。

问：用户要完成什么？

答：开发者能在共享配置中声明某个 stage 应使用哪些专业方法，运行时系统提示能稳定注入方法说明，测试能阻止未知方法或漏配置。

问：成功状态是什么？

答：至少 FMEA、JTBD、RICE、Kano、CAPA、ICE 等方法在一个 registry 中有 `id`、`name`、`description`、`guidance`；manifest stage 能引用 method ids；构建系统提示时注入当前 stage 的方法说明；同步测试覆盖 registry 存在、引用合法、重点 stage 带有方法包。

问：失败路径是什么？

答：未知 method id、空 method list、registry 缺字段、prompt 注入丢失都应由本地测试暴露，不靠运行时静默 fallback。

问：下游如何承接？

答：E11 prompt/template 版本管理可以复用同一个 registry 边界，在 prompt/template metadata 上记录 version 和回归样例，而不是继续扩大散落映射。

问：本轮不做什么？

答：不做 E11 prompt/template version，不做用户可编辑方法库 UI，不做数据库持久化，不做真实模型 smoke，不做最终主线合并推送。

### 2.4 Approaches

方案 A：只在前端新增 method registry 并注入 prompt。

取舍：实现快，但后端测试无法约束 manifest/contract 同步，容易前后端漂移。不选。

方案 B：在 `workflow_manifest.json` 增加 stage-level `methodIds`，前端新增 typed method registry 注入 prompt，后端同步测试读取 manifest 校验 method ids。

取舍：改动面适中，保持现有 manifest 驱动模式，能形成配置 -> prompt -> 测试闭环。推荐。

方案 C：新增后端 API 动态下发方法库。

取舍：未来可扩展，但当前没有用户编辑或远程配置需求，会引入 API、缓存、错误恢复和测试面，超过 E10 最小可验收范围。不选。

### 2.5 Presented Design

Architecture：`workflow_manifest.json` 继续是 workflow/stage 事实源；新增 stage `methodIds`。前端 `professionalMethods.ts` 提供 registry 和 `buildProfessionalMethodPromptSection()`；`buildSystemPrompt()` 在当前 stage 拼接方法说明。后端同步测试读取同一 manifest 并校验 method ids 合法。

Components：

- `workflow_manifest.json`：每个高价值 stage 声明 `methodIds`。
- `frontend/src/core/professionalMethods.ts`：定义专业方法 registry、读取和 prompt section 构造。
- `frontend/src/core/prompts/buildSystemPrompt.ts` 或现有 prompt builder：把当前 stage 的 method section 注入系统提示。
- `backend/tests/test_workflow_contract_sync.py`：校验 manifest 中的 method ids 存在且重点 stage 不为空。
- frontend prompt tests：校验当前阶段系统提示包含专业方法参考。

Data flow：用户选择 workflow/stage -> `WORKFLOWS` 从 manifest 得到 stage method ids -> `buildSystemPrompt()` 取当前 stage -> method registry 渲染为“专业方法参考”段落 -> LLM 在共享 `/api/agent/runs/stream` 仍按现有 typed SSE 返回。

Error handling：开发期 unknown method id 通过测试失败暴露；运行时构造 prompt 时若 manifest 引用未知 id，直接抛明确错误，不静默跳过；没有声明 method ids 的 stage 不注入方法段，避免把空配置伪装成成功。

Testing：先写失败测试，验证 prompt 当前缺少方法段、manifest 缺少 `methodIds` 或 registry 校验失败；再实现 registry 和注入；最后跑 frontend prompt tests、backend workflow contract sync 聚焦测试和 `git diff --check`。

## 3. 用户故事

作为 New Agents workflow 维护者，我希望在共享 workflow 配置中声明阶段使用的专业方法，并让系统提示自动带入这些方法说明，这样新增或调整 Lisa/Alex 工作流时，不需要在多个 prompt 字符串中手工复制方法说明，也能通过测试发现未知方法引用。

## 4. 范围

### 纳入

- 新增专业方法 registry，覆盖 FMEA、JTBD、RICE、Kano、CAPA、ICE，以及当前 Lisa/Alex 高频方法。
- 在共享 workflow manifest 的 stage 上声明 `methodIds`。
- 在系统提示构造中注入当前 stage 的专业方法参考。
- 补充前端 prompt tests 和后端 manifest sync tests。
- 更新 E10 todo 状态和本轮 plan。

### 不纳入

- Prompt/template version 和回归样例治理，留给 E11。
- 方法库 UI、数据库持久化、远程配置、用户自定义方法。
- 新增 Agent Runtime、API path、store 或 renderer。
- 真实模型 smoke、外部 LLM judge、最终 merge/push/delete branch。

## 5. 验收标准

- `workflow_manifest.json` 中选定 stage 可声明 `methodIds`，且至少覆盖 Lisa `TEST_DESIGN/STRATEGY`、Lisa `INCIDENT_REVIEW/IMPROVEMENT`、Alex `VALUE_DISCOVERY/JOURNEY`、Alex `IDEA_BRAINSTORM/CONVERGE` 等代表阶段。
- 未知 method id 会让同步测试失败。
- `buildSystemPrompt()` 对带 `methodIds` 的 stage 注入“专业方法参考”段，内容包含方法名和使用指引。
- 没有 `methodIds` 的 stage 不注入空标题或空内容。
- 现有共享 `/api/agent/runs/stream`、typed SSE、run persistence、artifact contract 不新增分支。
- `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 E10 标记为已完成待合回，并保留 E11 为剩余能力包。

## 6. 风险与缓解

- 风险：方法说明过长会挤占系统提示上下文。
  缓解：registry 中只放短说明和 stage 使用指引，不复制完整模板。
- 风险：前端 registry 与后端测试允许列表漂移。
  缓解：后端测试直接读取前端 registry 源文件中的 method id，或维护简单解析约束，确保 manifest 引用可校验。
- 风险：一次性给所有 stage 加 method ids 增加审查成本。
  缓解：本轮覆盖代表性高价值 stage，并通过测试要求已有声明合法；未声明 stage 不阻断运行。
- 风险：和 E11 版本治理边界混淆。
  缓解：本轮只管理 method ids 和 prompt 注入，不新增 version 字段。

## 7. 验证计划

- 前端：运行 `cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts`。
- 后端：运行 `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q`。
- 文档/格式：运行 `rg "TB[D]|TO[D]O|待[补]|占[位]" docs/superpowers/specs/2026-06-24-professional-method-library-design.md docs/superpowers/plans/2026-06-24-professional-method-library.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 和 `git diff --check`。
- CI 等价：本轮触及 TypeScript prompt 构造、JSON manifest 和 Python sync tests；上述前端聚焦 test 与后端 sync test 是最小等价门禁，若后续触及更广前端类型或 backend runtime 再扩大验证。
