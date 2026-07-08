# New Agents 全工作流真实 partial artifact streaming 纵切路线

- 状态：第 1-7 轮已完成；17 个在线阶段已具备确定性 partial artifact streaming 证据，稳定 API / TESTING 文档和证据归档已收口；Lisa 可选 LLM judge 64 分质量门失败已修复并通过 80 分门槛；2026-07-08 真实 SSE 复核已修复 artifact-data 阶段先输出 `chat` 导致右侧产物晚刷的问题，`VALUE_DISCOVERY/ELEVATOR` 本地真实 SSE 已验证提前递增，`IDEA_BRAINSTORM/DEFINE` 已验证提前递增但该次真实模型样本最终未过 DEFINE 数据一致性 contract
- 创建日期：2026-07-07
- 来源：用户要求系统性检查 New Agents 产出是否都能流式渲染，并确认后续应按纵切目标推进
- 优先级：P0
- 相关模块：`tools/new-agents/`

## 背景

2026-07-07 代码审查和聚焦测试确认：

- `/api/agent/runs/stream`、后端 SSE、Nginx 反代、前端 `generateResponseStream()`、`chatService` 和 Zustand 状态更新链路都支持流式传输与逐 chunk 写入。
- 5 个在线 workflow、17 个阶段都支持最终 `artifact_data -> Markdown` 确定性渲染。
- 只有 `TEST_DESIGN/CLARIFY` 和 `TEST_DESIGN/STRATEGY` 支持后端在完整 `artifact_data` 对象闭合前，基于已完成顶层成员生成正式 partial artifact delta。
- 其余 15 个阶段仍主要依赖完整 `artifact_data` 闭合后的 artifact delta，或前端对最终文档做 synthetic reveal；这不等价于真实段落级 partial artifact streaming。

用户明确指出：后续不应按“先契约、再 renderer、再验证”的横切方式推进，而应按用户可感知工作流纵切，每轮打通一个可验收能力闭环。

## 总体目标

让 New Agents 所有在线 workflow 的右侧正式产出物都具备真实 partial artifact streaming 能力：模型按 `artifact_data` 字段顺序流式输出时，后端能在已完成字段闭合后生成正式 Markdown delta，前端实时写入右侧 ArtifactPane，最终 `agent_turn` 仍通过完整 contract、持久化和下游消费校验。

该能力必须继续复用共享 Agent Runtime、typed SSE、`workflow_manifest.json`、artifact contract、run persistence、共享前端 store 和共享 ArtifactPane 渲染基础设施。不得新增 Lisa、Alex、workflow 或 stage 专属 runtime、API path、transport、store 或 bespoke rendering pipeline。

## 目标轮数声明

基线按 7 个目标模式轮次推进。每轮都是纵向切片，必须从后端 partial renderer 到前端消费、测试、文档和必要真实 smoke 形成闭环。

| 轮次 | 目标模式用户故事 | 覆盖阶段 | 交付边界 |
|---|---|---|---|
| 第 1 轮 | Lisa 测试用例集真实 partial streaming 闭环 | `TEST_DESIGN/CASES` | 用户生成测试用例集时，右侧用例统计、设计依据、用例清单、测试数据、自动化候选、覆盖追溯等章节能随已完成 `artifact_data` 字段逐步出现；最终用例集仍可被测试资产解析。 |
| 第 2 轮 | Lisa 测试设计交付文档真实 partial streaming 闭环 | `TEST_DESIGN/DELIVERY` | 用户生成交付文档时，执行摘要、需求摘要、策略摘要、用例摘要、覆盖地图、开放风险、验收和签署章节能逐步出现；最终文档仍通过 delivery contract 和导出相关回归。 |
| 第 3 轮 | 需求评审 workflow 真实 partial streaming 闭环 | `REQ_REVIEW/REVIEW`, `REQ_REVIEW/REPORT` | 用户完成需求深度评审和评审报告时，问题清单、质量总览、问题统计、修订建议、评审结论、关闭清单和优先级看板能逐步出现；两个阶段都保留完整 contract 校验。 |
| 第 4 轮 | 故障复盘 workflow 真实 partial streaming 闭环 | `INCIDENT_REVIEW/TIMELINE`, `INCIDENT_REVIEW/ROOT_CAUSE`, `INCIDENT_REVIEW/IMPROVEMENT` | 用户复盘故障时，事件还原、事实来源、时间线、5-Why、鱼骨图、根因结论、改进措施和行动看板能逐步出现；最终复盘报告仍可稳定渲染 Mermaid 与 ai4se-visual。 |
| 第 5 轮 | 创意脑暴 workflow 真实 partial streaming 闭环 | `IDEA_BRAINSTORM/DEFINE`, `IDEA_BRAINSTORM/DIVERGE`, `IDEA_BRAINSTORM/CONVERGE`, `IDEA_BRAINSTORM/CONCEPT` | 用户从问题域到产品概念的每个阶段都能看到右侧产出逐步增长；mindmap、quadrantChart、pie/flowchart 和 mvp-map 不因 partial 渲染破坏最终 contract。 |
| 第 6 轮 | 价值发现 workflow 真实 partial streaming 闭环 | `VALUE_DISCOVERY/ELEVATOR`, `VALUE_DISCOVERY/PERSONA`, `VALUE_DISCOVERY/JOURNEY`, `VALUE_DISCOVERY/BLUEPRINT` | 用户做价值定位、画像、旅程和需求蓝图时，右侧产出物按已完成结构化字段逐步出现；Alex 到 Lisa handoff 所需蓝图内容仍完整可用。 |
| 第 7 轮 | 全工作流 streaming 契约收口与证据归档 | 17 个在线阶段 | 更新契约文档、覆盖矩阵、测试说明和目标模式记录；用自动化与代表性真实 SSE smoke 证明 17 个阶段的 partial/final 行为边界清晰。 |

