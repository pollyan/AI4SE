import os
import tempfile
from unittest.mock import patch

import pytest

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
