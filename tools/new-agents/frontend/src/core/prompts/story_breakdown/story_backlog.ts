export const STORY_BACKLOG_PROMPT = `Story Backlog 阶段用于把 Epic Map 转成可评审、可测试、可排期的 User Story Backlog。请为每个用户故事补齐 Story ID、Epic ID、标题、标准用户故事表达、优先级、Sprint 切片建议、Story Points、可测试性和状态，并形成可被 Lisa 继续使用的验收标准输入与 Lisa Handoff 上下文。`;

const FENCE = '```';

export const STORY_BACKLOG_TEMPLATE = `结构化业务数据应覆盖：
- user_stories：每条故事必须引用已有 Epic，使用“作为...我想...以便...”表达，并标注优先级、Sprint、点数、可测试性和状态。
- acceptance_criteria：每条 AC 必须引用已有 story_id，写清可验证行为、边界条件和验证方式。
- dependencies：记录故事间依赖、外部系统依赖、质量风险和缓解策略。
- lisa_handoff_inputs：至少包含用户故事和验收标准两类输入，便于 Lisa 测试设计和需求评审。
- stage_gate：确认 P0 用户故事是否都有验收标准、优先级、可测试性和明确状态。

后端渲染器会继续基于 epics 生成 ai4se-visual flow-map，例如：
${FENCE}ai4se-visual
{"type": "flow-map","title":"Epic 流程图","nodes":[{"id":"Goal","label":"Goal","title":"产品目标"},{"id":"EPIC-001","label":"EPIC-001","title":"核心 Epic"}],"edges":[{"source":"Goal","target":"EPIC-001","label":"拆解为"}]}
${FENCE}`;
