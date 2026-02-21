# Smoke Test 产出物语义验证增强实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 增强 Lisa 冒烟测试，在每轮对话结束后对产出物（Artifact）的核心内容进行"精准切片式语义验证"，确保产出物与对话上下文语义一致。

**Architecture:** 采用"精准切片 + LLM-as-Judge"混合策略。从 SSE 事件流中提取 `data` 类型事件携带的 `structured_artifacts` 数据（而非 `tool-output-available`，因为后者只有 success 字符串），按业务维度切片后交由轻量级 Judge 验证语义正确性。每次 Judge 调用只传入几十行 JSON 切片而非完整产出物，确保耗时控制在 1-2 秒/次。

**Tech Stack:** Python, pytest, LangChain (ChatOpenAI), JSON

**核心设计决策：**
1. **产出物内容获取方式**：当前 ArtifactNode 的 writer 发送的 `tool-call` 事件只包含 `{"key": "xxx"}` 和 `"success"` 字符串，不包含产出物内容。产出物内容通过 `progress` 类型的 `data` 事件传递（`stream_data(progress, "progress")` → SSE `data` 事件）。我们需要在 `sse_parser.py` 中新增一个函数来从 `data` 事件中提取 `structured_artifacts`。
2. **切片策略**：不全量传递产出物 JSON 给 Judge，而是按轮次只提取当前最需验证的字段切片（如 R2 只验证 `assumptions`，R4 只验证 `cases` 中前 2 个用例）。
3. **Judge 复用**：扩展现有的 `judge.py`，新增一个 `judge_artifact_slice()` 函数，接收 JSON 切片和预期行为描述。

---

## Task 1: 在 sse_parser.py 中新增结构化产出物提取函数

**Files:**
- Modify: `tools/ai-agents/backend/tests/agent_smoke/sse_parser.py`

**Goal:** 新增 `extract_structured_artifacts()` 函数，从 SSE 事件流中提取 `structured_artifacts` 数据。

**背景分析：** SSE 流的数据事件有两类来源：
1. `tool-input-available` / `tool-output-available`：只含 key 和 success 字符串，不含内容。  
2. `data` 事件（type="data"）：来自 `stream_data(progress_data, "progress")`，其中 `progress_data` 可能包含 `structured_artifacts` 字段（当 `updates` 模式将 `structured_artifacts` 传入 `current_state` 后，`get_progress_info` 可能不会透传它）。

**实际数据流路径**（经代码分析确认）：
- `artifact_node.py` 第 211-220 行：writer 发送 `tool-call` 事件，args 只有 key
- `service.py` 第 396-399 行：`updates` mode 将 `structured_artifacts` 存入 `current_state`
- `service.py` 第 436-438 行：最终通过 `get_progress_info(current_state)` 发送 state 事件
- `data_stream_adapter.py` 第 40-46 行：state 事件被包装为 `stream_data(progress, "progress")` 

**[关键发现]** 经过分析，`get_progress_info()` 不会透传 `structured_artifacts`（它只提取 stages、artifacts 的 keys 等进度元数据）。因此，**结构化产出物内容不会出现在 SSE 流中**。

**解决方案：** 不从 SSE 流提取内容，而是**新增一个从 LangGraph Checkpointer 直接读取 State 快照的辅助函数**。在 `conftest.py` 中暴露 `graph` 实例，冒烟测试通过 `graph.get_state(config)` 读取最新的 `structured_artifacts`。

**Step 1: 确认 get_progress_info 不包含 structured_artifacts**

Run: `cd tools/ai-agents && python3 -c "from backend.agents.shared.progress import get_progress_info; import json; state = {'plan': [{'id': 'clarify', 'name': 'Test'}], 'current_stage_id': 'clarify', 'artifacts': {'k1': 'v1'}, 'structured_artifacts': {'k1': {'scope': ['x']}}}; result = get_progress_info(state); print('structured_artifacts' in json.dumps(result))"`
Expected: `False`（确认 structured_artifacts 不出现在 progress_info 中）

