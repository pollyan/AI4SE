export const EPIC_MAPPING_PROMPT = `Epic 映射阶段用于把已确认的输入范围拆成价值目标清晰、边界明确、依赖可见的 Epic Map。请围绕用户价值、业务能力、交付边界、优先级和跨 Epic 依赖组织拆解，并保持后续 User Story Backlog、验收标准、Sprint 切片和 Lisa Handoff 可追溯。`;

export const EPIC_MAPPING_TEMPLATE = `结构化业务数据应覆盖：
- input_analysis：保留输入分析阶段的目标、用户、约束和待澄清问题。
- epics：为每个 Epic 填写 epic_id、name、value_goal、scope、priority、dependencies。
- user_stories：为每个 Epic 补充最小可交付故事草案，确保 story_id 能引用 epic_id。
- dependencies：记录跨 Epic 或外部系统依赖及风险缓解。
- stage_gate：确认 Epic 是否覆盖核心目标、边界、依赖和优先级。`;
