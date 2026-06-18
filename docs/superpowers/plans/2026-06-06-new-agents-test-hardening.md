# New Agents Test Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐 New Agents 智能体链路的 P0 场景覆盖：后端 agent endpoint 异常 typed SSE、前端 chatService 错误/停止收尾、失败时 artifact 不被污染。

**Architecture:** 后端保持 `routes.py -> stream_services.py -> agent_runtime.py` 的职责边界，测试从 Flask endpoint 层验证 SSE 契约，不让异常变成 HTML 500。前端保持 `llm.ts` 负责流解析，`chatService.ts` 负责消息、artifact、生成状态写入，测试用 mock async generator 覆盖用户可见状态。

**Tech Stack:** pytest + Flask test_client + PydanticAI exceptions, Vitest + React Testing Library hooks + Zustand store.

---

## File Structure

- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
  - 增加 endpoint 层 typed SSE error 测试。
  - 覆盖 runtime 构建/依赖失败和模型结构化输出失败。
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`
  - 增加首 chunk 前失败、中途失败、用户停止、quota 友好错误、失败不新增 artifact version 的测试。
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`
  - 仅在本轮生成实际写入 artifact 时，才在 `finally` 追加 artifact version。
  - 保持现有左右栏写入和阶段推进行为。

## Task 1: Backend Agent Endpoint Typed SSE Errors

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [ ] **Step 1: Write failing endpoint tests**

Add helpers and tests:

```python
from agent_runtime import AgentRuntimeDependencyError
from pydantic_ai.exceptions import UnexpectedModelBehavior


def _parse_sse_event_payloads(response):
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.get_data(as_text=True).splitlines()
        if line.startswith("data: {")
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_agent_runs_stream_returns_typed_error_when_runtime_dependency_missing(
    mock_build_runtime,
    client,
    default_config,
):
    mock_build_runtime.side_effect = AgentRuntimeDependencyError(
        "pydantic-ai runtime unavailable"
    )

    response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "用户需求: 登录功能",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        },
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert response.get_data(as_text=True).strip().endswith("data: [DONE]")
    assert _parse_sse_event_payloads(response) == [
        {
            "type": "error",
            "code": "AGENT_RUNTIME_UNAVAILABLE",
            "message": "pydantic-ai runtime unavailable",
        }
    ]


@patch("stream_services.build_pydantic_agent_runtime")
def test_agent_runs_stream_returns_typed_error_when_model_output_exceeds_retries(
    mock_build_runtime,
    client,
    default_config,
):
    runtime = FakeRuntime()
    runtime.run_turn = lambda *args, **kwargs: (_ for _ in ()).throw(
        UnexpectedModelBehavior("Exceeded maximum output retries (3)")
    )
    mock_build_runtime.return_value = runtime

    response = client.post(
        "/api/agent/runs/stream",
        json={
            "prompt": "用户需求: 登录功能",
            "systemPrompt": "你是 Lisa 测试专家。",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
        },
    )

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert _parse_sse_event_payloads(response) == [
        {
            "type": "error",
            "code": "SCHEMA_VALIDATION_FAILED",
            "message": "Exceeded maximum output retries (3)",
        }
    ]
```

- [ ] **Step 2: Run focused backend tests to verify behavior**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q
```

Expected: tests should pass if service mapping is already correct; if they fail with 500 or missing typed event, fix only the minimal endpoint/service gap.

## Task 2: Frontend chatService Error and Abort Scenarios

**Files:**
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`
- Modify if needed: `tools/new-agents/frontend/src/services/chatService.ts`

- [ ] **Step 1: Write failing frontend tests**

Add tests:

