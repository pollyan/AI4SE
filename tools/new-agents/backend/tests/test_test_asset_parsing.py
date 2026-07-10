import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import test_asset_parsing
from test_artifact_data_renderers import VALID_CASES_ARTIFACT_DATA
from test_asset_parsing import parse_lisa_test_asset_markdown


CASES_MARKDOWN = """# 测试用例集

## 2. 用例清单

| ID | 用例标题 | 优先级 | 测试维度 | 关联测试点 | 关联风险 | 前置条件 | 操作步骤 | 测试数据 | 预期结果 |
|---|---|---|---|---|---|---|---|---|---|
| TC-001 | 用户使用正确密码登录成功 | P0 | 正向功能验证 | 登录主链路 | R-LOGIN-001 | 用户已注册 | 1. 打开登录页 2. 输入正确账号密码 3. 点击登录 | user@example.com / 正确密码 | 跳转到工作台 |

## 3. 测试点覆盖追溯

| 测试点 | 优先级 | 关联风险 | 覆盖用例 | 覆盖状态 |
|---|---|---|---|---|
| 登录主链路 | P0 | R-LOGIN-001 | TC-001 | 已覆盖 |
"""


def test_parse_lisa_test_asset_markdown_builds_export_payload_parts() -> None:
    parsed = parse_lisa_test_asset_markdown(CASES_MARKDOWN)

    assert parsed["testCases"] == [
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
        }
    ]
    assert parsed["coverageTrace"] == [
        {
            "testPoint": "登录主链路",
            "priority": "P0",
            "risk": "R-LOGIN-001",
            "testCases": ["TC-001"],
            "status": "已覆盖",
        }
    ]
    assert parsed["coverageSummary"] == {
        "totalTestCases": 1,
        "totalTestPoints": 1,
        "coveredTestPoints": 1,
        "partiallyCoveredTestPoints": 0,
        "uncoveredTestPoints": 0,
        "coverageRate": 100.0,
        "byPriority": [
            {
                "priority": "P0",
                "total": 1,
                "covered": 1,
                "partial": 0,
                "uncovered": 0,
                "coverageRate": 100.0,
            }
        ],
    }
    assert parsed["assetIssues"] == []
    assert parsed["riskMatrix"] == [
        {
            "risk": "R-LOGIN-001",
            "testCases": ["TC-001"],
            "testPoints": ["登录主链路"],
            "priorities": ["P0"],
            "dimensions": ["正向功能验证"],
            "coverageStatuses": ["已覆盖"],
        }
    ]
    assert parsed["intentTesterDrafts"][0]["sourceCaseId"] == "TC-001"
    assert parsed["intentTesterDrafts"][0]["priority"] == 1


def test_parse_lisa_test_asset_markdown_rejects_missing_case_table() -> None:
    markdown = """# 测试用例集

| 测试点 | 优先级 | 关联风险 | 覆盖用例 | 覆盖状态 |
|---|---|---|---|---|
| 登录主链路 | P0 | R-LOGIN-001 | TC-001 | 已覆盖 |
"""

    try:
        parse_lisa_test_asset_markdown(markdown)
    except ValueError as exc:
        assert str(exc) == "测试用例集缺少可解析的用例清单表格"
    else:
        raise AssertionError("missing case table should fail")


def test_build_lisa_test_assets_from_artifact_data_preserves_case_contract() -> None:
    builder = getattr(
        test_asset_parsing,
        "build_lisa_test_assets_from_artifact_data",
        None,
    )

    assert callable(builder), "artifactData 测试资产转换器必须存在"

    parsed = builder(VALID_CASES_ARTIFACT_DATA)

    assert parsed["testCases"][0] == {
        "id": "TC-001",
        "title": "用户使用正确密码登录成功",
        "priority": "P0",
        "dimension": "正向功能验证",
        "testPoint": "登录主链路",
        "risk": "R-LOGIN-001",
        "precondition": "用户已注册且账号可用",
        "steps": "1. 打开登录页 2. 输入正确账号密码 3. 点击登录",
        "testData": "user@example.com / 正确密码",
        "expectedResult": "跳转到工作台",
        "assertion": "工作台 URL、用户昵称和登录态均正确",
        "executionLayer": "E2E",
        "automationSuggestion": "优先自动化",
        "status": "可执行",
    }
