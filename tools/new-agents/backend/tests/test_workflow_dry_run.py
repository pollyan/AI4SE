import json
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


def _write_scaffold_spec(tmp_path: Path) -> Path:
    spec_path = tmp_path / "support_triage_spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "workflowId": "SUPPORT_TRIAGE",
                "agentId": "lisa",
                "slug": "support-triage",
                "name": "支持工单分诊",
                "description": "帮助支持团队结构化分诊支持工单",
                "welcomeMessage": "你好，我会帮助你完成支持工单分诊。",
                "starterPrompts": ["请帮我分诊这个线上支持工单。"],
                "stages": [
                    {
                        "id": "INTAKE",
                        "name": "信息收集",
                        "promptTemplateId": "support_triage.intake",
                        "artifactTitle": "# 支持工单分诊",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return spec_path


def _create_minimal_scaffold_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    manifest_path = repo_root / "tools/new-agents/workflow_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps({"handoffs": [], "workflows": {}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return repo_root


def test_workflow_scaffold_preview_plans_manifest_and_prompt_writes(tmp_path):
    from scripts.validation.new_agents_workflow_scaffold import (
        build_scaffold_plan,
        load_workflow_scaffold_spec,
    )

    repo_root = _create_minimal_scaffold_repo(tmp_path)
    spec = load_workflow_scaffold_spec(_write_scaffold_spec(tmp_path))

    plan = build_scaffold_plan(repo_root, spec)

    planned_paths = {write.relative_path for write in plan.writes}
    assert "tools/new-agents/workflow_manifest.json" in planned_paths
    assert (
        "tools/new-agents/frontend/src/core/prompts/support_triage/intake.ts"
        in planned_paths
    )
    assert "SUPPORT_TRIAGE" in plan.summary
    assert "python3 scripts/validation/new_agents_workflow_dry_run.py" in plan.next_command
    prompt_write = next(
        write
        for write in plan.writes
        if write.relative_path.endswith("support_triage/intake.ts")
    )
    assert "SUPPORT_TRIAGE_INTAKE_PROMPT" in prompt_write.content
    assert "SUPPORT_TRIAGE_INTAKE_TEMPLATE" in prompt_write.content


def test_workflow_scaffold_write_creates_prompt_and_updates_manifest(tmp_path):
    from scripts.validation.new_agents_workflow_scaffold import (
        apply_scaffold_plan,
        build_scaffold_plan,
        load_workflow_scaffold_spec,
    )

    repo_root = _create_minimal_scaffold_repo(tmp_path)
    spec = load_workflow_scaffold_spec(_write_scaffold_spec(tmp_path))
    plan = build_scaffold_plan(repo_root, spec)

    apply_scaffold_plan(plan)

    manifest = json.loads(
        (repo_root / "tools/new-agents/workflow_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    workflow = manifest["workflows"]["SUPPORT_TRIAGE"]
    assert workflow["agentId"] == "lisa"
    assert workflow["slug"] == "support-triage"
    assert workflow["stages"][0]["id"] == "INTAKE"
    assert workflow["stages"][0]["promptTemplateId"] == "support_triage.intake"
    prompt_path = (
        repo_root
        / "tools/new-agents/frontend/src/core/prompts/support_triage/intake.ts"
    )
    assert prompt_path.exists()
    prompt_text = prompt_path.read_text(encoding="utf-8")
    assert "export const SUPPORT_TRIAGE_INTAKE_PROMPT" in prompt_text
    assert "export const SUPPORT_TRIAGE_INTAKE_TEMPLATE" in prompt_text


def test_workflow_scaffold_rejects_existing_prompt_file_without_overwrite(tmp_path):
    from scripts.validation.new_agents_workflow_scaffold import (
        WorkflowScaffoldError,
        apply_scaffold_plan,
        build_scaffold_plan,
        load_workflow_scaffold_spec,
    )

    repo_root = _create_minimal_scaffold_repo(tmp_path)
    prompt_path = (
        repo_root
        / "tools/new-agents/frontend/src/core/prompts/support_triage/intake.ts"
    )
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("existing", encoding="utf-8")
    spec = load_workflow_scaffold_spec(_write_scaffold_spec(tmp_path))
    plan = build_scaffold_plan(repo_root, spec)

    try:
        apply_scaffold_plan(plan)
    except WorkflowScaffoldError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("expected existing prompt file conflict")

    assert prompt_path.read_text(encoding="utf-8") == "existing"


def test_workflow_scaffold_rejects_duplicate_stage_ids(tmp_path):
    from scripts.validation.new_agents_workflow_scaffold import (
        WorkflowScaffoldError,
        load_workflow_scaffold_spec,
    )

    spec_path = _write_scaffold_spec(tmp_path)
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    data["stages"].append(dict(data["stages"][0]))
    spec_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    try:
        load_workflow_scaffold_spec(spec_path)
    except WorkflowScaffoldError as exc:
        assert "duplicate stage id" in str(exc)
    else:
        raise AssertionError("expected duplicate stage id to fail")


def test_workflow_scaffold_cli_preview_does_not_write_files(tmp_path, capsys):
    from scripts.validation.new_agents_workflow_scaffold import main as scaffold_main

    repo_root = _create_minimal_scaffold_repo(tmp_path)
    spec_path = _write_scaffold_spec(tmp_path)

    exit_code = scaffold_main(["--repo-root", str(repo_root), "--spec", str(spec_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Preview only; no files written." in captured.out
    assert "support_triage/intake.ts" in captured.out
    assert "new_agents_workflow_dry_run.py" in captured.out
    assert not (
        repo_root
        / "tools/new-agents/frontend/src/core/prompts/support_triage/intake.ts"
    ).exists()
