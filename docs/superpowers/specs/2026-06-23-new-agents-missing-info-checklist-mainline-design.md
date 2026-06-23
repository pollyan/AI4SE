# E02 阶段缺失信息清单闭环 Spec

## 背景

`tools/new-agents` 的共享 Agent Runtime 已经能在不同 workflow 的阶段产物中输出“待澄清问题”“开放问题”“missing_information”“blocking”“下一步”等字段，但当前前端只把这些内容作为普通 Markdown 呈现。用户在当前阶段需要补充什么、哪些缺口会阻断进入下一阶段、下一步该补什么，缺少统一的即时反馈。

本 milestone 只补齐前端派生诊断能力，不改共享 runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型或共享 API。

## 目标

当当前阶段产出物包含缺失信息或待澄清问题时，前端应自动抽取为“阶段缺失信息清单”，并在 Artifact 与 Chat 两侧展示：

- ArtifactPane 展示完整清单、阻断项数量、问题、责任方、状态与下一步。
- ChatPane 展示轻量提醒，让用户在对话区也能看到当前阶段还缺什么和首个补充动作。
- 空产物或没有缺失信息章节时不显示清单。

## 非目标

- 不让模型自动生成追问。
- 不新增缺失信息确认状态的持久化模型。
- 不新增 agent 专属 runtime、API path、store 或 renderer。
- 不改变现有阶段推进、SSE 事件或 artifact 保存契约。

## 输入格式

共享解析逻辑应覆盖当前主线产物中已经出现或计划出现的两类格式：

1. Markdown 表格：

   `待澄清问题 / 开放问题 / 缺失信息 / missing_information` 等标题下的表格，列可包含 `问题`、`阻断性`、`责任方`、`状态`、`下一步`。

2. Markdown 列表：

   同类标题下的列表项，支持 `阻断 / blocking` 标记，以及 `责任方：...`、`状态：...`、`下一步：...` 片段。

## 验收标准

- 表格输入能抽取问题、阻断状态、责任方、状态和下一步。
- 列表输入能抽取问题、阻断状态和下一步。
- ArtifactPane 对当前 artifact 展示“阶段缺失信息清单”和阻断统计。
- ChatPane 对当前 artifact 展示轻量缺口提醒。
- 无相关缺口时不展示 ArtifactPane 清单或 ChatPane 提醒。
- 前端聚焦测试、lint 和 diff check 通过。
