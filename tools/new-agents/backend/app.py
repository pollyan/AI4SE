import json
import os
import logging
import time
import uuid
from flask import Flask, request, Response, jsonify, g
from flask_cors import CORS
from models import db, LlmConfig
from config import Config
from openai import OpenAI, APIError, AuthenticationError, RateLimitError


def create_app(test_config=None):
    """Application factory for Flask app."""
    app = Flask(__name__)

    # Configure logging
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

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

    @app.before_request
    def before_request():
        """记录请求开始时间"""
        g.request_id = str(uuid.uuid4())[:8]
        g.start_time = time.time()
        app.logger.info(f"[{g.request_id}] {request.method} {request.path} - Started")

    @app.after_request
    def after_request(response):
        """记录请求耗时"""
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            app.logger.info(f"[{g.request_id}] {request.method} {request.path} - Completed in {elapsed:.3f}s")
        return response

    @app.errorhandler(Exception)
    def handle_exception(e):
        # 让 Flask 处理其自身的 HTTP 错误（如 415 UnsupportedMediaType）
        if hasattr(e, 'code') and isinstance(e.code, int) and e.code < 500:
            return e
        app.logger.exception(f"[{g.request_id}] Unhandled exception: {str(e)}")
        return jsonify({"error": "服务器内部错误", "request_id": g.request_id}), 500

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
            app.logger.error(f"[{g.request_id}] Error getting config: {str(e)}")
            return jsonify({"error": "获取配置失败"}), 500

    @app.route('/api/chat/stream', methods=['POST'])
    def chat_stream():
        """SSE 流式代理转发 LLM 请求"""
        request_id = g.request_id

        data = request.get_json()
        if not data:
            app.logger.warning(f"[{request_id}] Empty request body")
            return jsonify({"error": "请求体为空"}), 400

        messages = data.get('messages', [])
        model_override = data.get('model')
        temperature = data.get('temperature', 0.7)

        if not messages:
            app.logger.warning(f"[{request_id}] Empty messages array")
            return jsonify({"error": "messages 不能为空"}), 400

        # 记录请求参数
        app.logger.info(f"[{request_id}] Chat request - model: {model_override or 'default'}, temp: {temperature}, messages: {len(messages)}")

        config = LlmConfig.query.filter_by(
            config_key='default', is_active=True
        ).first()

        if not config:
            app.logger.warning(f"[{request_id}] No LLM config found")
            return jsonify({"error": "系统未配置默认 LLM，请在设置中配置您自己的 API Key"}), 503

        api_key = config.api_key
        base_url = config.base_url
        default_model = config.model

        def generate():
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                model = model_override or default_model

                app.logger.info(f"[{request_id}] Calling OpenAI - model: {model}")

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
                app.logger.info(f"[{request_id}] Stream completed successfully")

            except AuthenticationError as e:
                app.logger.error(f"[{request_id}] OpenAI auth error: {str(e)}")
                yield f"data: {json.dumps({'error': f'API认证失败: {str(e)}'})}\n\n"

            except RateLimitError as e:
                app.logger.error(f"[{request_id}] OpenAI rate limit: {str(e)}")
                yield f"data: {json.dumps({'error': f'API请求频率超限: {str(e)}'})}\n\n"

            except APIError as e:
                app.logger.error(f"[{request_id}] OpenAI API error: {str(e)}")
                yield f"data: {json.dumps({'error': f'LLM服务错误: {str(e)}'})}\n\n"

            except Exception as e:
                app.logger.exception(f"[{request_id}] Unexpected error in stream: {str(e)}")
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
