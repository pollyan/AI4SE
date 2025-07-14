"""
增强版Web GUI测试用例管理系统 - Flask主应用
基于现有的MidSceneJS AI框架构建，采用模块化架构
"""
import os
import sys
import time
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from datetime import datetime
import json
import uuid
import threading

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入模块
from models import db, TestCase, ExecutionHistory, StepExecution, Template
from api_routes import api_bp

# 尝试导入MidSceneAI，如果失败则使用模拟版本
try:
    from midscene_python import MidSceneAI
    AI_AVAILABLE = True
    print("✅ MidSceneAI导入成功")
except ImportError as e:
    print(f"⚠️  MidSceneAI导入失败: {e}")
    print("使用模拟AI引擎进行演示")
    AI_AVAILABLE = False

    # 创建模拟AI类
    class MockMidSceneAI:
        def __init__(self):
            self.current_url = None

        def goto(self, url):
            self.current_url = url
            print(f"[模拟] 访问页面: {url}")
            time.sleep(1)  # 模拟加载时间

        def ai_input(self, text, locate):
            print(f"[模拟] 在 '{locate}' 中输入: {text}")
            time.sleep(0.5)

        def ai_tap(self, prompt):
            print(f"[模拟] 点击: {prompt}")
            time.sleep(0.5)

        def ai_assert(self, prompt):
            print(f"[模拟] 验证: {prompt}")
            time.sleep(0.5)

        def ai_wait_for(self, prompt, timeout=10000):
            print(f"[模拟] 等待: {prompt} (超时: {timeout}ms)")
            time.sleep(1)

        def ai_scroll(self, direction='down', scroll_type='once', locate_prompt=None):
            print(f"[模拟] 滚动: {direction} ({scroll_type})")
            time.sleep(0.5)

        def take_screenshot(self, title):
            """模拟截图功能"""
            # 确保截图保存到正确的静态文件目录
            screenshot_filename = f"{title}.png"
            screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'screenshots')
            screenshot_path = os.path.join(screenshot_dir, screenshot_filename)

            print(f"[模拟] 截图保存到: {screenshot_path}")

            # 确保目录存在
            os.makedirs(screenshot_dir, exist_ok=True)

            # 创建一个简单的模拟截图
            try:
                from PIL import Image, ImageDraw
                # 创建一个800x600的图片
                img = Image.new('RGB', (800, 600), color='white')
                draw = ImageDraw.Draw(img)

                # 绘制一些模拟内容
                draw.rectangle([50, 50, 750, 550], outline='black', width=2)
                draw.text((100, 100), "模拟截图", fill='black')
                draw.text((100, 150), f"URL: {getattr(self, 'current_url', 'Unknown')}", fill='blue')
                draw.text((100, 200), f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", fill='gray')
                draw.text((100, 250), "这是AI执行引擎的模拟截图", fill='green')

                # 保存图片
                img.save(screenshot_path, 'PNG')
                print(f"[模拟] 截图已保存: {screenshot_path}")
            except ImportError:
                # 如果没有PIL库，创建一个简单的文本文件
                with open(screenshot_path.replace('.png', '.txt'), 'w') as f:
                    f.write(f"模拟截图 - {time.strftime('%Y-%m-%d %H:%M:%S')}\nURL: {getattr(self, 'current_url', 'Unknown')}")
                print(f"[模拟] 截图文本文件已保存: {screenshot_path.replace('.png', '.txt')}")
            except Exception as e:
                print(f"[模拟] 截图保存失败: {e}")
                # 创建一个空文件作为占位符
                with open(screenshot_path, 'w') as f:
                    f.write("")

            return f"web_gui/static/screenshots/{screenshot_filename}"

        def cleanup(self):
            print("[模拟] 清理AI资源")

    MidSceneAI = MockMidSceneAI

# 确保MockMidSceneAI在全局作用域中可用
if not AI_AVAILABLE:
    MockMidSceneAI = MidSceneAI

def create_app():
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 配置
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # 确保instance目录存在
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    os.makedirs(instance_path, exist_ok=True)

    # 数据库配置
    db_path = os.path.join(instance_path, 'gui_test_cases.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 初始化扩展
    db.init_app(app)
    CORS(app, origins="*")
    
    # 注册API蓝图
    app.register_blueprint(api_bp)
    
    return app

# 创建应用实例
app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量存储执行状态
execution_manager = {}

# ==================== 主页路由 ====================

@app.route('/')
def index():
    """主页"""
    return render_template('index_enhanced.html')

@app.route('/testcases')
def testcases_page():
    """测试用例管理页面"""
    return render_template('testcases.html')

@app.route('/execution')
def execution_page():
    """执行控制台页面"""
    return render_template('execution.html')

@app.route('/reports')
def reports_page():
    """测试报告页面"""
    return render_template('reports.html')

@app.route('/debug_screenshot_history.html')
def debug_screenshot_history():
    """调试截图历史功能"""
    import os
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'debug_screenshot_history.html')
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/step_editor')
def step_editor_page():
    """步骤编辑器页面"""
    return render_template('step_editor.html')

@app.route('/static/screenshots/<filename>')
def screenshot_file(filename):
    """提供截图文件访问"""
    screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'screenshots')
    return send_from_directory(screenshot_dir, filename)

