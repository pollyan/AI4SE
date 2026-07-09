# Refactor Todo

本目录记录重构类扫描、方案和实施待办。已完成的 todo 归档到 `docs/todos/archive/`；当前没有可直接恢复实现的 P0/P1 功能候选，保留的 New Agents 增强诊断、DeepSeek V4 结构化产物和 milestone ledger 均作为历史事实源使用。

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

- `2026-06-24-goal-mode-milestone-ledger.md`：目标模式 milestone 历史账本；恢复目标模式时可读取它了解已完成能力包，但不得从旧 integration branch / E 编号直接恢复实现。
- `2026-06-23-deepseek-v4-structured-artifact-data.md`：DeepSeek V4 Flash 兼容的后端结构化产物数据改造已完成本地确定性 readiness gate；除非 CGA 发现新回归、真实 smoke 失败或新增 workflow/stage，否则不要继续按逐 stage 迁移恢复为活跃候选。真实 DeepSeek smoke 仍需要显式凭证、网络和额度。
- `2026-06-23-new-agents-enhancement-diagnostic.md`：New Agents 功能盘点与增强诊断 todo；已消化 E01 Workflow 入口 preview、E02 阶段缺失信息清单、E03/E08 Artifact/Workflow 质量治理闭环、E04 Lisa 测试资产质量闭环、E05 Artifact 定向修订闭环、E06 Run 历史复用中心、E07 Workflow handoff 上下文审阅、E09 运行统计产品化诊断建议、E10 专业方法库配置、E11 Prompt/template 版本管理、E12 Workflow schema dry-run 门禁、E13 Alex 用户故事拆解 workflow、E14 Alex PRD Review workflow。
  - 当前功能能力包已清空；后续只有在新失败证据、用户新目标或重新提升的 P2 backlog 出现时，才通过完整 CGA 形成新的厚切片。
  - 恢复目标模式时继续按 `docs/strategy/goal-mode-playbook.md` 执行中文 CGA、Superpowers 头脑风暴、中文 spec、中文 implementation plan 和 TDD，不机械按 ID 顺序推进。

2026-07-09 已复核：除上述历史事实源外，其他重构类事项均已归档或转为历史完成记录；不要从 `archive/`、旧 integration branch 记录或过程性“待办/剩余”直接恢复实施。

2026-06-24 目标模式记录：本轮在 `codex/workflow-quality-governance-current` 中消化 New Agents E03/E08 合并能力包「Artifact/Workflow 质量治理闭环」，以现有 `ArtifactPane` 审阅入口展示质量分、contract/visual/stage gate 检查、证据和待处理项。

2026-06-24 已复核：DeepSeek V4 格式化输出需求已由 17 个在线 stage 的 `artifact_data` schema、后端 deterministic renderer、DeepSeek `json_object_only` adapter、数据纠错 retry 和 readiness gate 收口。真实 DeepSeek V4 Flash smoke 仍需显式凭证、网络和额度，不属于默认本地门禁。

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