**Step 2: 在 conftest.py 新增 `lisa_graph` fixture**

在 `tools/ai-agents/backend/tests/agent_smoke/conftest.py` 中新增 fixture，暴露 LangGraph 实例以便测试读取 State：

```python
@pytest.fixture
def lisa_graph(real_ai_config):
    """
    暴露 Lisa 的 LangGraph 实例，用于测试中读取 State 快照。
    
    使用方式: state = lisa_graph.get_state({"configurable": {"thread_id": session_id}})
    """
    import asyncio
    from backend.agents.service import LangchainAssistantService
    
    service = LangchainAssistantService("lisa")
    asyncio.get_event_loop().run_until_complete(service.initialize())
    return service.agent
```

**Step 3: 在 sse_parser.py 新增 read_structured_artifact 辅助函数**

```python
def read_structured_artifact(
    graph, session_id: str, artifact_key: str
) -> dict:
    """
    从 LangGraph State 快照中读取指定的结构化产出物。
    
    Args:
        graph: LangGraph CompiledGraph 实例
        session_id: 会话 ID (thread_id)
        artifact_key: 产出物 key，如 "test_design_requirements"
    
    Returns:
        dict: 结构化产出物 JSON 对象，未找到返回空字典
    """
    import asyncio
    config = {"configurable": {"thread_id": session_id}}
    state = asyncio.get_event_loop().run_until_complete(
        graph.aget_state(config)
    )
    structured = state.values.get("structured_artifacts", {})
    artifact = structured.get(artifact_key, {})
    if hasattr(artifact, "model_dump"):
        return artifact.model_dump()
    return artifact if isinstance(artifact, dict) else {}
```

**Step 4: 验证修改**

Run: `cd tools/ai-agents && python3 -c "from backend.tests.agent_smoke.sse_parser import read_structured_artifact; print('OK')"`
Expected: OK

**Step 5: Commit**

```bash
git add tools/ai-agents/backend/tests/agent_smoke/sse_parser.py tools/ai-agents/backend/tests/agent_smoke/conftest.py
git commit -m "feat(smoke): add structured artifact reader from LangGraph state"
```

---

## Task 2: 在 judge.py 中新增 judge_artifact_slice 函数

**Files:**
- Modify: `tools/ai-agents/backend/tests/agent_smoke/judge.py`

**Goal:** 新增 `judge_artifact_slice()` 函数，接收 JSON 切片和预期行为描述，用 LLM 进行语义判定。

**Step 1: 在 judge.py 中添加 Artifact Judge 的 System Prompt 和函数**

在 `judge.py` 末尾追加：

