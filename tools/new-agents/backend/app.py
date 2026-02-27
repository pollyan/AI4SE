import json
from flask import Flask, request, Response, jsonify, current_app
from flask_cors import CORS
from models import init_db, get_session, LlmConfig, get_engine
from config import Config
from openai import OpenAI
import os

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "new-agents-backend"})

@app.route('/api/config', methods=['GET'])
def get_default_config():
    """获取系统默认模型配置（不返回 API Key）"""
    with app.app_context(): # Ensure we do query in context context 
        session = get_session()
        try:
            config = session.query(LlmConfig).filter_by(
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
        finally:
            session.close()

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

    with app.app_context():
        session = get_session()
        try:
            config = session.query(LlmConfig).filter_by(
                config_key='default', is_active=True
            ).first()
            if not config:
                return jsonify({"error": "系统未配置默认 LLM，请在设置中配置您自己的 API Key"}), 503
            api_key = config.api_key
            base_url = config.base_url
            default_model = config.model
        finally:
            session.close()

    # Note: the proxy integration itself might be difficult to test end-to-end via PyTest without mocking 
    # OpenAI. In TDD you test the contract/routing.
    
    # We delay instantiating client and generator in case of validation failures
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

if __name__ == '__main__':
    # Initialize real DB when running normally natively or via Docker
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5002, debug=True)
