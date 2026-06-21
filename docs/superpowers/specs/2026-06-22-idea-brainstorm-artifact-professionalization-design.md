# IDEA_BRAINSTORM 产出物专业化规格

## Current State Gap Analysis

### 事实源快照

- 已读取：`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-target.md`、`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-design.md`
- 已读取：`tools/new-agents/workflow_manifest.json` 中 `IDEA_BRAINSTORM` 的 `DEFINE`、`DIVERGE`、`CONVERGE`、`CONCEPT` 定义。
- 已读取：`tools/new-agents/frontend/src/core/prompts/idea_brainstorm/define.ts`、`diverge.ts`、`converge.ts`、`concept.ts`。
- 已读取：`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/tests/test_agent_contracts.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`。
- 已确认：`DEFINE` 已要求 Mermaid `mindmap`；`CONVERGE` 已要求 Mermaid `quadrantChart`；`CONCEPT` 已要求 `ai4se-visual mvp-map`。
- 当前工作区仍有两个无关 zip 改动：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`，本轮不触碰。

### 当前事实

| Stage | 当前产出能力 | 当前主要缺口 |
| --- | --- | --- |
| `DEFINE` | 有问题假设、目标用户、问题域 mindmap、问题-用户-场景匹配、约束和反向验证 | 缺少证据与验证状态、目标用户分层、问题真实性证据、不可做边界和阶段门禁 |
| `DIVERGE` | 有发散全景图和创意卡片库，要求 HMW 和创意技术 | 缺少发散方法说明、创意来源、对应问题、关键假设、反例/风险、搁置/排除理由和阶段门禁 |
| `CONVERGE` | 有 quadrantChart、评分口径、ICE 表、淘汰理由、推荐方案、下一步验证和合并逻辑 | 缺少评分证据来源、资源约束、敏感性分析、推荐方案确认状态、验证实验结构和阶段门禁 |
| `CONCEPT` | 有定位声明、Lean Canvas、MVP 功能分布、增长漏斗、Pre-mortem、下一步行动和 mvp-map | 缺少核心假设、验证路线、决策记录、不可做范围、行动 owner/状态和阶段门禁 |

## 本轮 Milestone

作为产品经理、创新顾问或创业者，当我使用 Alex 的创意头脑风暴 workflow 时，我可以得到一条从问题验证、创意发散、证据化收敛到产品概念简报的完整链路，而不是一组凭空生成的想法。

## Artifact 目标规格

### IDEA_BRAINSTORM / DEFINE

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 问题域验证基线 |
| 目标角色 | 产品经理、创新顾问、创业者 |
| 专业用途 | 明确问题是否真实、对谁重要、在什么场景发生、失败风险是什么 |
| 目标章节 | 问题假设陈述；目标用户画像；问题域全景；证据与验证状态；问题-用户-场景匹配；约束与边界；反向验证；阶段门禁 |
| 推荐格式 | 文本、表格、Mermaid mindmap、checklist |
| 必填字段 | 目标用户、场景、问题、现有方案、不足、证据等级、验证状态、验证动作、失败原因、不可做边界 |
| 可视化要求 | 保留第一阶段 Mermaid `mindmap`，节点必须对应问题域和子问题 |
| 协作状态字段 | 证据等级、验证状态、AI 假设/待验证 |
| 阶段门禁 | 问题、用户、场景、至少一个证据或验证动作明确后进入发散 |

### IDEA_BRAINSTORM / DIVERGE

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 创意发散卡片库 |
| 目标角色 | 产品经理、创新顾问、团队成员 |
| 专业用途 | 基于已定义问题域生成多样、可追溯、可后续评估的创意候选 |
| 目标章节 | 发散方法说明；发散全景图；创意卡片库；创意来源与假设；搁置/排除记录；阶段门禁 |
| 推荐格式 | Mermaid mindmap、表格、checklist |
| 必填字段 | 编号、HMW 问句、创意技术、具体维度、对应问题、创意来源、方案概述、差异化、关键假设、风险、状态、状态理由 |
| 协作状态字段 | Active / Parked / Killed、状态理由、验证状态 |
| 阶段门禁 | 至少 3 个 Active 或 Parked 创意，且每个能追溯到问题域 |

### IDEA_BRAINSTORM / CONVERGE

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 创意收敛决策记录 |
| 目标角色 | 产品经理、业务负责人、团队决策者 |
| 专业用途 | 通过证据化评分和资源约束选出推荐方案 |
| 目标章节 | 决策矩阵；评分口径；资源约束；ICE 评估；敏感性分析；淘汰与合并记录；推荐方案；验证实验；整合演进路径；阶段门禁 |
| 推荐格式 | Mermaid quadrantChart、表格、可选 Mermaid flowchart、checklist |
| 必填字段 | 创意编号、影响力、信心、实现难度、评分理由、证据来源、资源约束、排名、结论、淘汰/合并理由、推荐方案、验证实验 |
| 可视化要求 | 保留 Mermaid `quadrantChart`；合并时保留 flowchart |
| 协作状态字段 | 用户确认状态、验证状态、淘汰/合并状态 |
| 阶段门禁 | 推荐方案、淘汰理由、最小验证实验和用户确认状态明确 |

### IDEA_BRAINSTORM / CONCEPT

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 产品概念决策简报 |
| 目标角色 | 产品经理、业务负责人、团队沟通对象 |
| 专业用途 | 汇总问题、方案、MVP、增长和风险，形成可沟通、可验证的概念简报 |
| 目标章节 | 定位声明；核心假设；Lean Canvas；MVP 功能分布；核心增长漏斗；Pre-mortem 风险分析；验证路线；不可做范围；决策记录；下一步行动；阶段门禁 |
| 推荐格式 | 文本、表格、Mermaid pie/flowchart、`mvp-map`、checklist |
| 必填字段 | 目标用户、痛点、品类、价值主张、差异化、核心假设、MVP 模块、验证指标、风险、验证动作、owner、状态 |
| 可视化要求 | 保留 `mvp-map`；MVP 功能分布和增长漏斗需要对应前文 |
| 协作状态字段 | 假设状态、验证状态、owner、决策状态 |
| 阶段门禁 | 概念能在 3 秒内说明品类，MVP 能验证定位声明，下一步行动有 owner 和状态 |

## 验收条件

1. Given `IDEA_BRAINSTORM/DEFINE` artifact
   When 后端 contract 校验
   Then 缺少证据与验证状态、证据等级、验证动作或阶段门禁应失败。

2. Given `IDEA_BRAINSTORM/DIVERGE` artifact
   When 后端 contract 校验
   Then 缺少发散方法、创意来源与假设、状态理由或阶段门禁应失败。

3. Given `IDEA_BRAINSTORM/CONVERGE` artifact
   When 后端 contract 校验
   Then 缺少资源约束、敏感性分析、验证实验、证据来源或阶段门禁应失败。

4. Given `IDEA_BRAINSTORM/CONCEPT` artifact
   When 后端 contract 校验
   Then 缺少核心假设、验证路线、不可做范围、决策记录、owner/状态或阶段门禁应失败。

## 明确不纳入本轮

- 不开发新的创意看板、决策矩阵或 MVP 地图组件。
- 不改 shared Agent Runtime、typed SSE、workflow state、SSE/API path 或 artifact 渲染管线。
- 不新增真实模型 LLM judge；只更新 contract、template、manifest 和 fixture 证据。
