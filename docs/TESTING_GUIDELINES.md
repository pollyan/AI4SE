# 测试规范指南

本文档定义了Intent Test Framework项目的测试标准和最佳实践。所有新功能开发都必须遵循这些规范。

## 测试原则

1. **测试先行**：在实现新功能前，先设计测试用例
2. **全面覆盖**：确保测试覆盖所有关键路径和边界情况
3. **独立性**：每个测试必须独立运行，不依赖其他测试
4. **可重复性**：测试结果必须稳定可重复
5. **清晰命名**：测试名称应该清楚描述测试的目的

## 测试目录结构

```
tests/
├── __init__.py
├── conftest.py          # pytest配置和全局fixtures
├── unit/                # 单元测试
│   ├── __init__.py
│   ├── factories.py     # 测试数据工厂
│   ├── test_*_model.py  # 数据模型测试
│   └── test_*.py        # 其他单元测试
├── integration/         # 集成测试（待实现）
└── e2e/                # 端到端测试（待实现）
```

## 数据模型测试规范

### 1. 测试文件组织

- **按业务对象组织**：每个模型一个测试文件
- **命名规范**：`test_{model_name}_model.py`
- **示例**：`test_testcase_model.py`, `test_execution_history_model.py`

### 2. 必须包含的测试类型

每个数据模型必须包含以下测试：

#### a) 基本CRUD测试
```python
def test_should_create_model_with_valid_data(self, db_session):
    """测试使用有效数据创建模型"""

def test_should_read_model_by_id(self, db_session):
    """测试通过ID读取模型"""

def test_should_update_model_fields(self, db_session):
    """测试更新模型字段"""

def test_should_delete_model(self, db_session):
    """测试删除模型"""
```

#### b) 字段验证测试
```python
def test_should_validate_required_fields(self, db_session):
    """测试必填字段验证"""

def test_should_validate_field_types(self, db_session):
    """测试字段类型验证"""

def test_should_validate_field_lengths(self, db_session):
    """测试字段长度限制"""
```

#### c) 数据库约束测试
```python
def test_should_enforce_not_null_constraints(self, db_session):
    """测试NOT NULL约束"""

def test_should_enforce_unique_constraints(self, db_session):
    """测试UNIQUE约束"""

def test_should_enforce_foreign_key_constraints(self, db_session):
    """测试外键约束"""
```

#### d) 边界值测试
```python
def test_should_handle_minimum_values(self, db_session):
    """测试最小值边界"""

def test_should_handle_maximum_values(self, db_session):
    """测试最大值边界"""

def test_should_handle_empty_values(self, db_session):
    """测试空值处理"""
```

#### e) 关系测试
```python
def test_should_handle_relationships(self, db_session):
    """测试模型关系"""

def test_should_handle_cascade_operations(self, db_session):
    """测试级联操作"""
```

### 3. 测试数据工厂

使用factory-boy创建测试数据：

```python
# factories.py
import factory
from factory.alchemy import SQLAlchemyModelFactory

class TestCaseFactory(SQLAlchemyModelFactory):
    class Meta:
        model = TestCase
        sqlalchemy_session_persistence = 'flush'
    
    name = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('text')
    # ... 其他字段
```

### 4. Fixture使用规范

```python
@pytest.fixture
def db_session():
    """提供测试数据库会话"""
    # 使用SQLite内存数据库
    # 每个测试自动回滚
    # 启用外键约束
```

## API测试规范（待实现）

### 1. 测试覆盖要求

- 所有HTTP方法（GET, POST, PUT, DELETE）
- 成功路径和错误路径
- 权限验证
- 输入验证
- 响应格式验证

### 2. 测试组织

```python
class TestTestCaseAPI:
    def test_get_testcase_list(self, client):
        """测试获取测试用例列表"""
    
    def test_create_testcase(self, client):
        """测试创建测试用例"""
    
    def test_update_testcase(self, client):
        """测试更新测试用例"""
    
    def test_delete_testcase(self, client):
        """测试删除测试用例"""
```

## 测试工具和库

- **pytest**: 测试框架
- **pytest-cov**: 代码覆盖率
- **factory-boy**: 测试数据生成
- **faker**: 假数据生成
- **SQLAlchemy**: ORM测试

## 持续集成配置

### GitHub Actions配置

```yaml
# .github/workflows/python-tests.yml
- 支持Python 3.9, 3.10, 3.11
- 自动安装依赖
- 运行测试并生成报告
- 上传测试结果和覆盖率报告
- 生成测试摘要到Actions页面
```

### 环境变量

```yaml
TESTING: "true"
DATABASE_URL: "sqlite:///:memory:"
PYTHONPATH: ${{ github.workspace }}
```

## 测试运行命令

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/unit/test_testcase_model.py -v

# 运行并生成覆盖率报告
pytest tests/ --cov=web_gui --cov-report=html

# 运行特定测试类
pytest tests/unit/test_testcase_model.py::TestTestCaseModel -v

# 运行特定测试方法
pytest tests/unit/test_testcase_model.py::TestTestCaseModel::test_should_create_testcase_with_valid_data -v
```

## 测试编写最佳实践

1. **使用描述性的测试名称**
   - 好：`test_should_raise_error_when_name_is_empty`
   - 差：`test_name_validation`

2. **遵循AAA模式**
   - Arrange：准备测试数据
   - Act：执行被测试的操作
   - Assert：验证结果

3. **每个测试只验证一个行为**

4. **使用工厂而不是硬编码数据**
   ```python
   # 好
   testcase = TestCaseFactory.create()
   
   # 差
   testcase = TestCase(name="test", description="test desc", ...)
   ```

5. **清理测试数据**
   - 使用pytest的db_session fixture自动回滚
   - 避免测试间的数据污染

6. **测试异常情况**
   ```python
   with pytest.raises(ValueError):
       # 触发异常的代码
   ```

## 测试覆盖率要求

- **单元测试覆盖率**：≥ 80%
- **关键业务逻辑**：100%
- **数据模型**：≥ 90%
- **API端点**：≥ 85%

## 测试检查清单

在提交代码前，确保：

- [ ] 所有新功能都有对应的测试
- [ ] 所有测试都能通过
- [ ] 测试覆盖率符合要求
- [ ] 测试命名清晰描述测试目的
- [ ] 测试数据使用工厂生成
- [ ] 没有硬编码的测试数据
- [ ] 测试之间相互独立
- [ ] 边界值和异常情况都有测试覆盖

## 常见问题解决

### 1. Flask应用初始化问题

确保在测试环境中正确处理Flask应用初始化：

```python
# app_enhanced.py
def setup_routes(app, socketio):
    """将所有路由定义放在函数中，避免导入时执行"""
    @app.route('/')
    def index():
        return render_template('index.html')
```

### 2. SQLite外键约束

SQLite默认不启用外键约束，需要手动启用：

```python
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

### 3. 依赖管理

确保GitHub Actions中安装所有必要的依赖：

```yaml
pip install flask-socketio python-socketio
```

## 未来计划

1. **集成测试**：测试API端点和服务集成
2. **E2E测试**：使用Playwright测试完整用户流程
3. **性能测试**：确保系统性能符合要求
4. **安全测试**：验证安全措施的有效性

---

*本文档应随项目发展持续更新和完善。*