# VALUE_DISCOVERY 产出物专业化规格

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-target.md`、`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-design.md`
- 已读取：`tools/new-agents/frontend/src/core/prompts/value_discovery/elevator.ts`、`persona.ts`、`journey.ts`、`blueprint.ts`
- 已读取：`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/tests/test_agent_contracts.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- 已扫描：`tools/new-agents/backend/tests/test_workflow_handoffs.py`、`tools/new-agents/backend/tests/test_agent_endpoint.py`、`tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
- 当前工作区只剩两个无关 zip 改动：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`，本轮不触碰。

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| `VALUE_DISCOVERY` 产品价值发现专业化 | `ELEVATOR` 缺 Mermaid、证据等级和未验证假设；`PERSONA` 缺决策链/反画像；`JOURNEY` 缺机会评分和验证实验；`BLUEPRINT` 缺可测试性等级和 handoff 门禁 | 用户输入产品想法 -> Alex 澄清价值定位 -> 形成画像 -> 找到旅程机会 -> 生成可评审需求蓝图 -> handoff 给 Lisa | 单独改蓝图会缺上游证据；单独改定位会无法落到需求蓝图；四阶段必须形成产品经理视角闭环 | contract tests、sync tests、frontend runtime fixture、handoff fixture |
| `INCIDENT_REVIEW` 复盘闭环专业化 | 时间线、根因和改进行动需加强证据/门禁 | 用户输入故障事实 -> 形成复盘报告 | 目标角色和场景不同 | 下一轮 |
| 新可视化控件 | journey/roadmap 表格渲染体验有限 | 专属地图和看板 | 用户明确当前先做内容结构，不开发新控件 | 暂缓 |

### 候选 gap

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `VALUE_DISCOVERY` 全链路 artifact 专业化 | 推荐顺序第 3 + handoff 质量目标 | 价值定位、画像、旅程、蓝图形成可验证产品发现链路 | 有基础模板、journey、roadmap、score-matrix | 证据/假设/验证/可测试性字段不足 | 高 | 中 | contract/sync/frontend/handoff tests | 本轮 |
| `INCIDENT_REVIEW` 专业化 | 推荐顺序第 4 | 复盘事实、根因和改进闭环 | 有 timeline/mindmap/action-board | 证据强度、置信度、验收和追踪需加强 | 中高 | 中 | contract/sync tests | 下一轮 |
| `IDEA_BRAINSTORM` 专业化 | 推荐顺序第 5 | 创意探索证据化 | 有 define/diverge/converge/concept | 假设、证据、验证计划不足 | 中 | 中 | contract/sync tests | 后续 |

## 本轮 Milestone

作为产品经理或业务负责人，当我使用 Alex 的价值发现工作流时，我可以得到从价值定位、用户画像、用户旅程到可评审需求蓝图的连续专业产出，从而让蓝图既能支持产品决策，也能交给 Lisa 做需求评审或测试设计。

## Artifact 目标规格

### VALUE_DISCOVERY / ELEVATOR

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 价值定位诊断报告 |
| 目标角色 | 产品经理、创业者、业务负责人 |
| 专业用途 | 用最小信息澄清产品是什么、为谁解决什么、为什么值得做 |
| 目标章节 | 定位摘要；价值结构图；目标用户与场景；痛点证据；差异化价值；商业可行性；未验证假设；60 秒电梯演讲；阶段门禁 |
| 推荐格式 | 短文本、Mermaid flowchart、证据表、score-matrix、假设表、门禁 checklist |
| 必填字段 | 用户、场景、痛点、现有方案、不足、独特价值、证据等级、付费意愿、验证动作、状态 |
| 可视化要求 | 第一阶段必须包含 Mermaid flowchart，表达目标用户 -> 痛点 -> 现有方案不足 -> 产品价值 -> 商业验证 |
| 协作状态字段 | 证据等级、状态、责任方/验证人 |
| 阶段门禁 | 目标用户、核心痛点、差异化和至少一个验证动作明确后进入 persona |
| Contract 护栏 | 校验章节、关键表头、flowchart、score-matrix |

