export const INPUT_ANALYSIS_PROMPT = `输入分析阶段用于把用户提供的 PRD、需求蓝图、产品想法或变更背景整理成可拆解的业务输入。请识别输入来源、产品目标、目标用户、业务约束、范围边界、关键依赖和待澄清问题，并为后续 Epic Map、User Story Backlog、验收标准、Sprint 切片和 Lisa Handoff 建立统一上下文。`;

const FENCE = '```';

export const INPUT_ANALYSIS_TEMPLATE = `结构化业务数据应覆盖：
- document_info：标明 STORY_BREAKDOWN、当前阶段和产物状态。
- input_analysis：source_type、product_goal、target_users、constraints、open_questions。
- epics：先给出可验证的初始 Epic 假设。
- user_stories、acceptance_criteria、dependencies、sprint_slices、lisa_handoff_inputs：可以基于当前输入给出第一版草案，并在 chat 中明确需要用户确认的假设。
- stage_gate：至少包含输入来源、目标用户、约束和待澄清问题是否已整理。

最终 Markdown 必须先渲染全部业务正文，再以“## 文档信息”单行展示 document_info 元信息；不要把元信息放在正文开头或渲染成表格。

后端渲染器会基于结构化数据生成 ai4se-visual flow-map 示例：
${FENCE}ai4se-visual
{"type": "flow-map","title":"Epic 流程图","nodes":[{"id":"Goal","label":"Goal","title":"产品目标"},{"id":"EPIC-001","label":"EPIC-001","title":"核心 Epic"}],"edges":[{"source":"Goal","target":"EPIC-001","label":"拆解为"}]}
${FENCE}`;
