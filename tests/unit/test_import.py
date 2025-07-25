"""
测试模块导入
"""

def test_can_import_models():
    """测试是否可以导入models模块"""
    from web_gui.models import db, TestCase, ExecutionHistory, StepExecution, Template
    assert db is not None
    assert TestCase is not None
    assert ExecutionHistory is not None
    assert StepExecution is not None
    assert Template is not None

def test_can_import_app_enhanced():
    """测试是否可以导入app_enhanced模块"""
    from web_gui.app_enhanced import create_app, init_app
    assert create_app is not None
    assert init_app is not None

def test_can_create_test_app():
    """测试是否可以创建测试应用"""
    from web_gui.app_enhanced import create_app
    
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    }
    
    app = create_app(test_config=test_config)
    assert app is not None
    assert app.config['TESTING'] == True
    assert 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']