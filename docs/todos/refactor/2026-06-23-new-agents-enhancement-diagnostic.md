# New Agents 功能盘点与增强诊断 Todo

> 状态: 历史事实源；功能能力包已清空
> 创建日期: 2026-06-23
> 背景: 对 `tools/new-agents/` 进行只读功能盘点后，当前系统已经具备共享 Agent Runtime、typed SSE、多 workflow、artifact contract、运行持久化、artifact 协作和运行统计基础。后续增强应优先深化已有能力，而不是复制 Lisa/Alex 专属运行时或渲染链路。

## 总体诊断

当前 New Agents 是一个配置化多智能体工作台:

- Lisa: 测试专家，在线 workflow 包括 `TEST_DESIGN`、`REQ_REVIEW`、`INCIDENT_REVIEW`。
- Alex: 业务需求分析师 / 创新顾问，在线 workflow 包括 `IDEA_BRAINSTORM`、`VALUE_DISCOVERY`、`PRD_REVIEW`。
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
| Runtime | PydanticAI + raw JSON streaming + typed SSE | 高 | 质量治理已具备规则型 evidence gate；跨 run 趋势和 LLM judge 仍未接入 |
| Contract | required headings、Mermaid、structured visual、stage_action 校验；workflow schema dry-run 可聚合检查 manifest、前端 prompt/template、后端 contract、renderer/readiness、handoff 和打包同步 | 高 | `agent_contracts.py` 与 manifest 仍有重复同步成本；完整 scaffold/codegen 尚未实现 |
| Persistence | run、message、artifact version、context summary、metric、comment、lock、audit | 高 | 历史中心和复用能力仍偏基础 |
| UI | 双栏 workspace、workflow 切换、历史、设置、artifact 编辑、审阅、导出、运行统计 | 中高 | Header/ArtifactPane 承载能力多，质量诊断未统一 |
| Handoff | VALUE_DISCOVERY/BLUEPRINT 可交给 Lisa TEST_DESIGN 或 REQ_REVIEW | 中 | 只有 Alex 到 Lisa 的少量 handoff，模板简单 |
| Test assets | Lisa TEST_DESIGN/CASES 可实体化测试资产、风险、issue | 中 | 增强时不要围绕 intent-tester 联动扩展 |
| Testing | backend contract/runtime/API/persistence + frontend service/store/component tests | 高 | LLM judge/e2e evidence 需要持续管理 |

## 主要差距（历史扫描快照，后续已消化或转 P2）

| 维度 | 当时状态 | 当时缺口 | 当前处理结论 |
| --- | --- | --- | --- |
| 专业可信度 | prompt/template 已有 FMEA、5 Why、ICE、roadmap 等方法；Lisa 测试资产已补质量状态闭环 | 仍缺跨 workflow 质量评分、证据强度、复审闭环和趋势化质量门禁 | 规则型质量治理已消化；跨 run 趋势 / LLM judge evidence 转后续增强候选。 |
| Artifact 闭环 | 有版本、diff、批注、章节锁、导出、冲突合并 | 缺统一 artifact quality / contract / stage gate 诊断面板 | 已消化为 Artifact / Workflow 质量治理闭环。 |
| Workflow 入口 | 有 listing、onboarding、starter prompts；2026-06-23 已补在线 workflow 入口 preview | 仍缺自动推荐排序和更深的选择决策引导 | 入口 preview 已消化；自动推荐排序转后续体验增强候选。 |
| Run 复用 | 有历史列表、搜索、runId snapshot 恢复、复用状态筛选、当前 artifact 预览、继续原 run、复制为新 run | 跨 run 对比和收藏仍未做；不影响当前历史复用闭环 | 历史复用中心已消化；跨 run 对比 / 收藏转 P2。 |
| Workflow handoff | 有配置化 handoff 基础，已补上下文审阅卡和目标 run 输入增强 | 当前 P1 缺口已消化；后续只在新增 source/target handoff 时扩展配置 | 已完成 |
| 可观测性 | 有 success rate、provider、stage、recent turns，且已补 DeepSeek/格式化输出失败分类 drilldown 与行动建议 | 仍缺面向用户的跨 run 质量趋势和产品质量评分趋势 | 运行统计产品化已消化；跨 run 趋势转后续增强候选。 |
| 平台扩展 | manifest 已承载核心配置；workflow schema dry-run 已提供本地同步门禁 | 缺完整 scaffold/codegen 和 prompt/template 版本管理 | prompt/template 版本管理和 dry-run 门禁已消化；完整 scaffold/codegen 转 P2。 |

