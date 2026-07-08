import os
import tempfile
from unittest.mock import patch

import pytest

from agent_contracts import (
    REQUIRED_ARTIFACT_HEADINGS,
    REQUIRED_ARTIFACT_MERMAID_DIAGRAMS,
    REQUIRED_ARTIFACT_STRUCTURED_VISUALS,
)
from app import create_app
from models import LlmConfig, db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with app.app_context():
        db.create_all()
        yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def default_config(app):
    with app.app_context():
        db.session.add(
            LlmConfig(
                config_key="default",
                api_key="test-api-key",
                base_url="https://api.test.com/v1",
                model="test-model",
            )
        )
        db.session.commit()


def test_mermaid_repair_rejects_missing_broken_code(client, default_config) -> None:
    response = client.post(
        "/api/utils/mermaid/repair",
        json={"errorMessage": "Syntax Error"},
    )

    assert response.status_code == 400
    assert response.json == {"error": "brokenCode 不能为空"}


def test_mermaid_repair_returns_json_error_for_empty_json_body(
    client,
    default_config,
) -> None:
    response = client.post(
        "/api/utils/mermaid/repair",
        data="",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == {"error": "请求体为空"}


def test_mermaid_repair_returns_json_error_for_malformed_json_body(
    client,
    default_config,
) -> None:
    response = client.post(
        "/api/utils/mermaid/repair",
        data="{broken",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json == {"error": "请求体不是合法 JSON"}


@patch("routes.repair_mermaid_code")
def test_mermaid_repair_rejects_negative_block_index_before_service(
    mock_repair,
    client,
    default_config,
) -> None:
    response = client.post(
        "/api/utils/mermaid/repair",
        json={
            "brokenCode": "graph TD\n  A-->",
            "errorMessage": "Syntax Error",
            "blockIndex": -1,
        },
    )

    assert response.status_code == 400
    assert response.json == {"error": "blockIndex 不能为负数"}
    mock_repair.assert_not_called()


def test_mermaid_repair_requires_default_llm_config(client) -> None:
    response = client.post(
        "/api/utils/mermaid/repair",
        json={
            "brokenCode": "graph TD\n  A-->",
            "errorMessage": "Syntax Error",
        },
    )

    assert response.status_code == 503
    assert "系统未配置" in response.json["error"]


@patch("routes.repair_mermaid_code")
def test_mermaid_repair_returns_typed_json_response(
    mock_repair,
    client,
    default_config,
) -> None:
    mock_repair.return_value = "graph TD\n  A-->B"

    response = client.post(
        "/api/utils/mermaid/repair",
        json={
            "brokenCode": "graph TD\n  A-->",
            "errorMessage": "Syntax Error",
            "blockIndex": 1,
        },
    )

    assert response.status_code == 200
    assert response.json == {"repairedCode": "graph TD\n  A-->B"}
    request = mock_repair.call_args.args[0]
    assert request.broken_code == "graph TD\n  A-->"
    assert request.error_message == "Syntax Error"
    assert request.block_index == 1
    assert mock_repair.call_args.kwargs == {
        "api_key": "test-api-key",
        "base_url": "https://api.test.com/v1",
        "model_name": "test-model",
    }


def _complete_contract_markdown(workflow_id: str, stage_id: str) -> str:
    headings = REQUIRED_ARTIFACT_HEADINGS[(workflow_id, stage_id)]
    markdown = "\n\n".join(
        f"{heading}\n该章节用于验证 Mermaid repair 后的完整 artifact contract。"
        for heading in headings
    )
    mermaid_blocks = [
        f"```mermaid\n{diagram_type}\n```"
        for diagram_type in REQUIRED_ARTIFACT_MERMAID_DIAGRAMS.get(
            (workflow_id, stage_id),
            [],
        )
    ]
    structured_visual_blocks = [
        (
            "```ai4se-visual\n"
            "{\n"
            f'  "type": "{visual_type}",\n'
            '  "title": "风险看板",\n'
            '  "columns": ["风险", "优先级"],\n'
            '  "rows": [\n'
            '    {"风险": "R-001", "优先级": "P0"}\n'
            "  ]\n"
            "}\n"
            "```"
        )
        for visual_type in REQUIRED_ARTIFACT_STRUCTURED_VISUALS.get(
            (workflow_id, stage_id),
            [],
        )
    ]
    visual_blocks = mermaid_blocks + structured_visual_blocks
    if visual_blocks:
        return f"{markdown}\n\n" + "\n\n".join(visual_blocks)
    return markdown


@patch("routes.repair_mermaid_code")
def test_mermaid_repair_validates_candidate_artifact_contract(
    mock_repair,
    client,
    default_config,
) -> None:
    mock_repair.return_value = "quadrantChart\n  title 修复后的风险矩阵"
    current_artifact = _complete_contract_markdown("TEST_DESIGN", "STRATEGY")

    response = client.post(
        "/api/utils/mermaid/repair",
        json={
            "brokenCode": "quadrantChart\n  title broken",
            "errorMessage": "Syntax Error",
            "blockIndex": 0,
            "workflowId": "TEST_DESIGN",
            "stageId": "STRATEGY",
            "currentArtifact": current_artifact,
        },
    )

    assert response.status_code == 200
    assert response.json == {
        "repairedCode": "quadrantChart\n  title 修复后的风险矩阵"
    }


@patch("routes.repair_mermaid_code")
def test_mermaid_repair_rejects_candidate_when_artifact_contract_fails(
    mock_repair,
    client,
    default_config,
) -> None:
    mock_repair.return_value = "flowchart TD\n  A-->B"
    current_artifact = _complete_contract_markdown("TEST_DESIGN", "STRATEGY")

    response = client.post(
        "/api/utils/mermaid/repair",
        json={
            "brokenCode": "quadrantChart\n  title broken",
            "errorMessage": "Syntax Error",
            "blockIndex": 0,
            "workflowId": "TEST_DESIGN",
            "stageId": "STRATEGY",
            "currentArtifact": current_artifact,
        },
    )

    assert response.status_code == 502
    assert "artifact contract" in response.json["error"]
    assert "missing required artifact visualizations" in response.json["error"]
