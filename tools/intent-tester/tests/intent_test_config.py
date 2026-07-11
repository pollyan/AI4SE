"""Explicit Intent Tester application configuration for test fixtures/probes."""

from werkzeug.security import generate_password_hash


def intent_test_config(**overrides):
    config = {
        "TESTING": True,
        "AI4SE_ENV": "test",
        "INTENT_ACCESS_MODE": "restricted",
        "INTENT_EXECUTION_ENABLED": True,
        "INTENT_PUBLIC_ORIGIN": "http://127.0.0.1:5001",
        "INTENT_PROXY_TOPOLOGY": "local-host",
        "INTENT_PROXY_TOKEN": "test-proxy-token-with-at-least-32b",
        "SECRET_KEY": "test-secret-key-with-at-least-32-bytes",
        "INTENT_TESTER_ADMIN_PASSWORD_HASH": generate_password_hash(
            "test-admin-password"
        ),
        "OPENAI_API_KEY": "test-provider-key",
        "OPENAI_BASE_URL": "http://127.0.0.1:3000/v1",
        "MIDSCENE_MODEL_NAME": "test-model",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    }
    config.update(overrides)
    return config