## 增强机会清单

| ID | 增强点 | 类型 | 类别 | 复杂度 | 历史优先级 | 当前处理结论 |
| --- | --- | --- | --- | --- | --- | --- |
| E01 | Workflow 入口 preview | 改造现有功能 | 体验 | S | 历史 P0 | 已消化：每个在线 workflow 展示适用/不适用、输入要求、预期产物和样例输入 |
| E02 | 阶段缺失信息清单 | 深化现有功能 | 专业内容 | S | 历史 P0 | 已消化：共享 artifact quality summary 派生缺失信息项，chat 和 artifact 审阅区都能标明缺失项、阻断性和用户下一步 |
| E03 | Artifact 质量诊断面板 | 深化现有功能 | 可信质量 | M | 历史 P0 | 已消化：共享 ArtifactPane 审阅面板展示 headings、visual、stage gate、专业字段和现有 visual diagnostic 的通过/失败/警告；2026-06-24 已合流到 workflow 质量治理基线 |
| E04 | Lisa 测试资产质量闭环 | 深化现有功能 | 专业内容 | M | 历史 P0 | 已消化：测试资产集合输出统一 `qualitySummary`，资产中心和 Header 展示质量状态/gate，issue、测试点覆盖、风险生命周期动作会推动质量状态变化 |
| E05 | 章节级重生成 | 新增功能 | 功能 | M | 历史 P1 | 已消化为 Artifact 定向修订闭环：用户可从章节侧栏指定未锁定章节重生成，复用共享 typed SSE runtime，客户端只合并目标章节，保留锁定章节和非目标章节，并写入 artifact/stage/history |
| E06 | Run 历史中心增强 | 深化现有功能 | 功能 | M | 历史 P1 | 已消化：支持继续、复制为新 run、按 workflow/复用状态筛选、预览当前 artifact |
| E07 | Workflow handoff 增强 | 深化现有功能 | 平台扩展 | M | 历史 P1 | 已消化：handoff 展示来源版本、关键摘要、未确认项和目标 workflow 输入，并用同一增强 prompt 创建目标 run |
| E08 | 工作流质量评分 | 新增功能 | 可信质量 | M | 历史 P1，规则型已完成 | 已消化规则型质量治理闭环：每个 stage 有质量分、证据明细和待处理项；后续仅保留跨 run 趋势和 LLM judge evidence |
| E09 | 运行统计产品化 | 深化现有功能 | 可信质量 | M | 历史 P1 | 已消化：运行统计返回 contract retry 原因和确定性诊断建议，Header modal 展示行动建议；跨 run 质量趋势可并入后续厚切片 |
| E10 | 专业方法库配置 | 新增功能 | 专业内容 | L | 历史 P2 | 已消化：专业方法库通过 `professional_methods.json` 统一配置，代表性 stage 通过 `methodIds` 引用 FMEA、测试金字塔、JTBD、RICE、Kano、CAPA、ICE，并由 prompt builder 注入系统提示；同步测试阻止未知方法引用 |
| E11 | Prompt/template 版本管理 | 新增功能 | 平台扩展 | L | 历史 P2 | 已消化：每个 online stage 通过 `promptTemplateVersion` 记录 prompt/template 版本，并通过 `regressionSampleIds` 关联 `prompt_regression_samples.json` 中的回归样例；同步测试阻止漏版本、未知样例和样例指向错误 |
| E12 | Workflow schema dry-run/scaffold | 新增功能 | 平台扩展 | L | 历史 P2，诊断门禁已完成 | 已消化诊断型 dry-run 门禁：新 workflow 缺 manifest、前端 prompt/template 映射、后端 contract、artifact_data renderer/readiness、handoff 或 manifest 打包任一面时本地 dry-run 失败；完整 scaffold/codegen 保留后续 |
| E13 | Alex 用户故事拆解 workflow | 已消化 | 专业内容 | M | 历史 P0 | 2026-06-24 已在本分支主线化：共享 workflow `STORY_BREAKDOWN`、slug `story-breakdown`、四阶段 `artifact_data` renderer、story-map visual contract、Alex 在线入口和 Lisa handoff 均已接入；验证覆盖 backend contract/runtime/renderer/sync/handoff 与 frontend workflow/prompt tests |
| E14 | Alex PRD 质量评审与补全 workflow | 已消化 | 专业内容 | M | 历史 P0 | `PRD_REVIEW` 作为 Alex 在线 workflow 复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract 和 artifact_data renderer，覆盖输入盘点、质量评审、补全建议和修订蓝图 |

