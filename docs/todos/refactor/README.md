# Refactor Todo

本目录记录重构类扫描、方案和实施待办。已完成的 todo 归档到 `docs/todos/archive/`；当前没有活跃重构 todo。

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

- `2026-06-23-deepseek-v4-structured-artifact-data.md`：DeepSeek V4 Flash 结构化产物迁移与 evidence gate 已完成；真实外部 smoke 仅在凭证、网络和额度齐备时显式触发，不作为默认本地门禁。

2026-06-23 已复核：DeepSeek V4 不再按单 stage 继续拆 Superpowers；后续只接受真实 smoke 扩展、CI evidence 接入或 artifact data 持久化审计等能力包级候选。

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
