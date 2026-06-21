# REQ_REVIEW 产出物专业化规格

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-target.md`、`docs/todos/archive/2026-06-22-new-agents-artifact-professionalization-design.md`
- 已读取：`tools/new-agents/frontend/src/core/prompts/req_review/review.ts`、`tools/new-agents/frontend/src/core/prompts/req_review/report.ts`
- 已读取：`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/tests/test_agent_contracts.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- 已扫描：`tools/new-agents/frontend/src/core/__tests__/llm.test.ts`、`tools/new-agents/backend/tests/test_agent_endpoint.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`
- 当前工作区只剩两个无关 zip 改动：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`，本轮不触碰。
- Worktree 隔离降级：当前连续目标模式沿用主工作区，上一轮提交已推送；本轮只 stage `REQ_REVIEW` 相关文件和本轮文档，避免覆盖无关 zip 改动。

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| `REQ_REVIEW` 需求质量入口专业化 | `REVIEW` 缺 Mermaid、评审范围、问题状态和门禁；`REPORT` 缺问题关闭、复审条件、签署状态和变更记录 | 用户输入需求文档 -> Lisa 输出需求质量诊断问题清单 -> 汇总为可签署评审报告 -> 作为 `TEST_DESIGN` 上游输入 | 只改 `REVIEW` 会缺正式结论闭环；只改 `REPORT` 会缺高质量问题来源 | contract tests、sync tests、runtime/frontend fixture tests |
| `VALUE_DISCOVERY` handoff 专业化 | 产品价值文档证据等级和测试可验证性不足 | Alex 产出蓝图 -> Lisa 接手需求评审或测试设计 | 属于产品发现入口，和本轮需求评审入口可分开验收 | 下一轮目标模式 |
| `INCIDENT_REVIEW` 复盘闭环专业化 | 根因证据和改进验收需要加强 | 用户输入故障事实 -> 输出可追责复盘 | 目标角色和场景不同 | 后续目标模式 |

### 候选 gap

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `REQ_REVIEW` 全链路 artifact 专业化 | 目标状态设计 + `TEST_DESIGN` 上游质量需求 | 需求评审从问题清单到签署报告形成闭环 | 有问题清单、score-matrix、报告、pie、priority-board | 第一阶段无 Mermaid，协作状态和关闭/复审门禁不足 | 高 | 中低 | contract/sync/runtime/frontend tests | 本轮 |
| `VALUE_DISCOVERY` 专业化 | 推荐顺序第 3 | 提升产品经理视角和 handoff | 有四阶段基础模板 | 假设、证据、验证状态不足 | 中高 | 中 | contract/sync/handoff tests | 下一轮 |
| 新可视化控件 | 用户体验讨论 | 专属看板和地图 | 现有统一表格渲染 | UI 表达不够强 | 中 | 高 | 前端截图和组件测试 | 暂缓 |

### 排序结论

1. 本轮选择 `REQ_REVIEW`，因为它是 `TEST_DESIGN` 的直接上游入口，需求质量诊断越专业，后续测试设计越稳定。
2. `VALUE_DISCOVERY` 暂缓到下一轮，避免同时改 Alex 产品发现链路和 Lisa 需求评审链路。
3. 新可视化控件继续不纳入本轮，仅复用 Mermaid 和现有 `ai4se-visual` type/columns/rows。

## 本轮 Milestone

作为产品经理、测试负责人或研发负责人，当我把需求文档交给 Lisa 做需求评审时，我可以得到一份先诊断问题、再形成可签署报告的专业评审链路，从而明确哪些需求问题阻断开发/测试、谁负责修订、什么条件下可以复审或进入测试设计。

## Artifact 目标规格

### REQ_REVIEW / REVIEW

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 需求质量诊断与评审问题清单 |
| 目标角色 | 产品经理、测试负责人、研发负责人 |
| 专业用途 | 从测试可验证性和交付风险角度识别需求缺陷，形成可分派、可修订、可进入报告阶段的问题资产 |
| 目标章节 | 评审信息；评审范围与不评审范围；需求质量总览；需求质量结构图；问题统计；按维度问题清单；修订建议；阶段门禁 |
| 推荐格式 | 文档信息表、范围表、质量评分表、Mermaid flowchart、`score-matrix`、分维度问题表、修订建议表、门禁 checklist |
| 必填字段 | 问题 ID、评审维度、问题描述、优先级、阻断性、所属需求章节、影响范围、证据/依据、建议、责任方/确认人、状态 |
| 可视化要求 | 必须包含 Mermaid flowchart，展示需求输入、质量维度、问题分级、修订闭环和报告阶段承接 |
| 协作状态字段 | 状态、阻断性、责任方/确认人、证据等级 |
| 阶段门禁 | P0 问题必须有证据、修订建议和责任方；评审范围明确；报告阶段能消费问题 ID、优先级、责任方和状态 |
| Contract 护栏 | 校验新增章节、关键表头、Mermaid flowchart、score-matrix |
| Judge/E2E 建议 | 评估问题是否基于需求证据，不接受“建议完善需求”这种空泛描述 |

### REQ_REVIEW / REPORT

| 字段 | 目标规格 |
| --- | --- |
| Artifact 名称 | 可签署需求评审报告 |
| 目标角色 | 产品负责人、测试负责人、研发负责人 |
| 专业用途 | 给出可追责的评审结论、问题关闭要求、复审条件和签署状态 |
| 目标章节 | 评审结论；判定标准；评审信息；问题统计；优先级看板；问题关闭清单；复审条件；签署确认；变更记录 |
| 推荐格式 | 结论表、判定标准 bullet、Mermaid pie、`priority-board`、关闭清单表、复审 checklist、签署表、变更记录表 |
| 必填字段 | 结论、结论理由、P0/P1/P2 数量、问题 ID、优先级、责任方、下一步、关闭状态、复审条件、签署状态 |
| 可视化要求 | 保留 Mermaid pie 和 `priority-board` |
| 协作状态字段 | 关闭状态、责任方、签署状态、复审状态 |
| 阶段门禁 | 存在 P0 时结论不得为通过；无责任方的问题不得视为可关闭；复审条件必须可验证 |
| Contract 护栏 | 校验新增章节、关键表头、pie、priority-board |
| Judge/E2E 建议 | 评估报告结论是否和问题严重度一致，是否可签署和复审 |

## 验收条件

1. Given `REQ_REVIEW/REVIEW` artifact
   When 后端 contract 校验
   Then 缺少 Mermaid flowchart、评审范围、质量总览、问题状态或阶段门禁应失败
   Evidence: `tools/new-agents/backend/tests/test_agent_contracts.py`

2. Given `REQ_REVIEW/REPORT` artifact
   When 后端 contract 校验
   Then 缺少问题关闭清单、复审条件、签署确认或变更记录应失败
   Evidence: `tools/new-agents/backend/tests/test_agent_contracts.py`

3. Given 前端 req_review prompt/template
   When contract sync tests 扫描
   Then template 包含 required headings、Mermaid 和 `ai4se-visual` 示例
   Evidence: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

## 明确不纳入本轮

- 不开发新的需求质量专属看板组件。
- 不改 shared Agent Runtime、typed SSE、workflow manifest、store 或 artifact 渲染管线。
- 不新增真实模型 LLM judge；只更新 contract、template、smoke/fixture 证据。