## 轮次拆分规则

- 默认按上表执行，不跨 workflow 合并目标。
- 第 1、2 轮不得再拆薄，除非遇到当前代码无法自行裁决的架构冲突。
- 第 3 至 6 轮如果 CGA 证明单轮会同时触达 8 个以上源文件、预计超过约 800 行改动、或无法在一个目标模式轮次内形成稳定验证，可以拆成带字母后缀的子轮次，例如 `第 4a 轮 TIMELINE`、`第 4b 轮 ROOT_CAUSE`、`第 4c 轮 IMPROVEMENT`。
- 子轮次只允许缩小同一 workflow 内的阶段范围，不允许把后续 workflow 提前混入。
- 第 7 轮必须在所有实现轮次完成后执行，不得提前用文档更新替代真实阶段闭环。

## 每轮必须完成的工作

每个目标模式轮次都必须按 `docs/strategy/goal-mode-playbook.md` 执行：

1. 读取 `AGENTS.md`、目标模式手册、相关架构/API/测试文档、当前 todo 和对应阶段代码。
2. 输出完整 Current State Gap Analysis；若本轮是已确认目标轮次的连续执行，按 `docs/strategy/goal-mode-playbook.md` 输出目标承接检查。
3. 写中文 spec 和 implementation plan。
4. 按 TDD 补 failing tests，再实现最小 partial renderer 与消费链路改动。
5. 验证后端 runtime 可在 final `agent_turn` 前产生多个递增长度的 `agent_delta.output.artifact_update.replace.markdown`。
6. 验证前端 `llm.ts`、`chatService` 和 store 会消费这些 delta，不把它们压成最终一次性写入。
7. 验证最终 artifact 仍通过完整 artifact contract、Mermaid / ai4se-visual contract 和相关下游解析。
8. 更新必要文档，记录本轮真实覆盖和残余风险。

## 每轮验收口径

- 至少一个后端 raw JSON streaming 测试证明 final 前出现多个正式 artifact delta，且 artifact markdown 长度递增或章节递增。
- 至少一个 partial renderer 测试证明已闭合 `artifact_data` 顶层字段能渲染正式 Markdown 章节，不输出进度页、裸 JSON 或调试占位。
- 至少一个完整 renderer / contract 测试证明最终 artifact 仍满足当前阶段必需标题、字段、Mermaid 和 ai4se-visual 要求。
- 前端 SSE 解析或 chat service 测试证明 artifact delta 会实时更新 `artifactContent`。
- 涉及 Lisa 测试资产、handoff、导出或可视化下游时，必须跑对应下游测试。
- 如果环境具备本地默认模型配置，至少对本轮代表阶段执行一次真实 `/new-agents/api/agent/runs/stream` smoke，并记录 `agent_delta` 数量、artifact 长度序列、最终 snapshot 或 contract 结果。

## 非目标

- 不追求逐 token 或逐字打字机效果；目标是段落级或章节级正式产物增量。
- 不用固定延迟、假进度条或 synthetic reveal 冒充真实 partial artifact streaming。
- 不为某个 workflow 新增独立 runtime、SSE endpoint、store 或 UI 渲染管线。
- 不在缺少 contract 和下游验证时只补一个 renderer helper 后归档。
- 不把第 7 轮的文档收口提前当作实现完成。

## 当前事实快照

已完成真实 partial artifact streaming：

