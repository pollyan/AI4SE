# QG-018 全阶段右侧分段流式实施计划

> **For agentic workers:** 必须按本计划顺序执行。所有 Task 都是 `QG-018` 厚切片内的内部 tracer，不得单独提交、push、验收或计算进度；只有 25-stage/7-workflow 全部门禁闭合后形成一个聚焦交付。

**Goal:** 让 7 个 workflow、25 个在线 stage 都在完整业务 section 闭合并通过局部 contract 后逐段更新右侧 artifact，保持 QG-017 chat-first、最终 deterministic Markdown、持久化和阶段流转不变。

**Architecture:** 在结构化业务数据到 deterministic artifact 的进程内 seam 建立共享 `ArtifactRenderPlan` 深模块；完整和 partial 使用同一 section 顺序、依赖、validator 与 renderer；backend 发送累计 replace，frontend 对同一模型 attempt 的 replace 做单调门禁，typed `agent_retry` 划定并重置 attempt；7 个 workflow 复用一个 headless DOM probe。禁止 25 个 runtime 分支、第二套 store/renderer、Markdown reverse parsing 或 partial 假成功。

**Tech Stack:** Python 3.11、Pydantic、Flask typed SSE、pytest；React 18、TypeScript 5、Zustand、Vitest/Testing Library；Python Playwright + headless Chromium。

