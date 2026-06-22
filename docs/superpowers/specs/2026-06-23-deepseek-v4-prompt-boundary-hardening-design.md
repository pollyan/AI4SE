# DeepSeek V4 Prompt 边界去格式化设计

## 背景

DeepSeek V4 结构化产物数据链路已经完成 17 个在线 stage 的 `artifact_data` schema、后端 deterministic renderer、readiness gate、`artifact_data` persistence 和真实 smoke gate 对齐。后端 `agent_runtime.py` 在已迁移 stage 中要求模型只输出 JSON object，并且字段为 `chat`、`artifact_data`、`stage_action`、`warnings`。

但前端 `buildSystemPrompt()` 仍保留旧的 Markdown 产物更新规则，包括:

- `<mark>` 更新标识规则。
- `artifact_update` 当前阶段完整产物规则。
- “必须提供完整、全部的 Markdown 文档内容”。
- 当前 artifact 以 ```markdown fence 注入。

这会让 DeepSeek V4 在同一轮上下文中同时看到“只输出 artifact_data”和“输出完整 Markdown/mark/artifact_update”的冲突指令。即使后端最后追加了 `artifact_data` 结构化输出 instruction，旧 prompt 仍会增加模型误写 Markdown、Mermaid 或表格的概率。

## 用户故事

作为使用 DeepSeek V4 Flash 运行 New Agents 工作流的用户，当我在任意已迁移 `artifact_data` stage 生成产物时，我希望模型只负责输出业务结构化数据，后端负责 Markdown/Mermaid/`ai4se-visual` 格式化渲染，从而减少“格式不完整 / 结构化输出生成失败”。

## 目标

本轮目标是统一前端 prompt 与后端 `artifact_data` runtime 的边界:

1. 对所有已迁移 `artifact_data` stage，`buildSystemPrompt()` 不再注入 Markdown 更新、`<mark>`、`artifact_update`、完整文档重写或 markdown fence 指令。
2. 数据模式 prompt 仍保留 persona、workflow/stage、语言要求、左侧 chat 协作要求、阶段推进规则、当前/前序 artifact 上下文。
3. 当前 artifact 上下文只作为“已渲染参考内容”提供，不要求模型回写或维护 Markdown 格式。
4. 后端 typed SSE、shared Agent Runtime、artifact contract、run/artifact persistence 和 renderer registry 不改变。

## 非目标

- 不新增新的 `artifact_data` schema 或 renderer。
- 不新增 DeepSeek 专属 API、runtime、store 或 renderer。
- 不改真实模型调用凭证、网络 smoke 配置或 provider capability。
- 不改变未迁移到 `artifact_data` 的兼容输出路径。
- 不处理 New Agents Artifact 质量诊断、Alex 新 workflow 或主分支合并。

## 设计

### 1. 前端 stage 能力识别

在 `tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts` 中新增共享常量，列出当前已迁移到 `artifact_data` 的 workflow/stage:

- `TEST_DESIGN`: `CLARIFY`、`STRATEGY`、`CASES`、`DELIVERY`
- `REQ_REVIEW`: `REVIEW`、`REPORT`
- `INCIDENT_REVIEW`: `TIMELINE`、`ROOT_CAUSE`、`IMPROVEMENT`
- `IDEA_BRAINSTORM`: `DEFINE`、`DIVERGE`、`CONVERGE`、`CONCEPT`
- `VALUE_DISCOVERY`: `ELEVATOR`、`PERSONA`、`JOURNEY`、`BLUEPRINT`

该常量只影响 prompt 文案，不成为新的 runtime 或 contract 来源。后端 readiness gate 仍是最终 runtime 覆盖证据。

### 2. 数据模式 prompt

当当前 workflow/stage 命中 `artifact_data` 列表时:

- 移除 `<mark>` 规则。
- 阶段确认控件仍要求 `stage_action`，但不提 `artifact_update`。
- “不要在同一轮生成下一阶段产出物”保留。
- “产出物更新原则”改为“不要输出或维护 Markdown 产物正文；当前阶段业务数据由后端 renderer 生成右侧产物”。
- 当前 artifact 用普通参考块注入，说明其为后端已渲染参考，不能要求模型复制、补齐或回写 Markdown。

### 3. 兼容路径

如果未来存在未迁移 stage，则继续使用现有 Markdown prompt，以免破坏旧 `artifact_update` 路径。本轮当前在线 17 个 stage 全部命中数据模式。

## 验收条件

1. `buildSystemPrompt()` 对 `TEST_DESIGN/CLARIFY`、`VALUE_DISCOVERY/BLUEPRINT` 等已迁移 stage 不包含 `<mark>`、`artifact_update`、`必须提供完整、全部的 Markdown 文档内容`、```markdown fence。
2. 数据模式 prompt 仍包含 persona、当前工作流、当前阶段、阶段目标、chat 协作说明、`target_stage_id` 和前序阶段上下文摘要。
3. 前端 prompt 测试先能在旧实现上失败，再在实现后通过。
4. 后端 `test_deepseek_v4_readiness.py`、`test_agent_runtime.py`、`test_artifact_data_renderers.py` 继续通过，证明后端 artifact_data 指令、renderer 和 contract 未被破坏。
5. DeepSeek todo 记录本轮完成的 prompt 边界去格式化闭环。

## 风险

- 前端与后端各自维护 artifact_data stage 列表，存在未来新增 stage 时同步遗漏风险。本轮用前端测试覆盖当前 17 个 stage，并保留后端 readiness gate 作为 runtime 侧防线。
- 当前 artifact 从 Markdown fence 改为普通参考块后，模型仍会看到历史 Markdown 文本；但 prompt 明确要求只作为参考，不复制或回写 Markdown。
- 如果某些前端测试隐含期待 `<mark>` 规则，需要同步改为数据模式下不期待。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/buildSystemPrompt.test.ts`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_deepseek_v4_readiness.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py -q`
- `git diff --check`