- `TEST_DESIGN/CLARIFY`
- `TEST_DESIGN/STRATEGY`
- `TEST_DESIGN/CASES`
- `TEST_DESIGN/DELIVERY`
- `REQ_REVIEW/REVIEW`
- `REQ_REVIEW/REPORT`
- `INCIDENT_REVIEW/TIMELINE`
- `INCIDENT_REVIEW/ROOT_CAUSE`
- `INCIDENT_REVIEW/IMPROVEMENT`
- `IDEA_BRAINSTORM/DEFINE`
- `IDEA_BRAINSTORM/DIVERGE`
- `IDEA_BRAINSTORM/CONVERGE`
- `IDEA_BRAINSTORM/CONCEPT`
- `VALUE_DISCOVERY/ELEVATOR`
- `VALUE_DISCOVERY/PERSONA`
- `VALUE_DISCOVERY/JOURNEY`
- `VALUE_DISCOVERY/BLUEPRINT`

待按目标轮次补齐：

- 无实现阶段剩余；第 7 轮收口全工作流 streaming 契约与证据归档。

## 2026-07-08 真实 SSE 复核修正

- 触发：用户在本地 UI 观察到价值发现和头脑风暴右侧产出物仍像一次性刷新。
- 根因：结构化输出指令要求顶层 JSON 先输出 `chat` 再输出 `artifact_data`；真实模型会先完整生成 chat，导致后端 partial renderer 很晚才看到可渲染的 `artifact_data` 字段。
- 修复：`tools/new-agents/backend/agent_runtime.py` 对所有 17 个 artifact-data 阶段生成 `artifact_data`、`chat`、`stage_action`、`warnings` 的顶层顺序；`IDEA_BRAINSTORM/DEFINE` 额外补强 root-problem 覆盖提示。
- 验证：
  - 修复前 `VALUE_DISCOVERY/ELEVATOR` 真实 SSE：first artifact 17.03s，final 17.20s，长度 `[3634, 3634, 3634]`。
  - 修复前 `IDEA_BRAINSTORM/DEFINE` 真实 SSE：first artifact 16.94s，final 17.13s，长度 `[2817, 2817, 2817]`。
  - 修复后 `VALUE_DISCOVERY/ELEVATOR` 真实 SSE：first artifact 3.49s，final 21.13s，长度 `252 -> 637 -> 926 -> 1316 -> 1588 -> 1857 -> 2754 -> 3041 -> 3146 -> 3240`。
  - 修复后 `IDEA_BRAINSTORM/DEFINE` 真实 SSE：first artifact 2.24s，长度先后递增到 2326；该真实模型样本随后重试并再次递增到 2302，但最终因 root-problem 覆盖不满足 contract 返回 `SCHEMA_VALIDATION_FAILED`。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming tools/new-agents/backend/tests/test_agent_runtime.py::test_idea_define_structured_output_instruction_explains_root_problem_coverage -q`：18 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q`：318 passed。
  - `bash scripts/health/health_check.sh local`：后端重启后所有本地健康检查通过。
- 限制：后续真实外部模型复测被权限审查拦截，原因是会向外部模型端点发送仓库 workflow prompt 和 contract 指令；若要继续用真实模型证明 IDEA 最终 contract 成功，需要用户明确批准该外部调用。

## 目标模式执行记录

### 第 1 轮：Lisa 测试用例集真实 partial streaming 闭环

