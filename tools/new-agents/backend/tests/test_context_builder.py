import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["FLASK_TESTING"] = "1"

from app import create_app
from context_builder import build_run_context, build_run_context_prompt
from models import AgentContextSummary, db
from run_persistence import (
    append_run_message,
    claim_agent_run_turn_request,
    create_agent_run,
    record_artifact_version,
    replace_artifact_collaboration_state,
)


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
    os.close(db_fd)
    os.unlink(db_path)


def test_build_run_context_prompt_returns_current_prompt_without_prior_messages(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        prompt = build_run_context_prompt(run.id, "当前用户输入")

    assert prompt == "当前用户输入"


def test_build_run_context_prompt_includes_prior_messages_in_sequence(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(run.id, "user", "第一条需求")
        append_run_message(run.id, "assistant", "第一轮回复")

        prompt = build_run_context_prompt(run.id, "第二条需求")

    assert "[已记录用户补充]" in prompt
    assert prompt.index("[用户]\n第一条需求") < prompt.index("[助手]\n第一轮回复")
    assert prompt.index("[助手]\n第一轮回复") < prompt.index("[用户]\n第二条需求")
    assert prompt.endswith("[用户]\n第二条需求")


def test_build_run_context_excludes_only_bound_request_message_sequence(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        first_same_text = append_run_message(run.id, "user", "相同输入")
        append_run_message(run.id, "assistant", "第一轮回复")
        bound_request = claim_agent_run_turn_request(
            run.id,
            request_id="context-bound-request-001",
            stage_id="CLARIFY",
            user_content="BOUND-REQUEST-CANARY-001",
        )

        context = build_run_context(
            run.id,
            "BOUND-REQUEST-CANARY-001",
            exclude_message_sequence=bound_request.user_message_sequence,
        )

    assert first_same_text.sequence_index != bound_request.user_message_sequence
    assert context.prompt.count("BOUND-REQUEST-CANARY-001") == 1
    assert "[用户]\n相同输入" in context.prompt
    assert "[用户补充: CLARIFY]\n相同输入" in context.prompt
    assert "[助手]\n第一轮回复" in context.prompt
    assert context.prompt.endswith("[用户]\nBOUND-REQUEST-CANARY-001")


def test_bound_request_exclusion_keeps_prior_stage_supplement_when_truncated(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        old_supplement = "OLD-SUPPLEMENT-CANARY-001-" + ("旧摘要" * 380)
        append_run_message(run.id, "user", old_supplement)
        append_run_message(run.id, "assistant", "很长的历史回复" * 30)
        bound_request = claim_agent_run_turn_request(
            run.id,
            request_id="context-bound-request-002",
            stage_id="CLARIFY",
            user_content="BOUND-REQUEST-CANARY-002",
        )

        context = build_run_context(
            run.id,
            "BOUND-REQUEST-CANARY-002",
            max_chars=1350,
            exclude_message_sequence=bound_request.user_message_sequence,
        )

    assert context.warnings == ["context_truncated"]
    assert "[用户补充: CLARIFY]\nOLD-SUPPLEMENT-CANARY-001" in context.prompt
    assert context.prompt.count("BOUND-REQUEST-CANARY-002") == 1
    assert context.prompt.endswith("[用户]\nBOUND-REQUEST-CANARY-002")


def test_build_run_context_prompt_filters_assistant_control_feedback(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(run.id, "user", "第一条需求")
        append_run_message(run.id, "assistant", "**Error:** LLM_ERROR")
        append_run_message(
            run.id,
            "assistant",
            "⚠️ **模型配置或供应商异常**\n\n右侧产出物已保持不变。",
        )
        append_run_message(run.id, "assistant", "有效回复")

        prompt = build_run_context_prompt(run.id, "第二条需求")

    assert "Error" not in prompt
    assert "模型配置或供应商异常" not in prompt
    assert "有效回复" in prompt
    assert prompt.endswith("[用户]\n第二条需求")


def test_build_run_context_prompt_truncates_oldest_context_when_over_budget(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(run.id, "user", "旧消息" * 20)
        append_run_message(run.id, "assistant", "新回复")

        prompt = build_run_context_prompt(run.id, "当前输入", max_chars=80)

    assert "旧消息" not in prompt
    assert "新回复" in prompt
    assert "上下文因长度限制已截断" in prompt
    assert prompt.endswith("[用户]\n当前输入")


def test_build_run_context_reports_context_truncation_warning(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(run.id, "user", "旧消息" * 20)
        append_run_message(run.id, "assistant", "新回复")

        context = build_run_context(run.id, "当前输入", max_chars=80)

    assert context.prompt.endswith("[用户]\n当前输入")
    assert context.warnings == ["context_truncated"]


def test_build_run_context_prompt_includes_current_artifact_summaries(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(
            run.id,
            "CLARIFY",
            "# 澄清结论\n\n- 核心目标：提升登录转化\n- 关键风险：第三方回调不稳定",
        )
        append_run_message(run.id, "user", "上一轮输入")

        prompt = build_run_context_prompt(run.id, "继续设计策略")

    assert "已保存阶段产物摘要" in prompt
    assert "[阶段产物: CLARIFY]" in prompt
    assert "核心目标：提升登录转化" in prompt
    assert "关键风险：第三方回调不稳定" in prompt
    assert prompt.endswith("[用户]\n继续设计策略")


def test_build_run_context_prompt_includes_locked_artifact_sections(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        record_artifact_version(run.id, "CLARIFY", "# 需求分析文档\n\n登录边界")
        replace_artifact_collaboration_state(
            run.id,
            {
                "comments": [],
                "sectionLocks": [
                    {
                        "id": "lock-1",
                        "stageId": "CLARIFY",
                        "heading": "## 已确认范围",
                        "content": "## 已确认范围\n\n登录边界已经由业务确认。",
                        "createdAt": 1710000000000,
                    },
                ],
            },
        )

        prompt = build_run_context_prompt(run.id, "请继续补充风险分析")

    assert "[已锁定产物章节]" in prompt
    assert "[锁定章节: CLARIFY]" in prompt
    assert "以下章节已由用户锁定，后续生成不得修改这些章节原文" in prompt
    assert "## 已确认范围" in prompt
    assert "登录边界已经由业务确认。" in prompt
    assert prompt.endswith("[用户]\n请继续补充风险分析")


def test_build_run_context_prompt_truncates_long_artifact_summary(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(
            run.id,
            "CLARIFY",
            "# 澄清结论\n" + ("很长的阶段结论" * 200),
        )
        append_run_message(run.id, "user", "上一轮输入")

        prompt = build_run_context_prompt(run.id, "继续设计策略")

    assert "[阶段产物: CLARIFY]" in prompt
    assert "该阶段产物摘要已截断" in prompt
    assert prompt.endswith("[用户]\n继续设计策略")


def test_build_run_context_reports_warning_when_artifact_summary_exceeds_budget(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(
            run.id,
            "CLARIFY",
            "# 澄清结论\n" + ("旧产物内容" * 20),
        )
        append_run_message(run.id, "assistant", "最新助手回复")

        context = build_run_context(run.id, "当前输入", max_chars=80)

    assert context.prompt.endswith("[用户]\n当前输入")
    assert context.warnings == ["context_truncated"]


def test_build_run_context_prompt_prefers_persisted_artifact_summary(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(
            run.id,
            "CLARIFY",
            "# 原始产物\n- 这段原文不应出现在上下文",
        )
        summaries = AgentContextSummary.query.filter_by(
            run_id=run.id,
            source_type="artifact",
            source_stage_id="CLARIFY",
        ).all()
        for summary in summaries:
            summary.content = "人工校准后的阶段摘要"
        db.session.commit()

        prompt = build_run_context_prompt(run.id, "继续设计策略")

    assert "人工校准后的阶段摘要" in prompt
    assert "这段原文不应出现在上下文" not in prompt


def test_build_run_context_prompt_includes_structured_context_summaries(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        append_run_message(run.id, "user", "补充：短信验证码必须覆盖")
        record_artifact_version(
            run.id,
            "STRATEGY",
            "# 测试策略蓝图\n\n"
            "## 阶段结论\n"
            "- 登录主链路和第三方回调是本轮重点\n\n"
            "## 关键决策\n"
            "- 决定先覆盖 P0 登录回归",
        )

        prompt = build_run_context_prompt(run.id, "继续生成用例")

    assert "[已记录用户补充]" in prompt
    assert "[用户补充: STRATEGY]" in prompt
    assert "短信验证码必须覆盖" in prompt
    assert "[已记录阶段结论]" in prompt
    assert "[阶段结论: STRATEGY]" in prompt
    assert "登录主链路和第三方回调" in prompt
    assert "[已记录关键决策]" in prompt
    assert "[关键决策: STRATEGY]" in prompt
    assert "决定先覆盖 P0 登录回归" in prompt
    assert prompt.endswith("[用户]\n继续生成用例")
