"""
API Key Authentication Tests - P0-2 认证中间件测试
"""

import pytest
import os
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["FLASK_TESTING"] = "1"

from app import create_app
from models import db

VALID_AGENT_RUN_PAYLOAD = {
    "prompt": "hi",
    "systemPrompt": "system",
    "workflowId": "TEST_DESIGN",
    "stageId": "CLARIFY",
}


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


@pytest.fixture
def client(app):
    return app.test_client()


class TestAPIKeyAuth:
    """测试 API Key 认证中间件"""

    def test_no_key_returns_401(self, client, monkeypatch):
        """设置 PROXY_API_KEY 后，无 X-API-Key 返回 401"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")
        resp = client.post(
            "/api/agent/runs/stream",
            json=VALID_AGENT_RUN_PAYLOAD,
        )
        assert resp.status_code == 401

    def test_mermaid_repair_no_key_returns_401(self, client, monkeypatch):
        """设置 PROXY_API_KEY 后，Mermaid 修复端点无 X-API-Key 返回 401"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")
        resp = client.post(
            "/api/utils/mermaid/repair",
            json={
                "brokenCode": "graph TD\n  A-->",
                "errorMessage": "Syntax Error",
            },
        )
        assert resp.status_code == 401

    def test_config_check_no_key_returns_401(self, client, monkeypatch):
        """模型配置检测会携带服务端密钥，必须经过代理认证。"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")

        resp = client.post("/api/config/check")

        assert resp.status_code == 401

    def test_config_update_no_key_returns_401(self, client, monkeypatch):
        """默认模型配置写入同样必须经过代理认证。"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")

        resp = client.post("/api/config", json={})

        assert resp.status_code == 401

    @pytest.mark.parametrize(
        "path",
        ["/api/config", "/api/config/check"],
    )
    def test_config_admin_endpoints_reject_runtime_proxy_and_gateway_credentials(
        self,
        client,
        monkeypatch,
        path,
    ):
        monkeypatch.setenv("PROXY_API_KEY", "runtime-proxy-key")
        monkeypatch.setenv(
            "NEW_AGENTS_CONFIG_ADMIN_API_KEY",
            "config-admin-key",
        )
        monkeypatch.setenv("AI4SE_TRUST_GATEWAY_HEADER", "1")

        resp = client.post(
            path,
            json={"baseUrl": "https://attacker.example/v1"},
            headers={
                "X-API-Key": "runtime-proxy-key",
                "X-AI4SE-Gateway": "new-agents",
            },
        )

        assert resp.status_code == 401

    @pytest.mark.parametrize(
        "path",
        ["/api/config", "/api/config/check"],
    )
    def test_config_admin_endpoints_accept_only_config_admin_key(
        self,
        client,
        monkeypatch,
        path,
    ):
        monkeypatch.setenv("PROXY_API_KEY", "runtime-proxy-key")
        monkeypatch.setenv(
            "NEW_AGENTS_CONFIG_ADMIN_API_KEY",
            "config-admin-key",
        )

        resp = client.post(
            path,
            json={},
            headers={"X-API-Key": "config-admin-key"},
        )

        assert resp.status_code != 401

    @pytest.mark.parametrize(
        "path",
        ["/api/config", "/api/config/check"],
    )
    def test_production_config_admin_endpoints_fail_closed_without_key(
        self,
        client,
        monkeypatch,
        path,
    ):
        monkeypatch.delenv("PROXY_API_KEY", raising=False)
        monkeypatch.delenv("NEW_AGENTS_CONFIG_ADMIN_API_KEY", raising=False)
        monkeypatch.setenv("AI4SE_ENV", "production")
        monkeypatch.setenv(
            "NEW_AGENTS_CONFIG_ADMIN_ALLOW_UNAUTHENTICATED",
            "true",
        )

        resp = client.post(
            path,
            json={"baseUrl": "https://attacker.example/v1"},
            headers={"X-AI4SE-Gateway": "new-agents"},
        )

        assert resp.status_code == 401

    @pytest.mark.parametrize("environment", ["", "staging", "production-typo"])
    def test_unauthenticated_config_admin_requires_explicit_local_environment(
        self,
        client,
        monkeypatch,
        environment,
    ):
        monkeypatch.delenv("PROXY_API_KEY", raising=False)
        monkeypatch.delenv("NEW_AGENTS_CONFIG_ADMIN_API_KEY", raising=False)
        monkeypatch.delenv("NEW_AGENTS_DEFAULT_LLM_API_KEY", raising=False)
        monkeypatch.setenv("AI4SE_ENV", environment)
        monkeypatch.setenv(
            "NEW_AGENTS_CONFIG_ADMIN_ALLOW_UNAUTHENTICATED",
            "true",
        )

        resp = client.post(
            "/api/config/check",
            json={"baseUrl": "https://attacker.example/v1"},
        )

        assert resp.status_code == 401

    @patch("routes.check_default_llm_config")
    def test_unauthorized_config_check_never_calls_provider(
        self,
        mock_check_default_llm_config,
        client,
        monkeypatch,
    ):
        monkeypatch.setenv(
            "NEW_AGENTS_CONFIG_ADMIN_API_KEY",
            "config-admin-key",
        )

        resp = client.post(
            "/api/config/check",
            json={"baseUrl": "https://attacker.example/v1"},
            headers={"X-AI4SE-Gateway": "new-agents"},
        )

        assert resp.status_code == 401
        mock_check_default_llm_config.assert_not_called()

    @pytest.mark.parametrize(
        ("proxy_key", "admin_key", "provider_key"),
        [
            ("shared-key", "shared-key", "provider-key"),
            ("runtime-key", "shared-key", "shared-key"),
            ("shared-key", "admin-key", "shared-key"),
        ],
    )
    @patch("routes.check_default_llm_config")
    def test_equal_runtime_and_config_admin_keys_fail_closed(
        self,
        mock_check_default_llm_config,
        client,
        monkeypatch,
        proxy_key,
        admin_key,
        provider_key,
    ):
        monkeypatch.setenv("AI4SE_ENV", "production")
        monkeypatch.setenv("PROXY_API_KEY", proxy_key)
        monkeypatch.setenv("NEW_AGENTS_CONFIG_ADMIN_API_KEY", admin_key)
        monkeypatch.setenv("NEW_AGENTS_DEFAULT_LLM_API_KEY", provider_key)

        resp = client.post(
            "/api/config/check",
            json={
                "apiKey": "provider-key",
                "baseUrl": "https://attacker.example/v1",
                "model": "capture-authorization",
            },
            headers={"X-API-Key": admin_key},
        )

        assert resp.status_code == 503
        assert resp.json == {"error": "服务认证未正确配置"}
        mock_check_default_llm_config.assert_not_called()

    def test_runtime_default_config_check_requires_proxy_or_gateway_auth(
        self,
        client,
        monkeypatch,
    ):
        monkeypatch.setenv("PROXY_API_KEY", "runtime-proxy-key")

        resp = client.post("/api/config/default/check")

        assert resp.status_code == 401

    @pytest.mark.parametrize(
        "path",
        ["/api/agent/runs/stream", "/api/config/default/check"],
    )
    def test_runtime_requests_fail_closed_when_env_credentials_collide(
        self,
        client,
        monkeypatch,
        path,
    ):
        monkeypatch.setenv("PROXY_API_KEY", "shared-runtime-provider-key")
        monkeypatch.setenv(
            "NEW_AGENTS_CONFIG_ADMIN_API_KEY",
            "independent-admin-key",
        )
        monkeypatch.setenv(
            "NEW_AGENTS_DEFAULT_LLM_API_KEY",
            "shared-runtime-provider-key",
        )

        resp = client.post(
            path,
            json=VALID_AGENT_RUN_PAYLOAD if path.endswith("stream") else None,
            headers={"X-API-Key": "shared-runtime-provider-key"},
        )

        assert resp.status_code == 503
        assert resp.json == {"error": "服务认证未正确配置"}

    def test_wrong_key_returns_401(self, client, monkeypatch):
        """设置 PROXY_API_KEY 后，错误 Key 返回 401"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")
        resp = client.post(
            "/api/agent/runs/stream",
            json=VALID_AGENT_RUN_PAYLOAD,
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_correct_key_passes(self, client, app, monkeypatch):
        """设置 PROXY_API_KEY 后，正确 Key 放行（可能因无配置返回 503，但不是 401）"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")
        resp = client.post(
            "/api/agent/runs/stream",
            json=VALID_AGENT_RUN_PAYLOAD,
            headers={"X-API-Key": "secret-key"},
        )
        assert resp.status_code != 401

    def test_gateway_forwarded_agent_request_passes_without_browser_key(
        self,
        client,
        monkeypatch,
    ):
        """浏览器经 Nginx 网关注入内部头后，不需要把 PROXY_API_KEY 暴露给前端"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")
        resp = client.post(
            "/api/agent/runs/stream",
            json=VALID_AGENT_RUN_PAYLOAD,
            headers={"X-AI4SE-Gateway": "new-agents"},
        )
        assert resp.status_code != 401

    def test_gateway_forwarded_mermaid_repair_request_passes_without_browser_key(
        self,
        client,
        monkeypatch,
    ):
        """Mermaid 修复同样应允许可信网关转发，不要求浏览器持有后端密钥"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")
        resp = client.post(
            "/api/utils/mermaid/repair",
            json={
                "brokenCode": "graph TD\n  A-->",
                "errorMessage": "Syntax Error",
            },
            headers={"X-AI4SE-Gateway": "new-agents"},
        )
        assert resp.status_code != 401

    def test_wrong_gateway_marker_does_not_bypass_proxy_key(
        self,
        client,
        monkeypatch,
    ):
        """内部网关标记必须精确匹配，避免任意头值绕过认证"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")
        resp = client.post(
            "/api/agent/runs/stream",
            json=VALID_AGENT_RUN_PAYLOAD,
            headers={"X-AI4SE-Gateway": "wrong"},
        )
        assert resp.status_code == 401

    def test_gateway_marker_does_not_bypass_when_explicitly_disabled(
        self,
        client,
        monkeypatch,
    ):
        """真实本机 E2E 可禁用可伪造的固定网关标记。"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")
        monkeypatch.setenv("AI4SE_TRUST_GATEWAY_HEADER", "0")

        resp = client.post(
            "/api/agent/runs/stream",
            json=VALID_AGENT_RUN_PAYLOAD,
            headers={"X-AI4SE-Gateway": "new-agents"},
        )

        assert resp.status_code == 401

    @pytest.mark.parametrize(
        ("path", "payload"),
        [
            ("/api/config", {"baseUrl": "https://attacker.example/v1"}),
            ("/api/config/check", {"baseUrl": "https://attacker.example/v1"}),
            ("/api/agent/runs/stream", VALID_AGENT_RUN_PAYLOAD),
            (
                "/api/utils/mermaid/repair",
                {"brokenCode": "graph TD\nA-->", "errorMessage": "invalid"},
            ),
        ],
    )
    def test_strict_proxy_auth_rejects_forged_gateway_on_sensitive_posts(
        self,
        client,
        monkeypatch,
        path,
        payload,
    ):
        monkeypatch.setenv("PROXY_API_KEY", "server-only-secret-key")
        monkeypatch.setenv("AI4SE_TRUST_GATEWAY_HEADER", "0")

        resp = client.post(
            path,
            json=payload,
            headers={
                "X-API-Key": "browser-forged-key",
                "X-AI4SE-Gateway": "new-agents",
            },
        )

        assert resp.status_code == 401

    def test_no_proxy_key_allows_all(self, client, monkeypatch):
        """未设置 PROXY_API_KEY 时，请求正常放行"""
        monkeypatch.delenv("PROXY_API_KEY", raising=False)
        resp = client.post(
            "/api/agent/runs/stream",
            json=VALID_AGENT_RUN_PAYLOAD,
        )
        assert resp.status_code != 401

    def test_non_stream_endpoint_no_auth(self, client, monkeypatch):
        """非敏感端点不需要认证"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_get_method_on_agent_stream_no_auth(self, client, monkeypatch):
        """GET /api/agent/runs/stream 不需要认证（只对 POST 限制）"""
        monkeypatch.setenv("PROXY_API_KEY", "secret-key")
        resp = client.get("/api/agent/runs/stream")
        assert resp.status_code != 401
