# New Agents 右侧产出物新增/删除 Diff 标识记录

状态：已完成
创建日期：2026-06-25
完成日期：2026-06-25
相关模块：`tools/new-agents/frontend`
用户反馈来源：本地 UI 使用反馈，右侧 ArtifactPane 产出物审阅体验

## 背景

用户希望右侧产出物更新后能像代码 diff 工具一样标识变化：新增文字绿色、删除文字红色并带删除线，方便审阅本轮 Agent 对产出物的改动。

## 完成内容

- 在 `ArtifactPane` 正式阅读区增加“本轮变更”视图。
- 复用既有 `buildLineDiff(previousContent, currentContent)` 行级 diff 能力，不新增 diff 算法分支。
- 使用当前阶段 `artifactHistory` 推导本轮基线：
  - 最新历史版本等于当前内容时，使用倒数第二个版本作为基线。
  - 最新历史版本不等于当前内容时，使用最新历史版本作为生成中或未保存变化的基线。
- 新增工具栏 toggle，用户可显示或隐藏本轮变更。
- 新增 diff 行样式：新增行绿色，删除行红色并带删除线。
- 对 Markdown 表格、Mermaid、`ai4se-visual` 和代码块采取保守策略：本轮 diff 以源码行展示，不把半截结构化块交给 Markdown renderer。
- 保持 `artifactContent`、`stageArtifacts`、历史版本、下载 Markdown、DOCX/PDF 导出和下一轮 prompt 的事实源为干净最终 Markdown。

## 验收结果

- 当前阶段存在上一版和当前版时，右侧正式阅读区默认显示“本轮变更”。
- 新增内容显示为绿色行。
- 删除内容显示为红色删除线行。
- 用户可以隐藏本轮变更，回到干净 Markdown 预览。
- 下载 Markdown 时仍导出干净 `artifactContent`，不会包含 diff 前缀、颜色标记或已删除行。
- 当前阶段没有可用前序基线时，不显示本轮 diff 控件。

## 验证

- `cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.test.tsx -t "current artifact change diff|clean markdown|no previous baseline"`：通过，4 tests。
- `cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ArtifactPane.test.tsx`：通过，145 tests。
- `cd tools/new-agents/frontend && npm run test -- src/core/__tests__/artifactDiff.test.ts src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`：通过，133 tests。
- `cd tools/new-agents/frontend && npm run lint`：通过。
- `cd tools/new-agents/frontend && npm run test`：通过，43 files，671 tests。
- `./scripts/test/test-local.sh all`：本目标会话前序已尝试，受本机沙箱/系统权限阻塞。已记录的失败包括 Intent Tester proxy 无法监听 `0.0.0.0:3002`（`EPERM`）以及 New Agents Browser E2E Chromium MachPort 权限错误；后续提权重跑请求未在自动审批窗口内完成。

## 边界与后续

- 本轮不实现字符级、词级或段落级 diff。
- 本轮不新增 Agent Runtime / typed SSE / store patch 协议。
- 本轮不替代历史版本弹窗中的恢复 / 丢弃行能力。
- 完整增量 patch、`changed_sections`、块级 memoized rendering、最终内容一致性校验和局部渲染性能优化仍保留在 `docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md` 后续能力包中。
