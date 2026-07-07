# New Agents 第 7 轮 partial streaming 契约收口与证据归档设计

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-subagents.md`、`docs/index.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`docs/component-inventory.md`、`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`、`tools/new-agents/backend/sse_schemas.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`。
- 当前工作区：存在大量与本轮无关的删除和修改。本轮只写入本 spec / plan、`docs/api-contracts.md`、`docs/TESTING.md`、`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`。

已确认目标来源：

- 来源：`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`。
- 本轮承接：第 7 轮全工作流 streaming 契约收口与证据归档。
- 上一轮状态：第 1-6 轮已完成 17 个在线阶段实现与确定性验证；第 6 轮全量本地自动化通过。

改道条件检查：

- 新 P0/P1 或用户新目标：无新的替代目标。用户关于 playbook 的规则反馈已在第 6 轮先行处理。
- 未关闭质量门或用户明确反馈：无未关闭质量门。Lisa judge 64 分问题已修复并通过 80 分门槛；第 7 轮不新增 LLM judge。
- LLM judge / E2E / 审查状态：本轮只归档确定性证据和 judge 规则，不声称新的真实模型评分。
- 测试失败或生产阻断：无新的失败证据。
- 架构、文档或代码事实冲突：`docs/api-contracts.md` 已说明 `artifact_update.replace` 必须是正式产物，但缺少 `agent_delta.output`、`artifact_patch` 和 partial artifact streaming 示例；`docs/TESTING.md` 已说明 partial 原则，但缺少 17 阶段覆盖矩阵和 80 分 judge 门槛稳定说明。
- 工作区冲突：本轮只改文档和 todo，不触碰无关脏文件。
- 是否需要拆分或合并：不拆分。第 7 轮是单一工程信任闭环，目标是让后续维护者能从稳定文档找到 partial streaming 契约、测试入口和证据边界。

子智能体 / 旁路审查决策：

- 已派发只读 explorer Arendt 复核 API / TESTING / index / component inventory 的文档同步需求。
- 主线先按本地事实源推进，Arendt 返回后只采纳未覆盖的只读建议。
- 不派发 worker：本轮改动集中在少量稳定文档，主 Agent 串行更新更容易保持口径一致。

结论：继续承接第 7 轮。

## 自问自答式需求澄清

问题：第 7 轮交付给谁？

回答：交付给后续维护 New Agents runtime、workflow 或测试策略的人。他们需要从稳定文档确认 partial artifact streaming 的 SSE 契约、哪些阶段已有确定性覆盖、应该跑哪些测试、LLM judge 低分如何处理。

问题：为什么不再改代码？

回答：17 个在线阶段的实现轮次已经完成，聚焦测试和全量本地自动化已通过。第 7 轮的缺口是文档事实源滞后，不是 runtime 行为缺失。

问题：要不要同步 `docs/index.md` 或 `docs/component-inventory.md`？

回答：`docs/index.md` 已指向 `docs/api-contracts.md` 和 `docs/TESTING.md`；`docs/component-inventory.md` 已描述 typed SSE 相关模块。第 7 轮不新增入口或组件，不需要改这两个文件，除非只读审查发现明确导航缺口。

问题：证据归档放哪里？

回答：稳定规则放入 `docs/api-contracts.md` 和 `docs/TESTING.md`；本次路线、轮次状态、具体命令和通过结果继续放入当前 todo。这样稳定事实源不承载过长历史记录，todo 保留目标模式执行证据。

## 方案比较

方案 A：更新 `docs/api-contracts.md`、`docs/TESTING.md` 和当前 todo。

- 优点：补齐稳定事实源和执行证据，范围小，不引入新文档入口。
- 缺点：17 阶段矩阵会增加 `docs/TESTING.md` 长度。

方案 B：新建独立 evidence 文档，只在 todo 链接。

- 优点：主文档更短。
- 缺点：API 契约和测试策略仍滞后，后续维护者不一定会打开临时 evidence 文档。

方案 C：更新所有文档入口和组件清单。

- 优点：曝光更强。
- 缺点：本轮没有新增模块或页面，容易造成文档噪声。

选择方案 A。只在必要稳定事实源补契约和矩阵。

## 设计

### API 契约

在 `docs/api-contracts.md` 的 Agent Runtime SSE 响应格式中增加：

- `agent_delta` 事件示例，说明 final `agent_turn` 前可以多次出现。
- `AgentTurnDeltaOutput` 字段：`chat`、`artifact_update`、`artifact_patch`、`stage_action`、`warnings`。
- `artifact_patch` 的 `add_after` 语义、camelCase JSON 字段和约束：只有 `artifact_update.type="replace"` 时可携带；patch 是增量定位元数据，不替代 replace markdown。
- partial artifact 只能来自已闭合且通过局部模型校验的正式 renderer 输出。

### 测试策略

在 `docs/TESTING.md` 增加 New Agents partial artifact streaming 覆盖矩阵：

- 17 个在线阶段按 workflow / stage 列出。
- 每行标明 direct partial renderer 测试、runtime raw JSON streaming 测试、关键可视化或下游契约。
- 说明前端共享消费回归命令。
- 明确 LLM judge 默认通过线为 80 分；低于 80 分必须分析差距并修复，不能关闭 judge 后声称质量通过。

### Todo 收口

在当前 todo 的第 7 轮记录中归档：

- 本轮文档更新。
- 只读 explorer 结论。
- 文档检查命令。
- 不跑新代码测试的原因：本轮纯文档，代码验证沿用第 6 轮已完成的 17 阶段聚焦测试和全量本地自动化。
- 下一步状态：当前路线实现轮次和文档收口完成。

## 验收条件

1. Given 维护者阅读 `docs/api-contracts.md`
   When 查找 `/api/agent/runs/stream`
   Then 能看到 `agent_delta.output.artifact_update.replace.markdown` 和 `artifact_patch` 的契约边界
   Evidence: 文档 diff 和占位扫描。

2. Given 维护者阅读 `docs/TESTING.md`
   When 查找 New Agents partial artifact streaming
   Then 能看到 17 阶段覆盖矩阵、聚焦测试入口、前端共享回归和 LLM judge 80 分规则
   Evidence: 文档 diff 和占位扫描。

3. Given 当前 todo 作为路线记录
   When 查看第 7 轮
   Then 能看到契约收口已完成、哪些验证作为证据、哪些真实模型质量分没有声明
   Evidence: 文档 diff 和最终记录。
