# DeepSeek V4 VALUE_DISCOVERY/BLUEPRINT 结构化产物数据设计

## 背景

DeepSeek V4 Flash 当前按 `json_object_only` 能力使用，不能依赖供应商 strict schema。`VALUE_DISCOVERY/ELEVATOR`、`PERSONA`、`JOURNEY` 已迁移为 `artifact_data -> Pydantic schema -> deterministic renderer -> artifact contract` 链路，`BLUEPRINT` 仍要求模型直接拼完整需求蓝图 Markdown、Mermaid 流程图和 `ai4se-visual` `roadmap`，是 Alex 价值发现主路径最后一个格式脆弱阶段。

## 本轮目标

让 `VALUE_DISCOVERY/BLUEPRINT` 支持 DeepSeek V4 兼容的结构化产物数据输出：

- 模型只输出 JSON object，包含 `chat`、`artifact_data`、`stage_action`、`warnings`。
- 后端用 Pydantic schema 校验需求蓝图业务数据和跨字段引用。
- 后端确定性渲染 `# <产品名称> 需求蓝图`、功能架构 Mermaid `mindmap`、核心流程 Mermaid `flowchart`、`ai4se-visual` `roadmap`、P0/P1/P2 需求、成功指标、MVP 计划、非功能需求、验收标准、风险、Lisa Handoff 输入和阶段门禁。
- 继续复用共享 Agent Runtime、typed SSE、artifact contract、run/artifact persistence 和共享 UI，不新增 Alex、DeepSeek 或 VALUE_DISCOVERY 专属 runtime/API/store/renderer。

## Artifact Data Contract

`artifact_data` 必须包含：

- `document_info`：产品名称、版本、创建日期、产品方向、Artifact 名称、蓝图状态。
- `product_overview`：产品愿景、定位声明、用户价值、商业价值、商业模式。
- `target_users`：目标用户摘要，至少一个用户类型、核心痛点和优先级。
- `feature_modules`：功能架构模块与功能项，用于生成 Mermaid `mindmap`。
- `requirements`：P0/P1/P2 需求，包含 ID、名称、用户故事、对应痛点、范围边界、依赖、验收标准、可测试性等级、owner、状态。
- `main_flow`：核心流程节点与连线，用于生成 Mermaid `flowchart`。
- `success_metrics`：业务、用户、产品等成功指标。
- `mvp_plan`：MVP 包含功能和迭代路线。
- `non_functional_requirements`：性能、安全、兼容性、可观测性等非功能需求。
- `acceptance_criteria`：验收标准，必须引用已存在需求 ID。
- `roadmap`：版本、时间、核心功能、目标、成功指标，用于生成 `ai4se-visual` `roadmap`。
- `risks`：市场、产品、执行等风险。
- `lisa_handoff_inputs`：需求、验收标准、风险、数据/依赖等给 Lisa 的输入。
- `stage_gate`：阶段门禁检查项。

## Validation Rules

- 所有字符串非空，未知字段拒绝，数组至少包含一项。
- `requirements.requirement_id` 唯一。
- `feature_modules.features.requirement_id` 如存在，必须引用已存在需求 ID。
- `mvp_plan.included_features.requirement_id` 必须引用已存在需求 ID。
- `acceptance_criteria.requirement_id` 必须引用已存在需求 ID。
- `lisa_handoff_inputs.reference_id` 如果 `input_type` 为 `需求` 或 `验收标准`，必须分别引用已存在需求 ID 或验收 ID。
- `roadmap.rows` 至少一项，renderer 输出必须与 `roadmap` 数据一致。

## Rendering Requirements

renderer 必须稳定输出并通过 `validate_agent_turn()`：

- H1 包含 `需求蓝图`，例如 `# AI4SE 测试设计助手 需求蓝图`。
- 固定输出 manifest/contract 要求的全部标题：文档信息、产品概述、目标用户摘要、核心需求、核心流程、成功指标、MVP 范围与计划、非功能需求、验收标准、路线图、风险评估、Lisa Handoff 输入、阶段门禁。
- `### 功能架构` 输出 Mermaid `mindmap`。
- `### 主流程图` 输出 Mermaid `flowchart TD`。
- `## 9. 路线图` 输出 `ai4se-visual` fenced JSON，`type` 为 `roadmap`。
- 需求、验收标准、非功能需求和 Lisa Handoff 表格必须包含 `可测试性等级`、`owner`、`状态` 等 contract 关键词。

## Non-goals

- 不迁移 `IDEA_BRAINSTORM` 或 `INCIDENT_REVIEW`。
- 不改前端 typed SSE 协议。
- 不新增 handoff runtime；Lisa Handoff 输入仍作为 artifact 内容和现有 handoff 配置的消费素材。
- 不运行真实 DeepSeek smoke；该验证需要凭证、网络和额度。
