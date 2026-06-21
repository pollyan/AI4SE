TEST_CASE_HEADERS = [
    "ID",
    "用例标题",
    "优先级",
    "测试维度",
    "关联测试点",
    "关联风险",
    "前置条件",
    "操作步骤",
    "测试数据",
    "预期结果",
]
OPTIONAL_TEST_CASE_HEADERS = {
    "断言": "assertion",
    "执行层级": "executionLayer",
    "自动化建议": "automationSuggestion",
    "状态": "status",
}
COVERAGE_HEADERS = ["测试点", "优先级", "关联风险", "覆盖用例", "覆盖状态"]


def parse_lisa_test_asset_markdown(markdown: str) -> dict:
    case_rows = _parse_tables_with_headers(markdown, TEST_CASE_HEADERS)
    coverage_rows = _parse_tables_with_headers(markdown, COVERAGE_HEADERS)
    if not case_rows:
        raise ValueError("测试用例集缺少可解析的用例清单表格")

    test_cases = [_map_test_case(row) for row in case_rows]
    coverage_trace = [_map_coverage(row) for row in coverage_rows]

    return {
        "testCases": test_cases,
        "coverageTrace": coverage_trace,
        "coverageSummary": build_coverage_summary(test_cases, coverage_trace),
        "assetIssues": _build_asset_issues(test_cases, coverage_trace),
        "riskMatrix": build_risk_matrix(test_cases, coverage_trace),
        "intentTesterDrafts": build_intent_tester_drafts(test_cases),
    }


def build_coverage_summary(
    test_cases: list[dict],
    coverage_trace: list[dict],
) -> dict:
    total_points = len(coverage_trace)
    covered = sum(1 for row in coverage_trace if row["status"] == "已覆盖")
    partial = sum(1 for row in coverage_trace if row["status"] == "部分覆盖")
    uncovered = sum(1 for row in coverage_trace if row["status"] == "未覆盖")

    return {
        "totalTestCases": len(test_cases),
        "totalTestPoints": total_points,
        "coveredTestPoints": covered,
        "partiallyCoveredTestPoints": partial,
        "uncoveredTestPoints": uncovered,
        "coverageRate": _coverage_rate(covered, total_points),
        "byPriority": _build_priority_coverage(coverage_trace),
    }


def build_risk_matrix(test_cases: list[dict], coverage_trace: list[dict]) -> list[dict]:
    risk_index: dict[str, dict[str, set[str]]] = {}

    for test_case in test_cases:
        risk = _normalize_risk(test_case["risk"])
        if risk is None:
            continue
        entry = _risk_entry(risk_index, risk)
        entry["testCases"].add(test_case["id"])
        entry["testPoints"].add(test_case["testPoint"])
        entry["priorities"].add(test_case["priority"])
        entry["dimensions"].add(test_case["dimension"])

    for trace in coverage_trace:
        risk = _normalize_risk(trace["risk"])
        if risk is None:
            continue
        entry = _risk_entry(risk_index, risk)
        entry["testPoints"].add(trace["testPoint"])
        entry["priorities"].add(trace["priority"])
        entry["coverageStatuses"].add(trace["status"])
        for case_id in trace["testCases"]:
            entry["testCases"].add(case_id)

    return [
        {
            "risk": risk,
            "testCases": sorted(entry["testCases"]),
            "testPoints": sorted(entry["testPoints"]),
            "priorities": sorted(entry["priorities"]),
            "dimensions": sorted(entry["dimensions"]),
            "coverageStatuses": sorted(entry["coverageStatuses"]),
        }
        for risk, entry in sorted(risk_index.items())
    ]


def build_intent_tester_drafts(test_cases: list[dict]) -> list[dict]:
    return [_build_intent_tester_draft(test_case) for test_case in test_cases]


def normalize_risk(risk: str) -> str | None:
    normalized = risk.strip()
    if not normalized or normalized in {"-", "无", "N/A", "n/a"}:
        return None
    return normalized


def _parse_tables_with_headers(markdown: str, required_headers: list[str]) -> list[dict]:
    rows = []
    lines = markdown.splitlines()
    index = 0
    while index < len(lines):
        if not _is_table_row(lines[index]):
            index += 1
            continue

        headers = _split_table_row(lines[index])
        if not all(header in headers for header in required_headers):
            index += 1
            continue
        if index + 1 >= len(lines) or not _is_separator_row(lines[index + 1]):
            raise ValueError(f"Markdown 表格缺少分隔行: {', '.join(required_headers)}")

        index += 2
        while index < len(lines) and _is_table_row(lines[index]):
            values = _split_table_row(lines[index])
            if len(values) != len(headers):
                raise ValueError("Markdown 表格列数与表头不一致")
            rows.append(dict(zip(headers, values, strict=True)))
            index += 1
        continue
    return rows


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _is_separator_row(line: str) -> bool:
    cells = _split_table_row(line)
    return bool(cells) and all(
        set(cell.replace(":", "").strip()) <= {"-"}
        for cell in cells
    )


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _map_test_case(row: dict) -> dict:
    mapped = {
        "id": row["ID"],
        "title": row["用例标题"],
        "priority": row["优先级"],
        "dimension": row["测试维度"],
        "testPoint": row["关联测试点"],
        "risk": row["关联风险"],
        "precondition": row["前置条件"],
        "steps": row["操作步骤"],
        "testData": row["测试数据"],
        "expectedResult": row["预期结果"],
    }
    for markdown_header, output_field in OPTIONAL_TEST_CASE_HEADERS.items():
        if markdown_header in row:
            mapped[output_field] = row[markdown_header]
    return mapped


