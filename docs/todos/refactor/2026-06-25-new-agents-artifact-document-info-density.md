# New Agents 产出物文档信息密度优化 Todo

状态：活跃候选  
创建日期：2026-06-25  
相关模块：`tools/new-agents/`

## 背景

当前多个 New Agents 产出物会在开头展示“文档信息”段落，并经常使用较大的 Markdown 表格承载生成时间、工作流、阶段、版本、适用范围等元信息。

用户反馈：产出物最重要的位置应该优先展示有业务价值的内容，但首段大表格里的文档信息价值较低、占用空间过大，会挤压核心结论、问题、策略、用例、风险和下一步建议的首屏可见性。

## 当前问题

- “文档信息”作为首段大表格出现，视觉重量过高。
- 首屏空间被低价值元信息占据，用户需要滚动才能看到真正重要的专业内容。
- 多个 workflow / stage 的产出物可能重复存在同类问题，不能只修某一个 Lisa 或 Alex 阶段。
- 如果完全删除元信息，可能影响导出、归档、审计或跨 run 回看时的上下文判断。

## 目标能力包

降低产出物开头“文档信息”的视觉占用和优先级，让核心业务内容成为首屏主要信息。

如果仍需要保留文档信息，应把它移动到更次要的位置或改成更轻量的元信息展示，例如：

- 放到文档末尾的附录 / 元数据区。
- 折叠到低视觉权重的摘要行或 details 区。
- 缩减为一行轻量 metadata，而不是首段大表格。
- 在导出或审计视图中保留完整信息，但预览正文默认弱化。

## 架构约束

- 必须继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、artifact renderer、持久化 run/artifact 模型和共享 UI 基础设施。
- 不新增 Lisa、Alex、DeepSeek 或单个 workflow 专属的渲染分支。
- 差异优先通过 artifact template、renderer 配置、manifest contract 或共享 Markdown 结构规则表达。
- 不用隐藏 fallback 或假数据掩盖文档信息缺失；需要保留的元信息必须仍可追溯。

## 验收标准

- 新生成产出物首屏优先展示核心业务内容，而不是大块“文档信息”表格。
- “文档信息”如保留，应处于次要位置、低视觉权重或可折叠区域。
- 导出、历史回看、run snapshot 和 artifact version 仍能获得必要元信息。
- 所有在线 workflow 的产出物模板或 renderer 需要统一审计，避免只修单个阶段。
- 变更不得破坏现有 artifact contract、Mermaid / `ai4se-visual` 渲染和 typed SSE 流式展示。

## 建议排查方向

1. 搜索所有 artifact template / renderer 中的 `文档信息`、`基本信息`、`生成信息`、`版本信息` 等首段结构。
2. 区分必须保留的审计元信息和可删除的展示性信息。
3. 设计一套共享的轻量 metadata 展示规则。
4. 更新相关 workflow/stage 的 artifact template 或 deterministic renderer。
5. 补充 contract / renderer / frontend snapshot 测试，确保核心内容前置且元信息不丢失。

## 非目标

- 不重新设计所有产出物的信息架构。
- 不删除必要的审计、导出、版本或追溯信息。
- 不把元信息改成单个 workflow 的特殊样式。
- 不改变用户与 Agent 的主交互流程。

## 待决策问题

- 文档信息默认应移到文末，还是改成首段一行低权重 metadata。
- 导出文件是否需要保留完整文档信息表格，而在线预览使用轻量展示。
- 哪些字段属于必要元信息，哪些字段可以从正文中移除。
