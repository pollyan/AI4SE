from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import pytest
import requests

from .workflow_runner import WorkflowRunResult

ROOT = Path(__file__).resolve().parents[3]
DOTENV_PATH = ROOT / ".env"
_DOTENV_LOADED = False


@dataclass(frozen=True)
class JudgeResult:
    passed: bool
    score: int
    dimension_scores: dict[str, int]
    issues: list[str]
    evidence: list[str]
    recommendations: list[str]


MIN_LLM_JUDGE_SCORE = 80
MIN_VISUALIZATION_QUALITY_SCORE = 70
VISUALIZATION_DIMENSION_KEYWORDS = ("可视化", "visual")


def _load_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True

    if not DOTENV_PATH.exists():
        return

    dotenv_values: dict[str, str] = {}
    for raw_line in DOTENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            dotenv_values[key] = value

    for key, value in dotenv_values.items():
        if key not in os.environ:
            os.environ[key] = value


def is_llm_judge_enabled() -> bool:
    _load_dotenv()
    return os.environ.get("NEW_AGENTS_E2E_LLM_JUDGE") == "1"


def _professional_rubric(workflow_name: str) -> str:
    if workflow_name.startswith("Lisa"):
        return """
测试专家维度：
- 需求澄清：是否识别业务边界、外部依赖、阻断问题和隐含假设。
- 风险识别：是否覆盖业务风险、安全风险、数据一致性风险和非功能风险。
- 测试策略：是否有清晰分层、优先级、准入准出和风险缓解策略。
- 测试用例：是否包含前置条件、操作步骤、预期结果、优先级和可执行细节。
- 覆盖追溯：需求、风险、测试点和用例之间是否能互相追溯。
- 边界条件：是否覆盖空值、边界值、状态边界、权限边界和流程边界。
- 异常路径：是否覆盖失败、超时、重试、并发、幂等和降级场景。
- 非功能需求：是否覆盖性能、安全、兼容性、可观测性和审计要求。
- 可执行性：输出是否足够具体，测试团队能直接评审、拆分和执行。
""".strip()
    if workflow_name.startswith("Alex"):
        return """
业务分析师维度：
- 问题定义：是否清楚描述用户问题、业务背景和成功标准。
- 用户画像：是否识别核心用户、关键使用者、决策者和他们的痛点。
- 用户旅程：是否覆盖触发、使用、协作、交付和复盘等关键阶段。
- 价值主张：是否说明差异化价值、替代方案和用户愿意采用的理由。
- 需求拆解：是否把目标拆成可验收、可排序、可迭代的需求。
- 优先级：是否能区分 P0/P1/P2，并说明取舍依据。
- 验收标准：是否给出可验证的业务、产品和交互验收条件。
- 业务闭环：是否说明从需求蓝图梳理到交付、度量和反馈的闭环。
""".strip()
    return """
专业产物维度：
- 目标清晰：是否说明要解决的问题和用户价值。
- 结构完整：是否覆盖当前工作流要求的核心章节。
- 内容可用：是否避免空泛占位，能支持后续决策或执行。
- 证据充分：是否能从会话轨迹和阶段产物中找到判断依据。
""".strip()


def _judge_result_schema() -> str:
    return """
严格 JSON verdict：
{
  "pass": true,
  "score": 0,
  "dimension_scores": {
    "维度名称": 0
  },
  "issues": ["发现的问题"],
  "evidence": ["支持评分的具体证据"],
  "recommendations": ["下一步改进建议"]
}
字段要求：
- pass 必须是 boolean。
- score 必须是 0 到 100 的整数。
- dimension_scores 必须是非空对象，每个维度分数必须是 0 到 100 的整数。
- issues、evidence、recommendations 必须是字符串数组。
""".strip()


