from dataclasses import replace
from pathlib import Path

from scripts.validation.new_agents_workflow_dry_run import (
    WorkflowDryRunIssue,
    WorkflowDryRunReport,
    build_workflow_dry_run_report,
    load_workflow_dry_run_inputs,
    main,
)


REPO_ROOT = Path(__file__).resolve().parents[4]


def _issue_codes(report: WorkflowDryRunReport) -> set[str]:
    return {issue.code for issue in report.issues}


def test_new_agents_workflow_dry_run_passes_current_repository():
    inputs = load_workflow_dry_run_inputs(REPO_ROOT)

    report = build_workflow_dry_run_report(inputs)

    assert report.passed is True
    assert report.issues == []
    assert report.checks >= 10
    assert ("TEST_DESIGN", "CLARIFY") in inputs.manifest_stage_keys
    assert inputs.prompt_files_by_stage[("TEST_DESIGN", "CLARIFY")].name == "clarify.ts"


def test_new_agents_workflow_dry_run_reports_missing_frontend_template_mapping():
    inputs = load_workflow_dry_run_inputs(REPO_ROOT)
    missing_template_id = inputs.prompt_template_ids_by_stage[
        ("TEST_DESIGN", "CLARIFY")
    ]
    modified_inputs = replace(
        inputs,
        frontend_stage_content_template_ids=(
            inputs.frontend_stage_content_template_ids - {missing_template_id}
        ),
    )

    report = build_workflow_dry_run_report(modified_inputs)

    assert report.passed is False
    assert "FRONTEND_TEMPLATE_MAPPING_MISSING" in _issue_codes(report)
    assert any(
        issue.workflow_id == "TEST_DESIGN" and issue.stage_id == "CLARIFY"
        for issue in report.issues
    )


def test_new_agents_workflow_dry_run_reports_missing_artifact_data_renderer():
    inputs = load_workflow_dry_run_inputs(REPO_ROOT)
    modified_inputs = replace(
        inputs,
        artifact_data_renderer_stage_keys=(
            inputs.artifact_data_renderer_stage_keys - {("TEST_DESIGN", "CLARIFY")}
        ),
    )

    report = build_workflow_dry_run_report(modified_inputs)

    assert report.passed is False
    assert "ARTIFACT_DATA_RENDERER_MISSING" in _issue_codes(report)
    assert any(
        issue.workflow_id == "TEST_DESIGN" and issue.stage_id == "CLARIFY"
        for issue in report.issues
    )


def test_new_agents_workflow_dry_run_reports_missing_artifact_data_readiness():
    inputs = load_workflow_dry_run_inputs(REPO_ROOT)
    modified_inputs = replace(
        inputs,
        artifact_data_ready_stage_keys=(
            inputs.artifact_data_ready_stage_keys - {("TEST_DESIGN", "CLARIFY")}
        ),
    )

    report = build_workflow_dry_run_report(modified_inputs)

    assert report.passed is False
    assert "ARTIFACT_DATA_READY_MISSING" in _issue_codes(report)


def test_new_agents_workflow_dry_run_reports_manifest_visual_contract_mismatch():
    inputs = load_workflow_dry_run_inputs(REPO_ROOT)
    required_structured_visuals = dict(inputs.required_structured_visuals)
    required_structured_visuals[("TEST_DESIGN", "CLARIFY")] = {"flow-map"}
    modified_inputs = replace(
        inputs,
        required_structured_visuals=required_structured_visuals,
    )

    report = build_workflow_dry_run_report(modified_inputs)

    assert report.passed is False
    assert "MANIFEST_VISUAL_CONTRACT_MISMATCH" in _issue_codes(report)
    assert any(
        issue.workflow_id == "TEST_DESIGN" and issue.stage_id == "CLARIFY"
        for issue in report.issues
    )


def test_new_agents_workflow_dry_run_reports_flow_map_table_shape(tmp_path: Path):
    inputs = load_workflow_dry_run_inputs(REPO_ROOT)
    prompt_file = tmp_path / "story_flow_map_prompt.ts"
    prompt_file.write_text(
        """
export const STORY_FLOW_MAP_PROMPT = `请输出结构化业务数据。`;
export const STORY_FLOW_MAP_TEMPLATE = `最终渲染示例：
```ai4se-visual
{"type": "flow-map", "columns": ["节点", "状态"], "rows": [{"节点": "EPIC-001", "状态": "已识别"}]}
```
`;
""",
        encoding="utf-8",
    )
    prompt_files_by_stage = dict(inputs.prompt_files_by_stage)
    prompt_files_by_stage[("STORY_BREAKDOWN", "INPUT_ANALYSIS")] = prompt_file
    required_structured_visuals = dict(inputs.required_structured_visuals)
    required_structured_visuals[("STORY_BREAKDOWN", "INPUT_ANALYSIS")] = {
        "flow-map"
    }
    modified_inputs = replace(
        inputs,
        prompt_files_by_stage=prompt_files_by_stage,
        required_structured_visuals=required_structured_visuals,
    )

    report = build_workflow_dry_run_report(modified_inputs)

    assert report.passed is False
    assert "STRUCTURED_VISUAL_NODE_EDGE_SHAPE_MISSING" in _issue_codes(report)


def test_new_agents_workflow_dry_run_cli_returns_nonzero_for_reported_issues(
    capsys,
    monkeypatch,
):
    def fake_loader(repo_root: Path):
        return load_workflow_dry_run_inputs(repo_root)

    def fake_report(_inputs):
        return WorkflowDryRunReport(
            issues=[
                WorkflowDryRunIssue(
                    code="FRONTEND_TEMPLATE_MAPPING_MISSING",
                    message="缺少前端 template 映射",
                    workflow_id="TEST_DESIGN",
                    stage_id="CLARIFY",
                )
            ],
            checks=1,
        )

    monkeypatch.setattr(
        "scripts.validation.new_agents_workflow_dry_run.load_workflow_dry_run_inputs",
        fake_loader,
    )
    monkeypatch.setattr(
        "scripts.validation.new_agents_workflow_dry_run.build_workflow_dry_run_report",
        fake_report,
    )

    exit_code = main([str(REPO_ROOT)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "New Agents workflow dry-run failed" in captured.out
    assert "FRONTEND_TEMPLATE_MAPPING_MISSING" in captured.out
    assert "TEST_DESIGN/CLARIFY" in captured.out
