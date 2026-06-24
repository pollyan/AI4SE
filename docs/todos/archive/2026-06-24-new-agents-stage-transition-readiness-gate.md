# New Agents 阶段推进成熟度门禁 Todo

状态：活跃候选  
创建日期：2026-06-24  
相关模块：`tools/new-agents/`

完成日期：2026-06-25  
完成记录：

- 已实现第一条共享阶段成熟度门禁切片：`TEST_DESIGN/CLARIFY` 存在 P0/P1 阻断且待确认的澄清问题时，后端在 typed SSE 出口取消 `stage_action`。
- 已通过 `stage_readiness_blocked` warning 复用现有 typed SSE schema，避免新增 workflow 专属 API、store 或 renderer。
- 已让阻断 turn 的 chat 追加“还不能进入下一阶段”的缺口说明，列出阻断问题 ID 和状态。
- 已补前端 warning 兜底：收到 `stage_readiness_blocked` 时，即使 chat 有进入下一阶段语义，也不推断 `NEXT_STAGE`。
- 强制推进 UI、风险接受审计字段和全 workflow 成熟度规则未在本切片实现，后续应作为独立用户故事推进。

验证：

- `cd tools/new-agents/backend && ../../../.venv/bin/python -m pytest tests/test_stage_readiness.py tests/test_stream_services.py -q`
- `cd tools/new-agents/backend && ../../../.venv/bin/python -m pytest tests/test_stage_readiness.py tests/test_stream_services.py tests/test_sse_encoder.py tests/test_agent_contracts.py tests/test_agent_runtime.py -q`
- `cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts`
- `cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/core/config/__tests__/workflows.test.ts`

## 背景

在测试用例设计工作流中，用户选择类似“帮我设计一份登录功能的测试用例”的提示语后，右侧会生成需求澄清阶段产出物。当前产出物中仍可能包含大量待确认内容，例如系统边界、关键业务规则、需求实施清单、待澄清问题等。

但在这些高层信息尚未确认时，左侧仍可能提示用户进入下一阶段“策略制定”。这会让工作流在事实基础不足的情况下继续推进，导致后续策略、用例和执行建议建立在未确认假设上。

## 当前问题

当前阶段推进建议过于依赖模型在同一轮输出中的 `stage_action` 或聊天语义，而没有由共享运行时基于结构化产物做确定性的成熟度判定。

已有提示词和产物模板会要求模型区分“已确认事实”“AI 假设”“待确认问题”“阻断问题”，但缺少一个跨前后端一致执行的阶段门禁：

- 右侧产物存在 P0/P1 阻断问题时，仍可能出现“进入下一阶段”的引导。
- 用户只提供了一个高层 starter prompt 时，模型可能用 AI 假设补齐场景，但这些假设尚未经过用户接受。
- `stage_gate` 中的勾选项更多像展示文本，不足以阻止不成熟产物触发下一阶段确认控件。
- 前端缺少针对“为什么现在不能进入下一阶段”的明确提示和缺口清单。

## 目标能力包

建立共享的“阶段推进成熟度门禁”，让 New Agents 在允许或建议进入下一阶段前，必须先验证右侧结构化产物已经满足当前阶段的最低成熟度标准。

该能力包应作为共享 Agent Runtime / typed SSE / workflow manifest / artifact contract / 持久化 run 与 artifact 模型 / 共享 UI 基础设施的一部分实现，不允许新增 Lisa、Alex、DeepSeek 或未来 agent 专属 runtime、API path、store 或 renderer。

## 建议门禁语义

阶段推进应区分两个层级：

- 允许进入下一阶段：当前产物达到最低事实成熟度，或用户明确接受风险后强制推进。
- 建议进入下一阶段：当前产物不但满足最低门槛，而且高优先级问题已经确认或被用户接受为可推进假设。

如果门禁不通过，系统应取消或降级下一阶段 CTA，并在左侧或右侧显示“还缺什么信息才能进入下一阶段”。

## TEST_DESIGN / CLARIFY 阶段候选门禁条件

进入“策略制定”前，至少应满足以下条件：

