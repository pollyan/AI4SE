# QG-017 全工作流自然对话先于产出物实施计划

> **For agentic workers:** 必须按本计划顺序执行。所有 Task 都是 `QG-017` 厚切片内的内部 tracer，不得单独交付或提交；全部门禁闭合后只形成一个 QG-017 聚焦提交。

**Goal:** 让 25 个在线 stage 都先交付本轮模型生成的有意义左侧对话，再交付右侧首个真实产出物，同时保持 typed SSE、最终持久化、版本和阶段流转语义不变。

**Architecture:** 恢复结构化输出指令的 `chat → artifact_data` 原始顺序；在共享 backend service seam 增加自然对话先行 sequencer；在共享 frontend mapper 对历史 artifact-first、合并帧和 terminal-only 帧做防御性拆分；用同一 tracer 的 backend、frontend store 和真实 React DOM 证据尽早闭环。不得增加 Agent/workflow/stage 专属 runtime、endpoint、store 或 renderer。

**Tech Stack:** Python 3.11、Flask、Pydantic/PydanticAI、pytest；React 18、TypeScript 5、Zustand、Vitest/Testing Library；Python Playwright + Chromium。

**Design source:** [QG-017 设计与厚切片身份基线](../specs/2026-07-16-qg017-chat-before-artifact-design.md)。待办执行顺序固定为 `QG-017 → QG-018 → QG-019 → QG-020`。

## 执行校正记录

最初版本把内部 Task 横向排成“全部 backend → 全部 frontend → 最后 browser E2E”。2026-07-16 的正式 Standards review 指出它违反 Goal Mode Playbook 的跨层 tracer 原则。该问题在任何 commit、交付或进入 QG-018 前被发现；本计划已按可观察场景重组。已经发生的 RED/GREEN 命令保留为诚实执行证据，不追写成未发生的时间顺序；后续审查修复、验证以及 QG-018～QG-020 必须使用本计划所示的纵向组织。

## 全局约束

- 每个 tracer 都必须从一个用户可观察风险出发，在同一 RED → GREEN 链中覆盖所需 backend、typed SSE、frontend state 和跨层证据。
- “有意义对话”来自模型权威 `chat`。空白、固定生成话术、等价前缀和没有独立阅读价值的过短 partial 都不能解锁 artifact。
- backend 是首要顺序门禁；frontend 是历史/混合事件的第二道防线。两层都不得合成业务 chat。
- 正常 chat-only → artifact-only SSE 不增加 barrier；只有 artifact-first 缓存、同帧或 terminal-only 兼容拆分允许一次 render-commit barrier。
- artifact、chat 各自单调；最终 `AgentTurnOutput`、artifact_data、持久化、版本与 `NEXT_STAGE` 仍是唯一权威终态。
- 不实现 QG-018 的 24 个新增 partial renderer，不调整 QG-019 元信息，不建立 QG-020 真实模型矩阵，不修改 Intent Tester。
- 保留启动前的 Todo 清理改动并精确 stage；任何内部 tracer 都不是独立切片、commit 或交付点。

## Task 1：Tracer A — 正常 chat-first 回合从模型指令到 Lisa DOM 闭环

**用户可观察行为：** Lisa `TEST_DESIGN/CLARIFY` 发送消息后，模型先形成可读自然对话，左栏先提交；右栏随后开始当前已有的正式 partial artifact，最终终态、版本和阶段入口不变。

**Files:**

- Backend contract/runtime/tests: `tools/new-agents/backend/agent_contracts.py`, `agent_runtime.py`, `tests/test_agent_contracts.py`, `tests/test_agent_runtime.py`
- Shared service/tests: `tools/new-agents/backend/stream_ordering.py`, `stream_services.py`, `tests/test_stream_ordering.py`, `tests/test_stream_services.py`, `tests/test_agent_endpoint.py`
- Frontend parser/store/tests: `tools/new-agents/frontend/src/core/llm.ts`, `services/chatService.ts` 及对应测试
- DOM evidence: `ChatPane.tsx`, `ArtifactPane.tsx`, `tests/e2e/new_agents_browser/`