- 状态：已完成确定性验证；后续质量门修复已关闭 Lisa 可选 LLM judge 64 分失败。
- 设计与执行要点：已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
- 覆盖阶段：`TEST_DESIGN/CASES`
- 交付：后端可基于已闭合 `artifact_data` 顶层字段生成正式《测试用例集》partial artifact delta，包含用例统计、用例设计依据等递增章节；最终 artifact 仍通过完整 contract，并可解析为 Lisa 测试资产。
- 聚焦验证：
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_builds_formal_incremental_markdown_and_patch -q`：1 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data -q`：3 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_test_assets.py -q`：226 passed。
  - `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx`：140 passed。
- 全量验证：
  - `./scripts/test/test-local.sh all`：沙箱内失败，失败点为 MidScene proxy 端口绑定 `EPERM` 和 Playwright Chromium `bootstrap_check_in ... Permission denied`。
  - `./scripts/test/test-local.sh all` 非沙箱重跑曾通过一次。关键结果包括 Intent Tester API 294 passed、MidScene Proxy 17 passed、Common Frontend lint/build 通过、New Agents Frontend 696 passed、New Agents Backend 515 passed、New Agents Browser E2E 6 passed。
  - 最终文件状态下再次运行默认 `./scripts/test/test-local.sh all` 时，确定性模块通过，但可选 `test_lisa_final_artifact_passes_optional_llm_judge` 曾失败；LLM judge 评分 64，问题集中在最终用例质量覆盖不足、最终 artifact 缺少 `traceability-matrix`、部分用例缺少具体测试数据 / 环境细节。该质量门失败已在后续“Lisa LLM judge 质量门修复记录”中关闭。
  - 最终文件状态下运行 `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`：通过。关键结果包括 Intent Tester API 294 passed、MidScene Proxy 17 passed、Common Frontend lint/build 通过、New Agents Frontend 696 passed、New Agents Backend 515 passed、New Agents Browser E2E 3 passed / 3 skipped / 9 deselected。
- 残余风险：真实模型 smoke 取决于本地默认模型配置、网络和额度；本轮当前证据为确定性 mock raw JSON streaming 与前端 typed SSE 回归。Lisa 最终产物质量 judge 失败已单独修复，不再作为本轮开放风险保留。
- 下一轮候选：第 2 轮 `TEST_DESIGN/DELIVERY`。因目标和阶段顺序已经写入本文件，后续恢复时应先做目标承接检查；只有出现新 P0/P1、失败证据、架构冲突或需要拆分/合并时才恢复完整 CGA。

### 第 2 轮：Lisa 测试设计交付文档真实 partial streaming 闭环

- 状态：已完成确定性验证。
- 设计与执行要点：已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
- 覆盖阶段：`TEST_DESIGN/DELIVERY`
- 交付：后端可基于已闭合 `artifact_data` 顶层字段生成正式《测试设计文档》partial artifact delta，包含执行摘要、需求分析摘要、测试策略摘要等递增章节；最终 artifact 仍通过完整 DELIVERY contract，并保留 `coverage-map`。
- 聚焦验证：
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_delivery_artifact_data_builds_formal_incremental_markdown_and_patch -q`：1 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output -q`：1 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output -q`：4 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_test_assets.py -q`：227 passed。
  - `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx`：140 passed。
- 全量验证：
  - `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`：通过。关键结果包括 Intent Tester API 294 passed、MidScene Proxy 17 passed、Common Frontend lint/build 通过、New Agents Frontend 696 passed、New Agents Backend 516 passed / 1 deselected、New Agents Browser E2E 3 passed / 3 skipped / 9 deselected。
- LLM judge：后续质量门修复已将 Lisa 可选 judge 断言提升到 80 分，并通过 `test_lisa_final_artifact_passes_optional_llm_judge`。该测试通过即证明外部 judge verdict 满足 `score >= 80`；pytest 未打印具体分数，额外直接打印 verdict 的外部调用被权限审查拒绝，因此只记录“通过 80 分门槛”。
- 残余风险：本轮证明 DELIVERY 确定性 partial streaming 链路；真实模型 smoke 仍取决于本地模型配置、网络、额度和 judge 可用性。
- 下一轮候选：第 3 轮 `REQ_REVIEW/REVIEW` 与 `REQ_REVIEW/REPORT`。因目标和阶段顺序已经写入本文件，后续恢复时应先做目标承接检查；若 LLM judge 质量失败被纳入当前目标，则必须先按 80 分门禁分析并修复相关差距。

### Lisa LLM judge 质量门修复记录

- 状态：已完成。
- 触发原因：默认启用可选 LLM judge 时，`test_lisa_final_artifact_passes_optional_llm_judge` 返回 Lisa 质量评分 64，低于 playbook 80 分门槛。
- 差距归因：
  - Lisa 浏览器 E2E 固定样本 `TEST_DESIGN/CASES` 统计和用例明细不一致，缺少空值、边界值、降级、并发登录、安全审计、性能和可观测性覆盖。
  - `TEST_DESIGN/DELIVERY` 最终交付只包含 `coverage-map`，缺少最终 `traceability-matrix`，导致 judge 认为需求、风险、测试点和用例追溯不足。
  - 部分用例缺少明确测试数据、环境和非功能验收细节。
  - judge 执行断言仍是 70/75 分旧门槛，未与 playbook 的 80 分要求同步。
- 修复：
  - `tests/e2e/new_agents_browser/llm_judge.py`：统一 LLM artifact / handoff judge 最低分为 80。
  - `tests/e2e/new_agents_browser/sse_mock.py`：将 Lisa 登录支付样本扩展为 12 条可评审用例，补齐空值、边界、第三方登录降级、弱网降级、并发登录、并发支付、独立安全审计、性能基线和可观测性证据。
  - `tools/new-agents/backend/artifact_data_renderers.py`：从 DELIVERY `coverage_map` 派生最终 `traceability-matrix`，保持共享结构化 renderer，不新增 Lisa 专属链路。
  - `tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/workflow_manifest.json`、`tools/new-agents/frontend/src/core/prompts/test_design/delivery.ts`：同步 DELIVERY visual contract / prompt，要求 `coverage-map` 与 `traceability-matrix` 同时存在。
- 质量门验证：
  - `.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py::test_lisa_final_artifact_passes_optional_llm_judge -q`：1 passed；该测试现在强制 `score >= 80`。
  - `.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py::test_alex_final_artifact_passes_optional_llm_judge tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py::test_alex_to_lisa_handoff_passes_optional_llm_judge -q`：2 passed；公共 80 分门槛未破坏 Alex 与 Alex->Lisa handoff judge。
- 回归验证：
  - `.venv/bin/python -m pytest tests/e2e/new_agents_browser/test_llm_judge.py tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py::test_lisa_test_design_mock_fixture_covers_judge_feedback_gaps -q`：11 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q`：268 passed。
  - `cd tools/new-agents/frontend && npm run test -- --run src/core/prompts/__tests__/testDesignDeliveryPrompt.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx`：44 passed。
  - `NEW_AGENTS_E2E_LLM_JUDGE=0 .venv/bin/python -m pytest tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py tests/e2e/new_agents_browser/test_llm_judge.py -q`：12 passed / 1 skipped。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests -q`：517 passed / 1 skipped。
  - `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`：通过；关键结果包括 Intent Tester API 294 passed、MidScene Proxy 17 passed、Common Frontend lint/build 通过、New Agents Frontend 697 passed、New Agents Backend 517 passed / 1 deselected、New Agents Browser E2E 4 passed / 3 skipped / 10 deselected。
- 分数记录：正式 pytest 输出未打印外部 judge 具体分数；由于直接调用外部 judge 打印 verdict 被权限审查拒绝，当前记录为“通过 80 分门槛”，不记录未暴露的具体分值。

### 第 3 轮：需求评审 workflow 真实 partial streaming 闭环

- 状态：已完成确定性验证。
- 设计与执行要点：已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
- 覆盖阶段：`REQ_REVIEW/REVIEW`、`REQ_REVIEW/REPORT`
- 交付：
  - `REQ_REVIEW/REVIEW` 在 raw JSON streaming 期间可基于已闭合 `scope_items`、`quality_overview`、`issue_statistics` 等字段逐步生成正式《需求评审问题清单》artifact delta。
  - `REQ_REVIEW/REPORT` 在 raw JSON streaming 期间可基于已闭合 `conclusion`、`review_info`、`issue_statistics` 等字段逐步生成正式《需求评审报告》artifact delta。
  - 最终 REVIEW / REPORT artifact 仍通过完整 contract，并保留 `score-matrix`、Mermaid 问题统计和 `priority-board` 等可视化要求。
- 聚焦验证：
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_req_review_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_req_review_report_artifact_data_builds_formal_incremental_markdown_and_patch -q`：先失败，原因是 REQ_REVIEW partial dispatch 返回 `None`；实现后 2 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output -q`：2 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output -q`：6 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_test_assets.py -q`：229 passed。
  - `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx`：140 passed。
- 文档与全量验证：
  - `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`：通过。关键结果包括 Intent Tester API 294 passed、MidScene Proxy 17 passed、Common Frontend lint/build 通过、New Agents Frontend 697 passed、New Agents Backend 519 passed / 1 deselected、New Agents Browser E2E 4 passed / 3 skipped / 10 deselected。
- LLM judge：本轮未启用或引用新的 REQ_REVIEW LLM judge 质量门；不能据此声称 REQ_REVIEW 真实模型质量评分。若后续为需求评审增加 judge，默认门槛仍为 80 分。
- 残余风险：本轮证明 REQ_REVIEW 确定性 partial streaming 链路，不证明真实模型输出质量或外部 judge 质量；真实模型 smoke 仍取决于本地模型配置、网络和额度。
- 下一轮候选：第 4 轮 `INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/ROOT_CAUSE`、`INCIDENT_REVIEW/IMPROVEMENT`。因目标和阶段顺序已经写入本文件，后续恢复时应先做目标承接检查；如第 4 轮触达范围过大，可按本文件拆分规则拆成 `第 4a/4b/4c` 子轮次。

### 第 4 轮：故障复盘 workflow 真实 partial streaming 闭环

- 状态：已完成确定性验证。
- 设计与执行要点：已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
- 覆盖阶段：`INCIDENT_REVIEW/TIMELINE`、`INCIDENT_REVIEW/ROOT_CAUSE`、`INCIDENT_REVIEW/IMPROVEMENT`
- 交付：
  - `INCIDENT_REVIEW/TIMELINE` 在 raw JSON streaming 期间可基于已闭合 `incident_summary`、`impact_metrics`、`fact_sources`、`timeline_events` 等字段逐步生成正式《故障复盘报告》事件还原 artifact delta，并保留 Mermaid timeline。
  - `INCIDENT_REVIEW/ROOT_CAUSE` 在 raw JSON streaming 期间可基于已闭合 `analysis_context`、`why_chain`、`cause_evidence`、`fishbone_categories` 等字段逐步生成正式根因分析 artifact delta，并保留 `cause-map` 与 Mermaid mindmap。
  - `INCIDENT_REVIEW/IMPROVEMENT` 在 raw JSON streaming 期间可基于已闭合 `report_info`、`timeline_summary`、`root_cause_summary`、`priority_distribution`、`improvement_actions` 等字段逐步生成正式改进报告 artifact delta，并保留 Mermaid pie 与 `action-board`。
  - 三个阶段都继续复用共享 Agent Runtime、typed SSE、`AgentTurnOutput.artifact_patch` 和 ArtifactPane 消费链路；未新增 workflow 专属 runtime、API、store 或渲染管线。
- 聚焦验证：
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_incident_timeline_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_incident_root_cause_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_incident_improvement_artifact_data_builds_formal_incremental_markdown_and_patch -q`：先失败，原因是 INCIDENT_REVIEW partial dispatch 返回 `None`；实现后 3 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output -q`：3 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output -q`：9 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q`：292 passed。
  - `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx`：140 passed。
- 文档与全量验证：
  - `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`：通过。关键结果包括 Intent Tester API 294 passed、MidScene Proxy 17 passed、Common Frontend lint/build 通过、New Agents Frontend 697 passed、New Agents Backend 522 passed / 1 deselected、New Agents Browser E2E 4 passed / 3 skipped / 10 deselected。
- LLM judge：本轮未启用或引用新的 INCIDENT_REVIEW LLM judge 质量门；不能据此声称故障复盘真实模型质量评分。若后续为故障复盘增加 judge，默认门槛仍为 80 分。
- 残余风险：本轮当前证据为确定性 mock raw JSON streaming 与前端 typed SSE 回归；真实模型 smoke 仍取决于本地模型配置、网络和额度。
- 子智能体记录：第 4 轮执行时 playbook 尚未强制记录子智能体 / 旁路审查决策；第 5 轮起按新版规则显式记录。
- 下一轮候选：第 5 轮 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`。因目标和阶段顺序已经写入本文件，后续恢复时应先做目标承接检查；如第 5 轮触达范围过大，可按本文件拆分规则拆成同一 workflow 内的子轮次。

