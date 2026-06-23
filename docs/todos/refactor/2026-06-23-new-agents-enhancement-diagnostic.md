# New Agents 功能盘点与增强诊断 Todo

> 状态: 活动候选
> 创建日期: 2026-06-23
> 背景: 对 `tools/new-agents/` 进行只读功能盘点后，当前系统已经具备共享 Agent Runtime、typed SSE、多 workflow、artifact contract、运行持久化、artifact 协作和运行统计基础。后续增强应优先深化已有能力，而不是复制 Lisa/Alex 专属运行时或渲染链路。

## 总体诊断

当前 New Agents 是一个配置化多智能体工作台:

- Lisa: 测试专家，在线 workflow 包括 `TEST_DESIGN`、`REQ_REVIEW`、`INCIDENT_REVIEW`。
- Alex: 业务需求分析师 / 创新顾问，在线 workflow 包括 `IDEA_BRAINSTORM`、`VALUE_DISCOVERY`、`PRD_REVIEW`、`STORY_BREAKDOWN`。
- 所有在线 workflow 通过共享 `/api/agent/runs/stream`、typed SSE、共享 store、共享 artifact renderer 和共享 run persistence 工作。

最大增强机会不是新增一批孤立 agent，而是把已有能力从“能生成 artifact”深化为“能诊断、能审阅、能修订、能恢复、能复用、能验收”的专业闭环。

## 关键证据路径

