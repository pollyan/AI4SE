# New Agents 左侧自然聊天防模板化回归设计

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、目标模式手册、剩余活跃 todo、`tools/new-agents/frontend/src/core/prompts/buildSystemPrompt.ts`、`tools/new-agents/frontend/src/core/prompts/__tests__/buildSystemPrompt.test.ts`、`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/agent_runtime.py`、`tools/new-agents/backend/tests/test_agent_contracts.py`、`tools/new-agents/frontend/src/components/__tests__/ChatPane.markdown.test.tsx`。
- 当前工作区：intent-tester 生成文件是既有脏文件，本轮不触碰、不 stage。
- 本轮允许写入：自然聊天相关 prompt/contract 文案、对应前后端测试、本 spec、配套 plan 和对应 todo 记录。

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 左侧自然聊天防模板化回归 | `docs/todos/2026-06-25-new-agents-natural-chat-readability.md`；当前 prompt 中“建议保留 2 到 4 个短段落或短列表”的固定长度倾向 | 用户阅读左侧 assistant 同步 -> 简单时自然短段落 -> 复杂时按需短列表/重点 -> 不固定 bullet 数量或标签 | 只改 prompt 无法防回归；只补 UI Markdown 测试不能约束模型输出指令 | 前端 prompt 测试、后端 contract/runtime 指令测试、ChatPane Markdown 渲染测试 |
| 产出物去表格化审计 | 去表格化 todo | 右侧 Artifact 阅读节奏更自然 | 跨 renderer/prompt/导出，适合后续较大能力包 | renderer/prompt/导出测试 |
| 右侧本轮 diff 标识 | diff 标识 todo | 用户审阅新增/删除变化 | 需要状态、渲染和导出保护 | diff/UI/导出测试 |

### 排序结论

本轮选择“左侧自然聊天防模板化回归”。它直接对应用户反馈“不要八股文”，且能在 prompt/contract 层做机械保护，避免未来再次把 chat 改成固定栏目或固定 bullet。

### 切片厚度门禁

- 入口：New Agents shared Agent Runtime 的 system prompt 和 backend structured output instruction。
- 动作：模型生成 `chat` 字段，前端 ChatPane 渲染左侧对话。
- 处理：prompt 明确要求自然工作对话、按复杂度选择短段落或短列表，并禁止固定 bullet 数量、固定标签和固定字段模板。
- 可见结果：左侧对话保持自然同步感，同时复杂内容仍可扫读。
- 状态承接：不改变右侧 Artifact、SSE、store 或 stage_action。
- 失败反馈：如果模型仍输出完整 Artifact Markdown 到 chat，现有 contract validation 继续拦截。
- 证据：前后端 prompt/contract 测试和 ChatPane Markdown 渲染测试。
- 结论：通过。

## Superpowers 自问自答

### Explore Project Context

前端 `buildSystemPrompt.ts` 已经要求 chat 像自然工作对话，不复制右侧正文，并在右侧更新时提示用户查看右侧产物。后端 `agent_contracts.py` 已经禁止 chat 包含标题、表格、代码块、Mermaid、完整正文和旧标签协议。

缺口在于后端 raw structured streaming prompt 多处仍包含“建议保留 2 到 4 个短段落或短列表”。这不是固定 bullet 数量，但会强化固定长度模板倾向；同时测试只断言存在“自然工作对话”，没有断言禁止固定 bullet 数量和固定标签。

### Visual Companion Decision

本轮是 prompt/contract 行为收束，不涉及 UI 布局设计；现有 `ChatPane.markdown.test.tsx` 已覆盖 Markdown 可读渲染，不需要视觉 companion。

### Clarifying Questions

- 用户是谁：在 New Agents 左侧对话区阅读 Agent 工作同步的用户。
- 用户要完成什么：快速理解本轮做了什么、右侧更新了什么、还需确认什么。
- 成功状态是什么：prompt 不强制每轮固定 bullet 数量或固定标签；简单回复可短段落，复杂回复可少量列表和重点。
- 输入来源是什么：shared system prompt、backend structured output instruction 和模型 `chat` 字段。
- 不做什么：不重写 ChatPane UI、不逐字流式 chat、不改变右侧 Artifact 格式。

### Approaches

1. 推荐：软化 prompt/contract 中固定长度表达，新增前后端测试禁止固定 bullet 数量和固定标签。优点是最小化改动并机械保护用户反馈；缺点是不能保证所有模型都完美遵守，但契约方向明确。
2. 不选：把 chat 统一改成固定“摘要/风险/下一步”栏目。它正是用户不想要的八股文。
3. 不选：只改 ChatPane 样式。UI 能渲染列表/加粗，但无法防止模型被 prompt 引导成固定模板。

### Presented Design

前端 `buildSystemPrompt.ts` 的 chat 协同要求改为：根据内容复杂度自然选择短段落、少量列表、加粗重点或引用块；简单同步可以是一两个自然短段落；复杂或需要确认时再使用列表。明确禁止“每次必须输出固定数量 bullet”或“每条必须以固定标签开头”。

后端 `agent_contracts.py` 保留“适度使用 bullet、少量重点加粗或引用块帮助扫读，但不要每轮套用固定栏目或固定字段模板”。`agent_runtime.py` 中重复的 raw structured prompt 文案同步软化，去掉“2 到 4 个”的固定长度建议。

测试层补强三类证据：前端 system prompt 不包含固定 bullet/标签硬要求；后端 contract/runtime 指令包含自然/按需列表/不固定模板要求；ChatPane 继续能渲染自然段落、列表、加粗、链接和代码。

## 验收条件

1. Given 构建前端 system prompt，When 检查 chat 协同要求，Then 包含自然工作对话、短段落、按需短列表、重点加粗和不复制右侧正文。
2. Given 构建前端 system prompt，When 扫描固定模板反模式，Then 不包含“每次必须输出固定数量 bullet”“每条必须以固定标签开头”等硬约束。
3. Given 构建后端 artifact contract prompt，When 检查 chat 要求，Then 包含自然顾问式对话、适度 bullet、少量重点加粗和不要固定栏目/字段模板。
4. Given raw structured output instruction，When 检查 chat 要求，Then 不再包含“2 到 4 个短段落或短列表”。
5. Given ChatPane 渲染自然 Markdown 回复，Then 段落、列表、加粗、链接、引用和代码保持可读。

## 非目标

- 不要求逐字或逐句流式渲染左侧 chat。
- 不重写右侧 ArtifactPane 的产物格式。
- 不把所有 assistant 回复统一改成固定模板、固定标题或固定 bullet 数量。
