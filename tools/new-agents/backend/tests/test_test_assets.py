import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["FLASK_TESTING"] = "1"

from app import create_app
from models import db
from run_persistence import create_agent_run, record_artifact_version
from test_assets import (
    create_lisa_test_asset_risk,
    delete_lisa_test_asset_risk,
    export_lisa_test_assets,
    get_lisa_test_asset_collection,
    materialize_lisa_test_assets,
    record_lisa_test_asset_intent_tester_case,
    record_lisa_test_asset_intent_tester_execution,
    record_lisa_test_asset_intent_tester_result,
    update_lisa_test_asset_risk_by_id,
    update_lisa_test_asset_issue_status,
    update_lisa_test_asset_risk,
    update_lisa_test_case_asset,
    update_lisa_test_point_asset,
)


CASES_MARKDOWN = """# 测试用例集

## 1. 用例统计
**统计摘要**：共 2 条用例，P0: 1 条 | P1: 1 条 | P2: 0 条

## 2. 用例清单

### 2.1 正向功能验证

| ID | 用例标题 | 优先级 | 测试维度 | 关联测试点 | 关联风险 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 断言 | 执行层级 | 自动化建议 | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC-001 | 用户使用正确密码登录成功 | P0 | 正向功能验证 | 登录主链路 | R-LOGIN-001 | 用户已注册 | 1. 打开登录页 2. 输入正确账号密码 3. 点击登录 | user@example.com / 正确密码 | 跳转到工作台 | 工作台 URL、用户昵称和登录态均正确 | E2E | 优先自动化 | 可执行 |

### 2.2 异常与边界值

| ID | 用例标题 | 优先级 | 测试维度 | 关联测试点 | 关联风险 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 | 断言 | 执行层级 | 自动化建议 | 状态 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TC-002 | 密码错误时提示失败 | P1 | 异常与边界值 | 登录错误处理 | R-LOGIN-002 | 用户已注册 | 1. 输入正确账号 2. 输入错误密码 3. 点击登录 | user@example.com / 错误密码 | 显示密码错误提示 | 错误提示文案出现且不会创建登录会话 | E2E | 可自动化 | 可执行 |

## 3. 测试点覆盖追溯

| 测试点 | 优先级 | 关联风险 | 覆盖用例 | 覆盖状态 |
|---|---|---|---|---|
| 登录主链路 | P0 | R-LOGIN-001 | TC-001 | 已覆盖 |
| 登录错误处理 | P1 | R-LOGIN-002 | TC-002 | 部分覆盖 |
"""


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


