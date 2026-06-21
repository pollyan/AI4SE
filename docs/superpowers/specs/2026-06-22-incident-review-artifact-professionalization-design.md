# INCIDENT_REVIEW 产出物专业化规格

## Current State Gap Analysis

### 事实源快照

- 已读取：`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-target.md`、`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-design.md`
- 已读取：`tools/new-agents/workflow_manifest.json` 中 `INCIDENT_REVIEW` 的 `TIMELINE`、`ROOT_CAUSE`、`IMPROVEMENT` 定义。
- 已读取：`tools/new-agents/frontend/src/core/prompts/incident_review/timeline.ts`、`root_cause.ts`、`improvement.ts`。
- 已读取：`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/tests/test_agent_contracts.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`。
- 已确认：`TIMELINE` 已要求 Mermaid `timeline`；`ROOT_CAUSE` 已要求 Mermaid `mindmap` 和 `ai4se-visual cause-map`；`IMPROVEMENT` 已要求 Mermaid `pie` 和 `ai4se-visual action-board`。
- 当前工作区仍有两个无关 zip 改动：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`，本轮不触碰。

### 当前事实

| Stage | 当前产出能力 | 当前主要缺口 |
| --- | --- | --- |
| `TIMELINE` | 有事件概要、Mermaid 时间线、事实摘要、参与人员、待补充信息；提示词强调只记录事实，不做根因推断 | 缺少事实来源、证据可信度、影响量化可信度、事实/推测隔离、阻断/非阻断待补充信息和阶段门禁章节 |
| `ROOT_CAUSE` | 有 5-Why、`cause-map`、Mermaid mindmap、根因结论；提示词强调系统性问题而非个人归责 | 缺少证据强度、根因置信度、可行动性判定、排除项、未验证原因和阶段门禁章节 |
| `IMPROVEMENT` | 有 SMART 行动清单、Mermaid pie、`action-board`、防复发检查清单、经验教训和签署确认 | 缺少根因覆盖检查、复查计划、风险接受/遗留风险、失败回滚、组织学习机制和阶段门禁 |

### 本轮选择理由

`INCIDENT_REVIEW` 是推荐顺序第 4 个 workflow。它的当前模板已有专业方法框架，但“证据链”和“闭环追踪”仍不够强。对目标用户来说，故障复盘报告的专业度不只取决于是否有 5-Why 和行动清单，还取决于事实是否可追溯、根因是否可行动、改进是否覆盖根因、验收是否可验证、复查是否有责任人和时间点。

## 本轮 Milestone

作为 SRE、测试负责人、研发负责人或复盘主持人，当我使用 Lisa 的故障复盘 workflow 时，我可以得到一份事实可追溯、根因可审查、改进可追踪、复查可闭环的专业复盘报告。

## Artifact 目标规格

### INCIDENT_REVIEW / TIMELINE

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 故障事实还原记录 |
| 目标角色 | SRE、测试负责人、研发负责人、复盘主持人 |
| 专业用途 | 在不做根因推断的前提下还原故障事实、影响、响应和恢复过程 |
| 目标章节 | 事件概要；影响量化；事实来源；事件时间线；事实/推测隔离；事实摘要；参与人员；待补充信息；阶段门禁 |
| 推荐格式 | 表格、Mermaid timeline、事实/推测对照表、checklist |
| 必填字段 | 故障名称、严重等级、发现时间、恢复时间、持续时长、影响范围、影响量化、可信度、事实来源、参与角色、主要行动、阻断性 |
| 可视化要求 | 第一阶段必须保留 Mermaid `timeline`，表达发现、响应、处理、恢复确认全过程；时间点避免半角冒号破坏 Mermaid |
| 协作状态字段 | 可信度、来源、状态、阻断性 |
| 阶段门禁 | 故障表现、时间、影响范围、关键处理过程齐全；未确认信息按阻断/非阻断区分 |
| Contract 护栏 | 校验影响量化、事实来源、事实/推测隔离、阻断性、阶段门禁和 `timeline` |

### INCIDENT_REVIEW / ROOT_CAUSE

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 根因分析记录 |
| 目标角色 | SRE、研发负责人、质量改进负责人、复盘主持人 |
| 专业用途 | 基于事实完成可行动的系统性根因分析，并留下证据强度和置信度 |
| 目标章节 | 事件还原保留；5-Why 分析链；根因证据表；原因鱼骨图；根因结论；排除项；未验证原因；阶段门禁 |
| 推荐格式 | 表格、`ai4se-visual cause-map`、Mermaid mindmap、checklist |
| 必填字段 | 层级、问题、回答、原因类型、证据、证据强度、置信度、直接原因、根本原因、促成因素、可行动性、排除依据 |
| 可视化要求 | 保留 `cause-map` 和 Mermaid `mindmap` |
| 协作状态字段 | 证据强度、置信度、验证状态、可行动性 |
| 阶段门禁 | 至少 3 层 5-Why；根本原因可行动；鱼骨图至少 2 类原因；未验证原因明确标注 |
| Contract 护栏 | 校验证据强度、置信度、可行动性、排除项、未验证原因、阶段门禁、`mindmap` 和 `cause-map` |

### INCIDENT_REVIEW / IMPROVEMENT

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 故障复盘改进闭环报告 |
| 目标角色 | 质量改进负责人、研发负责人、SRE、管理者 |
| 专业用途 | 将根因转化为可追踪、可验收、防复发、可复查的改进行动 |
| 目标章节 | 报告信息；事件还原；根因分析；改进优先级；改进行动清单；根因覆盖检查；防复发检查清单；复查计划；遗留风险与风险接受；经验教训；组织学习；签署确认；阶段门禁 |
| 推荐格式 | 表格、Mermaid pie、`ai4se-visual action-board`、checklist |
| 必填字段 | 行动 ID、改进措施、类型、对应根因、负责人、期限、验证方式、验收标准、优先级、状态、追踪机制、复查日期、覆盖状态、风险接受人 |
| 可视化要求 | 保留 `action-board` 和 Mermaid `pie` |
| 协作状态字段 | 当前状态、覆盖状态、风险接受状态、签署状态 |
| 阶段门禁 | 每个根因至少有一项行动或明确风险接受；紧急行动有负责人、期限、验证方式和复查日期 |
| Contract 护栏 | 校验根因覆盖检查、复查计划、遗留风险与风险接受、组织学习、阶段门禁、`pie` 和 `action-board` |

## 验收条件

1. Given `INCIDENT_REVIEW/TIMELINE` artifact
   When 后端 contract 校验
   Then 缺少影响量化、事实来源、事实/推测隔离、阻断性或阶段门禁应失败。
   Evidence: `tools/new-agents/backend/tests/test_agent_contracts.py`

2. Given `INCIDENT_REVIEW/ROOT_CAUSE` artifact
   When 后端 contract 校验
   Then 缺少证据强度、置信度、可行动性、排除项、未验证原因或阶段门禁应失败。
   Evidence: `tools/new-agents/backend/tests/test_agent_contracts.py`

3. Given `INCIDENT_REVIEW/IMPROVEMENT` artifact
   When 后端 contract 校验
   Then 缺少根因覆盖检查、复查计划、遗留风险与风险接受、组织学习或阶段门禁应失败。
   Evidence: `tools/new-agents/backend/tests/test_agent_contracts.py`

4. Given 前端 incident_review prompt/template
   When contract sync tests 扫描
   Then template 包含 required headings、Mermaid 和 `ai4se-visual` 示例。
   Evidence: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

## 明确不纳入本轮

- 不开发新的复盘看板或时间线前端控件。
- 不改 shared Agent Runtime、typed SSE、workflow state、SSE/API path 或 artifact 渲染管线。
- 不新增真实模型 LLM judge；只更新 contract、template、manifest 和 fixture 证据。