**Design source:** [QG-018 设计与厚切片身份基线](../specs/2026-07-16-qg018-all-stage-paragraph-streaming-design.md)。顺序基线仍是 [当前唯一活跃 Todo](../../todos/2026-07-16-new-agents-streaming-and-artifact-ux.md#待办总览) 的 `QG-017 → QG-018 → QG-019 → QG-020`。

## 全局约束

- 先写能证明行为缺失的 RED，再改 production；每个 tracer 完成最小 GREEN 后立即跑聚焦回归。
- `workflow_manifest.json` 是在线 stage 顺序源；允许 code-level plan adapter mirror，但必须用集合相等与 fixture 矩阵机械保护。
- partial 只消费已经闭合的顶层 JSON member；不补值、不 `model_construct` 假成功、不放宽完整 schema。
- 单字段校验复用 full model annotation；跨引用/统计/派生约束抽共享 helper，由 full 与 partial projection 共用。
- 每个 partial section 单独通过 visual 校验；完整 model、完整 headings/visual contract、persistence 和 `stage_action` 只在 final 路径成立。
- QG-019 前保持现有 metadata 顺序；两次业务 snapshot 不能只靠 `document_info` 计数。
- browser mock 与前端 terminal synthetic reveal 只能证明确定性 UI contract，不升级成真实 backend/provider 证据。
- 启动前生成的 `tools/intent-tester/test-results/proxy/junit.xml` 改动保持未暂存；QG-018 不触碰 Intent Tester。

## Task 1：Tracer A — `REQ_REVIEW/REVIEW` 从闭合字段到两次独立 DOM 提交

**用户可观察行为：** Lisa 需求评审首阶段在自然对话后先显示评审信息/范围，再累积质量总览与后续问题章节；中间草稿在生成中可见，最终只保存一个版本。

**Files:**

- New deep module/tests: `tools/new-agents/backend/artifact_render_plan.py`, `backend/tests/test_artifact_render_plan.py`
- Stage adapter/runtime/tests: `backend/artifact_data_renderers.py`, `backend/agent_runtime.py`, `backend/tests/test_agent_runtime.py`, `backend/tests/test_stream_services.py`
- Frontend mapper/store/tests: `frontend/src/core/llm.ts`, `frontend/src/core/__tests__/llm.test.ts`, `frontend/src/services/chatService.ts`, `frontend/src/services/__tests__/chatService.test.ts`
- DOM fixture/probe: `tests/e2e/new_agents_browser/sse_mock.py`, `workflow_runner.py`, new `test_all_workflow_artifact_streaming.py`

### RED

1. `ArtifactRenderPlan` tracer 输入 `review_info → scope_items → quality_overview`：仅 metadata 的 `review_info` 不发送 artifact，`scope_items` 形成首个业务 result，`quality_overview` 形成下一累计 result；25-stage 全 fixture 矩阵另行要求每阶段至少三个业务 snapshots、稳定 `completed_section_ids`、每个 result visual 合法，full input 与现有 final Markdown 精确一致。
2. 无效 `issue_statistics` 或未知 issue reference 只暂扣依赖 section；已经完成的 review info/scope 不消失；完整 render 仍抛 ValidationError。
3. raw runtime 把真实 JSON 切在两个 business block 边界，要求 `meaningful chat-only → artifact A → cumulative B → final AgentTurnOutput`；A/B 都严格早于 final，无 patch/`stage_action`。
4. typed SSE mapper/store 通过 promise gate 暂停三份 replace，断言生成中 A、B 依次可见、artifact history 为 0、成功后仅 final 一版。
5. frontend 输入删除、缩短或改写已完成 section 的 replace，要求显式 stream contract error，旧稿不被覆盖。
6. headless `REQ_REVIEW/REVIEW` probe 使用浏览器 `ReadableStream` 分时 enqueue chat/A/B/final；当前单-full-delta fixture 应无法得到三个独立 marker commit。

### GREEN

1. 建立 `ArtifactRenderPlan` / `ArtifactSectionSpec` / `RenderedArtifact`，把字段 annotation validation、projection validation、per-section visual validation 与累计 Markdown 隐藏在小 interface 后。
2. 先把 `REQ_REVIEW/REVIEW` 的完整 renderer 与 partial renderer迁入同一 plan；仅为 tracer 所需的临时接线不得提交为最终兼容层，Task 2 必须消除剩余旧 tuple/专属 partial 分支。
3. runtime 完整流式 Markdown 直接调用 render plan，不再为了取 Markdown 构造带伪 chat 的 `AgentTurnOutput`。
4. frontend mapper 在单次 turn 内跟踪最新 replace，并用 heading anchor/内容前缀规则拒绝回退；patch、版本恢复、新 stage 不走该门禁。
5. 建立共享 browser `run_artifact_stream_probe`，observer 只依赖 semantic test id 与 fixture marker，不复制 renderer 业务规则。

### 聚焦证据

```bash
.venv/bin/python -m pytest \
  tools/new-agents/backend/tests/test_artifact_render_plan.py \
  tools/new-agents/backend/tests/test_agent_runtime.py \
  tools/new-agents/backend/tests/test_stream_services.py -q

cd tools/new-agents/frontend
npm run test -- --run \
  src/core/__tests__/llm.test.ts \
  src/services/__tests__/chatService.test.ts

cd ../../..
.venv/bin/python -m pytest -o addopts='' \
  tests/e2e/new_agents_browser/test_all_workflow_artifact_streaming.py \
  -k req_review -q
```

## Task 2：Tracer B — 高风险引用/派生/visual 约束与 19-shape/25-key 扩展

**用户可观察行为：** Strategy、Cases、Root Cause 等复杂 stage 也只显示引用、统计与可视化均已可信的完整章节；一个坏 section 不会撤回其他已完成章节，final 无效时仍显式失败。

**Files:**

- Plans/schemas/renderers: `backend/artifact_render_plan.py`, `artifact_data_renderers.py`, `artifact_data_renderer_value.py`, `artifact_data_value_schema.py`
- Contract/sync tests: `backend/tests/test_artifact_render_plan.py`, `test_artifact_data_renderers.py`, `test_agent_runtime.py`, `test_workflow_contract_sync.py`, `test_deepseek_v4_readiness.py`

### RED

1. 集合相等 RED：manifest online keys = artifactDataContract keys = plan adapter keys = instruction keys = fixture keys = 25；每个 key 至少三个可观察的 `role=business` snapshot。
2. `TEST_DESIGN/STRATEGY` 按 summary/goals/risks/引用组闭合，证明两个以上真实 snapshot；未知 QG/R/TS/TP 或错误 RPN 暂扣相关 block，已显示章节不回退。
3. `TEST_DESIGN/CASES` 全未 checked 的 `stage_gate` 必须让 full/partial 共同失败；当前 schema 应 RED。
4. `INCIDENT_REVIEW/ROOT_CAUSE` 重复 Why level、全未 checked gate 必须让 full/partial 共同失败；当前 schema 应 RED。
5. 25-stage fixture 逐 field 闭合：至少三个 business snapshots、completed block set 单调、每份 visual 合法、full partial 精确等于 canonical complete renderer。
6. representative invalid field/reference/visual matrices 证明只暂扣相关 block，最终完整 model 仍失败。

### GREEN

1. 把 19 种 document shape 的 title/ordered blocks 声明为 plan；25 个 stage 只做 adapter 注册，Story 4 key 复用一个 plan，PRD 4 key 使用 projection adapter，runtime 无 stage `if/elif`。
2. 删除旧 `_render_partial_test_design_clarify_markdown` 与单 stage partial 分支；完整 renderer wrapper 也委托同一 plan，消除 final/partial 顺序双事实源。
3. 按现有 parent model validators 抽取可复用 consistency helpers；字段或 projection 未能证明时暂扣，不用宽松 fallback。
4. 修复 CASES gate、ROOT_CAUSE Why 唯一性/gate 漂移，并同步最小 manifest/full/partial contract tests。
5. `render_available(full_fixture)` 与 `render_complete(full_fixture)` 使用同一 sections，existing headings/visual renderer tests 保持绿色。

### 聚焦证据

```bash
.venv/bin/python -m pytest \
  tools/new-agents/backend/tests/test_artifact_render_plan.py \
  tools/new-agents/backend/tests/test_artifact_data_renderers.py \
  tools/new-agents/backend/tests/test_agent_runtime.py \
  tools/new-agents/backend/tests/test_workflow_contract_sync.py \
  tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q
```

## Task 3：Tracer C — 7-workflow typed SSE → store → headless DOM 一致性

**用户可观察行为：** 每个 workflow 至少一个首阶段都在真实 React DOM 中出现两个独立业务增量并最终收敛，既有完整 workflow 流转、QG-017 chat-first 和 ArtifactPane section 复用不退化。

**Files:**

- Browser fixtures/probe: `tests/e2e/new_agents_browser/sse_mock.py`, `workflow_runner.py`, `test_all_workflow_artifact_streaming.py`，必要时 `conftest.py`
- Frontend render tests: `frontend/src/components/__tests__/ArtifactPane.incrementalRender.test.tsx` 与受影响 mapper/store tests
- Shared docs: `docs/TESTING.md`, `tools/new-agents/CONTEXT.md`, 当前 Todo

### RED / GREEN

1. 参数化 7 个首阶段：CLARIFY、REVIEW、TIMELINE、DEFINE、ELEVATOR、INPUT_ANALYSIS、INVENTORY；每个 fixture 提供两个业务 marker 和 final marker，统一 `ReadableStream` 分时发送 typed SSE。
2. 单个 MutationObserver 要求 `chat → artifact-1 → artifact-2 → final` 的 marker 顺序，至少三个 artifact snapshot 分属独立 commit；section 集合只增不减，最终内容精确一致。
3. 不直接写 Zustand、不截图、不用 terminal synthetic reveal；浏览器 fixture 仍走 frontend fetch/SSE parser/mapper/store/ArtifactPane。
4. ArtifactPane memo test 插入一个此前暂扣的中间 section，断言已有 heading anchor 的 render count 不增加。
5. 运行既有 Lisa/Alex 完整 workflow，确认 stage transition、历史 stage artifact 与 QG-017 `chat → artifact` 顺序不变。
6. 更新测试事实文档和 Todo 的 QG-018 进度；验证前仍保持 `IN_PROGRESS`。

### 聚焦证据

```bash
cd tools/new-agents/frontend
npm run test -- --run \
  src/core/__tests__/llm.test.ts \
  src/services/__tests__/chatService.test.ts \
  src/components/__tests__/ArtifactPane.incrementalRender.test.tsx

cd ../../..
.venv/bin/python -m pytest -o addopts='' \
  tests/e2e/new_agents_browser/test_all_workflow_artifact_streaming.py -q
.venv/bin/python -m pytest -o addopts='' \
  tests/e2e/new_agents_browser -q
```

## Task 4：正式审查、完成型验证与单一交付

### 正式双轴审查

以 QG-018 开始点 `8d00bb36` 为 fixed point，形成一个完整 review package：

- **Spec:** 25/25 plan、至少三个业务 snapshots、局部 schema/ref/visual、final exact、frontend regression guard、7-workflow DOM、persistence/stage action、QG-017 interaction。
- **Standards:** shared runtime/typed SSE、一个 registry/plan seam、无 stage runtime 分支、无 reverse parsing、无 silent fallback/假成功、manifest mirrors 机械同步、纵向 tracer 计划与 dirty ownership。

所有 Critical/Important 必须修复并复审关闭；首次审查与修复复审是一个 QG-018 审查门禁，不是两个切片。

### 完成型验证

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests -q
cd tools/new-agents/frontend && npm run test -- --run && npm run lint && npm run build
cd ../../..
.venv/bin/python -m pytest -o addopts='' tests/e2e/new_agents_browser -q
./scripts/test/test-local.sh new-agents
./scripts/test/test-local.sh
.venv/bin/python -m flake8 --select=E9,F63,F7,F82 \
  tools/new-agents tests/e2e/new_agents_browser
git diff --check
git status --short
```

外部模型/key 不是 QG-018 依赖。任何 `FAIL`/`FLAKY` 不得被重跑覆盖；先保留首次错误并诊断。全量 runner 生成的 Intent JUnit 报告不属于本切片，不得暂存。

### 精确交付

1. Todo 仅在正式审查与最终验证通过后把 QG-018 改为 DONE，记录 25-stage、7-workflow 与完整 runner 证据；下一入口写为 QG-019 ASSESS。
2. 逐文件核对 diff；启动前无 staged 项，Intent JUnit 保持 unstaged。只 stage QG-018 spec/plan、实现、测试和事实文档。
3. 运行 `git diff --cached --check`、检查 staged name/status/stat，创建唯一聚焦提交：

```bash
git commit -m "fix(new-agents): 统一全阶段产出物分段流式"
```

4. 记录 commit SHA 并按 Playbook push。只有远端同步成功且 QG-018 交付事实稳定后，才进入 QG-019；不得提前修改元信息布局。