```typescript
it('should show an assistant error message before the first stream chunk without changing artifact', async () => {
    vi.mocked(generateResponseStream).mockImplementation(async function* () {
        throw new Error('SCHEMA_VALIDATION_FAILED');
    });

    const { result } = renderHook(() => useChatService());

    act(() => {
        result.current.setInput('触发错误');
    });

    await act(async () => {
        await result.current.handleSend();
    });

    const state = useStore.getState();
    expect(state.chatHistory).toHaveLength(2);
    expect(state.chatHistory[1]).toMatchObject({
        role: 'assistant',
        content: '**Error:** SCHEMA_VALIDATION_FAILED',
    });
    expect(state.artifactContent).toBe('initial artifact');
    expect(state.artifactHistory).toEqual([]);
    expect(state.isGenerating).toBe(false);
});

it('should append an error to the in-progress assistant message when stream fails after a chunk', async () => {
    vi.mocked(generateResponseStream).mockImplementation(async function* () {
        yield {
            chatResponse: '正在分析...',
            newArtifact: 'initial artifact',
            action: '',
            hasArtifactUpdate: false,
        };
        throw new Error('LLM_ERROR');
    });

    const { result } = renderHook(() => useChatService());

    act(() => {
        result.current.setInput('中途失败');
    });

    await act(async () => {
        await result.current.handleSend();
    });

    const state = useStore.getState();
    expect(state.chatHistory).toHaveLength(2);
    expect(state.chatHistory[1].content).toBe(
        '正在分析...\n\n**Error:** LLM_ERROR'
    );
    expect(state.artifactContent).toBe('initial artifact');
    expect(state.artifactHistory).toEqual([]);
});

it('should mark an in-progress response as stopped without rendering an error', async () => {
    vi.mocked(generateResponseStream).mockImplementation(async function* () {
        yield {
            chatResponse: '正在生成...',
            newArtifact: 'initial artifact',
            action: '',
            hasArtifactUpdate: false,
        };
        throw new Error('Aborted by user');
    });

    const { result } = renderHook(() => useChatService());

    act(() => {
        result.current.setInput('停止生成');
    });

    await act(async () => {
        await result.current.handleSend();
    });

    const state = useStore.getState();
    expect(state.chatHistory[1].content).toBe(
        '正在生成...\n\n*(已停止生成)*'
    );
    expect(state.chatHistory[1].content).not.toContain('**Error:**');
    expect(state.artifactHistory).toEqual([]);
});

it('should show a friendly quota message when the model returns quota errors', async () => {
    vi.mocked(generateResponseStream).mockImplementation(async function* () {
        throw new Error('429 quota exceeded');
    });

    const { result } = renderHook(() => useChatService());

    act(() => {
        result.current.setInput('额度错误');
    });

    await act(async () => {
        await result.current.handleSend();
    });

    const state = useStore.getState();
    expect(state.chatHistory[1].content).toContain('模型额度或限流异常');
    expect(state.chatHistory[1].content).toContain('429 quota exceeded');
});
```

- [ ] **Step 2: Run focused frontend tests and inspect failures**

Run:

```bash
cd tools/new-agents/frontend && npm test -- --run src/services/__tests__/chatService.test.ts
```

Expected: at least the artifact history assertions fail before implementation, because `finally` currently records unchanged initial artifact after failed sends.

- [ ] **Step 3: Minimal implementation**

In `chatService.ts`, track whether this send actually wrote an artifact:

```typescript
let didUpdateArtifact = false;
```

Set it inside the existing `if (decision.artifactUpdate)` block:

```typescript
didUpdateArtifact = true;
```

Guard artifact version creation:

```typescript
if (didUpdateArtifact) {
    const state = useStore.getState();
    const artifactVersionPlan = planArtifactVersionUpdate(
        state.artifactContent,
        state.artifactHistory
    );
    if (artifactVersionPlan) {
        useStore.getState().addArtifactVersion({
            id: Date.now().toString(),
            timestamp: Date.now(),
            content: artifactVersionPlan.content
        });
    }
}
```

- [ ] **Step 4: Verify focused frontend tests pass**

Run:

```bash
cd tools/new-agents/frontend && npm test -- --run src/services/__tests__/chatService.test.ts
```

Expected: all `chatService.test.ts` tests pass.

## Task 3: Full Verification

**Files:** no additional edits expected.

- [ ] **Step 1: Run backend non-slow suite**

```bash
cd tools/new-agents/backend && python3 -m pytest -m "not slow" -q
```

Expected: all non-slow backend tests pass.

- [ ] **Step 2: Run frontend full suite**

```bash
cd tools/new-agents/frontend && npm test
```

Expected: all frontend tests pass.

- [ ] **Step 3: Run frontend type check**

```bash
cd tools/new-agents/frontend && npm run lint
```

Expected: TypeScript exits 0.

- [ ] **Step 4: Run repository syntax and whitespace checks**

```bash
flake8 --select=E9,F63,F7,F82 .
git diff --check
```

Expected: both commands exit 0.

## Self-Review

- Spec coverage: covers backend endpoint typed errors, frontend first-chunk failure, midstream failure, abort handling, quota-friendly display, and failure-time artifact version pollution.
- Placeholder scan: no TBD/TODO/implement later placeholders.
- Type consistency: frontend test chunks match `generateResponseStream` yielded object shape; backend tests reuse existing `FakeRuntime`, `default_config`, and Flask test client patterns.