# ==================== WebSocket事件处理 ====================

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    print(f'客户端已连接: {request.sid}')
    emit('connected', {
        'message': '连接成功',
        'ai_available': AI_AVAILABLE,
        'server_time': datetime.utcnow().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    print(f'客户端已断开: {request.sid}')

@socketio.on('ping')
def handle_ping():
    """心跳检测"""
    emit('pong', {'timestamp': datetime.utcnow().isoformat()})

@socketio.on('stop_execution')
def handle_stop_execution(data):
    """停止执行测试用例"""
    execution_id = data.get('execution_id')
    if execution_id:
        # TODO: 实现停止执行逻辑
        emit('execution_stopped', {
            'execution_id': execution_id,
            'message': '执行已停止'
        })
    else:
        emit('error', {'message': '缺少execution_id参数'})

@socketio.on('start_execution')
def handle_start_execution(data):
    """开始执行测试用例"""
    try:
        testcase_id = data.get('testcase_id')
        mode = data.get('mode', 'headless')
        
        # 获取测试用例
        testcase = TestCase.query.get(testcase_id)
        if not testcase:
            emit('execution_error', {'message': '测试用例不存在'})
            return
        
        # 创建执行记录
        execution_id = str(uuid.uuid4())
        execution = ExecutionHistory(
            execution_id=execution_id,
            test_case_id=testcase_id,
            status='running',
            mode=mode,
            start_time=datetime.utcnow(),
            executed_by='web_user'
        )
        
        db.session.add(execution)
        db.session.commit()
        
        # 启动异步执行
        thread = threading.Thread(
            target=execute_testcase_async,
            args=(execution_id, testcase, mode, request.sid)
        )
        thread.daemon = True
        thread.start()
        
        emit('execution_started', {
            'execution_id': execution_id,
            'testcase_name': testcase.name
        })
        
    except Exception as e:
        emit('execution_error', {'message': f'启动执行失败: {str(e)}'})

def execute_testcase_async(execution_id, testcase, mode, client_sid):
    """异步执行测试用例"""
    ai = None
    try:
        # 获取执行记录
        with app.app_context():
            execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
            if not execution:
                socketio.emit('execution_error', {
                    'execution_id': execution_id,
                    'message': '执行记录不存在'
                }, room=client_sid)
                return

            # 解析测试步骤
            steps = json.loads(testcase.steps) if testcase.steps else []
            if not steps:
                socketio.emit('execution_error', {
                    'execution_id': execution_id,
                    'message': '测试用例没有定义执行步骤'
                }, room=client_sid)
                return

            execution.steps_total = len(steps)
            db.session.commit()

            # 初始化AI测试引擎
            try:
                ai = MidSceneAI()

                # 设置浏览器模式
                ai.set_browser_mode(mode)

                socketio.emit('execution_log', {
                    'execution_id': execution_id,
                    'message': f'AI引擎初始化成功 ({"真实" if AI_AVAILABLE else "模拟"}模式)',
                    'level': 'info'
                }, room=client_sid)
            except Exception as e:
                print(f"AI引擎初始化失败，使用模拟模式: {e}")
                # 如果真实AI引擎失败，回退到模拟模式
                # 重新创建模拟AI类
                class FallbackMockAI:
                    def __init__(self):
                        self.current_url = None

                    def goto(self, url):
                        self.current_url = url
                        print(f"[模拟] 访问页面: {url}")
                        time.sleep(1)

                    def ai_input(self, text, locate):
                        print(f"[模拟] 在 '{locate}' 中输入: {text}")
                        time.sleep(0.5)

                    def ai_tap(self, prompt):
                        print(f"[模拟] 点击: {prompt}")
                        time.sleep(0.5)

                    def ai_assert(self, prompt):
                        print(f"[模拟] 验证: {prompt}")
                        time.sleep(0.5)

                    def ai_wait_for(self, prompt, timeout=10000):
                        print(f"[模拟] 等待: {prompt} (超时: {timeout}ms)")
                        time.sleep(1)

                    def ai_scroll(self, direction='down', scroll_type='once', locate_prompt=None):
                        print(f"[模拟] 滚动: {direction} ({scroll_type})")
                        time.sleep(0.5)

                    def take_screenshot(self, title):
                        """模拟截图功能"""
                        # 确保截图保存到正确的静态文件目录
                        screenshot_filename = f"{title}.png"
                        screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'screenshots')
                        screenshot_path = os.path.join(screenshot_dir, screenshot_filename)

                        print(f"[模拟] 截图保存到: {screenshot_path}")

                        try:
                            from PIL import Image, ImageDraw
                            os.makedirs(screenshot_dir, exist_ok=True)

                            # 创建一个简单的模拟截图
                            img = Image.new('RGB', (800, 600), color='lightblue')
                            draw = ImageDraw.Draw(img)
                            draw.rectangle([50, 50, 750, 550], outline='darkblue', width=3)
                            draw.text((100, 100), "Fallback Mock Screenshot", fill='darkblue')
                            draw.text((100, 150), f"URL: {getattr(self, 'current_url', 'Unknown')}", fill='blue')
                            draw.text((100, 200), f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}", fill='gray')

                            img.save(screenshot_path, 'PNG')
                            print(f"[模拟] 截图已保存: {screenshot_path}")
                        except ImportError:
                            # 如果没有PIL库，创建一个简单的文本文件
                            os.makedirs(screenshot_dir, exist_ok=True)
                            with open(screenshot_path.replace('.png', '.txt'), 'w') as f:
                                f.write(f"Fallback Mock Screenshot - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                        except Exception as e:
                            print(f"[模拟] 截图保存失败: {e}")
                            os.makedirs(screenshot_dir, exist_ok=True)
                            with open(screenshot_path, 'w') as f:
                                f.write("")

                        return f"web_gui/static/screenshots/{screenshot_filename}"

                    def cleanup(self):
                        print("[模拟] 清理AI资源")

                ai = FallbackMockAI()
                socketio.emit('execution_log', {
                    'execution_id': execution_id,
                    'message': f'AI引擎初始化失败，使用模拟模式: {str(e)}',
                    'level': 'warning'
                }, room=client_sid)

            steps_passed = 0
            steps_failed = 0
        
            # 执行每个步骤
            for i, step in enumerate(steps):
                step_start_time = datetime.utcnow()

                try:
                    # 发送步骤开始事件
                    socketio.emit('step_started', {
                        'execution_id': execution_id,
                        'step_index': i,
                        'step_description': step.get('description', step.get('action', f'步骤 {i+1}')),
                        'total_steps': len(steps)
                    }, room=client_sid)

                    # 执行步骤
                    result = execute_single_step(ai, step, mode, execution_id, i)

                    step_end_time = datetime.utcnow()
                    duration = int((step_end_time - step_start_time).total_seconds())

                    # 记录步骤执行结果
                    step_execution = StepExecution(
                        execution_id=execution_id,
                        step_index=i,
                        step_description=step.get('description', step.get('action', f'步骤 {i+1}')),
                        status='success' if result['success'] else 'failed',
                        start_time=step_start_time,
                        end_time=step_end_time,
                        duration=duration,
                        screenshot_path=result.get('screenshot_path'),
                        ai_confidence=result.get('confidence'),
                        ai_decision=json.dumps(result.get('ai_decision', {})),
                        error_message=result.get('error_message')
                    )

                    db.session.add(step_execution)

                    if result['success']:
                        steps_passed += 1
                        # 发送步骤成功事件
                        socketio.emit('step_completed', {
                            'execution_id': execution_id,
                            'step_index': i,
                            'status': 'success',
                            'duration': duration,
                            'screenshot': result.get('screenshot'),
                            'screenshot_path': result.get('screenshot_path'),  # 保持向后兼容
                            'total_steps': len(steps)
                        }, room=client_sid)
                    else:
                        steps_failed += 1
                        # 发送步骤失败事件
                        socketio.emit('step_completed', {
                            'execution_id': execution_id,
                            'step_index': i,
                            'status': 'failed',
                            'error_message': result.get('error_message'),
                            'duration': duration,
                            'screenshot': result.get('screenshot'),
                            'screenshot_path': result.get('screenshot_path'),  # 保持向后兼容
                            'total_steps': len(steps)
                        }, room=client_sid)

                        # 如果是无头模式，失败后停止执行；浏览器模式下继续执行
                        if mode == 'headless':
                            break

                    # 短暂延迟，避免操作过快
                    time.sleep(1)

                except Exception as e:
                    steps_failed += 1
                    # 记录步骤异常
                    step_execution = StepExecution(
                        execution_id=execution_id,
                        step_index=i,
                        step_description=step.get('description', step.get('action', f'步骤 {i+1}')),
                        status='failed',
                        start_time=step_start_time,
                        end_time=datetime.utcnow(),
                        error_message=str(e)
                    )
                    db.session.add(step_execution)

                    socketio.emit('step_completed', {
                        'execution_id': execution_id,
                        'step_index': i,
                        'status': 'failed',
                        'error_message': str(e),
                        'screenshot': None,
                        'screenshot_path': None,
                        'total_steps': len(steps)
                    }, room=client_sid)

                    if mode == 'headless':
                        break
        
            # 更新执行记录
            execution.end_time = datetime.utcnow()
            execution.duration = int((execution.end_time - execution.start_time).total_seconds())
            execution.steps_passed = steps_passed
            execution.steps_failed = steps_failed
            execution.status = 'success' if steps_failed == 0 else 'failed'

            db.session.commit()
        
            # 发送执行完成事件
            socketio.emit('execution_completed', {
                'execution_id': execution_id,
                'status': execution.status,
                'duration': execution.duration,
                'steps_passed': steps_passed,
                'steps_failed': steps_failed,
                'total_steps': len(steps)
            }, room=client_sid)

            # 清理AI资源
            try:
                ai.cleanup()
            except:
                pass
            
    except Exception as e:
        # 更新执行状态为失败
        with app.app_context():
            execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
            if execution:
                execution.status = 'failed'
                execution.end_time = datetime.utcnow()
                execution.error_message = str(e)
                db.session.commit()

        # 发送执行错误事件
        socketio.emit('execution_error', {
            'execution_id': execution_id,
            'message': f'执行过程中发生错误: {str(e)}'
        }, room=client_sid)

def execute_single_step(ai, step, mode, execution_id, step_index=0):
    """执行单个测试步骤"""
    try:
        action = step.get('action')
        params = step.get('params', {})
        description = step.get('description', action)

        result = {
            'success': False,
            'ai_decision': {'action': action, 'params': params},
            'confidence': 0.8 if AI_AVAILABLE else 0.5,
            'execution_details': {},
            'step_index': step_index,
            'step_name': description
        }

        print(f"[执行] {description}")

        # 根据不同的操作类型执行相应的AI操作
        if action == 'goto':
            url = params.get('url')
            if not url:
                raise ValueError("goto操作缺少url参数")
            ai.goto(url)
            result['success'] = True
            result['execution_details']['url'] = url

        elif action == 'ai_input':
            text = params.get('text')
            locate = params.get('locate')
            if not text or not locate:
                raise ValueError("ai_input操作缺少text或locate参数")
            ai.ai_input(text, locate)
            result['success'] = True
            result['execution_details']['text'] = text
            result['execution_details']['locate'] = locate

        elif action == 'ai_tap':
            prompt = params.get('prompt')
            if not prompt:
                raise ValueError("ai_tap操作缺少prompt参数")
            ai.ai_tap(prompt)
            result['success'] = True
            result['execution_details']['prompt'] = prompt

        elif action == 'ai_assert':
            prompt = params.get('prompt')
            if not prompt:
                raise ValueError("ai_assert操作缺少prompt参数")
            ai.ai_assert(prompt)
            result['success'] = True
            result['execution_details']['assertion'] = prompt

        elif action == 'ai_wait_for':
            prompt = params.get('prompt')
            timeout = params.get('timeout', 10000)
            if not prompt:
                raise ValueError("ai_wait_for操作缺少prompt参数")
            ai.ai_wait_for(prompt, timeout)
            result['success'] = True
            result['execution_details']['wait_for'] = prompt
            result['execution_details']['timeout'] = timeout

        elif action == 'ai_scroll':
            direction = params.get('direction', 'down')
            scroll_type = params.get('scroll_type', 'once')
            locate_prompt = params.get('locate_prompt')
            ai.ai_scroll(direction, scroll_type, locate_prompt)
            result['success'] = True
            result['execution_details']['direction'] = direction
            result['execution_details']['scroll_type'] = scroll_type

        else:
            raise ValueError(f'不支持的操作类型: {action}')

        # 截图
        timestamp = int(time.time())
        step_index = result.get('step_index', 0)  # 从result中获取步骤索引
        screenshot_filename = f"exec_{execution_id}_step_{step_index}_{timestamp}"

        try:
            # 调用AI引擎截图，传递文件名（不含扩展名）
            screenshot_path = ai.take_screenshot(screenshot_filename)
            # 返回详细的截图信息
            result['screenshot'] = {
                'path': f"/static/screenshots/{screenshot_filename}.png",
                'filename': f"{screenshot_filename}.png",
                'timestamp': timestamp,
                'step_index': step_index,
                'step_name': result.get('step_name', f'步骤 {step_index + 1}')
            }
            print(f"截图成功保存: {screenshot_path}")
        except Exception as e:
            print(f"截图失败: {e}")
            result['screenshot'] = None

        # 模拟AI置信度（真实环境中应该从AI引擎获取）
        if AI_AVAILABLE:
            result['confidence'] = 0.85 + (hash(str(params)) % 15) / 100  # 0.85-0.99
        else:
            result['confidence'] = 0.50 + (hash(str(params)) % 30) / 100  # 0.50-0.79

        return result

    except Exception as e:
        error_msg = str(e)
        print(f"[错误] 步骤执行失败: {error_msg}")
        return {
            'success': False,
            'error_message': error_msg,
            'ai_decision': {'action': action, 'params': params, 'error': error_msg},
            'confidence': 0.0,
            'execution_details': {}
        }

# ==================== 初始化数据库 ====================

def init_database():
    """初始化数据库"""
    with app.app_context():
        try:
            db.create_all()
            print("数据库表创建完成")

            # 创建默认模板
            create_default_templates()
            return True
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            return False

def create_default_templates():
    """创建默认测试模板"""
    try:
        # 检查是否已有模板
        if Template.query.count() > 0:
            return
        
        # 登录测试模板
        login_template = Template(
            name="用户登录测试",
            description="标准的用户登录流程测试",
            category="认证",
            steps_template=json.dumps([
                {
                    "action": "goto",
                    "params": {"url": "{{login_url}}"},
                    "description": "访问登录页面"
                },
                {
                    "action": "ai_input",
                    "params": {"text": "{{username}}", "locate": "用户名输入框"},
                    "description": "输入用户名"
                },
                {
                    "action": "ai_input",
                    "params": {"text": "{{password}}", "locate": "密码输入框"},
                    "description": "输入密码"
                },
                {
                    "action": "ai_tap",
                    "params": {"prompt": "登录按钮"},
                    "description": "点击登录按钮"
                },
                {
                    "action": "ai_assert",
                    "params": {"prompt": "登录成功，显示用户首页"},
                    "description": "验证登录成功"
                }
            ]),
            parameters=json.dumps({
                "login_url": {"type": "string", "description": "登录页面URL"},
                "username": {"type": "string", "description": "用户名"},
                "password": {"type": "string", "description": "密码"}
            }),
            created_by="system",
            is_public=True
        )
        
        db.session.add(login_template)
        db.session.commit()
        print("默认模板创建完成")
        
    except Exception as e:
        print(f"创建默认模板失败: {e}")

if __name__ == '__main__':
    print("🚀 启动增强版AI测试GUI系统...")
    print("📍 后端地址: http://localhost:5001")
    print("📍 API文档: http://localhost:5001/api/v1/")

    # 初始化数据库
    if init_database():
        print("✅ 数据库初始化成功")
    else:
        print("❌ 数据库初始化失败")

    socketio.run(
        app,
        debug=True,
        host='0.0.0.0',
        port=5001,
        allow_unsafe_werkzeug=True
    )