### 第 5 轮：创意脑暴 workflow 真实 partial streaming 闭环

- 状态：已完成确定性验证。
- 设计与执行要点：已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
- 覆盖阶段：`IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`
- 子智能体 / 旁路审查：
  - 已派发只读 explorer 复核 IDEA contract、final renderer/helper、runtime tests 和拆分风险；结论为四个阶段可作为同一 IDEA 纵切轮完成，主要风险是 `DIVERGE` 与 `CONVERGE` 的首个可视化增量依赖多个字段闭合，可能没有单 section `artifact_patch`，但不阻断 `artifact_update.replace.markdown` streaming。
  - 已派发只读 explorer 复核 Lisa judge 质量门、前端通用 artifact delta 消费和第 5 轮记录风险；结论为没有阻断第 5 轮的未关闭 P0 质量门，Lisa judge 80 分规则和前端共享消费链路一致。
  - 不派发 worker：本轮实现集中编辑同一 backend renderer 与 tests，多个 worker 会产生写入冲突。
- 交付：
  - `IDEA_BRAINSTORM/DEFINE` 在 raw JSON streaming 期间可基于已闭合 `problem_statement`、`target_users`、`problem_landscape` 等字段逐步生成正式《问题域分析》artifact delta，并保留 Mermaid mindmap。
  - `IDEA_BRAINSTORM/DIVERGE` 在 raw JSON streaming 期间可先输出发散方法，待 `idea_landscape` 与 `idea_cards` 都闭合后输出发散全景图和创意卡片库，并保留 Mermaid mindmap。
  - `IDEA_BRAINSTORM/CONVERGE` 在 raw JSON streaming 期间可待 `decision_matrix` 与 `ice_evaluations` 都闭合后输出决策矩阵和 ICE 评估表，后续资源约束、验证实验等章节逐步出现，并保留 Mermaid quadrantChart。
  - `IDEA_BRAINSTORM/CONCEPT` 在 raw JSON streaming 期间可基于定位声明、核心假设、Lean Canvas、MVP 功能等字段逐步生成正式产品概念简报，并保留 Mermaid pie、flowchart 和 `mvp-map`。
  - 四个阶段都继续复用共享 Agent Runtime、typed SSE、`AgentTurnOutput.artifact_patch` 和 ArtifactPane 消费链路；未新增 workflow 专属 runtime、API、store 或渲染管线。