```python
ARTIFACT_JUDGE_SYSTEM = (
    "你是一个严格的测试评估专家，负责评估 AI 智能体生成的结构化产出物是否符合预期。\n"
    "你会收到一段 JSON 格式的产出物切片和预期行为描述。\n"
    "请判断该 JSON 切片是否在语义上满足预期行为。\n"
    "你必须只返回一个 JSON 对象，包含 passed (bool) 和 reason (string) 两个字段。\n"
    "禁止输出 Markdown 代码块、引言或任何额外文字。"
)

ARTIFACT_JUDGE_USER = """请判断以下产出物 JSON 切片是否满足预期。

## 对话背景
{conversation_context}

## 预期行为
{expected_behavior}

## 产出物 JSON 切片
```json
{artifact_slice}
```

## 评估标准
1. JSON 切片中的字段值必须与对话背景中的信息语义一致。
2. 如果预期行为中要求某些字段状态变化（如 status 从 pending 变为 confirmed），必须验证是否已变化。
3. 不要求文字完全匹配，但内容的业务含义必须正确。
4. 如果 JSON 切片为空或缺少关键字段，判定为不通过。"""


def judge_artifact_slice(
    conversation_context: str,
    expected_behavior: str,
    artifact_slice: str,
) -> JudgeResult:
    """
    用 LLM 评估产出物 JSON 切片的语义正确性。

    Args:
        conversation_context: 对话背景摘要（如"用户确认了密码不需要特殊字符"）。
        expected_behavior: 用自然语言描述的预期行为。
        artifact_slice: 产出物 JSON 切片（字符串）。

    Returns:
        JudgeResult: 包含 passed（bool）和 reason（str）。
    """
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("SMOKE_TEST_JUDGE_MODEL", "deepseek-v3.2")

    llm = ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,  # type: ignore[arg-type]
        temperature=0
    )
    response = llm.invoke([
        SystemMessage(content=ARTIFACT_JUDGE_SYSTEM),
        HumanMessage(content=ARTIFACT_JUDGE_USER.format(
            conversation_context=conversation_context,
            expected_behavior=expected_behavior,
            artifact_slice=artifact_slice
        ))
    ])
    
    import json as json_module
    try:
        content = str(response.content).strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        data = json_module.loads(content)
        result = JudgeResult(**data)
        logger.info(
            f"Artifact Judge 结果: passed={result.passed}, "
            f"reason={result.reason}"
        )
        return result
    except Exception as e:
        logger.error(
            f"解析 Artifact Judge JSON 失败: {e}\n"
            f"Raw={response.content}"
        )
        return JudgeResult(
            passed=False,
            reason=f"Artifact Judge failed to parse JSON: {e}"
        )
```

**Step 2: 验证导入**

Run: `cd tools/ai-agents && python3 -c "from backend.tests.agent_smoke.judge import judge_artifact_slice; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add tools/ai-agents/backend/tests/agent_smoke/judge.py
git commit -m "feat(smoke): add judge_artifact_slice for semantic artifact validation"
```

---

## Task 3: 在 test_lisa_happy_path.py 的 R2 轮次增加 Assumptions 语义断言

**Files:**
- Modify: `tools/ai-agents/backend/tests/agent_smoke/test_lisa_happy_path.py`

**Goal:** 在 R2 (用户确认需求) 执行完毕后，从 LangGraph State 中提取 `assumptions` 切片，用 `judge_artifact_slice` 验证所有 assumptions 是否都已从 pending 变为 confirmed 状态。

**Step 1: 更新 import 和 fixture 引用**

在 `test_lisa_happy_path.py` 顶部的 import 中增加：

```python
from .sse_parser import (
    send_and_collect,
    extract_full_text,
    extract_tool_trajectory,
    assert_stream_integrity,
    read_structured_artifact,         # 新增
)
from .judge import judge_output, judge_artifact_slice  # 新增 judge_artifact_slice
```

更新测试方法签名，增加 `lisa_graph` fixture：

```python
def test_full_workflow_journey(
    self, client, lisa_session, lisa_graph  # 新增 lisa_graph
):
```

**Step 2: 在 R2 断言块中增加 Assumptions 语义验证**

在 R2 阶段的 `assert r2_verdict.passed` 之后（约第 161 行之后），追加：

```python
        # ═══ R2 产出物语义验证: Assumptions 状态同步 ═══
        r2_artifact = read_structured_artifact(
            lisa_graph, lisa_session, "test_design_requirements"
        )
        assumptions = r2_artifact.get("assumptions", [])
        import json
        assumptions_json = json.dumps(
            assumptions, ensure_ascii=False, indent=2
        )

        r2_artifact_verdict = judge_artifact_slice(
            conversation_context=(
                "用户在 R2 中回答了所有待确认问题：\n"
                f"{CONFIRM_REQUIREMENTS}"
            ),
            expected_behavior=(
                "所有 assumptions 条目的 status 都应该从 'pending' "
                "变为 'confirmed' 或 'assumed'。\n"
                "每个 assumption 的 note 字段应包含"
                "用户确认的结论摘要。\n"
                "不应有任何条目的 status 仍为 'pending'。"
            ),
            artifact_slice=assumptions_json,
        )
        assert r2_artifact_verdict.passed, (
            f"R2 产出物 assumptions 状态未同步: "
            f"{r2_artifact_verdict.reason}\n"
            f"实际 assumptions: {assumptions_json[:500]}"
        )
```

