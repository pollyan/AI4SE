# Alex 用户故事拆解 Workflow 主线化 Spec

> 日期: 2026-06-23
> 状态: 已完成

## 背景

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 E13 标为 P0: Alex 用户故事拆解 workflow。当前 New Agents 已具备共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、确定性 renderer、run/artifact persistence 和 Alex/Lisa workflow listing。后续增强应通过配置、prompt、contract、renderer 和测试表达，而不是新增 Alex 专属 runtime、API path、store 或渲染链路。

当前用户可用 Alex 做创意脑暴和价值发现，但无法把 PRD 或需求蓝图进一步拆成研发评审可用的 Epic、User Story、验收标准、依赖风险和 Sprint 切片，也无法把这个拆解包作为 Lisa 测试设计或需求评审输入。

## 用户故事

作为产品经理或业务分析师，当我把 PRD、需求蓝图或产品想法交给 Alex 时，我希望选择“用户故事拆解”workflow，获得一份结构化用户故事包，包括 Epic map、User Story backlog、验收标准、依赖/风险和 Sprint 切片建议，并能把可测试的内容交给 Lisa 继续做测试设计或需求评审。

## 范围

本轮包含:

- 新增共享 workflow `STORY_BREAKDOWN`，前端 slug 为 `story-breakdown`。
- 在 `workflow_manifest.json` 中声明 stages、artifact contract、visual contract、handoff 和 onboarding 信息。
- 在前端 workflow registry / Alex workflow listing 中暴露该 workflow。
- 增加 Alex story breakdown prompt/template，要求输出 `artifact_data` 而不是模型直写最终 Markdown。
- 在后端增加 `artifact_data` Pydantic schema、deterministic renderer、artifact contract heading 校验和 runtime instruction。
- 增加 handoff 支持，使最终故事包可交给 Lisa `TEST_DESIGN` 或 `REQ_REVIEW`。
- 增加后端 contract/runtime/renderer/handoff 测试和前端 workflow/prompt 测试。
- 更新 enhancement diagnostic，把 E13 标记为已消化并记录验证证据。

本轮不包含:

- 不接入 Jira、禅道、飞书项目或其他外部项目管理工具。
- 不新增 Alex 专属 runtime、API、store、SSE path 或 renderer。
- 不实现 PRD Review（E14）。
- 不做 Artifact 质量诊断面板、Lisa 测试资产质量状态或历史中心增强。
- 不运行真实模型 smoke，除非环境显式提供凭证、网络和额度。

## Workflow 设计

Workflow ID: `STORY_BREAKDOWN`

Slug: `story-breakdown`

Agent: `alex`

Stages:

1. `INPUT_ANALYSIS`: 盘点输入范围、用户角色、业务目标、约束和待澄清问题。
2. `EPIC_MAPPING`: 拆分 Epic、能力边界、价值目标和依赖关系。
3. `STORY_BACKLOG`: 生成 User Story、验收标准、优先级、依赖和可测试性提示。
4. `SPRINT_PLAN`: 组织 Sprint 切片、交付包、风险、Lisa handoff 输入和阶段门禁。

产出物标题应稳定覆盖:

- `# 用户故事拆解包`
- `## 输入分析`
- `## Epic Map`
- `## User Story Backlog`
- `## 验收标准`
- `## 依赖与风险`
- `## Sprint 切片建议`
- `## Lisa Handoff 输入`
- `## 阶段门禁`

结构化 visual:

- `ai4se-visual` `story-map`，表达 Epic、Story、优先级、Sprint 和依赖。

## 数据与渲染

模型输出 JSON:

- `chat`: 面向用户的工作说明。
- `artifact_data`: 当前阶段业务结构化数据。
- `stage_action`: 下一阶段请求或结束。
- `warnings`: 证据不足、输入缺失、风险等提示。

后端职责:

- Pydantic schema 校验非空字段、引用关系、唯一 ID、Sprint/story 引用一致性和 Lisa handoff 引用有效性。
- renderer 生成稳定 Markdown、Mermaid 或 `ai4se-visual` fenced block。
- `validate_agent_turn()` 继续作为 artifact contract 最终守门。

## 验收标准

- RED: 新 workflow manifest / backend contract / renderer / frontend listing 测试在实现前失败。
- GREEN: `STORY_BREAKDOWN` 通过共享 runtime 结构化输出和后端 deterministic renderer 生成完整 story breakdown artifact。
- `workflow_manifest.json`、前端 workflow registry、Alex workflow listing、backend `WORKFLOW_STAGES` / contract registry 保持同步。
- artifact contract 能拒绝缺失关键标题或 visual 的输出。
- handoff 能生成面向 Lisa `TEST_DESIGN` 和 `REQ_REVIEW` 的上下文摘要。
- 前端 workflow test 能看到 `story-breakdown` slug 和 Alex listing。
- 不新增 agent-specific runtime/API/store/renderer。

## 风险

- 该 workflow 触及 manifest、runtime、renderer、contract、handoff、前端 registry，多面同步风险高，必须用 sync tests 和扩展后端验证覆盖。
- 现有候选分支 `codex/alex-story-breakdown-workflow` 不是基于 DeepSeek mainline closure，不能直接 merge；本轮只把其业务意图按 TDD 移植到 `codex/deepseek-v4-mainline-closure` 基线。
- 真实模型质量不在默认本地门禁中；后续可补 LLM judge 或真实 smoke。

## 完成记录

- 2026-06-23: 已在隔离 worktree `codex/alex-story-breakdown-mainline` 主线化 `STORY_BREAKDOWN`。
- 后端已接入共享 `workflow_manifest.json`、`WORKFLOW_STAGES`、artifact contract、`artifact_data` renderer、runtime structured output instruction、run persistence stage 校验和 manifest 驱动 handoff。
- 前端已接入共享 workflow registry、Alex 在线 workflow listing、artifact_data prompt mode 和四阶段 prompt/template。
- 本轮未新增 Alex 专属 runtime、API path、store、SSE path 或 bespoke renderer。