### VALUE_DISCOVERY / PERSONA

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 用户画像与决策链分析 |
| 目标角色 | 产品经理、用户研究、业务负责人 |
| 专业用途 | 明确核心用户、行为、痛点、决策角色和验证缺口 |
| 目标章节 | 画像摘要；主要用户画像；行为与场景；决策链；痛点证据；反画像；用户优先级；阶段门禁 |
| 推荐格式 | 表格、bullet、检查清单 |
| 必填字段 | 用户类型、角色定义、使用者/决策者/付费者、行为场景、痛点、频率、影响程度、证据等级、优先级理由、验证状态 |
| 协作状态字段 | 证据等级、验证状态、AI 假设/待验证 |
| 阶段门禁 | 至少一个核心用户画像有场景、痛点、影响和证据等级 |
| Contract 护栏 | 校验决策链、痛点证据、反画像、阶段门禁和证据字段 |

### VALUE_DISCOVERY / JOURNEY

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 用户旅程与机会地图 |
| 目标角色 | 产品经理、设计师、业务负责人 |
| 专业用途 | 找到关键旅程、情绪低谷、机会优先级和验证实验 |
| 目标章节 | 用户旅程地图；结构化旅程地图；关键阶段分析；痛点优先级；机会评分；产品切入策略；验证实验；阶段门禁 |
| 推荐格式 | Mermaid journey、journey-map、表格、checklist |
| 必填字段 | 阶段、触点、用户任务、用户目标、情绪评分、关键痛点、现有方案不足、机会假设、成功指标、验证实验、状态 |
| 可视化要求 | 保留 journey 和 journey-map |
| 协作状态字段 | 机会假设状态、验证状态 |
| 阶段门禁 | 主要机会点必须关联高优先级痛点、成功指标和验证实验 |
| Contract 护栏 | 校验 journey、journey-map、机会评分、验证实验和阶段门禁 |

### VALUE_DISCOVERY / BLUEPRINT

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 可评审需求蓝图 |
| 目标角色 | 产品经理、测试负责人、研发负责人 |
| 专业用途 | 将价值发现成果转为可评审、可测试、可排期、可 handoff 给 Lisa 的需求蓝图 |
| 目标章节 | 文档信息；产品概述；目标用户；核心需求；功能架构；核心流程；非功能需求；验收标准；成功指标；MVP 范围；路线图；风险评估；阶段门禁 |
| 推荐格式 | 表格、Mermaid mindmap/flowchart、roadmap、checklist |
| 必填字段 | 需求 ID、优先级、用户故事、对应痛点、范围边界、依赖、验收标准、可测试性等级、owner、状态 |
| 可视化要求 | 保留功能架构 mindmap、主流程 flowchart 和 roadmap |
| 协作状态字段 | 已确认/待确认/AI 假设、owner、可测试性等级 |
| 阶段门禁 | P0 需求有验收标准、成功指标和可测试性等级；handoff 给 Lisa 的输入完整 |
| Contract 护栏 | 校验非功能需求、验收标准、可测试性等级、阶段门禁、roadmap |

## 验收条件

1. Given `VALUE_DISCOVERY/ELEVATOR` artifact
   When 后端 contract 校验
   Then 缺少 flowchart、价值结构图、痛点证据、未验证假设或阶段门禁应失败
   Evidence: `tools/new-agents/backend/tests/test_agent_contracts.py`

2. Given `VALUE_DISCOVERY/BLUEPRINT` artifact
   When 后端 contract 校验
   Then 缺少非功能需求、验收标准、可测试性等级或阶段门禁应失败
   Evidence: `tools/new-agents/backend/tests/test_agent_contracts.py`

3. Given 前端 value_discovery prompt/template
   When contract sync tests 扫描
   Then template 包含 required headings、Mermaid 和 `ai4se-visual` 示例
   Evidence: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

## 明确不纳入本轮

- 不开发新的 journey-map 或 roadmap 专属前端控件。
- 不改 shared Agent Runtime、typed SSE、workflow manifest、handoff runtime 或 artifact 渲染管线。
- 不新增真实模型 LLM judge；只更新 contract、template 和 fixture 证据。
