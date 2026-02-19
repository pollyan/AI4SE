"""
Lisa 智能体 P0 冒烟测试（多轮对话）

使用真实 LLM 调用验证完整的端到端工作流程。
所有测试标记为 @pytest.mark.slow，仅本地运行，不在 CI 中执行。

覆盖场景:
- [R1] 模糊消息 → 意图澄清（不触发产出物）
- [R2+TD1] 测试设计工作流 → 需求分析产出物 → 多轮推进
- [TD2] 多轮对话上下文保持

测试断言层次:
1. SSE 流完整性（text-start / text-delta / text-end / finish）
2. 工具调用轨迹（artifact_key 正确）
3. 文本回复非空且有意义
4. LLM-as-Judge 语义相关性验证
"""

import pytest
from .sse_parser import (
    send_and_collect,
    extract_full_text,
    extract_tool_trajectory,
    get_tool_events,
    assert_stream_integrity,
)
from .judge import judge_output


@pytest.mark.slow
class TestLisaIntentRouting:
    """
    [R1] 意图路由冒烟测试

    验证模糊消息被路由到澄清意图，不触发产出物更新。
    """

    def test_clarify_intent_for_vague_message(self, client, lisa_session):
        """
        模糊消息"你好"应触发澄清引导，而不是进入工作流。

        断言:
        - SSE 流正常（有文本输出）
        - 不触发任何工具调用（无产出物更新）
        """
        events = send_and_collect(client, lisa_session, "你好")

        # 应有文本引导回复
        text = extract_full_text(events)
        assert len(text) > 10, f"澄清引导回复过短: {repr(text)}"

        # 不应触发产出物更新
        tool_calls = get_tool_events(events)
        assert len(tool_calls) == 0, (
            f"模糊消息不应触发产出物更新，"
            f"但实际触发了 {len(tool_calls)} 个工具调用:\n"
            f"{[e.data for e in tool_calls]}"
        )


@pytest.mark.slow
class TestLisaTestDesignMultiTurn:
    """
    [R2+TD1+TD2] 测试设计工作流多轮对话冒烟测试

    验证从需求分析到工作流推进的完整 2 轮对话，
    以及跨轮次的上下文保持能力。
    """

    def test_requirement_analysis_and_continuation(self, client, lisa_session):
        """
        2 轮对话：需求分析 → 确认推进

        第1轮: 提出测试需求 → 验证 Lisa 生成需求分析产出物
        第2轮: 确认继续 → 验证工作流推进仍触发产出物更新

        断言:
        - [痛点B] 每轮 SSE 流完整性
        - [轨迹] 第1轮工具调用 key = test_design_requirements
        - [语义] 第1轮文本与登录功能测试相关（LLM-as-Judge）
        - [痛点A] 第2轮继续触发产出物更新（工作流状态保持）
        """
        user_msg_r1 = (
            "帮我分析一下用户登录功能的测试点，"
            "接口是 POST /api/login，参数是 username 和 password"
        )

        # ============ 第1轮：提出测试需求 ============
        events_r1 = send_and_collect(client, lisa_session, user_msg_r1)

        # [痛点B] SSE 流完整性
        assert_stream_integrity(events_r1)

        # [痛点B] 有文本输出
        text_r1 = extract_full_text(events_r1)
        assert len(text_r1) > 30, (
            f"第1轮回复过短 ({len(text_r1)} chars): {repr(text_r1[:100])}"
        )

        # [轨迹] 第1轮应触发工具调用，artifact_key 为 test_design_requirements
        trajectory_r1 = extract_tool_trajectory(events_r1)
        assert len(trajectory_r1) >= 1, (
            f"第1轮未触发工具调用。\n"
            f"实际事件类型: {[e.event_type for e in events_r1]}"
        )
        first_call = trajectory_r1[0]
        assert first_call.artifact_key == "test_design_requirements", (
            f"预期 artifact_key='test_design_requirements'，"
            f"实际为 '{first_call.artifact_key}'"
        )

        # [语义] LLM-as-Judge 验证相关性
        verdict = judge_output(
            user_input=user_msg_r1,
            expected_behavior=(
                "智能体的回复应与'用户登录功能测试'主题相关，"
                "包含对登录功能的分析或与测试相关的内容"
            ),
            actual_output=text_r1[:500]
        )
        assert verdict.passed, f"第1轮语义验证失败: {verdict.reason}"

        # ============ 第2轮：确认推进 ============
        events_r2 = send_and_collect(
            client, lisa_session, "需求分析没问题，请继续"
        )

        # [痛点B] 第2轮 SSE 流完整性
        assert_stream_integrity(events_r2)

        text_r2 = extract_full_text(events_r2)
        assert len(text_r2) > 10, (
            f"第2轮回复过短 ({len(text_r2)} chars): {repr(text_r2[:100])}"
        )

        # [痛点A] 第2轮仍有工具调用（工作流状态保持）
        trajectory_r2 = extract_tool_trajectory(events_r2)
        assert len(trajectory_r2) >= 1, (
            f"第2轮未触发工具调用，工作流状态可能丢失。\n"
            f"实际事件类型: {[e.event_type for e in events_r2]}"
        )

    def test_context_preserved_across_turns(self, client, lisa_session):
        """
        2 轮对话：上下文保持测试

        第1轮提到"短信验证码登录"，第2轮追问细节（不重复功能名）。
        验证智能体能记住上下文并继续工作流。

        断言:
        - 第2轮仍触发产出物更新（工作流状态持续）
        - 第2轮有有意义的文本回复
        """
        # 第1轮：建立上下文
        send_and_collect(
            client, lisa_session,
            "帮我设计短信验证码登录功能的测试点"
        )

        # 第2轮：追问细节，不重复功能名
        events_r2 = send_and_collect(
            client, lisa_session,
            "验证码过期时间是5分钟，请把这个约束补充到需求分析中"
        )

        # 验证上下文保持：仍触发产出物更新
        trajectory_r2 = extract_tool_trajectory(events_r2)
        assert len(trajectory_r2) >= 1, (
            "第2轮未保持工作流状态（未触发产出物更新）。\n"
            "可能原因：智能体丢失了第1轮的上下文。\n"
            f"第2轮实际事件: {[e.event_type for e in events_r2]}"
        )

        # 有文本回复
        text_r2 = extract_full_text(events_r2)
        assert len(text_r2) > 10, (
            f"第2轮回复过短: {repr(text_r2[:100])}"
        )