- 聚焦验证：
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_define_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_diverge_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_concept_artifact_data_builds_formal_incremental_markdown_and_patch -q`：先失败，原因是 IDEA partial dispatch 返回 `None`；实现后 4 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_concept_artifact_data_before_final_output -q`：4 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_concept_artifact_data_before_final_output -q`：13 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q`：296 passed。
  - `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx`：140 passed。
- 文档与全量验证：
  - `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`：沙箱内失败，失败点为 MidScene proxy 端口绑定 `EPERM`、Playwright 缓存目录写入 `EPERM` 和 Chromium `bootstrap_check_in ... Permission denied`。
  - `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all` 非沙箱重跑：通过。关键结果包括 Intent Tester API 294 passed、MidScene Proxy 17 passed、Common Frontend lint/build 通过、New Agents Frontend 697 passed、New Agents Backend 526 passed / 1 deselected、New Agents Browser E2E 4 passed / 3 skipped / 10 deselected。
- LLM judge：本轮未启用或引用新的 IDEA_BRAINSTORM LLM judge 质量门；不能据此声称创意脑暴真实模型质量评分。若后续为创意脑暴增加 judge，默认门槛仍为 80 分。
- 残余风险：本轮当前证据为确定性 mock raw JSON streaming 与前端 typed SSE 回归；真实模型 smoke 仍取决于本地模型配置、网络和额度。`DIVERGE` 和 `CONVERGE` 的首个可视化 partial 可能一次新增多个 section，因此对应 delta 可没有 `artifact_patch`，但 `artifact_update.replace.markdown` 仍为正式产物。
- 下一轮候选：第 6 轮 `VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`VALUE_DISCOVERY/BLUEPRINT`。因目标和阶段顺序已经写入本文件，后续恢复时应先做目标承接检查；如第 6 轮触达范围过大，可按本文件拆分规则拆成同一 workflow 内的子轮次。

### 第 6 轮：价值发现 workflow 真实 partial streaming 闭环

- 状态：已完成确定性验证。
- 设计与执行要点：已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
- 覆盖阶段：`VALUE_DISCOVERY/ELEVATOR`、`VALUE_DISCOVERY/PERSONA`、`VALUE_DISCOVERY/JOURNEY`、`VALUE_DISCOVERY/BLUEPRINT`
- 运行中反馈处理：
  - 用户指出 playbook 需要补规则以避免再次出现 LLM judge 低分未修复、子智能体漏用或运行中反馈未改道的问题。
  - 已先更新 `docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-subagents.md`，新增运行中反馈中断、judge 差距分析、分数记录和默认子智能体审查触发规则。
- 子智能体 / 旁路审查：
  - 已派发只读 explorer Hypatia 复核 VALUE contract、field order、final renderer/helper、runtime tests 和拆分风险。
  - Hypatia 结论为四个 VALUE 阶段可作为同一纵切轮完成，主要缺口是 `render_partial_agent_turn_from_artifact_data()` 缺 `VALUE_DISCOVERY` 分支；`score_matrix + score_summary`、`personas` 映射、`journey_summary` 顺序、`feature_modules + requirements` 等依赖只影响 patch 形态，不阻断正式 replace markdown delta。
  - 不派发 worker：本轮实现集中编辑同一 backend renderer 与两个测试文件，多个 worker 会产生写入冲突。
- 交付：
  - `VALUE_DISCOVERY/ELEVATOR` 在 raw JSON streaming 期间可基于已闭合 `positioning_summary`、`value_flow`、`target_scenarios`、`score_matrix + score_summary` 等字段逐步生成正式《价值定位分析》artifact delta，并保留 Mermaid `flowchart` 与 `score-matrix`。
  - `VALUE_DISCOVERY/PERSONA` 在 raw JSON streaming 期间可基于已闭合 `persona_summary`、`personas`、`behavior_scenarios`、`decision_chain` 等字段逐步生成正式《用户画像分析》artifact delta，并保留画像、行为场景和决策链章节。
  - `VALUE_DISCOVERY/JOURNEY` 在 raw JSON streaming 期间可基于已闭合 `journey_stages`、`pain_priorities`、`opportunity_scores` 等字段逐步生成正式《用户旅程分析》artifact delta，并保留 Mermaid `journey` 与 `journey-map`。
  - `VALUE_DISCOVERY/BLUEPRINT` 在 raw JSON streaming 期间可基于已闭合 `document_info + product_overview`、`target_users`、`feature_modules + requirements`、`main_flow`、`roadmap`、`lisa_handoff_inputs` 等字段逐步生成正式《需求蓝图》artifact delta，并保留 Lisa handoff 输入和 `roadmap`。
  - 四个阶段都继续复用共享 Agent Runtime、typed SSE、`AgentTurnOutput.artifact_patch` 和 ArtifactPane 消费链路；未新增 workflow 专属 runtime、API、store 或渲染管线。
- 聚焦验证：
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_elevator_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_persona_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_journey_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_value_blueprint_artifact_data_builds_formal_incremental_markdown_and_patch -q`：先失败，原因是 VALUE partial dispatch 返回 `None`；实现后 4 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_elevator_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_persona_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_journey_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_blueprint_artifact_data_before_final_output -q`：4 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_concept_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_elevator_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_persona_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_journey_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_blueprint_artifact_data_before_final_output -q`：17 passed。
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q`：300 passed。
  - `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx`：3 files passed / 140 tests passed。
- 文档与全量验证：
  - `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all` 非沙箱运行：通过。关键结果包括 Intent Tester API 294 passed、critical flake8 0、MidScene Proxy 17 passed、Common Frontend lint/build 通过、New Agents Frontend 697 passed、New Agents Backend 530 passed / 1 deselected、New Agents Browser E2E 4 passed / 3 skipped / 10 deselected。
- LLM judge：本轮未启用或引用新的 VALUE_DISCOVERY LLM judge 质量门；不能据此声称价值发现真实模型质量评分。若后续运行或引用 VALUE judge，默认门槛为 80 分，低于 80 分必须作为当前 P0 修复。
- 残余风险：本轮当前证据为确定性 mock raw JSON streaming 与前端 typed SSE 回归；真实模型 smoke 仍取决于本地模型配置、网络和额度。部分 VALUE 阶段会因多字段依赖一次新增多个 section，因此对应 delta 可没有 `artifact_patch`，但 `artifact_update.replace.markdown` 仍为正式产物。
- 下一轮候选：第 7 轮全工作流 streaming 契约收口与证据归档。因 17 个在线阶段的实现轮次已完成，下一轮应审计文档、覆盖矩阵、测试说明和代表性证据，不得把文档收口替代为新的实现阶段。

### 第 7 轮：全工作流 streaming 契约收口与证据归档

- 状态：已完成文档收口。
- 设计与执行要点：已压缩保留在本文件的本轮记录中；独立过程 spec/plan 文件已清理。
- 覆盖阶段：17 个在线阶段。
- 子智能体 / 旁路审查：
  - 已派发只读 explorer Arendt 复核 `docs/api-contracts.md`、`docs/TESTING.md`、`docs/index.md`、`docs/component-inventory.md` 和相关 schema / 测试。
  - 采纳结论：`docs/api-contracts.md` 需要补 `agent_delta`、partial `artifact_update.replace.markdown` 和 `artifact_patch` schema；`docs/TESTING.md` 需要补 17 阶段覆盖矩阵、稳定测试入口和 LLM judge 80 分门槛；新增 `docs/evidence/2026-07-07-new-agents-partial-artifact-streaming.md` 归档轮次证据；`docs/index.md` 只补证据归档链接；`docs/component-inventory.md` 不需要更新。
  - 不派发 worker：本轮为稳定文档收口，主 Agent 串行更新更容易保持 API / TESTING / evidence 口径一致。
- 交付：
  - `docs/api-contracts.md`：补充 `/api/agent/runs/stream` 的 `agent_delta` 示例、`AgentTurnDeltaOutput` 字段、`artifact_patch` schema、`add_after` / `replace` 约束，以及 final `agent_turn` 仍需通过完整 contract 的边界。
  - `docs/TESTING.md`：补充 New Agents partial artifact streaming 覆盖矩阵，列出 17 个在线阶段的 partial renderer test、runtime raw JSON streaming test、关键契约 / 下游验证、聚焦回归命令、前端共享流式消费回归，以及 LLM judge `score >= 80` 规则。
  - `docs/evidence/2026-07-07-new-agents-partial-artifact-streaming.md`：归档第 1-6 轮实现证据、最终聚焦验证、全量本地自动化、Lisa judge 64 分修复闭环和风险边界。
  - `docs/index.md`：新增证据归档入口。
- 文档验证：
- 代码测试决策：本轮纯文档收口，不新增 runtime 行为；代码证据引用第 6 轮已完成的 17 partial runtime tests、backend focused suite 300 passed、frontend shared stream regression 140 passed、full local automation passed。
- LLM judge：本轮未启用或引用新的 LLM judge；文档已稳定声明启用 / 要求 / 引用 judge 时默认 `score >= 80`，低于 80 必须作为质量门失败修复。
- 残余风险：真实模型 smoke 仍取决于本地模型配置、网络和额度；当前收口证明稳定契约和确定性证据齐备，不声称所有真实模型运行质量。
- 下一步候选：该纵切路线已完成。后续如要提升真实模型质量，应另开目标模式故事，围绕真实 smoke、judge 维度或具体 workflow 质量评分推进。

## 后续启动提示

```text
请按照 `AGENTS.md` 和 `docs/strategy/goal-mode-playbook.md` 进入目标模式。

注意：
- 本文件记录的 partial artifact streaming 纵切路线已经完成，不要再按“下一轮候选”机械恢复实施。
- 如果后续真实模型 smoke、LLM judge 或全量回归重新暴露流式产物问题，应基于当前失败证据重新做 Current State Gap Analysis，并优先读取 `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`。
- 任何后续修复仍必须复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、run persistence、共享前端 store 和 ArtifactPane。
```