def build_judge_prompt(workflow_name: str, run_result: WorkflowRunResult) -> str:
    conversation_trace = "\n".join(
        f"- [{event.stage_name}] {event.role}: {event.content}"
        for event in run_result.conversation_events
    )
    stage_transitions = "\n".join(
        f"- {event.from_stage} -> {event.to_stage}: {event.action}"
        for event in run_result.stage_transitions
    )
    stage_artifacts = "\n\n".join(
        f"### {snapshot.stage_name}\n{snapshot.artifact}"
        for snapshot in run_result.stage_artifacts
    )

    return f"""
请评审以下 New Agents 浏览器测试运行结果是否满足 {workflow_name} 工作流质量要求。
只返回 JSON，不要返回 Markdown。
评审标准：
{_professional_rubric(workflow_name)}

交互体验维度：
- 对话引导是否清晰，是否说明正在使用的方法和原因。
- 是否突出关键风险、关键结论和需要用户确认的信息。
- 是否避免在左侧对话重复完整 artifact 正文。
- 阶段切换是否自然，用户补充是否被后续阶段正确吸收。

可视化维度：
- 图表、矩阵、时间线、看板或评分卡是否适合当前阶段。
- 可视化是否帮助快速理解重点，而不是只作为装饰。
- 可视化内容是否与正文一致，是否可渲染或可测试。
- 如果产物包含 ai4se-visual，评估其 JSON 类型是否适合当前阶段，且是否能由前端共享组件渲染。
- 如果产物包含 traceability-matrix，评估需求、风险、测试点和用例之间是否可追溯且与正文一致。
- dimension_scores 中必须包含“可视化质量”或等价维度分数。

{_judge_result_schema()}

完整会话轨迹：
{conversation_trace}

阶段切换：
{stage_transitions}

每阶段产物：
{stage_artifacts}

最终产物：
{run_result.final_artifact}
""".strip()


def build_handoff_judge_prompt(
    handoff_name: str,
    source_result: WorkflowRunResult,
    target_result: WorkflowRunResult,
) -> str:
    source_trace = "\n".join(
        f"- [{event.stage_name}] {event.role}: {event.content}"
        for event in source_result.conversation_events
    )
    target_trace = "\n".join(
        f"- [{event.stage_name}] {event.role}: {event.content}"
        for event in target_result.conversation_events
    )
    source_artifacts = "\n\n".join(
        f"### {snapshot.stage_name}\n{snapshot.artifact}"
        for snapshot in source_result.stage_artifacts
    )
    target_artifacts = "\n\n".join(
        f"### {snapshot.stage_name}\n{snapshot.artifact}"
        for snapshot in target_result.stage_artifacts
    )

    return f"""
请评审以下 New Agents 跨智能体接力是否满足 {handoff_name} 的专业连续性要求。
只返回 JSON，不要返回 Markdown。

跨智能体接力维度：
- 源产物继承：Lisa 是否明确继承 Alex 需求蓝图中的产品定位、用户场景、核心需求、风险和验收线索。
- 角色专业性转换：Alex 的业务/产品语言是否被 Lisa 转换为测试边界、风险、策略、测试点和用例，而不是简单复述。
- 上下文完整性：handoff 后是否保留源 workflow、源阶段、目标 workflow、目标阶段和关键 artifact 版本语义。
- 追溯连续性：Lisa 产物是否能追溯到 Alex 蓝图中的核心需求、风险和机会点。
- 风险延续：Alex 识别的关键业务风险是否进入 Lisa 的测试风险、优先级和覆盖设计。
- 执行落地：Lisa 输出是否形成可评审、可执行、可导出或可进入测试管理工具的资产。
- 体验连续性：用户是否能感知从 Alex 到 Lisa 的角色切换，且无需重复粘贴源产物。
- 可视化连续性：Lisa 是否保留或转换 Alex 产物中的图表、矩阵、路线图或追溯结构。

可视化质量维度：
- 图表、矩阵、时间线、看板或评分卡是否帮助用户理解跨 Agent 接力重点。
- dimension_scores 中必须包含“可视化质量”或等价维度分数。

Lisa 测试专业维度：
{_professional_rubric("Lisa 测试策略与用例设计")}

{_judge_result_schema()}

源 Alex 会话轨迹：
{source_trace}

源 Alex 阶段产物：
{source_artifacts}

源 Alex 最终产物：
{source_result.final_artifact}

目标 Lisa 会话轨迹：
{target_trace}

目标 Lisa 阶段产物：
{target_artifacts}

目标 Lisa 最终产物：
{target_result.final_artifact}
""".strip()


def parse_judge_result(content: str) -> JudgeResult:
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("judge result must be a JSON object")

    required_fields = (
        "pass",
        "score",
        "dimension_scores",
        "issues",
        "evidence",
        "recommendations",
    )
    for field in required_fields:
        if field not in parsed:
            raise ValueError(f"missing required judge result field: {field}")

    passed = parsed["pass"]
    if not isinstance(passed, bool):
        raise ValueError("pass must be a boolean")

    score = _parse_score(parsed["score"], "score")
    dimension_scores = parsed["dimension_scores"]
    if not isinstance(dimension_scores, dict) or not dimension_scores:
        raise ValueError("dimension_scores must be a non-empty object")
    normalized_dimension_scores: dict[str, int] = {}
    for dimension, value in dimension_scores.items():
        if not isinstance(dimension, str) or not dimension.strip():
            raise ValueError("dimension name must be a non-empty string")
        normalized_dimension_scores[dimension] = _parse_score(
            value,
            "dimension score",
        )
    if _find_visualization_dimension(normalized_dimension_scores) is None:
        raise ValueError("missing visualization quality dimension")

    return JudgeResult(
        passed=passed,
        score=score,
        dimension_scores=normalized_dimension_scores,
        issues=_parse_string_list(parsed["issues"], "issues"),
        evidence=_parse_string_list(parsed["evidence"], "evidence"),
        recommendations=_parse_string_list(
            parsed["recommendations"],
            "recommendations",
        ),
    )