1. 测试范围与非范围边界明确；P0/P1 范围边界问题不能停留在“待确认”状态。
2. 至少一个主关键路径已经明确，包括入口、参与角色、核心组件或服务、成功结果和关键失败结果。
3. 所有 P0 阻断问题必须已有确认结论，或已被用户明确接受为可推进的 AI 假设。
4. P1 阻断问题如会影响策略选择、优先级、覆盖范围或风险判断，也必须确认或显式风险接受。
5. 关键业务规则具备最低可测试信息，例如成功判定、失败处理、关键数据状态或状态迁移。
6. 下游策略制定所需输入已经可追溯到产物中的事实、规则、风险或用户确认假设。
7. `stage_gate` 不能只展示勾选文案；它需要和结构化产物字段一致，能够被后端或前端确定性读取。
8. 当用户仅选择 starter prompt 且未补充系统细节时，模型可以提出 AI 假设和澄清问题，但不应默认建议进入下一阶段，除非用户明确接受这些假设，或当前工作流处于显式 demo / test-run 模式。

低优先级、非阻断问题可以留到后续阶段，但必须在产物中标记为不阻断，并说明不阻断的理由。

## 设计建议

后端应提供共享的阶段成熟度评估逻辑，输入为经过校验的 `artifact_data`、当前 `workflow`、当前 `stage` 和模型返回的 `stage_action`。

评估结果建议包含：

- `ready_to_advance`: 是否允许进入下一阶段。
- `recommended_to_advance`: 是否建议进入下一阶段。
- `blocking_findings`: 阻断推进的缺口列表。
- `risk_acceptance_required`: 是否允许用户显式风险接受后强制推进。
- `evidence`: 支撑判定的结构化字段路径或引用。

当模型返回 `stage_action=request_next_stage` 但成熟度门禁不通过时，系统应采取确定性行为：

- 后端拒绝该 `stage_action`，或降级为无下一阶段动作。
- 前端不显示下一阶段确认控件。
- UI 显示缺口清单，引导用户先确认高优先级问题。
- 持久化记录应能解释为什么本轮没有进入下一阶段。

门禁规则应通过 `workflow_manifest.json`、阶段 contract 或共享配置表达，避免把 TEST_DESIGN、Lisa、Alex、DeepSeek 等工作流写死到运行时代码里。

## 验收标准

- 用户选择“帮我设计一份登录功能的测试用例”这类信息不足的 starter prompt 后，如果右侧产物仍存在高优先级待确认问题，左侧不得建议或展示“进入策略制定”的 CTA。
- 当右侧产物存在 P0 阻断问题且状态为“待确认”时，即使模型返回 `stage_action=request_next_stage`，共享运行时也必须拒绝或降级该动作。
- 当关键路径、系统边界、高优先级问题处置和下游输入均满足门禁时，系统可以显示进入下一阶段的确认控件。
- UI 必须清楚说明当前不能进入下一阶段的原因，并列出需要用户确认的关键缺口。
- 如允许手动强制推进，必须展示风险接受语义，并在 run / artifact 记录中保留可追溯信息。
- 改动不得破坏现有 typed SSE、共享 Agent Runtime、artifact contract、持久化模型和共享 UI 渲染链路。

## 建议测试

- 后端 contract 测试：CLARIFY 产物包含 P0 阻断待确认问题且模型返回下一阶段动作时，运行时不应产生可用的下一阶段 CTA。
- 后端 contract 测试：CLARIFY 产物中 P0/P1 阻断问题已确认或用户接受为可推进假设，且关键路径明确时，允许进入策略制定。
- 前端流式解析测试：接收到门禁不通过的 agent turn 时，不显示下一阶段按钮，并展示缺口清单。
- 端到端或等价验收：选择登录功能 starter prompt 且不补充更多信息时，右侧产物可以生成澄清清单，但左侧不建议进入策略制定。

## 非目标

- 不要求一次性解决所有低优先级待确认问题。
- 不禁止模型提出 AI 假设，但 AI 假设不能在未经接受时伪装成确认事实。
- 不为单个 agent 或单个 workflow 新增专属 runtime、API、store 或 renderer。
- 不隐藏不完整产物；应明确展示不完整原因和下一步需要确认的事项。

## 待决策问题

- P1 问题是否一律阻断推进，还是仅当它影响策略、覆盖范围或风险排序时才阻断？
- “AI 假设可推进”是否必须经过用户显式确认，还是可以由特定 demo / test-run 模式自动接受？
- 强制推进是否需要单独的 UI 控件和持久化审计字段？
- 门禁结果应该作为 artifact metadata、agent turn metadata，还是独立的 stage readiness contract 暴露给前端？