def test_export_lisa_test_assets_parses_cases_and_coverage(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)

        assets = export_lisa_test_assets(run.id)

    assert assets["runId"] == run.id
    assert assets["workflowId"] == "TEST_DESIGN"
    assert assets["sourceStageId"] == "CASES"
    assert assets["sourceArtifactVersion"] == 1
    assert assets["testCases"] == [
        {
            "id": "TC-001",
            "title": "用户使用正确密码登录成功",
            "priority": "P0",
            "dimension": "正向功能验证",
            "testPoint": "登录主链路",
            "risk": "R-LOGIN-001",
            "precondition": "用户已注册",
            "steps": "1. 打开登录页 2. 输入正确账号密码 3. 点击登录",
            "testData": "user@example.com / 正确密码",
            "expectedResult": "跳转到工作台",
            "assertion": "工作台 URL、用户昵称和登录态均正确",
            "executionLayer": "E2E",
            "automationSuggestion": "优先自动化",
            "status": "可执行",
        },
        {
            "id": "TC-002",
            "title": "密码错误时提示失败",
            "priority": "P1",
            "dimension": "异常与边界值",
            "testPoint": "登录错误处理",
            "risk": "R-LOGIN-002",
            "precondition": "用户已注册",
            "steps": "1. 输入正确账号 2. 输入错误密码 3. 点击登录",
            "testData": "user@example.com / 错误密码",
            "expectedResult": "显示密码错误提示",
            "assertion": "错误提示文案出现且不会创建登录会话",
            "executionLayer": "E2E",
            "automationSuggestion": "可自动化",
            "status": "可执行",
        },
    ]
    assert assets["coverageTrace"] == [
        {
            "testPoint": "登录主链路",
            "priority": "P0",
            "risk": "R-LOGIN-001",
            "testCases": ["TC-001"],
            "status": "已覆盖",
        },
        {
            "testPoint": "登录错误处理",
            "priority": "P1",
            "risk": "R-LOGIN-002",
            "testCases": ["TC-002"],
            "status": "部分覆盖",
        },
    ]
    assert assets["coverageSummary"] == {
        "totalTestCases": 2,
        "totalTestPoints": 2,
        "coveredTestPoints": 1,
        "partiallyCoveredTestPoints": 1,
        "uncoveredTestPoints": 0,
        "coverageRate": 50.0,
        "byPriority": [
            {
                "priority": "P0",
                "total": 1,
                "covered": 1,
                "partial": 0,
                "uncovered": 0,
                "coverageRate": 100.0,
            },
            {
                "priority": "P1",
                "total": 1,
                "covered": 0,
                "partial": 1,
                "uncovered": 0,
                "coverageRate": 0.0,
            },
        ],
    }
    assert assets["assetIssues"] == []
    assert assets["riskMatrix"] == [
        {
            "risk": "R-LOGIN-001",
            "testCases": ["TC-001"],
            "testPoints": ["登录主链路"],
            "priorities": ["P0"],
            "dimensions": ["正向功能验证"],
            "coverageStatuses": ["已覆盖"],
        },
        {
            "risk": "R-LOGIN-002",
            "testCases": ["TC-002"],
            "testPoints": ["登录错误处理"],
            "priorities": ["P1"],
            "dimensions": ["异常与边界值"],
            "coverageStatuses": ["部分覆盖"],
        },
    ]
    assert assets["intentTesterDrafts"][0] == {
        "sourceCaseId": "TC-001",
        "name": "TC-001 用户使用正确密码登录成功",
        "description": (
            "来源: New Agents Lisa TEST_DESIGN/CASES\n"
            "测试点: 登录主链路\n"
            "关联风险: R-LOGIN-001\n"
            "前置条件: 用户已注册\n"
            "测试数据: user@example.com / 正确密码\n"
            "预期结果: 跳转到工作台\n"
            "断言: 工作台 URL、用户昵称和登录态均正确\n"
            "执行层级: E2E\n"
            "自动化建议: 优先自动化\n"
            "状态: 可执行"
        ),
        "category": "正向功能验证",
        "priority": 1,
        "tags": ["lisa", "new-agents", "TC-001", "P0", "R-LOGIN-001"],
        "steps": [
            {
                "action": "ai_assert",
                "params": {"prompt": "确认前置条件成立：用户已注册"},
            },
            {
                "action": "ai_assert",
                "params": {
                    "prompt": (
                        "按自然语言测试步骤执行并观察：1. 打开登录页 "
                        "2. 输入正确账号密码 3. 点击登录；测试数据："
                        "user@example.com / 正确密码"
                    )
                },
            },
            {
                "action": "ai_assert",
                "params": {"prompt": "验证预期结果：跳转到工作台"},
            },
        ],
        "draftWarnings": [
            "该草稿由 Lisa Markdown 用例派生，导入 intent-tester 前需要人工校准页面 URL、定位语义和可执行步骤。"
        ],
    }
    assert assets["intentTesterDrafts"][1]["priority"] == 2


def test_export_lisa_test_assets_reports_latest_source_artifact_version(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN.replace("TC-001", "TC-101"))

        assets = export_lisa_test_assets(run.id)

    assert assets["sourceArtifactVersion"] == 2
    assert assets["testCases"][0]["id"] == "TC-101"