def _find_visualization_dimension(dimension_scores: dict[str, int]) -> str | None:
    for dimension in dimension_scores:
        normalized_dimension = dimension.strip().lower()
        if any(
            keyword in normalized_dimension
            for keyword in VISUALIZATION_DIMENSION_KEYWORDS
        ):
            return dimension
    return None


def assert_visualization_quality_dimension(
    result: JudgeResult,
    *,
    minimum_score: int = MIN_VISUALIZATION_QUALITY_SCORE,
) -> None:
    dimension = _find_visualization_dimension(result.dimension_scores)
    if dimension is None:
        raise AssertionError(
            "LLM judge result is missing visualization quality dimension"
        )
    score = result.dimension_scores[dimension]
    assert score >= minimum_score, (
        f"Visualization quality score too low: {score}, "
        f"minimum: {minimum_score}, issues: {result.issues}"
    )


def _parse_score(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    if value < 0 or value > 100:
        raise ValueError(f"{label} must be between 0 and 100")
    return value


def _parse_string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(f"{label} must be a string array")
    return list(value)


def assert_llm_judges_artifact_quality(
    workflow_name: str,
    run_result: WorkflowRunResult,
) -> None:
    _load_dotenv()
    if not is_llm_judge_enabled():
        pytest.skip("NEW_AGENTS_E2E_LLM_JUDGE is not enabled")

    api_key = os.environ.get("NEW_AGENTS_E2E_JUDGE_API_KEY")
    base_url = os.environ.get("NEW_AGENTS_E2E_JUDGE_BASE_URL")
    model = os.environ.get("NEW_AGENTS_E2E_JUDGE_MODEL")
    missing = [
        name
        for name, value in {
            "NEW_AGENTS_E2E_JUDGE_API_KEY": api_key,
            "NEW_AGENTS_E2E_JUDGE_BASE_URL": base_url,
            "NEW_AGENTS_E2E_JUDGE_MODEL": model,
        }.items()
        if not value
    ]
    if missing:
        pytest.skip("missing LLM judge environment variables: " + ", ".join(missing))

    prompt = build_judge_prompt(workflow_name, run_result)

    response = requests.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "你是严格的软件测试产物评审员。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        },
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    result = parse_judge_result(content)
    assert result.passed, (
        f"LLM judge failed with score {result.score}: {result.issues}"
    )
    assert result.score >= MIN_LLM_JUDGE_SCORE, (
        f"LLM judge score too low: {result.score}, issues: {result.issues}"
    )
    assert_visualization_quality_dimension(result)


def assert_llm_judges_handoff_quality(
    handoff_name: str,
    source_result: WorkflowRunResult,
    target_result: WorkflowRunResult,
) -> None:
    _load_dotenv()
    if not is_llm_judge_enabled():
        pytest.skip("NEW_AGENTS_E2E_LLM_JUDGE is not enabled")

    api_key = os.environ.get("NEW_AGENTS_E2E_JUDGE_API_KEY")
    base_url = os.environ.get("NEW_AGENTS_E2E_JUDGE_BASE_URL")
    model = os.environ.get("NEW_AGENTS_E2E_JUDGE_MODEL")
    missing = [
        name
        for name, value in {
            "NEW_AGENTS_E2E_JUDGE_API_KEY": api_key,
            "NEW_AGENTS_E2E_JUDGE_BASE_URL": base_url,
            "NEW_AGENTS_E2E_JUDGE_MODEL": model,
        }.items()
        if not value
    ]
    if missing:
        pytest.skip("missing LLM judge environment variables: " + ", ".join(missing))

    prompt = build_handoff_judge_prompt(
        handoff_name,
        source_result,
        target_result,
    )

    response = requests.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "你是严格的软件测试接力流程评审员。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        },
        timeout=60,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    result = parse_judge_result(content)
    assert result.passed, (
        f"LLM handoff judge failed with score {result.score}: {result.issues}"
    )
    assert result.score >= MIN_LLM_JUDGE_SCORE, (
        f"LLM handoff judge score too low: {result.score}, issues: {result.issues}"
    )
    assert_visualization_quality_dimension(result)
