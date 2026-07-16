export const SPRINT_PLAN_PROMPT = `Sprint 计划阶段用于把 User Story Backlog 整理成可交付切片，并完成 Lisa Handoff。请围绕 Sprint 目标、故事组合、交付物、验收重点、依赖风险、可测试性和需求评审输入形成最终用户故事拆解包，确保 Lisa 可以直接进入测试设计或需求评审。`;

const FENCE = '```';

export const SPRINT_PLAN_TEMPLATE = `结构化业务数据应覆盖：
- sprint_slices：每个 Sprint 必须包含 sprint_id、goal、story_ids、deliverable、acceptance_focus。
- dependencies：保留会影响 Sprint 交付或 Lisa 后续工作的依赖与风险。
- lisa_handoff_inputs：把 P0 用户故事、关键验收标准、依赖风险和验证重点整理成可交给 Lisa 的输入。
- stage_gate：确认所有 P0 用户故事均具备验收标准、Sprint 切片、依赖风险记录和 Lisa Handoff 输入。
- document_info：标明 STORY_BREAKDOWN、SPRINT_PLAN 和产物状态。

最终 Markdown 必须先渲染全部业务正文，再以“## 文档信息”单行展示 document_info 元信息；不要把元信息放在正文开头或渲染成表格。

最终渲染会由后端生成 ai4se-visual flow-map 和 story-map，例如：
${FENCE}ai4se-visual
{"type": "flow-map","title":"Epic 流程图","nodes":[{"id":"Goal","label":"Goal","title":"产品目标"},{"id":"EPIC-001","label":"EPIC-001","title":"核心 Epic"}],"edges":[{"source":"Goal","target":"EPIC-001","label":"拆解为"}]}
${FENCE}

${FENCE}ai4se-visual
{"type": "story-map","columns":["Epic","Story","优先级","Sprint","依赖","可测试性"],"rows":[{"Epic":"EPIC-001","Story":"US-001 核心故事","优先级":"P0","Sprint":"Sprint 1","依赖":"无","可测试性":"高"}]}
${FENCE}`;