## Goal Mode 消化记录

- 2026-06-23: 已完成 Alex `PRD_REVIEW` 质量评审与补全 workflow 主线化切片。新增 `prd-review` 在线入口、4 个阶段 prompt/template、manifest artifact/visual contract、后端 `artifact_data` schema/renderer、runtime structured output instruction 和前后端同步测试。该切片不新增 Alex 专属 runtime、API path、store 或 renderer pipeline。
- 2026-06-23: 已完成 Artifact 审阅诊断中心厚切片，合并消化 E02 当前 artifact 审阅侧缺失信息清单和 E03 Artifact 质量诊断面板。新增前端共享诊断核心，从 `workflow_manifest.json` 读取当前阶段 artifact/visual contract，结合当前 Markdown 与现有 runtime visual diagnostics，在右侧产物审阅面板展示 required headings、Mermaid、structured visual、stage gate、运行时可视化警告、待澄清/开放/未确认/阻断信息和下一步。该切片不新增 agent 专属 runtime、API path、store 或 renderer pipeline；不纳入自动修复、LLM judge、跨 run 趋势或 Lisa 测试资产闭环。
- 2026-06-23: 已完成 Lisa 测试资产质量闭环厚切片，消化 E04。后端 `TestAssetCollection` 增加由持久化 issue 状态、测试点覆盖和风险生命周期计算的 `qualitySummary`；前端 service 严格解析该 contract；资产中心和 Header 快捷面板展示统一质量状态与 gate；确认/忽略 issue、保存测试点、保存风险会推动质量状态变化。该切片复用现有测试资产 API、持久化模型和共享 UI，不新增 Lisa 专属 runtime、API path、store 或 renderer。
- 2026-06-24: 已完成 Run 历史复用中心厚切片，消化 E06。后端 run list 返回并过滤 `reuseStatus=ready|needs_artifact|failed`，新增共享 `POST /api/agent/runs/<run_id>/clone` 复制源 run 的 messages、当前 artifacts 和 context summaries 为独立 active run；前端 service 严格解析复用状态并提供 clone API；Header 历史会话升级为可筛选、可预览当前 artifact、可继续原 run、可复制为新 run 的复用中心，并展示预览/复制失败反馈。该切片复用现有 run persistence、snapshot restore、共享 Header UI 和 workflow registry，不新增 agent 专属 runtime、API path、store 或 renderer。
- 2026-06-24: 已完成 Workflow handoff 上下文审阅闭环厚切片，消化 E07。后端 `workflow_handoffs.py` 从 source artifact 生成 `sourceSummary`、`unconfirmedItems` 和 `targetInputChecklist`，增强 prompt 并持久化为目标 run 第一条 user message；前端 service 严格解析该 contract，ChatPane 在跨智能体接力卡片展示来源版本、摘要、未确认项和目标输入检查项，store 继续复用共享 handoff 应用路径。验证命令包括后端 handoff/API pytest、前端 handoff service/ChatPane/store Vitest、前端 lint 和 `git diff --check`。
- 2026-06-24: 已完成 Artifact 定向修订闭环厚切片，消化 E05。ArtifactPane 章节侧栏增加未锁定章节重生成动作；`useChatService` 新增 `handleRegenerateArtifactSection()`，通过现有共享 `generateResponseStream` / `/api/agent/runs/stream` typed SSE 发起定向修订 prompt；前端共享 `artifactSections` helper 负责 H1-H3 章节 anchor、锁定匹配、锁定保护和目标章节合并。模型仍返回完整 artifact，但客户端只接收目标章节内容，非目标章节保持原样，锁定章节按锁快照恢复，成功后写入 `artifactContent`、`stageArtifacts` 和 `artifactHistory`。该切片不新增后端 runtime、API path、store 或 renderer。
- 2026-06-24: 已完成 Workflow schema dry-run 工程信任闭环，消化 E12 的诊断门禁部分。新增 `scripts/validation/new_agents_workflow_dry_run.py`，从真实仓库事实聚合检查 shared `workflow_manifest.json`、前端 `STAGE_CONTENT_BY_TEMPLATE_ID` 与 prompt 文件、后端 `WORKFLOW_STAGES` / artifact contract、DeepSeek `artifact_data` readiness、renderer stage keys、handoff prompt 和 manifest 打包/挂载；旧 workflow contract sync 测试复用同一 loader，不再维护独立 prompt 文件硬编码表。该切片不新增 runtime、API、store、renderer 或真实 LLM 调用；完整 scaffold/codegen、LLM judge evidence 保留为后续候选。

