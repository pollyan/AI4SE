"""Regression coverage for the retired MidScene callback routes."""

from backend.models import ExecutionHistory


def test_midscene_execution_start_is_404_without_creating_history(
    api_client, create_test_testcase
):
    testcase = create_test_testcase(name="retired start")
    response = api_client.post(
        "/api/midscene/execution-start",
        json={
            "execution_id": "retired-start",
            "testcase_id": testcase.id,
            "mode": "headless",
        },
    )

    assert response.status_code == 404
    assert ExecutionHistory.query.filter_by(execution_id="retired-start").first() is None


def test_midscene_execution_result_is_404_without_updating_history(
    api_client, create_execution_history
):
    execution = create_execution_history(
        execution_id="retired-result", status="running", end_time=None
    )
    response = api_client.post(
        "/api/midscene/execution-result",
        json={"execution_id": execution.execution_id, "status": "success"},
    )

    assert response.status_code == 404
    ExecutionHistory.query.session.refresh(execution)
    assert execution.status == "running"
    assert execution.end_time is None
