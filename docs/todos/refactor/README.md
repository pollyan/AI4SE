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

- `2026-06-23-deepseek-v4-structured-artifact-data.md`：DeepSeek V4 Flash 兼容的后端结构化产物数据改造记录；本地确定性 readiness 已覆盖当前全部在线 workflow stage，并已补齐格式化输出失败分类、`artifact_data` retry 诊断上下文、运行统计 drilldown、最近失败分诊队列和真实 smoke gate 结构化链路对齐；真实 DeepSeek 外部执行证据仍因凭证、网络和额度作为可选验证保留。
- `2026-06-23-new-agents-enhancement-diagnostic.md`：New Agents 功能盘点、差距分析和增强路线活动候选；已记录 2026-06-23 Alex `PRD_REVIEW` 质量评审与补全 workflow、`STORY_BREAKDOWN` 用户故事拆解 workflow、Artifact 审阅诊断中心、Lisa 测试资产质量闭环、Workflow handoff 上下文审阅、Run 历史复用中心、DeepSeek 格式化失败运行统计诊断闭环、Workflow 质量治理闭环、Artifact 定向修订闭环、Workflow schema dry-run 门禁、完整 scaffold/codegen、跨 run 工作流质量趋势闭环和 DeepSeek 真实 smoke gate 结构化链路对齐消化结果，下一批高价值候选为 E08 LLM judge evidence、prompt/template 版本管理、专业方法库配置化和 DeepSeek 真实外部执行证据。

## 后续切片颗粒度

后续恢复目标模式时，剩余工作按完整能力包执行，每个能力包单独走一次 Superpowers 流程：

1. E08 LLM judge evidence。
2. Prompt/template 版本管理。
3. 专业方法库配置化。
4. DeepSeek 真实外部执行证据。

2026-06-23 已完成 E12 workflow scaffold/codegen 工程信任闭环：新增 scaffold CLI 可从 JSON spec 预览或写入 workflow manifest 和 prompt skeleton，默认拒绝非法 spec、重复 stage/template、已有 workflow 和已有 prompt 文件，并输出后续 dry-run 命令继续暴露 backend contract、renderer/readiness 等剩余缺口。

每个能力包都必须作为完整厚切片推进，默认包含 CGA、自问自答式头脑风暴、中文 spec、中文 implementation plan、TDD、验证、todo 更新和聚焦 commit。CGA 选定 milestone 后，必须先输出中文自问自答头脑风暴，再生成中文 spec；该头脑风暴至少回答用户意图、成功标准、边界取舍、2-3 个实现路径、推荐路径、风险和验收证据。不要把同一能力包拆成“先 schema、再 UI、再测试、再文档”的多轮小切片；同一用户意图下的后端契约、前端入口、状态承接、错误反馈、验证证据和文档记录应在同一轮交付。DeepSeek 真实外部执行证据是例外：真实 smoke gate 已完成结构化链路对齐，后续如果当轮仍缺少凭证、网络或额度，只能记录真实外部验证未完成，不能用 mock 结果替代真实 DeepSeek 调用。

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
