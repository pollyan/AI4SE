from __future__ import annotations

import json

import pytest

from .llm_judge import (
    assert_llm_judges_artifact_quality,
    assert_visualization_quality_dimension,
    build_handoff_judge_prompt,
    build_judge_prompt,
    parse_judge_result,
)
from .workflow_runner import (
    ConversationEvent,
    StageArtifactSnapshot,
    StageTransitionEvent,
    WorkflowRunResult,
)


def test_build_judge_prompt_includes_workflow_trace() -> None:
    run_result = WorkflowRunResult(
        final_artifact="# 最终产物\n\n完整交付内容",
        stage_artifacts=(
            StageArtifactSnapshot(
                stage_name="需求澄清",
                artifact="# 需求分析文档\n\n## 1. 被测系统与边界",
            ),
            StageArtifactSnapshot(
                stage_name="策略制定",
                artifact="# 测试策略蓝图\n\n## 1. 质量目标",
            ),
        ),
        conversation_events=(
            ConversationEvent(
                role="user",
                stage_name="需求澄清",
                content="请为登录支付链路设计测试策略。",
            ),
            ConversationEvent(
                role="assistant",
                stage_name="需求澄清",
                content="需求澄清完成，请确认进入策略制定。",
            ),
        ),
        stage_transitions=(
            StageTransitionEvent(
                from_stage="需求澄清",
                to_stage="策略制定",
                action="confirm",
            ),
        ),
    )

    prompt = build_judge_prompt("Lisa 测试策略与用例设计", run_result)

    assert "Lisa 测试策略与用例设计" in prompt
    assert "完整会话轨迹" in prompt
    assert "请为登录支付链路设计测试策略。" in prompt
    assert "需求澄清 -> 策略制定: confirm" in prompt
    assert "# 需求分析文档" in prompt
    assert "# 测试策略蓝图" in prompt
    assert "# 最终产物" in prompt


def test_build_judge_prompt_uses_lisa_testing_rubric() -> None:
    prompt = build_judge_prompt(
        "Lisa 测试策略与用例设计",
        _sample_run_result(),
    )

    assert "测试专家维度" in prompt
    assert "需求澄清" in prompt
    assert "风险识别" in prompt
    assert "测试策略" in prompt
    assert "测试用例" in prompt
    assert "覆盖追溯" in prompt
    assert "非功能需求" in prompt
    assert "交互体验维度" in prompt
    assert "可视化维度" in prompt
    assert "ai4se-visual" in prompt
    assert "traceability-matrix" in prompt
    assert "可视化质量" in prompt
    assert "dimension_scores" in prompt
    assert "recommendations" in prompt
    assert '"issues": ["问题1"]' not in prompt


def test_build_judge_prompt_uses_alex_business_rubric() -> None:
    prompt = build_judge_prompt(
        "Alex 需求蓝图梳理",
        _sample_run_result(),
    )

    assert "业务分析师维度" in prompt
    assert "问题定义" in prompt
    assert "用户画像" in prompt
    assert "用户旅程" in prompt
    assert "价值主张" in prompt
    assert "需求拆解" in prompt
    assert "业务闭环" in prompt
    assert "交互体验维度" in prompt
    assert "可视化维度" in prompt
    assert "dimension_scores" in prompt
    assert "evidence" in prompt


def test_build_handoff_judge_prompt_uses_cross_agent_rubric() -> None:
    alex_result = WorkflowRunResult(
        final_artifact="# 需求蓝图\n\n## 风险评估\n权限隔离、输出质量、追溯能力",
        stage_artifacts=(
            StageArtifactSnapshot(
                stage_name="需求蓝图",
                artifact="# 需求蓝图\n\nAI 测试设计助手帮助测试负责人生成测试策略。",
            ),
        ),
        conversation_events=(
            ConversationEvent(
                role="user",
                stage_name="价值定位",
                content="做 AI 测试设计助手。",
            ),
        ),
        stage_transitions=(),
    )
    lisa_result = WorkflowRunResult(
        final_artifact="# 测试用例集\n\n## 覆盖追溯\n权限隔离、输出质量、追溯能力均有用例覆盖",
        stage_artifacts=(
            StageArtifactSnapshot(
                stage_name="需求澄清",
                artifact="# 需求分析文档\n\n来源 Alex 需求蓝图。",
            ),
        ),
        conversation_events=(
            ConversationEvent(
                role="user",
                stage_name="需求澄清",
                content="请基于 Alex 的价值蓝图继续做 Lisa 测试设计。",
            ),
        ),
        stage_transitions=(),
    )

    prompt = build_handoff_judge_prompt(
        "Alex 需求蓝图梳理 -> Lisa 测试设计",
        alex_result,
        lisa_result,
    )

    assert "跨智能体接力维度" in prompt
    assert "源产物继承" in prompt
    assert "角色专业性转换" in prompt
    assert "需求蓝图" in prompt
    assert "测试用例集" in prompt
    assert "权限隔离、输出质量、追溯能力" in prompt
    assert "Alex 需求蓝图梳理 -> Lisa 测试设计" in prompt
    assert "dimension_scores" in prompt
    assert "可视化质量" in prompt


