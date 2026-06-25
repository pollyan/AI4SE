# New Agents 右侧产出物增量更新与局部渲染 Todo

状态：待处理
创建日期：2026-06-25
相关模块：`tools/new-agents/`
用户反馈来源：本地 UI 使用反馈，右侧 ArtifactPane 产出物生成与更新体验

## 背景

用户希望右侧产出物做到真正的增量更新：每次生成和内容渲染时，只处理改变的部分，而不是每次都把完整 Markdown 文档作为一个整体替换和重渲染。

当前初步代码证据：

- SSE schema 已支持 `agent_delta`，其中 `artifact_update.markdown` 仍承载完整或阶段性 Markdown 文本。
- 后端 `artifact_data_renderers.py` 有 partial renderer，例如 `render_partial_test_design_clarify_markdown(...)`、`render_partial_test_design_strategy_markdown(...)`，但输出仍是 Markdown 字符串。
- 前端 `ArtifactPane.tsx` 当前主要以 `artifactContent` 作为整篇内容，经过 `preprocessMarkdown(...)` 后交给 `ReactMarkdown` 渲染。
- `ArtifactPane.tsx` 已有历史版本、章节提取、diff、批注、锁定、导出、手工编辑等能力，增量更新必须兼容这些现有协作能力。

## 目标能力包

让右侧产出物更新链路具备“局部变更感知”：后端或前端能识别本轮变更影响的章节/块，前端只更新和高亮变化区域，避免全篇闪动、全篇重排和大文档重复渲染。

## 建议方向

1. 定义 artifact patch 模型
   - 在不破坏现有 `artifact_update.markdown` 的前提下，评估新增可选 `artifact_patch` 或 `changed_sections` 元数据。
   - patch 应以共享结构表达，例如 `stageId`、`baseVersion`、`sectionAnchor`、`operation`、`before`、`after`、`range`。
   - 不新增 Lisa / Alex 专属 runtime、SSE path 或 renderer 分支。
2. 建立稳定章节/块锚点
   - 复用或强化 `ArtifactPane` 已有 `extractMarkdownSections(...)` 思路。
   - 处理重复标题、Mermaid / fenced block、Markdown 表格、列表、结构化可视化块等边界。
   - 章节锚点必须能服务批注、锁定、历史版本和手工编辑。
3. 前端增量应用
   - store 保留完整 artifact 内容作为事实源，同时维护本轮变更块索引。
   - UI 层按章节/块 memoize 渲染，避免无变化章节重复 ReactMarkdown 渲染。
   - 生成中 delta 到达时，只替换当前变更块；最终 `agent_turn` 到达后与完整内容校验一致。
4. 回退策略
   - 当 patch 与当前 baseVersion 不匹配、锚点歧义、结构化块边界不安全或服务端只给完整 Markdown 时，显式降级为整篇替换。
   - 降级必须可诊断，不能伪造局部更新成功。

## 验收标准

- 连续生成或更新产出物时，未变化章节不发生可感知闪动或重置。
- 前端能知道本轮变化涉及哪些章节/块，并只对这些区域做更新态处理。
- store / persistence 仍保存完整 artifact 内容，导出、复制、历史版本、批注、锁定和手工编辑不丢数据。
- patch 不安全时明确降级为完整 Markdown 替换，并保留可诊断原因。
- 该能力通过共享 Agent Runtime / typed SSE / ArtifactPane 基础设施实现，不引入 workflow 专属通道。

## 建议测试

- 后端 SSE schema / runtime 测试：可输出可选 patch 元数据，旧完整 `artifact_update.markdown` 路径仍兼容。
- 前端 store 测试：应用同 baseVersion 的 section patch 后，只改变目标章节并保留完整 artifact。
- 前端组件测试：未变化章节的渲染组件不重新 mount，变化章节更新。
- 回归测试：批注锚点、章节锁、历史版本、导出、手工编辑保存与冲突处理仍可用。
- 浏览器验收：长产物增量生成时只看到局部变化，不出现全篇闪动。

## 非目标

- 不要求 token 级逐字流式渲染。
- 不把完整 artifact 内容从 store / persistence 中移除。
- 不跳过最终完整内容校验。
- 不为单个 workflow 或 agent 创建独立增量协议。

## 2026-06-25 进展：需求澄清段落级流式收束

- 已收束 `TEST_DESIGN/CLARIFY` 的 `artifact_data` partial renderer：当 `requirement_facts`、`system_boundaries` 等顶层字段在 raw JSON stream 中完整闭合时，后端可在 final 前发出正式 Markdown 增量。
- 已保留完整 `artifact_update.markdown` 作为事实源；这次进展不是完整 `artifact_patch` / `changed_sections` 协议，长文档局部 patch、块级 memoized rendering、协作状态与导出回归仍保留在本 todo 后续能力包中。
- 验证：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "paragraph_level_clarify_artifact_data or paragraph_level_strategy_artifact_data or artifact_data_before_final_output" -q` 通过，`cd tools/new-agents/frontend && npm run test -- src/services/__tests__/chatService.test.ts` 通过。

## 2026-06-25 进展：前端章节变更索引

- 已新增 `artifactSections` 纯函数，前端可基于完整 Markdown 提取稳定章节 anchor，并比较本轮 Artifact 内容变化影响的章节。
- 已在 Zustand store 中维护非持久化 `artifactChangeIndex`，`setArtifactContent(...)` 记录同阶段 Artifact 更新范围，stage / workflow / snapshot / history reset 路径清空索引。
- 已在右侧 ArtifactPane 的“本轮变更”视图显示章节摘要，便于用户先从章节层面审阅长文档更新。
- 本切片仍未新增后端 `artifact_patch` / `changed_sections` SSE 契约，也未拆分 ReactMarkdown 为 memoized section rendering；这些仍属于本 todo 的后续工作。
- 验证：
  - `cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx -t "artifactSections|artifact section changes|changed section summary"` 通过，3 个测试文件内 8 个相关测试通过。
  - `cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactSections.test.ts src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx` 通过，3 个测试文件内 196 个测试通过；ArtifactPane 既有 act warning 仍存在。
  - `cd tools/new-agents/frontend && npm run lint` 通过。
  - `cd tools/new-agents/frontend && npm run test` 通过，44 个测试文件、679 个测试通过；ArtifactPane 既有 act warning 仍存在。
  - `./scripts/test/test-local.sh all` 已尝试：Intent Tester API、flake8、Common frontend build、New Agents frontend、New Agents backend 通过；Intent Tester proxy 因 `listen EPERM: operation not permitted 0.0.0.0:3002` 失败，New Agents Browser E2E 因 Chromium `bootstrap_check_in ... Permission denied (1100)` 失败，属于本地权限/沙箱阻塞，未作为本切片代码失败处理。