def test_export_lisa_test_assets_reports_asset_quality_issues(app):
    inconsistent_markdown = CASES_MARKDOWN.replace(
        "TC-002 | 部分覆盖",
        "TC-999 | 部分覆盖",
    )
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", inconsistent_markdown)

        assets = export_lisa_test_assets(run.id)

    assert assets["assetIssues"] == [
        {
            "type": "unknown_coverage_case",
            "testPoint": "登录错误处理",
            "caseId": "TC-999",
            "message": "覆盖追溯引用了不存在的测试用例 TC-999",
        },
        {
            "type": "orphan_test_case",
            "caseId": "TC-002",
            "message": "测试用例 TC-002 未被任何测试点覆盖追溯引用",
        },
    ]


def test_materialized_asset_issues_have_pending_status(app):
    inconsistent_markdown = CASES_MARKDOWN.replace(
        "TC-002 | 部分覆盖",
        "TC-999 | 部分覆盖",
    )
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", inconsistent_markdown)

        collection = materialize_lisa_test_assets(run.id)

    assert collection["assetIssues"][0]["id"] > 0
    assert collection["assetIssues"][0]["status"] == "pending"
    assert collection["assetIssues"][1]["status"] == "pending"


def test_update_lisa_test_asset_issue_status_persists_status(app):
    inconsistent_markdown = CASES_MARKDOWN.replace(
        "TC-002 | 部分覆盖",
        "TC-999 | 部分覆盖",
    )
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", inconsistent_markdown)
        collection = materialize_lisa_test_assets(run.id)
        issue_id = collection["assetIssues"][0]["id"]

        updated = update_lisa_test_asset_issue_status(
            collection["id"],
            issue_id,
            {"status": "confirmed"},
        )
        reloaded = get_lisa_test_asset_collection(collection["id"])

    assert updated["id"] == issue_id
    assert updated["status"] == "confirmed"
    assert reloaded["assetIssues"][0]["status"] == "confirmed"


def test_update_lisa_test_asset_issue_status_rejects_invalid_status(app):
    inconsistent_markdown = CASES_MARKDOWN.replace(
        "TC-002 | 部分覆盖",
        "TC-999 | 部分覆盖",
    )
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", inconsistent_markdown)
        collection = materialize_lisa_test_assets(run.id)
        issue_id = collection["assetIssues"][0]["id"]

        with pytest.raises(ValueError, match="未知资产问题状态"):
            update_lisa_test_asset_issue_status(
                collection["id"],
                issue_id,
                {"status": "closed"},
            )


