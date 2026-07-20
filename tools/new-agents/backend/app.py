import os
import hmac
import logging
import time
import uuid
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from sqlalchemy import inspect, text
from models import db
from config import Config
from config_admin_auth import (
    browser_config_admin_available,
    config_admin_keys_collide,
)
from config_service import upsert_default_llm_config_from_env
from routes import api_bp


def init_db(app):
    """Create database tables and seed server-managed defaults."""
    with app.app_context():
        db.create_all()
        _ensure_agent_artifact_version_columns()
        _ensure_agent_run_turn_metric_columns()
        _ensure_artifact_comment_columns()
        _ensure_artifact_section_lock_columns()
        upsert_default_llm_config_from_env()


def _ensure_agent_artifact_version_columns():
    """Upgrade existing artifact version tables with structured data storage."""
    inspector = inspect(db.engine)
    if "agent_artifact_versions" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("agent_artifact_versions")
    }
    if "artifact_data_json" not in existing_columns:
        db.session.execute(
            text(
                "ALTER TABLE agent_artifact_versions ADD COLUMN artifact_data_json TEXT"
            )
        )
        db.session.commit()


def _ensure_agent_run_turn_metric_columns():
    """Upgrade existing turn metric tables with sanitized diagnostics storage."""
    inspector = inspect(db.engine)
    if "agent_run_turn_metrics" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("agent_run_turn_metrics")
    }
    if "diagnostic_json" not in existing_columns:
        db.session.execute(
            text("ALTER TABLE agent_run_turn_metrics ADD COLUMN diagnostic_json TEXT")
        )
        db.session.commit()


def _ensure_artifact_comment_columns():
    """Upgrade existing comment tables created before threaded comments."""
    inspector = inspect(db.engine)
    if "agent_artifact_comments" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("agent_artifact_comments")
    }
    column_migrations = {
        "anchor_text": "ALTER TABLE agent_artifact_comments ADD COLUMN anchor_text TEXT",
        "status": "ALTER TABLE agent_artifact_comments ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'open'",
        "resolved_at_ms": "ALTER TABLE agent_artifact_comments ADD COLUMN resolved_at_ms INTEGER",
        "replies_json": "ALTER TABLE agent_artifact_comments ADD COLUMN replies_json TEXT NOT NULL DEFAULT '[]'",
    }
    for column_name, statement in column_migrations.items():
        if column_name not in existing_columns:
            db.session.execute(text(statement))
    db.session.commit()


def _ensure_artifact_section_lock_columns():
    """Upgrade existing section lock tables created before section anchors."""
    inspector = inspect(db.engine)
    if "agent_artifact_section_locks" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("agent_artifact_section_locks")
    }
    if "section_anchor" not in existing_columns:
        db.session.execute(
            text(
                "ALTER TABLE agent_artifact_section_locks ADD COLUMN section_anchor TEXT"
            )
        )
        db.session.commit()


def create_app(test_config=None):
    """Application factory for Flask app."""
    app = Flask(__name__)

    # Configure logging
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    # P0-1: CORS restricted to allowed origins only
    cors_origins = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:18679"
    )
    allowed_origins = [
        origin.strip() for origin in cors_origins.split(",") if origin.strip()
    ]
    CORS(app, origins=allowed_origins)

    if test_config is None:
        app.config.from_object(Config)
    else:
        app.config.from_mapping(test_config)

    # Configure SQLAlchemy
    if "SQLALCHEMY_DATABASE_URI" not in app.config:
        app.config["SQLALCHEMY_DATABASE_URI"] = app.config.get(
            "DATABASE_URL", Config.DATABASE_URL
        )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Create tables if not in testing mode (tests handle their own setup)
    if not os.environ.get("FLASK_TESTING"):
        init_db(app)

    # Register routes
    init_routes(app)

    return app


def init_routes(app):
    """Register all routes with the app."""

    @app.before_request
    def before_request():
        """记录请求开始时间 + P0-2: API Key 认证"""
        g.request_id = str(uuid.uuid4())[:8]
        g.start_time = time.time()
        app.logger.info(f"[{g.request_id}] {request.method} {request.path} - Started")

        # P0-2: API Key authentication for sensitive endpoints
        proxy_api_key = (os.environ.get("PROXY_API_KEY") or "").strip()
        config_admin_api_key = (
            os.environ.get("NEW_AGENTS_CONFIG_ADMIN_API_KEY") or ""
        ).strip()
        request_coordinate = (request.method, request.path)
        config_admin_requests = {
            ("POST", "/api/config"),
            ("POST", "/api/config/check"),
        }
        gateway_protected_requests = {
            ("POST", "/api/agent/runs/stream"),
            ("POST", "/api/config/default/check"),
            ("POST", "/api/utils/mermaid/repair"),
        }
        sensitive_requests = config_admin_requests | gateway_protected_requests
        if request_coordinate in sensitive_requests and config_admin_keys_collide():
            app.logger.error(
                f"[{g.request_id}] Service authentication credentials collide"
            )
            return jsonify({"error": "服务认证未正确配置"}), 503
        if request_coordinate in config_admin_requests:
            allow_unauthenticated = browser_config_admin_available()
            client_key = request.headers.get("X-API-Key", "")
            has_valid_admin_key = bool(config_admin_api_key) and hmac.compare_digest(
                client_key,
                config_admin_api_key,
            )
            if not has_valid_admin_key and not allow_unauthenticated:
                app.logger.warning(
                    f"[{g.request_id}] Unauthorized config administration attempt"
                )
                return jsonify({"error": "未授权访问，请提供配置管理密钥"}), 401
        elif proxy_api_key and request_coordinate in gateway_protected_requests:
            client_key = request.headers.get("X-API-Key", "")
            gateway_marker = request.headers.get("X-AI4SE-Gateway", "")
            trust_gateway_header = os.environ.get(
                "AI4SE_TRUST_GATEWAY_HEADER",
                "1",
            ).strip().lower() in {"1", "true", "yes"}
            is_gateway_request = trust_gateway_header and gateway_marker == "new-agents"
            has_valid_proxy_key = hmac.compare_digest(client_key, proxy_api_key)
            if not has_valid_proxy_key and not is_gateway_request:
                app.logger.warning(
                    f"[{g.request_id}] Unauthorized API access attempt to {request.path}"
                )
                return jsonify({"error": "未授权访问，请提供有效的 API Key"}), 401

    @app.after_request
    def after_request(response):
        """记录请求耗时"""
        if hasattr(g, "start_time"):
            elapsed = time.time() - g.start_time
            app.logger.info(
                f"[{g.request_id}] {request.method} {request.path} - Completed in {elapsed:.3f}s"
            )
        return response

    @app.errorhandler(Exception)
    def handle_exception(e):
        # 让 Flask 处理其自身的 HTTP 错误（如 415 UnsupportedMediaType）
        if hasattr(e, "code") and isinstance(e.code, int) and e.code < 500:
            return e
        app.logger.exception(f"[{g.request_id}] Unhandled exception: {str(e)}")
        return jsonify({"error": "服务器内部错误", "request_id": g.request_id}), 500

    app.register_blueprint(api_bp)


# For backward compatibility and direct execution
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
