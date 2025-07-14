"""
Web GUI测试用例管理系统 - Flask主应用
基于现有的MidSceneJS AI框架构建的Web界面
"""
import os
import sys
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import uuid
import zipfile
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入现有的AI框架
from midscene_python import MidSceneAI

# 导入AI增强解析器
from services.ai_enhanced_parser import parse_natural_language

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_cases.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 启用CORS支持前端调用
CORS(app)

# 初始化数据库
db = SQLAlchemy(app)

# 数据模型定义
class TestCase(db.Model):
    """测试用例模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    natural_language_input = db.Column(db.Text, nullable=False)  # 用户的自然语言输入
    generated_steps = db.Column(db.Text)  # AI生成的测试步骤(JSON格式)
    target_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(50), default='draft')  # draft, ready, running, completed, failed
    
    # 关联测试执行记录
    executions = db.relationship('TestExecution', backref='test_case', lazy=True, cascade='all, delete-orphan')

class TestExecution(db.Model):
    """测试执行记录模型"""
    id = db.Column(db.Integer, primary_key=True)
    test_case_id = db.Column(db.Integer, db.ForeignKey('test_case.id'), nullable=False)
    execution_id = db.Column(db.String(100), unique=True, nullable=False)  # UUID
    status = db.Column(db.String(50), default='pending')  # pending, running, completed, failed
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    result = db.Column(db.Text)  # JSON格式的执行结果
    logs = db.Column(db.Text)  # 执行日志
    screenshots = db.Column(db.Text)  # 截图路径列表(JSON格式)
    error_message = db.Column(db.Text)

# AI服务类
class AITestService:
    """AI测试服务，封装MidSceneAI功能"""
    
    def __init__(self):
        self.ai = None
    
    def get_ai_instance(self):
        """获取AI实例，延迟初始化"""
        if self.ai is None:
            try:
                self.ai = MidSceneAI()
                return self.ai
            except Exception as e:
                print(f"AI初始化失败: {e}")
                return None
        return self.ai
    
    def parse_natural_language_to_steps(self, natural_input, target_url=None):
        """
        将自然语言描述转换为测试步骤
        使用AI增强解析器进行智能解析
        """
        try:
            # 使用AI增强解析器
            steps = parse_natural_language(natural_input, target_url, use_ai=True)
            return steps
        except Exception as e:
            print(f"AI解析失败，使用基础解析: {e}")
            # 回退到基础解析
            return parse_natural_language(natural_input, target_url, use_ai=False)
    
    def execute_test_case(self, test_case, execution_id):
        """执行测试用例"""
        ai = self.get_ai_instance()
        if not ai:
            return {
                "success": False,
                "error": "AI服务初始化失败"
            }
        
        try:
            # 解析测试步骤
            steps = json.loads(test_case.generated_steps) if test_case.generated_steps else []
            
            results = []
            screenshots = []
            
            for i, step in enumerate(steps):
                step_result = {
                    "step": i + 1,
                    "type": step["type"],
                    "description": step["description"],
                    "success": False,
                    "result": None,
                    "error": None
                }
                
                try:
                    # 根据步骤类型执行相应的AI操作
                    if step["type"] == "goto":
                        result = ai.goto(step["params"]["url"])
                        step_result["result"] = result
                        step_result["success"] = True
                        
                    elif step["type"] == "ai_input":
                        result = ai.ai_input(
                            step["params"]["text"],
                            step["params"]["locate_prompt"]
                        )
                        step_result["result"] = result
                        step_result["success"] = True
                        
                    elif step["type"] == "ai_tap":
                        result = ai.ai_tap(step["params"]["prompt"])
                        step_result["result"] = result
                        step_result["success"] = True
                        
                    elif step["type"] == "ai_wait_for":
                        result = ai.ai_wait_for(step["params"]["prompt"])
                        step_result["result"] = result
                        step_result["success"] = True
                        
                    elif step["type"] == "ai_assert":
                        result = ai.ai_assert(step["params"]["prompt"])
                        step_result["result"] = result
                        step_result["success"] = True
                        
                    elif step["type"] == "ai_query":
                        result = ai.ai_query(step["params"]["prompt"])
                        step_result["result"] = result
                        step_result["success"] = True
                        
                    elif step["type"] == "ai_action":
                        result = ai.ai_action(step["params"]["prompt"])
                        step_result["result"] = result
                        step_result["success"] = True
                    
                    # 每个步骤后截图
                    screenshot_path = ai.take_screenshot(f"{execution_id}_step_{i+1}")
                    screenshots.append(screenshot_path)
                    
                except Exception as e:
                    step_result["error"] = str(e)
                    step_result["success"] = False
                
                results.append(step_result)
                
                # 如果步骤失败，可以选择继续或停止
                if not step_result["success"]:
                    print(f"步骤 {i+1} 失败: {step_result['error']}")
            
            return {
                "success": True,
                "results": results,
                "screenshots": screenshots
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # 清理AI资源
            try:
                ai.cleanup()
            except:
                pass

# 全局AI服务实例
ai_service = AITestService()

# API路由定义
@app.route('/')
def index():
    """主页"""
    return render_template('index_enhanced.html')

@app.route('/local-proxy')
def local_proxy():
    """本地代理下载页面"""
    return render_template('local_proxy.html')

@app.route('/download/local-proxy')
def download_local_proxy():
    """下载本地代理包"""
    try:
        # 代理包路径
        proxy_dir = Path(__file__).parent.parent / 'dist' / 'intent-test-proxy'

        if not proxy_dir.exists():
            return jsonify({
                'success': False,
                'error': '代理包不存在，请先构建代理包'
            }), 404

        # 创建临时ZIP文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as tmp_file:
            with zipfile.ZipFile(tmp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in proxy_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(proxy_dir)
                        zipf.write(file_path, arcname)

            return send_from_directory(
                directory=Path(tmp_file.name).parent,
                path=Path(tmp_file.name).name,
                as_attachment=True,
                download_name='intent-test-proxy.zip'
            )

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'下载失败: {str(e)}'
        }), 500

@app.route('/api/test-cases', methods=['GET'])
def get_test_cases():
    """获取所有测试用例"""
    cases = TestCase.query.order_by(TestCase.created_at.desc()).all()
    return jsonify([{
        'id': case.id,
        'name': case.name,
        'description': case.description,
        'natural_language_input': case.natural_language_input,
        'target_url': case.target_url,
        'status': case.status,
        'created_at': case.created_at.isoformat(),
        'updated_at': case.updated_at.isoformat()
    } for case in cases])

@app.route('/api/test-cases', methods=['POST'])
def create_test_case():
    """创建新的测试用例"""
    data = request.get_json()
    
    # 验证必需字段
    if not data.get('name') or not data.get('natural_language_input'):
        return jsonify({'error': '测试用例名称和自然语言描述不能为空'}), 400
    
    # 使用AI解析自然语言生成测试步骤
    steps = ai_service.parse_natural_language_to_steps(
        data['natural_language_input'],
        data.get('target_url')
    )
    
    # 创建测试用例
    test_case = TestCase(
        name=data['name'],
        description=data.get('description', ''),
        natural_language_input=data['natural_language_input'],
        generated_steps=json.dumps(steps, ensure_ascii=False, indent=2),
        target_url=data.get('target_url', ''),
        status='ready'
    )
    
    db.session.add(test_case)
    db.session.commit()
    
    return jsonify({
        'id': test_case.id,
        'message': '测试用例创建成功',
        'generated_steps': steps
    }), 201

@app.route('/api/test-cases/<int:case_id>', methods=['GET'])
def get_test_case(case_id):
    """获取单个测试用例详情"""
    case = TestCase.query.get_or_404(case_id)
    
    # 解析生成的步骤
    steps = json.loads(case.generated_steps) if case.generated_steps else []
    
    return jsonify({
        'id': case.id,
        'name': case.name,
        'description': case.description,
        'natural_language_input': case.natural_language_input,
        'target_url': case.target_url,
        'status': case.status,
        'generated_steps': steps,
        'created_at': case.created_at.isoformat(),
        'updated_at': case.updated_at.isoformat()
    })

@app.route('/api/test-cases/<int:case_id>/execute', methods=['POST'])
def execute_test_case(case_id):
    """执行测试用例"""
    case = TestCase.query.get_or_404(case_id)
    
    # 创建执行记录
    execution_id = str(uuid.uuid4())
    execution = TestExecution(
        test_case_id=case.id,
        execution_id=execution_id,
        status='running'
    )
    
    db.session.add(execution)
    db.session.commit()
    
    try:
        # 更新测试用例状态
        case.status = 'running'
        db.session.commit()
        
        # 执行测试
        result = ai_service.execute_test_case(case, execution_id)
        
        # 更新执行记录
        execution.end_time = datetime.utcnow()
        execution.result = json.dumps(result, ensure_ascii=False)
        execution.screenshots = json.dumps(result.get('screenshots', []))
        
        if result['success']:
            execution.status = 'completed'
            case.status = 'completed'
        else:
            execution.status = 'failed'
            case.status = 'failed'
            execution.error_message = result.get('error', '执行失败')
        
        db.session.commit()
        
        return jsonify({
            'execution_id': execution_id,
            'status': execution.status,
            'result': result
        })
        
    except Exception as e:
        # 更新失败状态
        execution.status = 'failed'
        execution.error_message = str(e)
        execution.end_time = datetime.utcnow()
        case.status = 'failed'
        
        db.session.commit()
        
        return jsonify({
            'execution_id': execution_id,
            'status': 'failed',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # 创建数据库表
    with app.app_context():
        db.create_all()
    
    print("🚀 启动Web GUI测试用例管理系统...")
    print("📱 访问地址: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