def test_parse_judge_result_accepts_strict_verdict() -> None:
    result = parse_judge_result(
        """
        {
          "pass": true,
          "score": 86,
          "dimension_scores": {
            "需求澄清": 90,
            "交互体验": 82,
            "可视化质量": 88
          },
          "issues": ["风险矩阵还可以更细"],
          "evidence": ["阶段切换完整", "最终产物包含追溯表"],
          "recommendations": ["补充非功能测试说明"]
        }
        """
    )

    assert result.passed is True
    assert result.score == 86
    assert result.dimension_scores == {
        "需求澄清": 90,
        "交互体验": 82,
        "可视化质量": 88,
    }
    assert result.issues == ["风险矩阵还可以更细"]
    assert result.evidence == ["阶段切换完整", "最终产物包含追溯表"]
    assert result.recommendations == ["补充非功能测试说明"]


def test_parse_judge_result_rejects_missing_visualization_dimension() -> None:
    with pytest.raises(ValueError, match="visualization quality dimension"):
        parse_judge_result(
            """
            {
              "pass": true,
              "score": 86,
              "dimension_scores": {
                "需求澄清": 90,
                "交互体验": 82
              },
              "issues": [],
              "evidence": [],
              "recommendations": []
            }
            """
        )


def test_assert_visualization_quality_dimension_rejects_low_score() -> None:
    result = parse_judge_result(
        """
        {
          "pass": true,
          "score": 86,
          "dimension_scores": {
            "需求澄清": 90,
            "可视化质量": 69
          },
          "issues": ["可视化较弱"],
          "evidence": ["产物只有文字说明"],
          "recommendations": ["补充结构化图表"]
        }
        """
    )

    with pytest.raises(AssertionError, match="Visualization quality score too low"):
        assert_visualization_quality_dimension(result)


def test_assert_llm_judges_artifact_quality_requires_80_score(monkeypatch) -> None:
    monkeypatch.setenv("NEW_AGENTS_E2E_LLM_JUDGE", "1")
    monkeypatch.setenv("NEW_AGENTS_E2E_JUDGE_API_KEY", "test-key")
    monkeypatch.setenv("NEW_AGENTS_E2E_JUDGE_BASE_URL", "https://judge.example")
    monkeypatch.setenv("NEW_AGENTS_E2E_JUDGE_MODEL", "judge-model")

    class JudgeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "pass": True,
                                    "score": 79,
                                    "dimension_scores": {
                                        "测试专业性": 79,
                                        "可视化质量": 82,
                                    },
                                    "issues": ["仍有质量缺口"],
                                    "evidence": ["有结构化产物"],
                                    "recommendations": ["补齐质量缺口后重跑"],
                                },
                                ensure_ascii=False,
                            )
                        }
                    }
                ]
            }

    monkeypatch.setattr(
        "tests.e2e.new_agents_browser.llm_judge.requests.post",
        lambda *args, **kwargs: JudgeResponse(),
    )

    with pytest.raises(AssertionError, match="LLM judge score too low: 79"):
        assert_llm_judges_artifact_quality(
            "Lisa 测试策略与用例设计",
            _sample_run_result(),
        )


def test_parse_judge_result_rejects_missing_required_field() -> None:
    with pytest.raises(ValueError, match="missing required judge result field"):
        parse_judge_result(
            """
            {
              "pass": true,
              "score": 86,
              "issues": [],
              "evidence": [],
              "recommendations": []
            }
            """
        )


def test_parse_judge_result_rejects_out_of_range_scores() -> None:
    with pytest.raises(ValueError, match="score must be between 0 and 100"):
        parse_judge_result(
            """
            {
              "pass": true,
              "score": 101,
              "dimension_scores": {"交互体验": 90, "可视化质量": 90},
              "issues": [],
              "evidence": [],
              "recommendations": []
            }
            """
        )

    with pytest.raises(
        ValueError,
        match="dimension score must be between 0 and 100",
    ):
        parse_judge_result(
            """
            {
              "pass": true,
              "score": 90,
              "dimension_scores": {"交互体验": -1, "可视化质量": 90},
              "issues": [],
              "evidence": [],
              "recommendations": []
            }
            """
        )


def _sample_run_result() -> WorkflowRunResult:
    return WorkflowRunResult(
        final_artifact="# 最终产物\n\n完整交付内容",
        stage_artifacts=(
            StageArtifactSnapshot(
                stage_name="需求澄清",
                artifact="# 需求分析文档\n\n## 1. 被测系统与边界",
            ),
        ),
        conversation_events=(
            ConversationEvent(
                role="user",
                stage_name="需求澄清",
                content="请为登录支付链路设计测试策略。",
            ),
        ),
        stage_transitions=(
            StageTransitionEvent(
                from_stage="需求澄清",
                to_stage="策略制定",
                action="confirm",
            ),
        ),
    )
