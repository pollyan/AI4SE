# New Agents Artifact Document Info Density Design

## CGA 摘要

活跃候选 `docs/todos/refactor/2026-06-25-new-agents-artifact-document-info-density.md` 要解决产出物首屏被低价值元信息表格占据的问题。当前事实：

- `tools/new-agents/workflow_manifest.json` 中 `TEST_DESIGN/CLARIFY`、`TEST_DESIGN/DELIVERY`、`VALUE_DISCOVERY/BLUEPRINT` 仍要求首段 `文档信息`。
- `REQ_REVIEW/REVIEW` 仍把 `评审信息` 作为首段大表格，其中混合 artifact 名称、评审时间和需求概述，会压过需求质量总览。
- `tools/new-agents/frontend/src/core/prompts/test_design/clarify.ts`、`test_design/delivery.ts`、`value_discovery/blueprint.ts` 的模板把 `文档信息` 放在标题后第一段。
- `tools/new-agents/backend/artifact_data_renderers.py` 的 `render_test_design_clarify_markdown()`、`render_test_design_delivery_markdown()`、`render_value_discovery_blueprint_markdown()` 也先渲染文档信息表。
- `STRATEGY` 阶段当前不包含 `文档信息` 首段，不能把该问题和“测试策略阶段格式 Bug”混为一个修复。

## 用户故事

作为 New Agents 用户，我打开新生成的产出物时，首屏应优先看到核心业务内容，例如需求事实、执行摘要或产品概述，而不是大块文档信息表；必要元信息仍应在文档末尾可追溯，用于导出、历史回看和审计。

## 设计

采用共享“文末附录”规则：

- 产出物标题后立即进入核心业务章节。
- 文档信息保留为最后的 `## 附录：文档信息`，继续使用现有结构化数据字段和表格。
- 不新增前端折叠组件、workflow 专属 renderer 或 API。
- 更新 workflow manifest、后端 required heading contract、前端模板和后端 deterministic renderer，使模型输出、contract 校验和 artifact_data 渲染口径一致。

## 范围

本轮只覆盖当前在线模板和 renderer 中已确认首段大表格的三个阶段：

- `TEST_DESIGN / CLARIFY`
- `TEST_DESIGN / DELIVERY`
- `VALUE_DISCOVERY / BLUEPRINT`
- `REQ_REVIEW / REVIEW`

`REQ_REVIEW / REPORT` 的 `评审信息` 不是首段，`INCIDENT_REVIEW / TIMELINE` 的 `事件概要` 属于业务摘要，其他非首段或非文档信息结构本轮不改，避免扩大到另一轮信息架构重设计。

## 非目标

- 不删除 `document_info` / `delivery_metrics` / `blueprint_document_info` 等结构化字段。
- 不改变 typed SSE、artifact_data schema、run persistence、artifact version 或导出链路。
- 不新增 Lisa/Alex/DeepSeek 专属 renderer。
- 不重排所有产出物的章节体系。

## 验收

- CLARIFY 渲染后 `## 1. 需求事实清单` 出现在 `## 附录：文档信息` 之前。
- DELIVERY 渲染后 `## 1. 执行摘要` 出现在 `## 附录：文档信息` 之前，原 `## 10. 变更记录` 调整为 `## 9. 变更记录`。
- BLUEPRINT 渲染后 `## 1. 产品概述` 出现在 `## 附录：文档信息` 之前。
- REVIEW 渲染后 `## 评审范围与不评审范围` 和 `## 需求质量总览` 出现在 `## 附录：评审信息` 之前。
- 四个阶段的 `validate_agent_turn()` 仍通过。
- 前端模板与 manifest/后端 contract 的 required headings 一致。

## 自主裁决记录

未停下来请求用户确认，原因是用户已明确启动目标模式并授权按 playbook 自主消化 active todo；本设计不新增架构分支、不改变外部权限、不删除必要审计信息。选择“文末附录”而不是“首段轻量 metadata”，是因为前者不需要新增 UI 能力，也能让首屏核心内容前置。
