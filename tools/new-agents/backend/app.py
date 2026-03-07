import json
import os
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from models import db, LlmConfig
from config import Config
from openai import OpenAI


def create_app(test_config=None):
    """Application factory for Flask app."""
    app = Flask(__name__)
    CORS(app)

    if test_config is None:
        app.config.from_object(Config)
    else:
        app.config.from_mapping(test_config)

    # Configure SQLAlchemy
    if 'SQLALCHEMY_DATABASE_URI' not in app.config:
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config.get('DATABASE_URL', Config.DATABASE_URL)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Create tables if not in testing mode (tests handle their own setup)
    if not os.environ.get('FLASK_TESTING'):
        with app.app_context():
            db.create_all()

    # Register routes
    init_routes(app)

    return app


def init_routes(app):
    """Register all routes with the app."""

    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({"status": "ok", "service": "new-agents-backend"})

    @app.route('/api/config', methods=['GET'])
    def get_default_config():
        """获取系统默认模型配置（不返回 API Key）"""
        try:
            config = LlmConfig.query.filter_by(
                config_key='default', is_active=True
            ).first()
            if not config:
                return jsonify({"hasDefault": False}), 200
            return jsonify({
                "hasDefault": True,
                "baseUrl": config.base_url,
                "model": config.model,
                "description": config.description
            })
        except Exception as e:
            app.logger.error(f"Error getting config: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/chat/stream', methods=['POST'])
    def chat_stream():
        """SSE 流式代理转发 LLM 请求"""
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体为空"}), 400

        messages = data.get('messages', [])
        model_override = data.get('model')
        temperature = data.get('temperature', 0.7)

        if not messages:
            return jsonify({"error": "messages 不能为空"}), 400

        config = LlmConfig.query.filter_by(
            config_key='default', is_active=True
        ).first()

        if not config:
            return jsonify({"error": "系统未配置默认 LLM，请在设置中配置您自己的 API Key"}), 503

        api_key = config.api_key
        base_url = config.base_url
        default_model = config.model

        def generate():
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                model = model_override or default_model
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    stream=True
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        yield f"data: {json.dumps({'content': delta.content})}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )


# For backward compatibility and direct execution
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)