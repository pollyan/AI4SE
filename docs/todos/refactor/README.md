# Refactor Todo

本目录记录重构类扫描、方案和实施待办。已完成的 todo 归档到 `docs/todos/archive/`；当前活跃重构候选集中在 New Agents 增强诊断和 DeepSeek V4 结构化产物收口。

## 使用规则

- 先扫描，再方案，再计划，再实现；不要从本目录的候选项直接进入编码。
- 扫描文档必须记录事实证据、影响文件、风险等级和建议验证，不只记录主观判断。
- 所有 `tools/new-agents/` 重构必须继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型和共享 UI 基础设施。
- Lisa、Alex 和未来 Agent 的差异优先通过 `agentId`、workflow 配置、阶段 prompt、artifact template、后端 contract、visualization contract 和 handoff 配置表达。
- 不新增 agent-specific runtime、transport、state store、SSE/API path 或 bespoke rendering pipeline，除非先形成明确架构变更文档并获得用户确认。
- 进入实现前按 `docs/strategy/goal-mode-playbook.md` 做 Current State Gap Analysis、spec、plan 和验证。

## 文档命名

- `YYYY-MM-DD-new-agents-refactor-scan.md`：只读架构扫描报告。
- `YYYY-MM-DD-new-agents-refactor-options.md`：基于扫描报告的重构方案比较。
- `YYYY-MM-DD-new-agents-refactor-phaseN-plan.md`：选定阶段后的 TDD 实施计划。

## 当前入口

- `2026-06-23-deepseek-v4-structured-artifact-data.md`：DeepSeek V4 Flash 兼容的后端结构化产物数据改造记录；本地确定性 readiness 已覆盖当前全部在线 workflow stage，真实 DeepSeek smoke 仍因凭证、网络和额度作为外部可选验证保留。
- `2026-06-23-new-agents-enhancement-diagnostic.md`：New Agents 功能盘点、差距分析和增强路线活动候选；已记录 2026-06-23 Alex `PRD_REVIEW` 质量评审与补全 workflow、`STORY_BREAKDOWN` 用户故事拆解 workflow、Artifact 审阅诊断中心消化结果，下一批高优先级候选为 Lisa 测试资产质量闭环。

2026-06-23 已复核：除上述活动候选外，其他重构类事项均已归档或转为 `docs/plans/tech-debt.md` 中的历史完成记录；不要从 `archive/` 中的过程性“待办/剩余”直接恢复实施。

## 已归档

- `../archive/2026-06-21-new-agents-refactor-scan.md`：第一轮 New Agents 智能体重构扫描报告。
- `../archive/2026-06-21-new-agents-refactor-options.md`：第二轮 New Agents 智能体重构方案设计。
- `../archive/2026-06-21-new-agents-refactor-phase1-plan.md`：New Agents 智能体重构阶段 1 实施计划。
- `../archive/2026-06-21-new-agents-refactor-phase2-plan.md`：New Agents 智能体重构阶段 2 实施计划。
- `../archive/2026-06-21-new-agents-refactor-phase3-plan.md`：New Agents 智能体重构阶段 3 第一批模块边界计划。
- `../archive/2026-06-21-new-agents-refactor-phase4-plan.md`：New Agents 智能体重构阶段 4 test assets 解析边界计划。
- `../archive/2026-06-21-new-agents-refactor-phase5-remaining-plan.md`：New Agents 智能体重构阶段 5 剩余路线与前端 ArtifactPane 拆分计划。
- `../archive/2026-06-22-new-agents-artifact-professionalization-target.md`：New Agents 全 workflow 产出物专业化目标状态与目标模式输入提示词。
- `../archive/2026-06-22-new-agents-artifact-professionalization-design.md`：New Agents 全 workflow 产出物专业化目标状态设计。