def test_export_lisa_test_assets_rejects_missing_cases_artifact(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")

        with pytest.raises(ValueError, match="缺少 TEST_DESIGN/CASES 测试用例集"):
            export_lisa_test_assets(run.id)


def test_export_lisa_test_assets_rejects_non_test_design_run(app):
    with app.app_context():
        run = create_agent_run("REQ_REVIEW", "lisa", "REVIEW")

        with pytest.raises(ValueError, match="仅支持 TEST_DESIGN workflow"):
            export_lisa_test_assets(run.id)


def test_materialize_lisa_test_assets_persists_editable_collection(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        run_id = run.id

        collection = materialize_lisa_test_assets(run.id)
        reloaded = get_lisa_test_asset_collection(collection["id"])

    assert collection["runId"] == run_id
    assert collection["workflowId"] == "TEST_DESIGN"
    assert collection["sourceStageId"] == "CASES"
    assert collection["sourceArtifactVersion"] == 1
    assert collection["testCases"][0]["id"] == "TC-001"
    assert collection["testCases"][0]["versionNumber"] == 1
    assert collection["testCases"][0]["versions"] == [
        {
            "versionNumber": 1,
            "title": "用户使用正确密码登录成功",
            "priority": "P0",
            "dimension": "正向功能验证",
            "testPoint": "登录主链路",
            "risk": "R-LOGIN-001",
            "precondition": "用户已注册",
            "steps": "1. 打开登录页 2. 输入正确账号密码 3. 点击登录",
            "testData": "user@example.com / 正确密码",
            "expectedResult": "跳转到工作台",
        }
    ]
    assert collection["testPoints"] == [
        {
            "testPoint": "登录主链路",
            "priority": "P0",
            "risk": "R-LOGIN-001",
            "testCases": ["TC-001"],
            "status": "已覆盖",
        },
        {
            "testPoint": "登录错误处理",
            "priority": "P1",
            "risk": "R-LOGIN-002",
            "testCases": ["TC-002"],
            "status": "部分覆盖",
        },
    ]
    assert collection["riskMatrix"] == reloaded["riskMatrix"]
    assert reloaded["testCases"][1]["id"] == "TC-002"


def test_materialize_lisa_test_assets_refreshes_from_latest_artifact_version(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        first = materialize_lisa_test_assets(run.id)
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN.replace("TC-001", "TC-101"))

        refreshed = materialize_lisa_test_assets(run.id)

    assert refreshed["id"] == first["id"]
    assert refreshed["sourceArtifactVersion"] == 2
    assert [test_case["id"] for test_case in refreshed["testCases"]] == [
        "TC-002",
        "TC-101",
    ]


def test_intent_tester_mapping_persists_imported_case_and_latest_execution(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)

        imported = record_lisa_test_asset_intent_tester_case(
            collection["id"],
            "TC-001",
            {
                "intentTesterCaseId": 42,
                "intentTesterCaseName": "TC-001 用户使用正确密码登录成功",
            },
        )
        executed = record_lisa_test_asset_intent_tester_execution(
            collection["id"],
            "TC-001",
            {
                "executionId": "exec-123",
                "status": "pending",
                "mode": "headless",
                "browser": "chrome",
                "startTime": "2026-06-19T10:00:00",
                "endTime": None,
                "duration": None,
                "errorMessage": None,
            },
        )
        reloaded = get_lisa_test_asset_collection(collection["id"])

    assert imported == {
        "sourceCaseId": "TC-001",
        "intentTesterCaseId": 42,
        "intentTesterCaseName": "TC-001 用户使用正确密码登录成功",
        "latestExecution": None,
        "latestResult": None,
    }
    assert executed == {
        "sourceCaseId": "TC-001",
        "intentTesterCaseId": 42,
        "intentTesterCaseName": "TC-001 用户使用正确密码登录成功",
        "latestExecution": {
            "executionId": "exec-123",
            "testCaseId": 42,
            "status": "pending",
            "mode": "headless",
            "browser": "chrome",
            "startTime": "2026-06-19T10:00:00",
            "endTime": None,
            "duration": None,
            "errorMessage": None,
        },
        "latestResult": None,
    }
    assert reloaded["intentTesterMappings"] == [executed]


def test_intent_tester_result_snapshot_persists_failed_steps_and_screenshots(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)
        record_lisa_test_asset_intent_tester_case(
            collection["id"],
            "TC-001",
            {
                "intentTesterCaseId": 42,
                "intentTesterCaseName": "TC-001 用户使用正确密码登录成功",
            },
        )

        updated = record_lisa_test_asset_intent_tester_result(
            collection["id"],
            "TC-001",
            {
                "executionId": "exec-456",
                "status": "failed",
                "duration": 60,
                "errorMessage": "断言失败",
                "steps": [
                    {
                        "stepIndex": 0,
                        "description": "打开登录页",
                        "status": "success",
                        "screenshotPath": "/static/screenshots/step-0.png",
                        "action": "ai_assert",
                    },
                    {
                        "stepIndex": 1,
                        "description": "验证预期结果",
                        "status": "failed",
                        "errorMessage": "未看到工作台",
                        "screenshotPath": "/static/screenshots/step-1.png",
                        "action": "ai_assert",
                    },
                ],
            },
        )
        reloaded = get_lisa_test_asset_collection(collection["id"])

    expected_result = {
        "executionId": "exec-456",
        "status": "failed",
        "stepsTotal": 2,
        "stepsPassed": 1,
        "stepsFailed": 1,
        "duration": 60,
        "errorMessage": "断言失败",
        "screenshots": [
            "/static/screenshots/step-0.png",
            "/static/screenshots/step-1.png",
        ],
        "failedSteps": [
            {
                "stepIndex": 1,
                "description": "验证预期结果",
                "status": "failed",
                "errorMessage": "未看到工作台",
                "screenshotPath": "/static/screenshots/step-1.png",
                "action": "ai_assert",
            }
        ],
    }
    assert updated["latestResult"] == expected_result
    assert reloaded["intentTesterMappings"][0]["latestResult"] == expected_result


def test_intent_tester_mapping_survives_materialize_for_existing_case(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)
        record_lisa_test_asset_intent_tester_case(
            collection["id"],
            "TC-001",
            {
                "intentTesterCaseId": 42,
                "intentTesterCaseName": "TC-001 用户使用正确密码登录成功",
            },
        )
        record_artifact_version(
            run.id,
            "CASES",
            CASES_MARKDOWN.replace("用户使用正确密码登录成功", "用户登录后进入工作台"),
        )

        refreshed = materialize_lisa_test_assets(run.id)

    assert refreshed["sourceArtifactVersion"] == 2
    assert refreshed["intentTesterMappings"] == [
        {
            "sourceCaseId": "TC-001",
            "intentTesterCaseId": 42,
            "intentTesterCaseName": "TC-001 用户使用正确密码登录成功",
            "latestExecution": None,
            "latestResult": None,
        }
    ]


def test_intent_tester_mapping_is_removed_when_source_case_disappears(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)
        record_lisa_test_asset_intent_tester_case(
            collection["id"],
            "TC-001",
            {
                "intentTesterCaseId": 42,
                "intentTesterCaseName": "TC-001 用户使用正确密码登录成功",
            },
        )
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN.replace("TC-001", "TC-101"))

        refreshed = materialize_lisa_test_assets(run.id)

    assert [test_case["id"] for test_case in refreshed["testCases"]] == [
        "TC-002",
        "TC-101",
    ]
    assert refreshed["intentTesterMappings"] == []


def test_intent_tester_execution_rejects_unimported_source_case(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)

        with pytest.raises(ValueError, match="测试用例尚未导入 intent-tester"):
            record_lisa_test_asset_intent_tester_execution(
                collection["id"],
                "TC-001",
                {
                    "executionId": "exec-123",
                    "status": "pending",
                    "mode": "headless",
                    "browser": "chrome",
                    "startTime": "2026-06-19T10:00:00",
                    "endTime": None,
                    "duration": None,
                    "errorMessage": None,
                },
            )


def test_lisa_test_asset_risks_include_stable_id_and_manual_flag(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)

        collection = materialize_lisa_test_assets(run.id)

    risk = next(item for item in collection["riskMatrix"] if item["risk"] == "R-LOGIN-001")
    assert isinstance(risk["id"], int)
    assert risk["id"] > 0
    assert risk["isManual"] is False


def test_lisa_test_asset_stable_id_survives_risk_matrix_rebuild(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)
        original_risk = next(
            item for item in collection["riskMatrix"] if item["risk"] == "R-LOGIN-001"
        )

        update_lisa_test_point_asset(
            collection["id"],
            "登录错误处理",
            {
                "risk": "A-RISK",
                "status": "已覆盖",
                "testCases": ["TC-002"],
            },
        )
        reloaded = get_lisa_test_asset_collection(collection["id"])

    unchanged_risk = next(
        item for item in reloaded["riskMatrix"] if item["risk"] == "R-LOGIN-001"
    )
    assert unchanged_risk["id"] == original_risk["id"]
    assert unchanged_risk["testCases"] == ["TC-001"]
    assert unchanged_risk["testPoints"] == ["登录主链路"]


def test_update_lisa_test_case_asset_creates_new_case_version(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)

        updated = update_lisa_test_case_asset(
            collection["id"],
            "TC-001",
            {
                "title": "用户登录成功后进入项目首页",
                "priority": "P1",
            },
        )
        reloaded = get_lisa_test_asset_collection(collection["id"])

    assert updated["id"] == "TC-001"
    assert updated["title"] == "用户登录成功后进入项目首页"
    assert updated["priority"] == "P1"
    assert updated["versionNumber"] == 2
    test_case = next(
        item for item in reloaded["testCases"] if item["id"] == "TC-001"
    )
    assert [version["versionNumber"] for version in test_case["versions"]] == [1, 2]
    assert test_case["versions"][0]["title"] == "用户使用正确密码登录成功"
    assert test_case["versions"][1]["title"] == "用户登录成功后进入项目首页"


def test_update_lisa_test_point_asset_persists_point_and_rebuilds_risk_matrix(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)

        updated = update_lisa_test_point_asset(
            collection["id"],
            "登录错误处理",
            {
                "priority": "P0",
                "risk": "R-LOGIN-LOCK",
                "status": "已覆盖",
                "testCases": ["TC-002"],
            },
        )
        reloaded = get_lisa_test_asset_collection(collection["id"])

    assert updated == {
        "testPoint": "登录错误处理",
        "priority": "P0",
        "risk": "R-LOGIN-LOCK",
        "testCases": ["TC-002"],
        "status": "已覆盖",
    }
    assert reloaded["coverageSummary"]["coveredTestPoints"] == 2
    assert reloaded["coverageSummary"]["partiallyCoveredTestPoints"] == 0
    assert reloaded["coverageSummary"]["coverageRate"] == 100.0
    risk = next(item for item in reloaded["riskMatrix"] if item["risk"] == "R-LOGIN-LOCK")
    assert risk["id"] > 0
    assert risk["isManual"] is False
    assert risk["testCases"] == ["TC-002"]
    assert risk["testPoints"] == ["登录错误处理"]
    assert risk["priorities"] == ["P0"]
    assert risk["dimensions"] == []
    assert risk["coverageStatuses"] == ["已覆盖"]
    assert risk["status"] == "open"
    assert risk["owner"] == ""
    assert risk["note"] == ""


def test_update_lisa_test_point_asset_rejects_invalid_status(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)

        with pytest.raises(ValueError, match="未知测试点覆盖状态"):
            update_lisa_test_point_asset(
                collection["id"],
                "登录错误处理",
                {"status": "blocked"},
            )


def test_update_lisa_test_asset_risk_lifecycle_persists_status_owner_note(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)

        updated = update_lisa_test_asset_risk(
            collection["id"],
            "R-LOGIN-002",
            {
                "status": "mitigating",
                "owner": "QA 张三",
                "note": "补充锁定场景",
            },
        )
        reloaded = get_lisa_test_asset_collection(collection["id"])

    assert updated["risk"] == "R-LOGIN-002"
    assert updated["status"] == "mitigating"
    assert updated["owner"] == "QA 张三"
    assert updated["note"] == "补充锁定场景"
    risk = next(item for item in reloaded["riskMatrix"] if item["risk"] == "R-LOGIN-002")
    assert risk["status"] == "mitigating"
    assert risk["owner"] == "QA 张三"
    assert risk["note"] == "补充锁定场景"


def test_update_lisa_test_asset_risk_lifecycle_survives_risk_matrix_rebuild(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)

        update_lisa_test_asset_risk(
            collection["id"],
            "R-LOGIN-002",
            {
                "status": "accepted",
                "owner": "QA 李四",
                "note": "业务接受当前残余风险",
            },
        )
        update_lisa_test_point_asset(
            collection["id"],
            "登录错误处理",
            {
                "status": "已覆盖",
                "testCases": ["TC-002"],
            },
        )
        reloaded = get_lisa_test_asset_collection(collection["id"])

    risk = next(item for item in reloaded["riskMatrix"] if item["risk"] == "R-LOGIN-002")
    assert risk["coverageStatuses"] == ["已覆盖"]
    assert risk["status"] == "accepted"
    assert risk["owner"] == "QA 李四"
    assert risk["note"] == "业务接受当前残余风险"


def test_update_lisa_test_asset_risk_lifecycle_rejects_invalid_status(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)

        with pytest.raises(ValueError, match="未知风险状态"):
            update_lisa_test_asset_risk(
                collection["id"],
                "R-LOGIN-002",
                {"status": "blocked"},
            )


def test_risk_library_create_lisa_test_asset_risk_adds_manual_unlinked_risk(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)

        created = create_lisa_test_asset_risk(
            collection["id"],
            {
                "risk": "R-MANUAL-001",
                "status": "mitigating",
                "owner": "QA 王五",
                "note": "人工补充支付风控风险",
            },
        )
        reloaded = get_lisa_test_asset_collection(collection["id"])

    assert created["id"] > 0
    assert created["risk"] == "R-MANUAL-001"
    assert created["isManual"] is True
    assert created["testCases"] == []
    assert created["testPoints"] == []
    assert created["status"] == "mitigating"
    risk = next(item for item in reloaded["riskMatrix"] if item["id"] == created["id"])
    assert risk["owner"] == "QA 王五"
    assert risk["note"] == "人工补充支付风控风险"


def test_risk_library_rename_lisa_test_asset_risk_by_id_updates_sources_and_preserves_id(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)
        original = next(
            item for item in collection["riskMatrix"] if item["risk"] == "R-LOGIN-002"
        )

        updated = update_lisa_test_asset_risk_by_id(
            collection["id"],
            original["id"],
            {
                "risk": "R-LOGIN-LOCK",
                "status": "mitigating",
                "owner": "QA 张三",
                "note": "统一命名为锁定风险",
            },
        )
        reloaded = get_lisa_test_asset_collection(collection["id"])

    assert updated["id"] == original["id"]
    assert updated["risk"] == "R-LOGIN-LOCK"
    assert updated["status"] == "mitigating"
    assert {item["risk"] for item in reloaded["riskMatrix"]} == {
        "R-LOGIN-001",
        "R-LOGIN-LOCK",
    }
    renamed = next(item for item in reloaded["riskMatrix"] if item["id"] == original["id"])
    assert renamed["risk"] == "R-LOGIN-LOCK"
    point = next(
        item for item in reloaded["testPoints"] if item["testPoint"] == "登录错误处理"
    )
    assert point["risk"] == "R-LOGIN-LOCK"
    test_case = next(item for item in reloaded["testCases"] if item["id"] == "TC-002")
    assert test_case["risk"] == "R-LOGIN-LOCK"
    assert test_case["versionNumber"] == 2
    assert [version["risk"] for version in test_case["versions"]] == [
        "R-LOGIN-002",
        "R-LOGIN-LOCK",
    ]


def test_risk_library_delete_lisa_test_asset_risk_removes_unlinked_manual_risk(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)
        created = create_lisa_test_asset_risk(
            collection["id"],
            {"risk": "R-MANUAL-DELETE"},
        )

        deleted = delete_lisa_test_asset_risk(collection["id"], created["id"])
        reloaded = get_lisa_test_asset_collection(collection["id"])

    assert deleted == {"id": created["id"], "deleted": True}
    assert all(item["id"] != created["id"] for item in reloaded["riskMatrix"])


def test_risk_library_delete_lisa_test_asset_risk_rejects_linked_risk(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CASES")
        record_artifact_version(run.id, "CASES", CASES_MARKDOWN)
        collection = materialize_lisa_test_assets(run.id)
        linked = next(
            item for item in collection["riskMatrix"] if item["risk"] == "R-LOGIN-002"
        )

        with pytest.raises(ValueError, match="风险仍有关联资产"):
            delete_lisa_test_asset_risk(collection["id"], linked["id"])