### RED

1. 25-stage 参数化断言要求字段清单和 JSON 示例均 `chat < artifact_data`。
2. 共享 service 断言 `run_started → natural chat-only delta → artifact delta → agent_turn`。
3. 前端 mapper/store 断言不存在 artifact 已变化但 assistant 仍为空或只有状态话术的快照。
4. Lisa browser fixture 在发送前安装 MutationObserver；同一 DOM 提交出现 chat/artifact 记为失败。

### GREEN

1. 删除 runtime 的 artifact-first 指令重排与固定 chat 合成。
2. 在共享 service seam 引入 `NaturalChatFirstDeltaSequencer`，不增加协议 event type。
3. 前端首次自然 chat 单独 yield；正常独立 artifact 事件不增加固定等待。
4. 使用稳定语义 test id 观察 `ChatPane` / `ArtifactPane`，fixture chat marker 来自 mock 数据事实源。

### 聚焦证据

```bash
.venv/bin/python -m pytest \
  tools/new-agents/backend/tests/test_agent_runtime.py \
  tools/new-agents/backend/tests/test_stream_ordering.py \
  tools/new-agents/backend/tests/test_stream_services.py \
  tools/new-agents/backend/tests/test_agent_endpoint.py -q

cd tools/new-agents/frontend
npm run test -- --run \
  src/core/__tests__/llm.test.ts \
  src/services/__tests__/chatService.test.ts \
  src/components/__tests__/ChatPane.test.tsx \
  src/components/__tests__/ArtifactPane.test.tsx

cd ../../..
.venv/bin/python -m pytest -o addopts='' \
  tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py -q
```

## Task 2：Tracer B — provider 乱序、terminal/replay 与错误停止不泄露半成品

**用户可观察行为：** provider 即使先输出 artifact 或只在终态提供 chat，也必须先显示权威自然对话；若自然 chat 前失败，用户只看到 typed error，右栏不出现缓存半成品。

**Files:** 与 Task 1 共享 seam；重点为 `stream_ordering.py`、`stream_services.py`、`llm.ts` 及其测试。

### RED

1. artifact-only → 过短 chat fragment → final natural chat：fragment 不解锁，final chat-only 严格早于 artifact。
2. terminal-only、durable replay、同一 delta 含 chat/artifact：都拆成相同顺序。
3. artifact 缓存后 provider/schema/visual error：没有 artifact delta，发送 error 前显式 `discard()`。
4. 固定话术及其无标点/扩展前缀在 backend final contract 和 frontend terminal parser 都失败。
5. 正常 chat-only → 后续独立 artifact-only：不调用 render-commit barrier；只有同帧、缓存或 terminal-only 调用。

### GREEN

1. sequencer 只用达到最小可读长度且非占位前缀的 partial 解锁；final 仍由严格 `AgentTurnOutput` 契约裁决。
2. pending artifact 只保留最新合法状态，首个 chat frame 不携带 artifact/patch/stage action。
3. 所有 terminal error 从统一 helper 清空 pending；不吞原错误或构造成功。
4. frontend 保存“本事件前是否已有自然 chat”，据此决定是否需要 barrier。
5. Python/TypeScript 的固定话术、前缀和 partial 最小长度由 sync test 机械保护。

### 聚焦证据

```bash
.venv/bin/python -m pytest \
  tools/new-agents/backend/tests/test_agent_contracts.py \
  tools/new-agents/backend/tests/test_stream_ordering.py \
  tools/new-agents/backend/tests/test_stream_services.py \
  tools/new-agents/backend/tests/test_workflow_contract_sync.py -q

cd tools/new-agents/frontend
npm run test -- --run src/core/__tests__/llm.test.ts
```

## Task 3：Tracer C — Alex、阶段动作与 store/DOM 顺序保持一致

**用户可观察行为：** Alex `VALUE_DISCOVERY` 也使用同一顺序基础设施；右栏首帧之后才出现阶段确认，最终 artifact、版本和 stage action 不被排序层提前。