- Workflow manifest、阶段、artifact/visual contract、handoff、onboarding: `tools/new-agents/workflow_manifest.json`
- 前端 workflow 构造和 slug registry: `tools/new-agents/frontend/src/core/workflows.ts`、`tools/new-agents/frontend/src/core/workflowRegistry.ts`
- Agent/persona/workflow listing: `tools/new-agents/frontend/src/core/config/agents.ts`、`tools/new-agents/frontend/src/core/config/agentWorkflows.ts`
- Prompt/template: `tools/new-agents/frontend/src/core/prompts/`
- 共享 workspace state: `tools/new-agents/frontend/src/store.ts`
- Chat / Artifact / Header UI: `tools/new-agents/frontend/src/components/ChatPane.tsx`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/Header.tsx`
- typed SSE client: `tools/new-agents/frontend/src/core/llm.ts`
- 后端 Agent Runtime: `tools/new-agents/backend/agent_runtime.py`
- Agent output contract: `tools/new-agents/backend/agent_contracts.py`
- Manifest contract registry: `tools/new-agents/backend/workflow_contract_registry.py`
- SSE orchestration and metrics: `tools/new-agents/backend/stream_services.py`
- Run persistence/snapshot/artifact collaboration: `tools/new-agents/backend/run_persistence.py`
- Context builder: `tools/new-agents/backend/context_builder.py`
- Workflow handoff: `tools/new-agents/backend/workflow_handoffs.py`
- Lisa test assets: `tools/new-agents/backend/test_assets.py`
- Backend tests: `tools/new-agents/backend/tests/`
- Frontend tests: `tools/new-agents/frontend/src/**/__tests__/`
- Architecture docs: `docs/architecture.md`、`docs/api-contracts.md`、`docs/TESTING.md`

## 当前能力地图

| 能力域 | 当前能力 | 成熟度 | 主要限制 |
| --- | --- | --- | --- |
| Agent / workflow | Alex、Lisa 共 7 个在线 workflow、25 个阶段 | 中高 | persona 和专业方法还没有完整配置化；后续重点转向质量诊断、Lisa 资产闭环和 DeepSeek V4 结构化输出收口 |
| Runtime | PydanticAI + raw JSON streaming + typed SSE | 高 | 质量诊断偏 schema/contract 错误，不是产品质量评分 |
| Contract | required headings、Mermaid、structured visual、stage_action 校验 | 高 | `agent_contracts.py` 与 manifest 仍有重复同步成本 |
| Persistence | run、message、artifact version、context summary、metric、comment、lock、audit | 高 | 历史中心和复用能力仍偏基础 |
| UI | 双栏 workspace、workflow 切换、历史、设置、artifact 编辑、审阅、导出、运行统计 | 中高 | Header/ArtifactPane 承载能力多，质量诊断未统一 |
| Handoff | VALUE_DISCOVERY/BLUEPRINT 可交给 Lisa TEST_DESIGN 或 REQ_REVIEW，且 handoff card 展示来源版本、关键摘要、未确认项和目标输入 | 中高 | 仍只有 Alex 到 Lisa 的少量 handoff；后续可扩展更多 source/target 配置 |
| Test assets | Lisa TEST_DESIGN/CASES 可实体化测试资产、风险、issue | 中 | 增强时不要围绕 intent-tester 联动扩展 |
| Testing | backend contract/runtime/API/persistence + frontend service/store/component tests | 高 | LLM judge/e2e evidence 需要持续管理 |

## 主要差距

| 维度 | 当前状态 | 缺口 | 优先级 |
| --- | --- | --- | --- |
| 专业可信度 | prompt/template 已有 FMEA、5 Why、ICE、roadmap 等方法；Lisa 测试资产已补质量状态闭环 | 仍缺跨 workflow 质量评分、证据强度、复审闭环和趋势化质量门禁 | P1 |
| Artifact 闭环 | 有版本、diff、批注、章节锁、导出、冲突合并 | 缺统一 artifact quality / contract / stage gate 诊断面板 | P0 |
| Workflow 入口 | 有 listing、onboarding、starter prompts；2026-06-23 已补在线 workflow 入口 preview | 仍缺自动推荐排序和更深的选择决策引导 | P1 |
| Run 复用 | 有历史列表、搜索、runId snapshot 恢复、复用状态筛选、当前 artifact 预览、继续原 run、复制为新 run | 跨 run 对比和收藏仍未做；不影响当前历史复用闭环 | P1 已部分完成 |
| Workflow handoff | 有配置化 handoff 基础，已补上下文审阅卡和目标 run 输入增强 | 当前 P1 缺口已消化；后续只在新增 source/target handoff 时扩展配置 | 已完成 |
| 可观测性 | 有 success rate、provider、stage、recent turns | 缺面向用户的质量趋势、contract retry drilldown、失败原因行动建议 | P1 |
| 平台扩展 | manifest 已承载核心配置 | 缺 schema 校验、dry-run、scaffold、prompt/template 版本管理 | P2 |

## 增强机会清单

| ID | 增强点 | 类型 | 类别 | 复杂度 | 优先级 | 验收标准 |
| --- | --- | --- | --- | --- | --- | --- |
| E01 | Workflow 入口 preview | 改造现有功能 | 体验 | S | P0 | 已消化：每个在线 workflow 展示适用/不适用、输入要求、预期产物和样例输入 |
| E02 | 阶段缺失信息清单 | 深化现有功能 | 专业内容 | S | P0 | 已消化当前 artifact 审阅侧：右侧产物审阅可展示待澄清、开放、未确认、阻断和阶段门禁待处理信息；chat 侧轻提示后续归入会话引导增强 |
| E03 | Artifact 质量诊断面板 | 深化现有功能 | 可信质量 | M | P0 | 已消化：右侧产物审阅诊断中心展示 required headings、Mermaid、structured visual、stage gate 和 runtime visual diagnostic 的通过/失败/警告，并聚合缺失信息清单 |
| E04 | Lisa 测试资产质量闭环 | 深化现有功能 | 专业内容 | M | P0 | 已消化：测试资产集合输出统一 `qualitySummary`，资产中心和 Header 展示质量状态/gate，issue、测试点覆盖、风险生命周期动作会推动质量状态变化 |
| E05 | 章节级重生成 | 新增功能 | 功能 | M | P1 | 用户可指定章节重写，保留锁定章节，仍输出完整 artifact |
| E06 | Run 历史中心增强 | 深化现有功能 | 功能 | M | P1 | 已消化：支持继续、复制为新 run、按 workflow/复用状态筛选、预览当前 artifact |
| E07 | Workflow handoff 增强 | 深化现有功能 | 平台扩展 | M | P1 | 已消化：handoff 展示来源版本、关键摘要、未确认项和目标 workflow 输入；启动目标 run 时首条上下文包含同一审阅结构 |
| E08 | 工作流质量评分 | 新增功能 | 可信质量 | M | P1 | 每个 stage 有质量分、证据明细和待处理项 |
| E09 | 运行统计产品化 | 深化现有功能 | 可信质量 | M | P1 | 显示 workflow/stage/provider 趋势、contract retry 原因和行动建议 |
| E10 | 专业方法库配置 | 新增功能 | 专业内容 | L | P2 | FMEA、JTBD、RICE、Kano、CAPA 等可由配置注入 prompt/template |
| E11 | Prompt/template 版本管理 | 新增功能 | 平台扩展 | L | P2 | 每个 stage 有 prompt/template version 和回归样例 |
| E12 | Workflow schema dry-run/scaffold | 新增功能 | 平台扩展 | L | P2 | 新 workflow 缺 manifest/prompt/contract/test 任一面时 dry-run 失败 |
| E13 | Alex 用户故事拆解 workflow | 新增功能 | 专业内容 | M | P0 | 已消化：`STORY_BREAKDOWN` 作为 Alex 在线 workflow 复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、artifact_data renderer 和 handoff，覆盖输入分析、Epic 映射、Story Backlog、Sprint 切片与 Lisa handoff |
| E14 | Alex PRD 质量评审与补全 workflow | 新增功能 | 专业内容 | M | P0 | 已消化：`PRD_REVIEW` 作为 Alex 在线 workflow 复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract 和 artifact_data renderer，覆盖输入盘点、质量评审、补全建议和修订蓝图 |

## Goal Mode 消化记录

- 2026-06-23: 已完成 Alex `PRD_REVIEW` 质量评审与补全 workflow 主线化切片。新增 `prd-review` 在线入口、4 个阶段 prompt/template、manifest artifact/visual contract、后端 `artifact_data` schema/renderer、runtime structured output instruction 和前后端同步测试。该切片不新增 Alex 专属 runtime、API path、store 或 renderer pipeline。
- 2026-06-23: 已完成 Alex `STORY_BREAKDOWN` 用户故事拆解 workflow 主线化切片。新增 `story-breakdown` 在线入口、4 个阶段 prompt/template、manifest artifact/visual contract、后端 `artifact_data` schema/renderer、runtime structured output instruction、Lisa handoff 和前后端同步测试。该切片不新增 Alex 专属 runtime、API path、store 或 renderer pipeline。
- 2026-06-23: 已完成 Artifact 审阅诊断中心厚切片，合并消化 E02 当前 artifact 审阅侧缺失信息清单和 E03 Artifact 质量诊断面板。新增前端共享诊断核心，从 `workflow_manifest.json` 读取当前阶段 artifact/visual contract，结合当前 Markdown 与现有 runtime visual diagnostics，在右侧产物审阅面板展示 required headings、Mermaid、structured visual、stage gate、运行时可视化警告、待澄清/开放/未确认/阻断信息和下一步。该切片不新增 agent 专属 runtime、API path、store 或 renderer pipeline；不纳入自动修复、LLM judge、跨 run 趋势或 Lisa 测试资产闭环。
- 2026-06-23: 已完成 Lisa 测试资产质量闭环厚切片，消化 E04。后端 `TestAssetCollection` 增加由持久化 issue 状态、测试点覆盖和风险生命周期计算的 `qualitySummary`；前端 service 严格解析该 contract；资产中心和 Header 快捷面板展示统一质量状态与 gate；确认/忽略 issue、保存测试点、保存风险会推动质量状态变化。该切片复用现有测试资产 API、持久化模型和共享 UI，不新增 Lisa 专属 runtime、API path、store 或 renderer。
- 2026-06-23: 已完成 Workflow handoff 上下文审阅厚切片，消化 E07。后端共享 `workflow_handoffs.py` 为每个候选生成确定性 `sourceSummary`、`unconfirmedItems` 和 `targetInputChecklist`，目标 run 首条 prompt 带来源版本、摘要、未确认项、目标输入和 bounded source artifact；前端 service 严格解析该 contract，ChatPane 在启动 handoff 前展示审阅卡。该切片复用现有 workflow manifest、handoff endpoints、run persistence、store transition 和共享 UI，不新增 agent 专属 runtime、API path、store 或 renderer。
- 2026-06-23: 已完成 Run 历史复用中心厚切片，消化 E06。后端 run list 返回并过滤 `reuseStatus=ready|needs_artifact|failed`，新增共享 `POST /api/agent/runs/<run_id>/clone` 复制源 run 的 messages、当前 artifacts 和 context summaries 为独立 active run；前端 service 严格解析复用状态并提供 clone API；Header 历史会话升级为可筛选、可预览当前 artifact、可继续原 run、可复制为新 run 的复用中心，并展示预览/复制失败反馈。该切片复用现有 run persistence、snapshot restore、共享 Header UI 和 workflow registry，不新增 agent 专属 runtime、API path、store 或 renderer。

## Lisa 专业化方向

- `REQ_REVIEW`: 加强需求可测试性、完整性、歧义、边界、异常路径、非功能需求和复审条件评分。
- `TEST_DESIGN`: 深化 FMEA、测试金字塔、覆盖矩阵、边界值、等价类、状态迁移、决策表、自动化候选、上线准入和风险接受记录。
- `INCIDENT_REVIEW`: 深化时间线证据链、影响范围、5 Whys、鱼骨图、CAPA、owner/due date、验收标准、防复发机制和风险接受。

建议首批 Lisa 切片:

1. 需求评审质量评分和复审条件。
2. TEST_DESIGN/CASES 测试资产质量闭环已在 2026-06-23 本轮消化，后续只在发现回归或需要接入跨 run 质量趋势时维护。
3. INCIDENT_REVIEW/IMPROVEMENT CAPA 行动项闭环。

## Alex 专业化方向

- `VALUE_DISCOVERY`: 加强 JTBD、用户旅程证据、机会评分、RICE/Kano/MoSCoW、需求蓝图完整性、非功能需求和 Lisa handoff 输入质量。
- `IDEA_BRAINSTORM`: 加强问题域证据、创意来源、ICE 评分口径、MVP 范围收敛、Pre-mortem、验证实验和决策记录。
- `STORY_BREAKDOWN`: 已在 2026-06-23 本轮消化为 Alex 在线 workflow，可将 `VALUE_DISCOVERY/BLUEPRINT`、PRD 或 PRD Review 修订蓝图拆解为 Epic、User Story、验收标准、依赖、风险、Sprint 切片和 Lisa handoff 输入。
- `PRD_REVIEW`: 已在 2026-06-23 本轮消化为 Alex 在线 workflow；后续可作为 Story Breakdown 或 Lisa `REQ_REVIEW` 的上游输入。

建议首批 Alex 切片:

1. VALUE_DISCOVERY/BLUEPRINT 质量门禁和 handoff 输入强化。
2. IDEA_BRAINSTORM/CONVERGE 评分口径和验证实验闭环。
3. DeepSeek V4 结构化 artifact_data 输出兼容性收口。

## 推荐路线

### A. 快速专业化路线

目标: 1-2 周内明显提升专业感和产出可信度。

包含: E01/E02/E03/E04/E07/E13/E14 均已在 2026-06-23 目标模式切片中消化。快速专业化路线剩余工作转入质量评分、历史 run 复用和运行统计产品化等 P1 能力包。

暂不做:

- Prompt/template 版本管理。
- 全量专业方法库配置。
- 新 runtime 或新 renderer。

验证:

- Backend contract tests。
- Frontend ArtifactPane/Header/WorkflowSelect tests。
- 至少 2 条 mock typed SSE browser/e2e workflow。

### B. 功能闭环路线

目标: 让用户从开始、生成、审阅、修订、恢复、复用形成闭环。

包含: E03、E05、E06、E07、E08；其中 E03、E06、E07 已消化，E05/E08 仍可作为后续厚切片候选。

暂不做:

- intent-tester 联动增强。
- 跨团队权限/分享模型。

验证:

- run snapshot API/service tests。
- artifact edit/conflict/collaboration tests。
- workflow handoff backend/frontend tests。

### C. 平台化路线

目标: 让后续新增 agent/workflow 更低成本、更可靠。

包含: E09、E10、E11、E12。

暂不做:

- 一次性迁移所有 prompt/template。
- agent-specific API/store/render pipeline。

验证:

- workflow manifest schema negative tests。
- config sync tests。
- prompt registry tests。
- 可选 LLM judge evidence 管理。

## 首批建议落地切片

### 1. Artifact 质量诊断面板

- 状态: 已在 2026-06-23 Artifact 审阅诊断中心切片中消化，且与 E02 当前 artifact 审阅侧缺失信息清单合并为一个用户可见厚切片。
- 涉及模块: `ArtifactPane.tsx`、`StructuredVisual.tsx`、`agent_contracts.py`、`workflow_contract_registry.py`、相关 tests。
- 需要同步: manifest artifact/visual contract、前端诊断展示、后端 contract helper。
- 完成定义: 当前阶段 artifact 能展示必填标题、可视化、阶段门禁、专业字段的通过/失败/警告，并聚合待澄清/开放/未确认/阻断信息。
- 不纳入: 自动修复全文。

### 2. Workflow 入口专业 preview

- 涉及模块: `workflow_manifest.json`、`AgentSelect.tsx`、`WorkflowSelect.tsx`、`agentWorkflows.ts`、onboarding tests。
- 需要同步: listing、onboarding、starter prompts、workflow slug tests。
- 完成定义: 用户进入工作区前能判断 workflow 是否适合当前目标。
- 不纳入: 自动 workflow 推荐排序。

### 3. Lisa 测试资产质量闭环

- 状态: 已在 2026-06-23 目标模式切片中消化。
- 涉及模块: `test_assets.py`、`routes_test_assets.py`、`testAssetService.ts`、`Header.tsx`。
- 需要同步: TEST_DESIGN/CASES artifact contract、资产 issue schema、前端资产 modal。
- 完成定义: 测试点、风险、用例 issue 可处理，并通过持久化集合 `qualitySummary` 统一影响资产质量状态。
- 不纳入: 新增 intent-tester 联动或自动执行。
- 后续不再作为活跃候选重复选择；只在发现当前代码回归、真实 Lisa 输出 contract 失配，或需要接入跨 run 质量趋势时作为维护项处理。

### 4. 历史会话复用增强

- 状态: 已在 2026-06-23 Run 历史复用中心切片中消化。
- 涉及模块: `run_persistence.py`、`routes.py`、`runSnapshotService.ts`、`Header.tsx`。
- 需要同步: run list response、snapshot restore、store reset/clone 行为。
- 完成定义: 历史 run 可复制为新 run、继续、预览 artifact，并按 workflow/质量状态筛选。
- 不纳入: 多用户分享权限。
- 后续不再作为活跃候选重复选择；跨 run 对比、收藏或 E08 质量评分可作为新的独立厚切片处理。

### 5. Handoff 上下文强化

- 状态: 已在 2026-06-23 Workflow handoff 上下文审阅切片中消化。
- 涉及模块: `workflow_manifest.json`、`workflow_handoffs.py`、Alex blueprint prompt/template、`ChatPane.tsx`。
- 需要同步: handoff prompt template、target workflow/stage、context truncation policy。
- 完成定义: handoff 明确来源版本、关键需求、验收标准、风险、未确认项和目标用途。
- 不纳入: 新 runtime 分支。
- 后续不再作为活跃候选重复选择；只在新增 source/target handoff、发现 contract 回归，或需要将摘要策略配置化到 manifest 时作为维护项处理。

### 6. Alex 用户故事拆解 workflow

- 状态: 已在 2026-06-23 目标模式切片中消化。
- 涉及模块: `workflow_manifest.json`、`frontend/src/core/workflows.ts`、`frontend/src/core/config/agentWorkflows.ts`、`frontend/src/core/prompts/`、`backend/agent_contracts.py`、`backend/artifact_data_renderers.py`、相关前后端测试。
- 需要同步: workflow slug `story-breakdown`、Alex workflow listing、stage prompts、artifact required headings、structured visual contract、backend stage contract、frontend route/workflow tests。
- 建议阶段: 需求输入解析、Epic 拆分、User Story 与验收标准、Sprint 切片与交付包。
- 产出物: Epic map、User Story backlog、AC 表、依赖/风险清单、Sprint 切片建议、Lisa handoff 输入。
- 完成定义: 用户输入需求蓝图或 PRD 后，可通过共享 `/api/agent/runs/stream` 生成可进入研发评审的用户故事包，并能继续交给 Lisa 做测试设计或需求评审。
- 不纳入: Jira/禅道等外部项目管理工具写入。
- 后续不再作为活跃候选重复选择；只在发现当前代码回归或 contract 失配时作为维护项处理。

### 7. Alex PRD 质量评审与补全 workflow

- 状态: 已在 2026-06-23 目标模式切片中消化。
- 完成定义: Alex 能明确区分“产品完整性问题”和“测试可测性问题”，输出可被 PM 修订 PRD 的补全建议，并保留可交给 Lisa `REQ_REVIEW` 或后续 `STORY_BREAKDOWN` 的结构化输入。
- 后续不再作为活跃候选重复选择；只在发现当前代码回归或 contract 失配时作为维护项处理。

## 架构约束

- 必须继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、run persistence 和共享 UI 基础设施。
- 不新增 Lisa/Alex 专属 runtime、transport、state store、SSE/API path 或 bespoke rendering pipeline。
- 工作流差异优先通过 `workflow_manifest.json`、`agentId`、stage prompt/template、artifact contract、visual contract、handoff 配置和测试表达。
- 不使用 mock、假数据、隐藏 fallback 或假成功响应掩盖能力缺口。
- 不围绕 intent-tester 设计新增联动能力；已有测试资产导入能力只作为边界记录。

## 进入实现前需要补的设计问题

- Artifact 质量诊断应完全前端解析，还是后端提供只读 diagnostic endpoint。
- 质量评分是否先做规则型 gate，再引入 LLM judge evidence。
- 历史 run “复制为新 run”已在 E06 中裁决为复制 messages、当前 artifact versions 和 context summaries；协作批注、章节锁、审计事件、turn metrics 和测试资产不自动复制。
- Handoff prompt 当前继续使用共享单模板，并由 deterministic helper 补来源版本、摘要、未确认项和目标输入；manifest 字段级摘要策略后续仅在 handoff 数量扩张时再评估。
- 专业方法库配置是否纳入 manifest，还是先建独立 registry 后再合并。