### 2026-06-24: E03/E08 Artifact/Workflow 质量治理闭环

- Milestone: 在现有 `ArtifactPane` 审阅入口合并消化 E03 Artifact 质量诊断面板与 E08 工作流质量评分。
- 能力增量: 当前 stage artifact 可显示质量分、通过/警告/失败统计、headings / visual / stage gate / visual diagnostic 证据和待处理项，并在最终集成中合流 E02 缺失信息清单。
- 实现边界: 前端确定性质量模型 `workflowQuality.ts` + `ArtifactPane` 审阅抽屉展示；不新增后端 API、runtime、SSE、持久化模型或 agent 专属 renderer。
- 验证: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/workflowQuality.test.ts src/components/__tests__/ArtifactPane.test.tsx`，143 passed。
- 验证: `cd tools/new-agents/frontend && npm run lint`，TypeScript check passed。
- 未覆盖: LLM judge 语义评分、跨 run 质量趋势和完整 scaffold/codegen，分别保留为后续派生候选。

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
- `PRD_REVIEW`: 已消化为 Alex 在线 workflow；后续可作为 `STORY_BREAKDOWN` 或 Lisa `REQ_REVIEW` 的上游输入。
- `STORY_BREAKDOWN`: 已消化为 Alex 在线 workflow；后续可作为 Lisa `TEST_DESIGN` 或 `REQ_REVIEW` 的上游输入。

建议首批 Alex 切片:

1. 已完成：`PRD_REVIEW` PRD 质量评审与补全 workflow。
2. 已完成：`STORY_BREAKDOWN` 用户故事拆解 workflow。
3. VALUE_DISCOVERY/BLUEPRINT 质量门禁和 handoff 输入强化；handoff 输入强化已消化，后续只扩展到更多 source/target 组合或质量评分联动。
4. IDEA_BRAINSTORM/CONVERGE 评分口径和验证实验闭环。

## 推荐路线

### A. 快速专业化路线

目标: 1-2 周内明显提升专业感和产出可信度。

包含: E01/E02/E03/E04/E05/E07/E08 规则型治理闭环/E13/E14 均已在 2026-06-23 目标模式切片中消化。快速专业化路线剩余工作转入 E08 跨 run 趋势/LLM judge、E12 完整 scaffold/codegen、prompt/template 版本管理和 DeepSeek 真实 smoke 等 P1/P2 能力包；运行统计产品化当前 DeepSeek/格式化失败诊断闭环已消化。

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

包含: E03、E05、E06、E07、E08；其中 E03、E05、E06、E07、E08 规则型治理闭环已消化，后续功能闭环路线只保留 E08 跨 run 质量趋势、跨 run 对比或收藏等新厚切片候选。

暂不做:

- intent-tester 联动增强。
- 跨团队权限/分享模型。

验证:

- run snapshot API/service tests。
- artifact edit/conflict/collaboration tests。
- workflow handoff backend/frontend tests。

### C. 平台化路线

目标: 让后续新增 agent/workflow 更低成本、更可靠。

包含: E09、E10、E11、E12；其中 E09 运行统计诊断建议、E10 专业方法库配置、E11 Prompt/template 版本管理和 E12 诊断型 workflow schema dry-run 门禁均已消化。后续平台化重点转向 E12 完整 scaffold/codegen、跨 run 质量趋势和 LLM judge evidence。

暂不做:

- 一次性迁移所有 prompt/template。
- agent-specific API/store/render pipeline。

验证:

- workflow manifest schema negative tests。
- config sync tests。
- prompt registry tests。
- 可选 LLM judge evidence 管理。

## 首批建议落地切片

### 1. 阶段缺失信息清单

- 涉及模块: `artifactQuality.ts`、`ArtifactPane.tsx`、`ChatPane.tsx`、相关 frontend tests。
- 完成定义: 已在 2026-06-23 本轮消化，并在最终集成中与 workflow 质量治理面板合流。当前阶段 artifact 缺少标题、专业字段、visual、stage gate 决策或存在 visual diagnostic 时，共享诊断层会派生缺失信息项；Artifact 审阅面板和 ChatPane 左侧提示都展示缺失项、阻断/提醒和下一步动作。
- 验证记录: 新增 `artifactQuality.ts` 纯函数测试、`ArtifactPane` 组件测试和 `ChatPane` 组件测试。
- 不纳入: 自动修复全文、质量评分、趋势分析。

### 2. Artifact 质量诊断面板

- 状态: 已在 2026-06-23 Artifact 审阅诊断中心切片中消化，且与 E02 当前 artifact 审阅侧缺失信息清单合并为一个用户可见厚切片。
- 涉及模块: `ArtifactPane.tsx`、`StructuredVisual.tsx`、`agent_contracts.py`、`workflow_contract_registry.py`、相关 tests。
- 需要同步: manifest artifact/visual contract、前端诊断展示、后端 contract helper。
- 完成定义: 已在 2026-06-24 「Artifact/Workflow 质量治理闭环」中前端确定性消化：当前阶段 artifact 能在审阅抽屉展示必填标题、可视化、阶段门禁、专业字段的通过/失败/警告，并与 E08 质量评分合并呈现。
- 验证记录: 新增 `artifactQuality.ts` 纯函数测试和 `ArtifactPane` 组件测试；保留后端 manifest artifact contract registry 基线，并在 E03/E08 合流后由 workflow quality tests 覆盖质量分、证据和待处理项。
- 不纳入: 自动修复全文。

### 3. Workflow 入口专业 preview

- 涉及模块: `workflow_manifest.json`、`AgentSelect.tsx`、`WorkflowSelect.tsx`、`agentWorkflows.ts`、onboarding tests。
- 需要同步: listing、onboarding、starter prompts、workflow slug tests。
- 完成定义: 用户进入工作区前能判断 workflow 是否适合当前目标。
- 不纳入: 自动 workflow 推荐排序。

### 4. Lisa 测试资产质量闭环

- 状态: 已在 2026-06-23 目标模式切片中消化。
- 涉及模块: `test_assets.py`、`routes_test_assets.py`、`testAssetService.ts`、`Header.tsx`。
- 需要同步: TEST_DESIGN/CASES artifact contract、资产 issue schema、前端资产 modal。
- 完成定义: 测试点、风险、用例 issue 可处理，并通过持久化集合 `qualitySummary` 统一影响资产质量状态。
- 不纳入: 新增 intent-tester 联动或自动执行。
- 后续不再作为活跃候选重复选择；只在发现当前代码回归、真实 Lisa 输出 contract 失配，或需要接入跨 run 质量趋势时作为维护项处理。

### 5. 历史会话复用增强

- 涉及模块: `run_persistence.py`、`routes.py`、`runSnapshotService.ts`、`Header.tsx`。
- 需要同步: run list response、snapshot restore、store reset/clone 行为。
- 完成定义: 历史 run 可复制为新 run、继续、预览 artifact，并按 workflow/质量状态筛选。
- 不纳入: 多用户分享权限。

### 6. Handoff 上下文强化

- 状态: 已在 2026-06-24 目标模式切片中消化。
- 涉及模块: `workflow_manifest.json`、`workflow_handoffs.py`、Alex blueprint prompt/template、`ChatPane.tsx`。
- 需要同步: handoff prompt template、target workflow/stage、context truncation policy。
- 完成定义: handoff 明确来源版本、关键摘要、未确认项、目标输入检查项和目标用途，并用同一增强 prompt 启动目标 run。
- 不纳入: 新 runtime 分支。
- 后续不再作为活跃候选重复选择；只在需要新增更多 workflow source/target 组合、接入质量评分或发现 handoff contract 回归时作为维护项处理。

## 已消化记录

### 2026-06-24 E09 运行统计产品化诊断建议

- Milestone: 运行统计产品化诊断闭环。
- 消化范围: E09「运行统计产品化」中的 contract retry 原因、provider/config 问题、低成功率和 stage 集中失败行动建议。
- 代码结果:
  - 后端 `/api/agent/observability` 继续复用现有 run metric persistence，新增 `contractRetryReasons` 和 `diagnostics` 字段。
  - 前端 observability service 严格解析新增字段，malformed diagnostics 明确失败。
  - Header「运行统计」modal 展示“诊断建议”、每条 action 和 contract retry reason badge。
- 非目标: 不新增 observability API path，不改 Agent Runtime、typed SSE、run/artifact 持久化模型，不做真实模型 smoke。
- 计划与 spec:
  - `docs/superpowers/specs/2026-06-24-runtime-observability-actions-design.md`
  - `docs/superpowers/plans/2026-06-24-runtime-observability-actions.md`

### 6. Alex 用户故事拆解 workflow

- 涉及模块: `workflow_manifest.json`、`frontend/src/core/workflows.ts`、`frontend/src/core/config/agentWorkflows.ts`、`frontend/src/core/prompts/`、`backend/agent_contracts.py`、`backend/artifact_data_renderers.py`、相关前后端测试。
- 需要同步: workflow slug `story-breakdown`、Alex workflow listing、stage prompts、artifact required headings、structured visual contract、backend stage contract、frontend route/workflow tests。
- 建议阶段: 需求输入解析、Epic 拆分、User Story 与验收标准、Sprint 切片与交付包。
- 产出物: Epic map、User Story backlog、AC 表、依赖/风险清单、Sprint 切片建议、Lisa handoff 输入。
- 完成定义: 用户输入需求蓝图或 PRD 后，可通过共享 `/api/agent/runs/stream` 生成可进入研发评审的用户故事包，并能继续交给 Lisa 做测试设计或需求评审。
- 不纳入: Jira/禅道等外部项目管理工具写入。

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

## 当前剩余能力包

功能能力包已清空；后续进入最终集成、主线验证、merge/push/删分支闭环。

其余 E 编号如果需要恢复，必须先通过 CGA 证明当前主线仍存在回归、未验收缺口或用户重新定义目标。当前 E01-E14 不再作为活跃实现清单；后续只围绕验证回归、CI 失败、完整 scaffold/codegen、跨 run 质量趋势或 LLM judge evidence 等重新定义的厚切片继续演进。

## 进入实现前需要补的设计问题

- Artifact 质量诊断应完全前端解析，还是后端提供只读 diagnostic endpoint。
- 质量评分是否先做规则型 gate，再引入 LLM judge evidence。
- 历史 run “复制为新 run”已在 E06 中裁决为复制 messages、当前 artifact versions 和 context summaries；协作批注、章节锁、审计事件、turn metrics 和测试资产不自动复制。
- Handoff prompt 是否继续使用单模板，还是在 manifest 中声明 handoff 输入字段和摘要策略。
- 专业方法库配置是否纳入 manifest，还是先建独立 registry 后再合并。