**Step 3: 在 R4 断言块中增加 Cases 语义验证**

在 R4 阶段的 `assert r4_reply_verdict.passed` 之后（约第 225 行之后），追加：

```python
        # ═══ R4 产出物语义验证: 测试用例内容 ═══
        r4_artifact = read_structured_artifact(
            lisa_graph, lisa_session, "test_design_cases"
        )
        cases = r4_artifact.get("cases", [])
        # 只取前 3 个用例做语义验证，控制 Token 开销
        cases_slice = cases[:3] if len(cases) > 3 else cases
        import json
        cases_json = json.dumps(
            cases_slice, ensure_ascii=False, indent=2
        )

        r4_artifact_verdict = judge_artifact_slice(
            conversation_context=(
                "此测试针对 POST /api/login 接口，"
                "参数为手机号(11位)和密码(6-20位含字母数字)。\n"
                "业务规则：密码连续错误5次锁定30分钟，锁定期间返回锁定提示。\n"
                "用户已确认：密码不需要特殊字符，手机号仅限中国大陆格式。"
            ),
            expected_behavior=(
                "测试用例应覆盖登录功能的核心场景，包括但不限于：\n"
                "1. 正常登录成功\n"
                "2. 密码格式校验（如纯数字、纯字母等非法密码）\n"
                "3. 手机号格式校验\n"
                "4. 密码连续错误锁定机制\n"
                "每个用例应有明确的步骤(steps)和预期结果(expect)。\n"
                "用例内容必须与登录功能相关，不能出现注册、找回密码等范围外的用例。"
            ),
            artifact_slice=cases_json,
        )
        assert r4_artifact_verdict.passed, (
            f"R4 产出物 cases 内容不合理: "
            f"{r4_artifact_verdict.reason}\n"
            f"实际用例切片: {cases_json[:500]}"
        )
```

**Step 4: 验证语法**

Run: `cd tools/ai-agents && python3 -c "import ast; ast.parse(open('backend/tests/agent_smoke/test_lisa_happy_path.py').read()); print('Syntax OK')"`
Expected: Syntax OK

**Step 5: Commit**

```bash
git add tools/ai-agents/backend/tests/agent_smoke/test_lisa_happy_path.py
git commit -m "feat(smoke): add artifact semantic validation for R2 assumptions and R4 cases"
```

---

## Task 4: 运行冒烟测试并验证

**注意:** 冒烟测试需要真实的 LLM API Key，标记为 `@pytest.mark.slow`。

**Step 1: 先运行常规单元测试确保没有破坏**

Run: `cd tools/ai-agents && pytest backend/tests/ -v --ignore=backend/tests/agent_smoke -x`
Expected: 全部通过

**Step 2: 运行冒烟测试（需要 API Key）**

Run: `cd tools/ai-agents && pytest backend/tests/agent_smoke/test_lisa_happy_path.py -v -s --timeout=300`
Expected: 所有断言通过，包括新增的 R2 assumptions 和 R4 cases 语义验证

**Step 3: 如果 aget_state 报错，改用同步 get_state**

如果 `asyncio.get_event_loop().run_until_complete(graph.aget_state(config))` 出现 event loop 问题，
将 `read_structured_artifact` 中的调用改为：
```python
state = graph.get_state(config)
```
（注意：LangGraph 的 CompiledGraph 同时提供同步和异步接口）

**Step 4: Commit（如有修复）**

```bash
git add -A
git commit -m "fix(smoke): adjust state reader for event loop compatibility"
```

---

## Task 5: 运行全量测试并推送

**Step 1: 运行本地全量测试**

Run: `./scripts/test/test-local.sh`
Expected: 所有测试通过

**Step 2: 推送代码**

```bash
git push
```