**Files:** `chatService.ts` 与测试、Pane 组件测试、browser workflow runner、Lisa/Alex E2E scenarios。

### RED / GREEN

1. store subscription 记录 assistant、artifact 与 pending transition；RED 锁定 transition 不能先于 artifact 状态。
2. 消费顺序保持 chat → artifact → pending stage transition；最终版本只保存一次。
3. Alex browser scenario 复用同一 runner，要求 `stream_order == ("chat", "artifact")`。
4. 浏览器不复制生产占位识别；直接匹配 fixture 的权威首段 chat marker，并把同一次 MutationObserver callback 的双栏变化判为 `simultaneous`。
5. 修复受影响的 React `act(...)` warning；不得屏蔽 console。

### 聚焦证据

```bash
cd tools/new-agents/frontend
npm run test -- --run \
  src/services/__tests__/chatService.test.ts \
  src/components/__tests__/ChatPane.test.tsx \
  src/components/__tests__/ArtifactPane.test.tsx

cd ../../..
.venv/bin/python -m pytest -o addopts='' \
  tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py \
  tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py -q
```

## Task 4：事实同步、正式审查、验证与单一交付

### 文档与状态

- 更新 `docs/TESTING.md`、`tools/new-agents/CONTEXT.md`。
- 旧 QS-02 spec/plan 只保留历史缓解说明，并链接当前 QG-017 设计。
- 活动 Todo 在验证前保持 `IN_PROGRESS`；只有审查与完成型验证通过后改为 DONE 并记录证据。

### 正式双轴审查

以 QG-017 开始前 commit 为固定点，审查完整厚切片：

- **Spec:** 25 stage、normal/artifact-first/terminal/replay/error、Lisa/Alex DOM、持久化和 stage action。
- **Standards:** 共享 runtime、typed SSE、无专属分支、无 silent fallback/假成功、配置镜像同步、纵向 tracer 计划。

所有 Critical/Important 必须关闭。修复后复审原 finding、修复 delta、相邻影响面与新增证据；不得以首次 review 替代复审。

### 完成型验证

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests -q
.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_browser -q
cd tools/new-agents/frontend && npm run test -- --run && npm run lint && npm run build
cd ../../.. && ./scripts/test/test-local.sh new-agents
./scripts/test/test-local.sh
flake8 --select=E9,F63,F7,F82 tools/new-agents tests/e2e/new_agents_browser
git diff --check
git status --short
```

缺依赖或服务必须修复；QG-017 不依赖 DeepSeek key。全量结果只对执行时的最终 diff 有效。

### 精确交付

1. 逐文件核对 diff 和启动前 dirty ownership。
2. 只 stage QG-017 spec/plan、实现、测试、事实文档和 Todo QG-017 状态；既有 Todo 清理按其已确认边界处理，不混入无关文件。
3. 运行 `git diff --cached --check`、检查 staged stat，再创建唯一提交：

```bash
git commit -m "fix(new-agents): 先展示自然对话再渲染产出物"
```

4. 记录 commit SHA。只有 QG-017 真正完成后，才进入 QG-018 的 ASSESS；不得提前修改 QG-018 实现。

## 执行结果（2026-07-16）

- Task 1～3 的 RED/GREEN 与跨层 tracer 均完成；Task 4 的 Spec/Standards 正式审查共 6 个 Important finding，修复后全部复审关闭，没有遗留 Critical/Important。
- 最终完成型验证：backend `944 passed, 1 skipped`；frontend `888 passed`、lint/build PASS；browser `18 passed, 3 skipped`；New Agents runner PASS；全仓 runner PASS；关键 flake8 与 `git diff --check` PASS。
- 早期全仓尝试的 Python/PATH 配置错误不计为通过；修正环境后曾观察到未改动 Intent CSP 测试的数据库清理干扰，随后单测、Intent 全量与最终全仓运行均通过，原始异常已在 owning Todo 结果中保留。
- 厚切片身份、边界和单一交付未改变；QG-018～QG-020 在本计划执行期间保持未开始。
