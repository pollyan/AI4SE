# New Agents 右侧产出物流式位置提示 Todo

> 状态: 已完成，待归档
> 创建日期: 2026-06-24
> 背景: 右侧产出物已恢复为正式 Markdown 格式的逐步渲染。当前体验可以接受“按字段/章节逐段出现”，不强求逐字 token 级渲染；新的体验缺口是下一部分内容生成期间，右侧对应位置缺少“正在渲染中”的位置提示，用户容易误以为页面卡住或流式中断。

## 完成记录

- 完成日期: 2026-06-25
- 目标模式产物:
  - `docs/superpowers/specs/2026-06-25-new-agents-artifact-streaming-position-indicator-design.md`
  - `docs/superpowers/plans/2026-06-25-new-agents-artifact-streaming-position-indicator.md`
- 实现摘要:
  - `ArtifactPane` 在 `isGenerating=true` 且已有正式 `artifactContent` 时，在正文流末尾显示 UI-only indicator。
  - 首个 artifact delta 到达前仍使用顶部生成状态；已有正文后不再显示顶部全局生成卡片。
  - indicator 使用独立 JSX 节点和 `data-artifact-ephemeral="true"`，不拼入 Markdown 源文本。
  - Markdown 下载、源码视图和 store 中的 `artifactContent` 均不包含 indicator 文案。
- 验证:
  - `npm run test -- src/components/__tests__/ArtifactPane.test.tsx` in `tools/new-agents/frontend`
  - `npm run test` in `tools/new-agents/frontend`

## 当前状态

- 后端结构化 `artifact_data` streaming 已能在最终 `agent_turn` 前通过 typed SSE 发送 `agent_delta.artifact_update`。
- 右侧不应再显示 `# 产出物生成中`、字符数、字段名等调试式进度页。
- 2026-06-25 协议边界重构已补后端回归测试: partial `artifact_data` 不得合成为 `artifact_update.replace` 进度页；前端 parser 保留历史占位过滤防线。
- 已渲染内容应继续使用最终产物相同的正式样式，例如 `# 需求分析文档`、`## 文档信息`、正式表格、Mermaid 和 `ai4se-visual`。
- 当前逐步渲染粒度是章节/字段级，不是逐字级；该粒度本身可接受。

## 体验缺口

当后端正在生成下一部分 `artifact_data` 时，右侧只显示已经完成的章节。下一章节尚未到达或尚未通过局部 renderer 校验时，页面缺少一个和内容位置绑定的进行中状态。

用户期望:

- 已完成章节保持正式渲染。
- 下一部分即将出现的位置显示一个轻量的“正在渲染中”提示。
- 提示应出现在右侧产物正文流的对应位置，而不是顶部全局状态或独立进度页。
- 生成完成后提示自动消失，并由真实内容替换。

## 目标

实现右侧 ArtifactPane 的“章节位置级 streaming indicator”:

- 在产物生成期间，把已完成内容和正在生成位置都展示在同一个右侧产物正文流里。
- indicator 文案可类似“正在渲染下一部分...”或“正在生成后续章节...”，并配合轻量 loading 状态。
- indicator 只作为 UI 状态存在，不写入最终 artifact markdown，不进入持久化 artifact version，不参与复制、导出、质量诊断或 contract 校验。
- 当新的 `artifact_update.markdown` 到达时，indicator 跟随最新内容末尾移动；最终 `agent_turn` 到达后 indicator 清除。

## 非目标

- 不要求逐字 token 级产物渲染。
- 不恢复字符数、字段名、`# 产出物生成中` 等调试式进度页。
- 不新增 Lisa、Alex 或 DeepSeek 专属 renderer、store、API path 或 runtime。
- 不改变最终 Markdown artifact contract。
- 不把 loading 文案持久化到 run artifact、artifact version、导出文件或剪贴板。

## 架构约束

- 必须继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型和共享 UI 基础设施。
- 差异应通过共享 `ArtifactPane` / stream state 表达，而不是为具体 workflow 或 agent 分叉渲染链路。
- indicator 应兼容所有在线 workflow；首批验收可以优先覆盖 `TEST_DESIGN/CLARIFY`，但实现不得硬编码 Lisa 或该阶段。

## 建议实现方向

### 方案 A: 前端 UI-only indicator

前端在 `isGenerating=true` 且右侧已有流式 artifact delta、最终 `agent_turn` 尚未到达时，在 ArtifactPane 正文末尾追加一个非 Markdown 的 loading 组件。

优点:

- 不改变 SSE schema。
- 不污染 artifact markdown。
- 对后端侵入最小。

需要注意:

- 不能把 indicator 拼进 `artifactContent` 字符串。
- 复制、导出、版本保存、质量诊断读取的仍必须是原始 artifact markdown。
- 当 artifact 更新到达时，应重新渲染 markdown，并把 indicator 放在新内容之后。

### 方案 B: typed SSE 增加渲染状态 hint

后端 `agent_delta` 可选携带非持久化 `rendering_status` / `artifact_stream_state`，告知当前正在等待的 artifact field 或 section。

优点:

- 位置提示可以更精确，例如“正在生成业务规则与数据状态”。

代价:

- 需要扩展 SSE schema、前端解析、测试和兼容策略。
- 必须保证新增字段仍是共享 runtime 通用能力，不变成 workflow 专属协议。

建议优先评估方案 A；只有当 UI-only 无法定位到合理位置时，再考虑方案 B。

## 验收标准

- 生成过程中，右侧已完成内容以正式 artifact 样式逐段出现。
- 下一部分尚未到达时，右侧正文末尾或下一章节位置显示“正在渲染中”类提示。
- 提示不会出现在最终 artifact markdown 中。
- 提示不会出现在复制、导出、artifact version、run snapshot、质量诊断输入中。
- 最终响应完成后，indicator 清除，右侧只保留正式产物内容。
- 不再出现 `# 产出物生成中`、`已接收字符数`、`已识别字段`。
- 对截断场景仍能保留最后一个有效 artifact delta，并能明确显示截断 warning，不伪造完整内容。

## 建议测试

- Frontend:
  - `ArtifactPane` 在 `isGenerating=true` 且 artifact 为部分内容时显示非持久化 indicator。
  - `isGenerating=false` 后 indicator 消失。
  - 复制/导出/质量诊断使用的 artifact 内容不包含 indicator 文案。
  - typed SSE 多个 `agent_delta` 到达时，indicator 随最新 artifact 内容移动。
- Backend:
  - 若不扩展 SSE schema，保留现有 runtime streaming 测试即可。
  - 若扩展 SSE schema，需要补 `sse_schemas.py`、`stream_services.py`、frontend `llm.ts` 解析测试。
- Browser/E2E:
  - 使用 fake streaming LLM 模拟 `artifact_data` 分块输出。
  - 验证右侧在 final 前显示正式内容和 loading indicator。
  - 验证 final 后右侧没有 loading indicator。

## 残余问题

- indicator 是否应该只放在正文末尾，还是根据 workflow/stage 的章节顺序预判下一章节标题。
- 对 Mermaid 或 `ai4se-visual` 这种渲染较慢的块，是否需要区分“模型仍在生成”和“浏览器仍在渲染图表”。
- 当用户切换到源码视图时，是否也展示非持久化 indicator，或只在预览视图展示。