def _map_coverage(row: dict) -> dict:
    return {
        "testPoint": row["测试点"],
        "priority": row["优先级"],
        "risk": row["关联风险"],
        "testCases": [
            item.strip()
            for item in row["覆盖用例"].split(",")
            if item.strip()
        ],
        "status": row["覆盖状态"],
    }


def _build_priority_coverage(coverage_trace: list[dict]) -> list[dict]:
    priorities = sorted({row["priority"] for row in coverage_trace})
    summary = []
    for priority in priorities:
        rows = [row for row in coverage_trace if row["priority"] == priority]
        covered = sum(1 for row in rows if row["status"] == "已覆盖")
        partial = sum(1 for row in rows if row["status"] == "部分覆盖")
        uncovered = sum(1 for row in rows if row["status"] == "未覆盖")
        summary.append(
            {
                "priority": priority,
                "total": len(rows),
                "covered": covered,
                "partial": partial,
                "uncovered": uncovered,
                "coverageRate": _coverage_rate(covered, len(rows)),
            }
        )
    return summary


def _coverage_rate(covered: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((covered / total) * 100, 2)


def _build_asset_issues(test_cases: list[dict], coverage_trace: list[dict]) -> list[dict]:
    issues = []
    known_case_ids = {test_case["id"] for test_case in test_cases}
    referenced_case_ids = set()

    for trace in coverage_trace:
        for case_id in trace["testCases"]:
            referenced_case_ids.add(case_id)
            if case_id not in known_case_ids:
                issues.append(
                    {
                        "type": "unknown_coverage_case",
                        "testPoint": trace["testPoint"],
                        "caseId": case_id,
                        "message": f"覆盖追溯引用了不存在的测试用例 {case_id}",
                    }
                )

    for case_id in sorted(known_case_ids - referenced_case_ids):
        issues.append(
            {
                "type": "orphan_test_case",
                "caseId": case_id,
                "message": f"测试用例 {case_id} 未被任何测试点覆盖追溯引用",
            }
        )

    return issues


def _risk_entry(risk_index: dict[str, dict[str, set[str]]], risk: str) -> dict[str, set[str]]:
    if risk not in risk_index:
        risk_index[risk] = {
            "testCases": set(),
            "testPoints": set(),
            "priorities": set(),
            "dimensions": set(),
            "coverageStatuses": set(),
        }
    return risk_index[risk]


def _normalize_risk(risk: str) -> str | None:
    return normalize_risk(risk)


def _build_intent_tester_draft(test_case: dict) -> dict:
    description_lines = [
        "来源: New Agents Lisa TEST_DESIGN/CASES",
        f"测试点: {test_case['testPoint']}",
        f"关联风险: {test_case['risk']}",
        f"前置条件: {test_case['precondition']}",
        f"测试数据: {test_case['testData']}",
        f"预期结果: {test_case['expectedResult']}",
    ]
    optional_descriptions = [
        ("assertion", "断言"),
        ("executionLayer", "执行层级"),
        ("automationSuggestion", "自动化建议"),
        ("status", "状态"),
    ]
    for field, label in optional_descriptions:
        value = test_case.get(field)
        if isinstance(value, str) and value.strip():
            description_lines.append(f"{label}: {value}")

    return {
        "sourceCaseId": test_case["id"],
        "name": f"{test_case['id']} {test_case['title']}",
        "description": "\n".join(description_lines),
        "category": test_case["dimension"],
        "priority": _intent_tester_priority(test_case["priority"]),
        "tags": _intent_tester_tags(test_case),
        "steps": [
            {
                "action": "ai_assert",
                "params": {"prompt": f"确认前置条件成立：{test_case['precondition']}"},
            },
            {
                "action": "ai_assert",
                "params": {
                    "prompt": (
                        f"按自然语言测试步骤执行并观察：{test_case['steps']}；"
                        f"测试数据：{test_case['testData']}"
                    )
                },
            },
            {
                "action": "ai_assert",
                "params": {"prompt": f"验证预期结果：{test_case['expectedResult']}"},
            },
        ],
        "draftWarnings": [
            "该草稿由 Lisa Markdown 用例派生，导入 intent-tester 前需要人工校准页面 URL、定位语义和可执行步骤。"
        ],
    }


def _intent_tester_priority(priority: str) -> int:
    return {"P0": 1, "P1": 2, "P2": 3}.get(priority, 3)


def _intent_tester_tags(test_case: dict) -> list[str]:
    tags = ["lisa", "new-agents", test_case["id"], test_case["priority"]]
    risk = _normalize_risk(test_case["risk"])
    if risk is not None:
        tags.append(risk)
    return tags
