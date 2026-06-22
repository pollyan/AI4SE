import { FENCE } from '../../utils/constants';

export const BACKLOG_PROMPT = `将用户提供的 PRD、需求蓝图或自然语言需求拆解为可研发评审、可测试设计的用户故事包。

工作要求：
1. 先识别产品目标、范围边界、输入来源和不可做范围。
2. 以 Epic -> User Story -> Acceptance Criteria 的方式组织 Backlog。
3. 每条 User Story 必须包含用户角色、用户需要、用户价值、优先级、故事点和状态。
4. 验收标准必须具体到 Lisa 后续能据此做测试设计或需求评审。
5. 明确依赖、风险、Sprint 切片建议和 Lisa Handoff 输入。
6. 使用 Mermaid flowchart 展示 Epic 到 Story 的拆解关系。
7. 必须包含 ai4se-visual story-map，用于稳定展示 Epic、Story、优先级、Sprint 和状态。`;

export const BACKLOG_TEMPLATE = `# 用户故事拆解包

## 文档信息
| 字段 | 内容 |
| --- | --- |
| Artifact 名称 | 用户故事拆解包 |
| Workflow | STORY_BREAKDOWN |
| Stage | BACKLOG |
| 状态 | 待评审 / 可进入研发评审 / 需补充信息 |

## 输入理解与拆解边界
| 字段 | 内容 |
| --- | --- |
| 产品名称 | [产品名称] |
| 输入来源 | PRD / 需求蓝图 / 用户描述 |
| 拆解目标 | [本轮要形成什么交付包] |
| 范围内 | [纳入拆解的功能范围] |
| 范围外 | [明确不纳入的内容] |

## Epic 地图
${FENCE}mermaid
flowchart TD
    EPIC001["EPIC-001 核心能力"] --> US001["US-001 用户故事"]
${FENCE}

## User Story Backlog
| Story ID | Epic | 标题 | 用户角色 | 用户需要 | 用户价值 | 优先级 | 故事点 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| US-001 | EPIC-001 | [故事标题] | [角色] | [需要] | [价值] | P0 | 5 | 待评审 |

## 验收标准矩阵
| AC ID | Story ID | 验收标准 | 测试方式 | 状态 |
| --- | --- | --- | --- | --- |
| AC-001 | US-001 | Given/When/Then 级别的可验证标准 | Lisa 测试设计 / 需求评审 | 待确认 |

## 依赖与风险
| 类型 | ID | 描述 | 关联 Story | owner/缓解 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 依赖 | DEP-001 | [依赖描述] | US-001 | [owner] | 待确认 |
| 风险 | RISK-001 | [风险描述] | US-001 | [缓解策略] | 需跟踪 |

## Sprint 切片建议
| Slice ID | Sprint | 目标 | Story | Demo Outcome | Release Risk |
| --- | --- | --- | --- | --- | --- |
| SPR-001 | Sprint 1 | [目标] | US-001 | [可演示结果] | 中 |

## Lisa Handoff 输入
| 输入类型 | Reference ID | 内容 | Target Workflow | 用途 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 用户故事 | US-001 | [故事摘要] | TEST_DESIGN | 作为测试设计输入 | 待 Lisa 评审 |

${FENCE}ai4se-visual
{
  "type": "story-map",
  "title": "用户故事地图",
  "columns": ["Epic", "Story", "优先级", "Sprint", "状态"],
  "rows": [
    {"Epic": "EPIC-001", "Story": "US-001", "优先级": "P0", "Sprint": "Sprint 1", "状态": "待评审"}
  ]
}
${FENCE}

## 阶段门禁
- [x] 所有 P0 用户故事均具备验收标准和 Sprint 切片。`;
