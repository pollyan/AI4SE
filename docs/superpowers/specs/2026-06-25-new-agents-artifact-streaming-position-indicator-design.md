# New Agents Artifact Streaming Position Indicator Design

## CGA 摘要

当前 P0 “右侧 Artifact 真实流式渲染”已经完成，后端会在最终 `agent_turn` 前发送 renderer-backed `agent_delta.artifact_update.replace`。`docs/todos/refactor/2026-06-24-new-agents-artifact-streaming-position-indicator.md` 的前置条件已经成立。

候选排序：

- 选中：Artifact streaming position indicator。它是 P0 修复后的直接体验补强，范围可限定为共享 ArtifactPane UI-only。
- 暂缓：模型配置测试假失败。它是可信启动问题，但不依赖刚完成的 streaming 链路。
- 暂缓：阶段推进成熟度门禁。它更偏工作流正确性，写入面更大。
- 暂缓：批注创建 500。它是服务端协作状态 bug，需单独排查 API/DB。

## 用户故事

作为 New Agents 用户，当右侧 Artifact 已经开始显示正式内容且模型仍在生成后续内容时，我能在正文流末尾看到一个轻量“正在生成后续章节”的位置提示；生成完成后该提示消失，最终 Artifact 内容不包含提示文案。

## 设计

在 `tools/new-agents/frontend/src/components/ArtifactPane.tsx` 中增加一个 UI-only indicator。它不是 Markdown 字符串的一部分，不写入 `artifactContent`，不进入下载、导出、版本保存、run snapshot、质量诊断或复制输入。

显示条件：

- `isGenerating === true`
- `artifactContent.trim()` 非空，说明右侧已有正式流式内容
- 当前不处于手动编辑模式

展示位置：

- 预览模式：渲染在 `ReactMarkdown` 后面，作为正文流末尾的独立组件。
- 源码模式：渲染在 `<pre>` 后面，仍是独立组件，不拼接进源码文本。

空内容生成时保留现有顶部“正在构建右侧产出物”状态，不显示正文位置 indicator，避免看起来像已有正式内容。

## 验收

- `ArtifactPane` 在生成中且已有 artifact 内容时显示正文末尾位置提示。
- 生成结束后提示消失。
- 空 artifact 生成中不显示正文位置提示，只保留顶部生成状态。
- Markdown 下载内容不包含 indicator 文案。
- 实现不改变 SSE schema、store shape、run persistence、artifact version 或后端 contract。
