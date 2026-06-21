# Refactor Todo

本目录记录重构类扫描、方案和实施待办。已完成的 New Agents UI/UX todo 已归档到 `docs/todos/archive/new-agents-ux-professionalization-2026-06-21.md`；当前活跃 todo 只保留重构扫描和后续重构计划。

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
- `YYYY-MM-DD-new-agents-refactor-plan.md`：选定方案后的 TDD 实施计划。

## 当前入口

- `2026-06-21-new-agents-refactor-scan.md`：第一轮 New Agents 智能体重构扫描模板。
- `2026-06-21-new-agents-refactor-options.md`：第二轮 New Agents 智能体重构方案设计模板。
