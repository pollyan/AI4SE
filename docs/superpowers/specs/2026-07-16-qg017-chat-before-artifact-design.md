# QG-017 全工作流自然对话先于产出物设计

## 厚切片身份基线

- **ID / 名称**：`QG-017 — 全工作流有意义对话先于右侧产出物`。
- **完整用户任务**：用户在任一 New Agents workflow/stage 发起生成后，先在左侧看到由本轮模型输出的、有独立阅读价值的自然工作对话，再在右侧看到第一段真实产出物；随后双栏分别单调更新，阶段动作、持久化和版本只在最终结果收敛后生效。
- **顺序基线**：[归档能力包的待办总览](../../todos/archive/2026-07-16-new-agents-streaming-and-artifact-ux.md#待办总览)，固定顺序为 `QG-017 → QG-018 → QG-019 → QG-020`。
- **纳入边界**：25 个在线 stage 的结构化输出字段顺序；raw JSON partial parser；共享 Agent Runtime 到 typed SSE 的首帧排序；前端 SSE mapper、store 和左右 Pane 的可见时序；terminal-only、chat-first、artifact-first、混合 delta、错误中断、重放与 `NEXT_STAGE`；Lisa/Alex 的语义 DOM 证据；相关测试与事实文档同步。
- **排除边界**：不为单个 Agent/workflow/stage 新增 runtime 或分支；不在本切片补齐 24 个 stage 的段落级 partial renderer（属于 `QG-018`）；不调整文档元信息位置（属于 `QG-019`）；不建立真实 DeepSeek 全矩阵与 CI 调度（属于 `QG-020`）；不修改 Intent Tester；不做截图或像素回归。
- **依赖**：共享 `/api/agent/runs/stream`、`AgentTurnOutput`、`AgentTurnDeltaOutput`、artifact-data renderer、前端 `generateResponseStream` / `useChatService`、现有服务端 run 持久化；不依赖 DeepSeek API Key 才能完成确定性实现和低层验证。
- **七项门禁**：入口是任一 New Agents 工作区发送消息；动作是生成或继续当前阶段；处理是模型自然 `chat`、artifact data、typed SSE 和共享前端状态按契约流转；可见结果是自然 chat-only 帧严格早于首个真实 artifact 帧；状态承接是最终 chat/artifact、run、version 和阶段确认保持原有权威；失败反馈是 provider/schema/stream/visual/transition 错误显式停止且不把占位话术或半成品伪装成成功；证据是 25-stage 指令契约、Lisa/Alex runtime/endpoint、前端 mapper/store 和无头浏览器语义 DOM 时序测试。
- **验收证据**：所有 25 个 stage 的模型指令与 JSON 示例均为 `chat → artifact_data → stage_action → warnings`；首个有意义 chat-only delta 的索引严格小于首个 artifact delta；已释放内容单调收敛；artifact-first provider、terminal-only/replay、错误中断和阶段动作均有确定性回归；至少一个 Lisa 与一个 Alex 场景证明 typed SSE → parser/store → `ChatPane`/`ArtifactPane` DOM 顺序。
- **单一交付边界**：只有共享后端、共享前端、跨层证据、事实文档和 Todo 状态共同闭合后，才形成一个 QG-017 聚焦交付；内部 RED/GREEN 步骤、helper、测试文件和前后端修改都不是独立切片。

## Current State Gap Analysis

### 实际读取的事实源与工作区

本轮读取了 `AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、唯一活动 Todo、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/TESTING.md`、New Agents runtime/SSE/frontend/store/Pane/browser E2E 代码、相关单测、最近提交与当前 Git 状态。归档 Todo 只用于核对历史语义，没有恢复其中候选；Intent Tester 因用户明确排除而未展开实现事实。

当前分支为 `master`，相对 `origin/master` ahead 5，启动时 staged 集为空。工作区已有 16 个 Markdown 路径，属于用户此前确认的 Todo 清理、归档移动和历史链接修订；没有启动前业务代码改动。本切片不得回滚这些文档，交付时必须精确区分既有清理、QG-017 新增 spec/plan/实现和任何无关改动。

当前唯一活动能力包文件确实只列出 `QG-017～QG-020`。但旧 [QS-02 设计](2026-07-10-qs02-shared-run-consistency-design.md) 和 [QS-02 计划](../plans/2026-07-10-qs02-shared-run-consistency.md) 仍把“固定进度话术先于 artifact”记录为 QG-017 的完成语义，和用户最新明确的“占位不算有意义对话”冲突。裁决以用户最新目标、当前活动 Todo 和当前代码事实为准：QS-02 只保留历史部分缓解证据，不再拥有本轮 QG-017。

### 当前能力、失败证据与质量门

- 25 个 artifact-data 指令源本来全部声明 `chat → artifact_data`，但 `agent_runtime._normalize_artifact_data_instruction_order()` 在发送给模型前机械反转为 `artifact_data → chat`，并有 25-stage 参数化测试锁定该旧顺序。
- production-shaped `/api/agent/runs/stream` 总是为 runtime 注入 `RawStreamingConfig`，真实链路会进入受影响的 raw JSON parser。
- partial parser 在自然 chat 尚未出现时用固定 `ARTIFACT_FIRST_PROGRESS_CHAT` 填充并放行 artifact；typed SSE 层不缓冲或重排。`TEST_DESIGN/CLARIFY` 因拥有唯一字段级 partial renderer 最早暴露问题，其余 24 个 stage 仍有同源风险。
- 前端只补了“首个 artifact-only delta”的固定话术与 20ms 延迟。terminal-only 路径仍在同一 chunk 同时写 chat 与 artifact；同一 async iteration 的两次 Zustand 更新不构成浏览器绘制顺序保证。
- 当前 browser fixture 只发送 `run_started → agent_turn → DONE`，runner 还先等待右侧 artifact、再读取左侧 chat，无法捕获该回归。
- 聚焦 frontend 基线实际执行并通过 2 项现有流映射测试；ChatPane/ArtifactPane/chatService 旁路运行 257 项通过但有 2 个 React `act(...)` warning，时序测试存在假绿风险。
- backend 当前默认 Python 环境缺少 pytest，因此相关测试为 `NOT_RUN`，不是通过；进入 RED 前必须建立可复用的仓库 Python 环境。

### 候选能力包

| 候选 | 目标态 | 当前缺口 | 价值 | 风险 / 依赖 | 可观察证据 | 去向 |
|---|---|---|---|---|---|---|
| `QG-017` 自然对话先行 | 左侧模型自然对话严格早于右侧首段真实产出 | runtime 反转字段、占位替代自然 chat、terminal 同帧、E2E 盲区 | 直接解决用户当前首要体验问题，并为后续流式统一建立顺序契约 | 需跨 backend/SSE/frontend；不能破坏 CLARIFY partial | 25-stage 指令、Lisa/Alex SSE、DOM 时序 | **本轮推荐** |
| `QG-018` 25-stage 分段流式 | 25/25 stage 逐业务章节累积 | 仅 CLARIFY 有字段级 partial renderer | 覆盖更广的右栏体验 | 依赖 QG-017 先冻结双栏顺序，否则会放大错误顺序 | 25-stage fixture 与 7-workflow DOM | 固定下一轮，不并入本轮 |
| `QG-020` 真实链路测试重构 | PR/Nightly/发布真实模型无头门禁 | 当前 E2E mock 终态事件且 CI 不跑浏览器矩阵 | 提高四项长期可信度 | 真实证据依赖 API Key，且用户已要求在前三项后执行 | 真实 DeepSeek/SSE/DOM/持久化 | 保持第 4 顺序，不提前 |

用户已确认顺序，当前没有新 P0、生产阻断或安全风险足以改道。`QG-019` 是独立的信息层级目标，既不阻断 QG-017，也不能与其合并。故本轮选择 QG-017，其余候选保持用户确认的原顺序。

### 子智能体与旁路审查

多智能体工具可用。本轮派发三个只读任务：Todo/dirty ownership 审计、QG-017 backend/runtime 根因追踪、QG-017 frontend/DOM 测试盲区追踪。三个任务均未写入、stage、commit 或 push；主 Agent 已复核其路径、Git 状态和聚焦测试输出。实施写入由主 Agent 独占共享文件，避免串行厚切片与 dirty 文档发生 ownership 冲突；最终正式审查再按 Playbook 形成完整审查包。

## 需求与成功标准

### 有意义对话定义

“有意义对话”必须来自本轮模型的 `chat` 字段，非空、通过既有 chat/artifact 分离契约，且不能等于 `正在生成...`、`正在生成右侧产出物。`、`我正在整理当前输入并生成右侧结构化初稿，随后会同步关键结论。` 等本地固定状态或占位话术。`run_started` 和左右栏 loading indicator 可以保留为运行状态，但不计入顺序验收。

模型 chat 应简要说明本轮处理、关键判断、右侧将更新的内容和需要用户确认的事项，不复制完整 artifact。测试不对自然语言逐字快照，只使用模型来源、非占位、非空、字段职责和时序不变量。

### 成功路径

1. 用户发送本轮输入，服务端建立或复用 run，并可先发送 `run_started` 状态。
2. 模型按 `chat → artifact_data → stage_action → warnings` 输出；partial parser 将已经形成的自然 chat 作为 chat-only delta 发送。
3. 只有 typed SSE 已经发送有意义 chat-only delta 后，首个 artifact delta 才允许离开服务端；后续 artifact 保持当前或 QG-018 扩展后的单调 partial renderer 行为。
4. 前端先把自然 chat 写入 assistant message。正常 chat-first 流不增加固定 sleep；只有接收到合并的 terminal/replay 兼容帧时，前端才使用一次浏览器 render-commit barrier 将 chat-only 帧与 artifact 帧分开，不能用固定毫秒等待冒充流式生成。
5. 最终 `agent_turn` 校验、持久化、版本保存和 `NEXT_STAGE` 保持现有语义；最终 chat/artifact 精确收敛到服务端权威结果。

### artifact-first、terminal-only 与失败路径

- **provider artifact-first**：服务端缓存尚未授权释放的 artifact，不合成 chat；自然 chat 出现后先发送 chat-only delta，再释放最新合法 artifact。若直到终态才得到 chat，也必须按此顺序拆分。
- **同一 delta 同时含 chat/artifact**：共享 sequencer 拆为 chat-only delta 和后续 artifact delta；不要求 workflow 特判。
- **terminal-only / durable replay**：服务端或客户端兼容 seam 从权威 final `chat` 产生 chat-only 帧，再交付 final artifact；不得回退固定进度话术。
- **自然 chat 前发生 provider/schema/transport 错误**：不显示真实 artifact，只显示既有 typed error；缓存内容丢弃。
- **自然 chat 后发生错误或用户停止**：已显示 chat 保留；已释放的 partial artifact 按现有 truncated 语义标记，不能保存正常版本或推进阶段。
- **非法 visual/stage action**：继续使用现有显式错误/门禁；排序层不得吞掉验证失败、构造成功或提前触发 `NEXT_STAGE`。

## 方案比较与决定

### 方案一：单次模型输出恢复 chat-first，并在共享 transport/frontend 建立无占位排序门禁（采用）

恢复 25-stage 指令原本的 chat-first 语义；在 runtime/SSE 边界为 provider 乱序、同帧和 replay 建立统一 sequencer；前端删除固定 artifact-first 对话并保留共享防御性缓冲。它不增加模型调用，保持一个权威 `AgentTurnOutput`，能同时解决正常路径与异常顺序，且为 QG-018 提供稳定前置契约。

代价是需要跨 backend、frontend 和 browser fixture 修改并更新旧 QS-02 事实，但这些都属于同一用户动作链。

### 方案二：先调用模型生成 chat，再第二次调用生成 artifact（不采用）

两次调用天然有时间顺序，也容易让左栏很早出现。但它增加延迟、成本和失败面；两次输出可能使用不同假设，stage action 与 artifact 数据难以保持一个原子终态，也会破坏当前单一 runtime/persistence 语义。

### 方案三：继续 artifact-first，由 artifact 数据确定性合成左侧对话（不采用）

该方案最快且完全确定性，但产出的仍是模板或数据摘要，不是用户要求的模型自然工作对话；它会继续把假进度当真实内容，并让 chat/artifact 职责混淆。

## 架构与组件

### 结构化输出指令

`artifact_data_instruction_registry.py` 保持唯一 stage 数据说明来源；`agent_runtime.build_structured_output_instruction()` 不再反转字段清单和 JSON 示例。同步测试机械覆盖 manifest 的 25 个在线 stage，新增 stage 若没有 chat-first 指令则失败。

### 共享 runtime / typed SSE sequencer

共享排序 seam 位于 runtime 输出到 `AgentTurnDeltaEvent` 的公共路径，不进入 Lisa/Alex 分支。它维护本轮是否已发送模型自然 chat、尚未释放的最新 artifact delta 和最终输出：

- 首次自然 chat 总是以不含 artifact 的 delta 发送；
- artifact 在该事实成立前只缓存，不外发；
- 成立后按现有去重/单调规则外发 artifact；
- final、replay 和 PydanticAI fallback 都经过同一顺序不变量；
- 事件内容仍使用现有 Pydantic schema，协议不新增 event type。

sequencer 不验证业务 schema 的替代品。artifact renderer、visual contract、stage readiness、持久化和终态 event 仍由原 owning 组件负责。

### 前端共享 stream mapper

`llm.ts` 将“已经看到模型自然 chat”与 `run_started`/本地 loading 分开记账；删除固定 `ARTIFACT_FIRST_PROGRESS_CHAT` 作为业务 chat 的路径。收到老服务端的 artifact-first、chat+artifact 或 terminal-only event 时，先发权威 chat-only `StreamChunk`，再在一次 render-commit barrier 后发 artifact；无权威 chat 时只缓存，不用占位解锁。

`chatService.ts` 继续先消费 assistant chunk、再消费 artifact decision，并保持终止、版本、锁定章节和阶段确认逻辑。测试通过 store snapshot 与浏览器 MutationObserver/语义 DOM 证明可见顺序，不把函数调用顺序当作绘制证据。

### 浏览器证据

现有 Python Playwright fixture 增加可按事件分段发送的 typed SSE journey，并给左右 Pane 的关键语义容器添加稳定 test id。Lisa 和 Alex 各选择一个共享 runtime 场景，记录 DOM 变更序列：首次出现非占位 assistant 文本时，右侧 unique artifact marker 尚不存在；之后 marker 出现并最终收敛。测试只使用文本、属性和状态，不生成截图基线。

浏览器 fixture 的真实模型升级属于 QG-020；本切片的浏览器层明确属于“真实 UI + mock backend”证据，不冒充真实 DeepSeek。

## 数据流

```text
user send
  -> POST /api/agent/runs/stream
  -> run_started (状态，不计入有意义对话)
  -> provider raw JSON: chat ... artifact_data ...
  -> runtime partial parser
  -> shared sequencer: natural chat-only agent_delta
  -> frontend assistant message / ChatPane commit
  -> artifact agent_delta(s)
  -> ArtifactPane incremental render
  -> validated agent_turn
  -> durable message/artifact/version + optional pending NEXT_STAGE
  -> [DONE]
```

provider 乱序时，artifact 在 sequencer 中等待自然 chat；frontend 收到旧服务端合并帧时执行相同的防御性拆分。两层都不生成伪自然对话。

## 测试设计

### 确定性后端

- 25-stage 参数化测试：字段清单与 JSON 示例均 `chat < artifact_data`。
- Lisa `TEST_DESIGN/CLARIFY`：字段级 partial artifact-first chunk 被缓存，自然 chat-only delta 先出现，再恢复原 partial artifact 与 final 收敛。
- Alex 代表 stage：完整 artifact_data-first chunk 同样满足顺序，证明不是 CLARIFY 特判。
- shared stream service/endpoint：`run_started → natural chat-only agent_delta → artifact agent_delta → agent_turn`，覆盖 terminal output、重放、错误和 stage action。

### 确定性前端

- terminal-only、artifact-only、chat+artifact、chat-first 多 delta 的首个有意义 chat index 严格小于首个 artifact index。
- chat/artifact 长度单调，final 精确收敛；错误/停止不保存正常版本，`NEXT_STAGE` 只在 final 生效。
- Zustand snapshot 不出现“artifact 已变化但 assistant 仍只有占位”的状态。
- 修复受影响 ChatPane 测试的 `act(...)` warning，时序测试输出必须干净。

### 跨层与浏览器

- Lisa 与 Alex 各一条真实 React + mock typed SSE 的无头 Chromium DOM 序列测试。
- QG-017 不以真实模型证据为完成门禁；DeepSeek Key 可用后，QG-020 必须把同一时序不变量提升到真实 frontend/backend/provider 层。

### 文档与 CI 等价

- 更新 `docs/TESTING.md`、`tools/new-agents/CONTEXT.md` 和旧 QS-02 spec/plan，消除 artifact-first/固定话术的当前执行语义。
- 聚焦验证覆盖 backend runtime/stream service、frontend llm/chat service/Pane；必要跨层覆盖 browser E2E；完成型验证按当前 `scripts/test/test-local.sh`、package scripts 和 CI workflow 动态映射。

## 风险与约束

- DeepSeek 通常遵循字段顺序但不能作为唯一保证，因此共享 sequencer 是不可省略的防线。
- artifact-first 最坏情况下会等到 final chat 才释放右侧；这是满足用户顺序的诚实退化，不得用假 chat 提前解锁。QG-018 负责把所有正常 stage 的 artifact 分段能力补齐。
- 浏览器 render-commit barrier 只解决老服务端合并帧的可见顺序，不能成为正常路径的固定延迟或流式替代。
- 不改变最终 schema、artifact_data、deterministic renderer、runId/requestId、持久化或 handoff 权威，不新增协议镜像。
- 本切片不得碰 Intent Tester，也不得把 QG-018～QG-020 的工作提前打包进来。
