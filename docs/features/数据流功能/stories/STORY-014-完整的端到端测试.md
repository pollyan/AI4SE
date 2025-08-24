# STORY-014: 完整的端到端测试

**Story ID**: STORY-014  
**Epic**: EPIC-001 数据流核心功能  
**Sprint**: Sprint 3  
**优先级**: High  
**估算**: 8 Story Points  
**分配给**: QA Engineer + Backend Developer + Frontend Developer  
**创建日期**: 2025-01-30  
**产品经理**: John  

---

## 📖 故事描述

**作为** QA工程师  
**我希望** 创建完整的端到端测试套件来验证数据流功能  
**以便** 确保所有组件协同工作正常，用户能够获得预期的完整体验  
**这样** 我们就能有信心将功能发布到生产环境，并保证功能的质量和稳定性  

---

## 🎯 验收标准

### AC-1: 核心数据流场景测试
**给定** 用户需要创建数据驱动的测试用例  
**当** 执行完整的数据流操作时  
**那么** 所有步骤应该正确执行并传递数据  

**核心测试场景**:
```json
{
  "name": "电商购物流程数据流测试",
  "description": "测试从商品浏览到购买完成的完整数据流",
  "steps": [
    {
      "action": "navigate",
      "params": {"url": "https://demo-shop.com/products"},
      "description": "访问商品列表页面"
    },
    {
      "action": "aiQuery",
      "params": {
        "query": "获取第一个商品的信息",
        "dataDemand": "{name: string, price: number, id: string}"
      },
      "output_variable": "first_product",
      "description": "提取第一个商品信息"
    },
    {
      "action": "ai_tap",
      "params": {"locate": "${first_product.name}商品链接"},
      "description": "点击进入商品详情"
    },
    {
      "action": "aiString",
      "params": {"query": "获取商品详情页的价格"},
      "output_variable": "detail_price",
      "description": "获取详情页价格"
    },
    {
      "action": "ai_assert",
      "params": {
        "condition": "详情页价格${detail_price}与列表页价格${first_product.price}一致"
      },
      "description": "验证价格一致性"
    },
    {
      "action": "evaluateJavaScript",
      "params": {
        "script": "return {url: window.location.href, title: document.title, price: '${detail_price}'}"
      },
      "output_variable": "page_info",
      "description": "获取页面综合信息"
    },
    {
      "action": "aiAsk",
      "params": {"query": "这个商品适合什么用户群体？"},
      "output_variable": "target_audience",
      "description": "AI分析目标用户群体"
    }
  ]
}
```

### AC-2: 智能提示功能端到端测试
**给定** 用户在编辑器中配置测试步骤  
**当** 使用智能变量提示功能时  
**那么** 应该提供准确的变量建议和实时验证  

**测试步骤**:
1. 打开测试用例编辑器
2. 添加aiQuery步骤并配置output_variable
3. 在后续步骤的参数中输入`${`触发智能提示
4. 验证提示菜单显示正确的变量列表
5. 选择变量并验证自动补全功能
6. 验证嵌套属性访问的智能提示
7. 验证实时参数预览功能

### AC-3: 错误处理和恢复测试
**给定** 系统在异常情况下运行  
**当** 发生各种错误时  
**那么** 应该提供友好的错误信息和恢复建议  

**错误场景测试**:
- 变量引用不存在的变量
- 访问对象不存在的属性
- 数组索引越界
- AI API调用失败
- 网络连接中断
- 数据库连接失败
- 无效的变量引用语法

### AC-4: 性能和并发测试
**给定** 系统需要处理高负载情况  
**当** 多个用户同时使用数据流功能时  
**那么** 系统应该保持稳定的性能表现  

**性能测试要求**:
- 10个并发用户同时创建和执行测试用例
- 每个测试用例包含20+个变量操作
- 智能提示API响应时间 < 200ms
- 变量存储和检索操作 < 100ms
- 系统内存使用稳定，无内存泄漏

### AC-5: 浏览器兼容性测试
**给定** 用户使用不同的浏览器访问系统  
**当** 使用数据流功能时  
**那么** 在所有主流浏览器中都应该正常工作  

**浏览器覆盖**:
- Chrome (最新版本)
- Firefox (最新版本)
- Safari (最新版本)
- Edge (最新版本)

### AC-6: 移动设备响应式测试
**给定** 用户可能在移动设备上使用系统  
**当** 在小屏幕设备上操作时  
**那么** 智能提示和编辑功能应该适配移动端  

**移动端测试**:
- 智能提示菜单的触摸友好性
- 编辑器在小屏幕上的可用性
- 变量预览功能的响应式显示

---

## 🔧 技术实现要求

### E2E测试框架
```python
# tests/e2e/test_data_flow.py

import pytest
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

class TestDataFlowE2E:
    """数据流功能端到端测试"""
    
    @pytest.fixture
    def driver(self):
        """浏览器驱动初始化"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # CI/CD环境使用无头模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    @pytest.fixture
    def test_case_data(self):
        """测试用例数据"""
        return {
            "name": "数据流E2E测试用例",
            "description": "验证完整的数据流功能",
            "steps": [
                {
                    "action": "navigate",
                    "params": {"url": "https://demo-ecommerce.com"},
                    "description": "访问演示网站"
                },
                {
                    "action": "aiQuery",
                    "params": {
                        "query": "获取首页推荐商品信息",
                        "dataDemand": "{name: string, price: number}"
                    },
                    "output_variable": "featured_product",
                    "description": "提取推荐商品"
                },
                {
                    "action": "ai_input",
                    "params": {
                        "text": "搜索${featured_product.name}",
                        "locate": "搜索框"
                    },
                    "description": "搜索商品"
                },
                {
                    "action": "ai_assert",
                    "params": {
                        "condition": "搜索结果包含${featured_product.name}"
                    },
                    "description": "验证搜索结果"
                }
            ]
        }
    
    def test_complete_data_flow(self, driver, test_case_data):
        """完整数据流测试"""
        # 1. 登录系统
        self._login(driver)
        
        # 2. 创建测试用例
        test_case_id = self._create_test_case(driver, test_case_data)
        
        # 3. 执行测试用例
        execution_id = self._execute_test_case(driver, test_case_id)
        
        # 4. 验证执行结果
        self._verify_execution_results(driver, execution_id, test_case_data)
        
        # 5. 验证变量数据
        self._verify_variable_data(driver, execution_id)
    
    def test_smart_variable_input(self, driver):
        """智能变量提示测试"""
        self._login(driver)
        
        # 创建包含变量的测试用例
        driver.get(f"{self.base_url}/testcases/new")
        
        # 添加第一个步骤（生成变量）
        self._add_step(driver, {
            "action": "aiQuery",
            "params": {"query": "获取页面标题", "dataDemand": "{title: string}"},
            "output_variable": "page_title"
        })
        
        # 添加第二个步骤（使用变量）
        step_params_input = driver.find_element(By.CSS_SELECTOR, '[data-field="text"]')
        step_params_input.click()
        
        # 输入变量引用触发器
        step_params_input.send_keys("验证标题：${")
        
        # 等待智能提示出现
        suggestion_dropdown = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "variable-suggestion-dropdown"))
        )
        
        assert suggestion_dropdown.is_displayed()
        
        # 验证建议内容
        suggestions = driver.find_elements(By.CLASS_NAME, "suggestion-item")
        assert len(suggestions) > 0
        
        # 查找page_title变量
        page_title_suggestion = None
        for suggestion in suggestions:
            if "page_title" in suggestion.text:
                page_title_suggestion = suggestion
                break
        
        assert page_title_suggestion is not None
        
        # 点击选择变量
        page_title_suggestion.click()
        
        # 验证自动补全
        input_value = step_params_input.get_attribute("value")
        assert "page_title}" in input_value
        
        # 验证预览功能
        preview_element = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CLASS_NAME, "preview-value"))
        )
        assert preview_element.is_displayed()
    
    def test_error_handling(self, driver):
        """错误处理测试"""
        self._login(driver)
        
        # 测试无效变量引用
        driver.get(f"{self.base_url}/testcases/new")
        
        step_input = driver.find_element(By.CSS_SELECTOR, '[data-field="text"]')
        step_input.send_keys("${invalid_variable}")
        
        # 等待错误提示
        error_message = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "error-message"))
        )
        
        assert "invalid_variable" in error_message.text
        assert "未定义" in error_message.text
    
    def test_performance_under_load(self, driver):
        """负载下的性能测试"""
        import time
        import threading
        
        def simulate_user_session():
            """模拟用户会话"""
            local_driver = webdriver.Chrome(options=webdriver.ChromeOptions())
            try:
                self._login(local_driver)
                
                # 创建和执行测试用例
                start_time = time.time()
                test_case_id = self._create_test_case(local_driver, self.test_case_data)
                execution_id = self._execute_test_case(local_driver, test_case_id)
                
                # 等待执行完成
                self._wait_for_execution_complete(local_driver, execution_id)
                
                duration = time.time() - start_time
                return duration < 30  # 应在30秒内完成
                
            finally:
                local_driver.quit()
        
        # 启动多个并发用户
        threads = []
        results = []
        
        for i in range(5):  # 5个并发用户
            thread = threading.Thread(
                target=lambda: results.append(simulate_user_session())
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 验证所有用户都成功完成
        assert all(results), "部分用户会话失败"
    
    def _login(self, driver):
        """登录系统"""
        driver.get(f"{self.base_url}/login")
        
        username_input = driver.find_element(By.NAME, "username")
        password_input = driver.find_element(By.NAME, "password")
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        username_input.send_keys("test_user")
        password_input.send_keys("test_password")
        login_button.click()
        
        # 等待登录成功
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))
        )
    
    def _create_test_case(self, driver, test_case_data):
        """创建测试用例"""
        driver.get(f"{self.base_url}/testcases/new")
        
        # 填写基本信息
        name_input = driver.find_element(By.NAME, "name")
        name_input.send_keys(test_case_data["name"])
        
        # 添加步骤
        for i, step in enumerate(test_case_data["steps"]):
            self._add_step(driver, step)
        
        # 保存测试用例
        save_button = driver.find_element(By.CSS_SELECTOR, "button.save-test-case")
        save_button.click()
        
        # 获取测试用例ID
        WebDriverWait(driver, 10).until(
            EC.url_contains("/testcases/")
        )
        
        current_url = driver.current_url
        test_case_id = current_url.split("/testcases/")[-1].split("/")[0]
        return int(test_case_id)
    
    def _execute_test_case(self, driver, test_case_id):
        """执行测试用例"""
        driver.get(f"{self.base_url}/testcases/{test_case_id}")
        
        execute_button = driver.find_element(By.CSS_SELECTOR, "button.execute-test-case")
        execute_button.click()
        
        # 等待执行开始
        execution_modal = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "execution-modal"))
        )
        
        # 获取执行ID
        execution_id_element = execution_modal.find_element(By.CSS_SELECTOR, "[data-execution-id]")
        execution_id = execution_id_element.get_attribute("data-execution-id")
        
        return execution_id
    
    def _verify_execution_results(self, driver, execution_id, expected_data):
        """验证执行结果"""
        # 等待执行完成
        self._wait_for_execution_complete(driver, execution_id)
        
        # 验证执行状态
        status_element = driver.find_element(By.CLASS_NAME, "execution-status")
        assert "success" in status_element.get_attribute("class")
        
        # 验证步骤结果
        step_results = driver.find_elements(By.CLASS_NAME, "step-result")
        assert len(step_results) == len(expected_data["steps"])
        
        for i, step_result in enumerate(step_results):
            status = step_result.find_element(By.CLASS_NAME, "step-status")
            assert "success" in status.get_attribute("class")
    
    def _verify_variable_data(self, driver, execution_id):
        """验证变量数据"""
        # 打开变量浏览器
        variables_tab = driver.find_element(By.CSS_SELECTOR, "[data-tab='variables']")
        variables_tab.click()
        
        # 验证变量列表
        variable_items = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "variable-item"))
        )
        
        # 应该至少有一个变量
        assert len(variable_items) > 0
        
        # 验证第一个变量
        first_variable = variable_items[0]
        variable_name = first_variable.find_element(By.CLASS_NAME, "variable-name").text
        variable_value = first_variable.find_element(By.CLASS_NAME, "variable-value").text
        
        assert variable_name  # 变量名非空
        assert variable_value  # 变量值非空
    
    @property
    def base_url(self):
        return "http://localhost:5000"  # 或从配置获取
```

### API测试套件
```python
# tests/e2e/test_api_integration.py

import pytest
import requests
import asyncio
from concurrent.futures import ThreadPoolExecutor

class TestAPIIntegration:
    """API集成测试"""
    
    @pytest.fixture
    def api_client(self):
        """API客户端"""
        return APIClient(base_url="http://localhost:5000/api/v1")
    
    def test_variable_management_api_flow(self, api_client):
        """变量管理API流程测试"""
        # 1. 创建执行
        execution_data = {
            "test_case_id": 1,
            "mode": "headless",
            "browser": "chrome"
        }
        execution = api_client.post("/executions", json=execution_data)
        execution_id = execution["execution_id"]
        
        # 2. 存储变量
        variable_data = {
            "variable_name": "test_product",
            "value": {"name": "iPhone", "price": 999},
            "source_step_index": 1,
            "source_api_method": "aiQuery"
        }
        api_client.post(f"/executions/{execution_id}/variables", json=variable_data)
        
        # 3. 获取变量建议
        suggestions = api_client.get(f"/executions/{execution_id}/variable-suggestions")
        assert len(suggestions["variables"]) > 0
        assert any(v["name"] == "test_product" for v in suggestions["variables"])
        
        # 4. 验证变量引用
        validation_data = {
            "references": ["${test_product.name}", "${test_product.price}"],
            "step_index": 2
        }
        validation_result = api_client.post(
            f"/executions/{execution_id}/variables/validate", 
            json=validation_data
        )
        
        assert all(r["is_valid"] for r in validation_result["validation_results"])
    
    def test_concurrent_api_access(self, api_client):
        """并发API访问测试"""
        execution_id = "test-concurrent-exec"
        
        def store_variable(index):
            """存储变量的并发任务"""
            variable_data = {
                "variable_name": f"var_{index}",
                "value": f"value_{index}",
                "source_step_index": index,
                "source_api_method": "aiString"
            }
            return api_client.post(
                f"/executions/{execution_id}/variables", 
                json=variable_data
            )
        
        # 启动100个并发请求
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(store_variable, i) for i in range(100)]
            results = [future.result() for future in futures]
        
        # 验证所有请求都成功
        assert all(r.get("success", True) for r in results)
        
        # 验证变量都被正确存储
        variables = api_client.get(f"/executions/{execution_id}/variable-suggestions")
        assert len(variables["variables"]) == 100

class APIClient:
    """测试用API客户端"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
    
    def post(self, endpoint, **kwargs):
        response = self.session.post(f"{self.base_url}{endpoint}", **kwargs)
        response.raise_for_status()
        return response.json()
    
    def get(self, endpoint, **kwargs):
        response = self.session.get(f"{self.base_url}{endpoint}", **kwargs)
        response.raise_for_status()
        return response.json()
```

### 测试配置和工具
```yaml
# tests/e2e/pytest.ini
[tool:pytest]
testpaths = tests/e2e
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --html=tests/reports/e2e_report.html
    --self-contained-html
    --cov=web_gui
    --cov-report=html:tests/reports/coverage
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    e2e: marks tests as end-to-end tests
```

---

## 🧪 测试计划

### 测试分类和覆盖
1. **功能测试**
   - 核心数据流场景
   - 智能提示功能
   - 错误处理和恢复
   - 边界条件测试

2. **性能测试**
   - 并发用户测试
   - 大数据量处理
   - 响应时间验证
   - 资源使用监控

3. **兼容性测试**
   - 多浏览器测试
   - 移动设备测试
   - 不同分辨率测试

4. **集成测试**
   - API集成测试
   - 数据库集成测试
   - 外部服务集成测试

### 测试环境
1. **本地开发环境**
   - Docker Compose测试栈
   - 模拟外部依赖
   - 快速反馈循环

2. **CI/CD环境**
   - 自动化测试执行
   - 并行测试运行
   - 测试报告生成

3. **Staging环境**
   - 生产环境模拟
   - 完整功能验证
   - 用户验收测试

---

## 📊 Definition of Done

- [ ] **测试覆盖**: 所有核心数据流场景测试通过
- [ ] **性能验证**: 并发和负载测试达到性能指标
- [ ] **兼容性**: 主流浏览器和移动设备测试通过
- [ ] **错误处理**: 所有异常场景都有适当的处理和测试
- [ ] **自动化**: 测试套件集成到CI/CD流水线
- [ ] **文档**: 测试用例文档和执行指南完整
- [ ] **监控**: 测试执行的监控和报告机制
- [ ] **用户验收**: 关键用户场景的验收测试通过

---

## 🔗 依赖关系

**前置依赖**:
- 所有功能Story开发完成
- STORY-013: 性能优化和错误处理已完成
- 测试环境和工具链准备就绪

**后续依赖**:
- 生产环境部署
- 用户培训和文档
- 持续监控和维护

---

## 💡 实现注意事项

### 测试策略
- 优先测试核心用户路径
- 平衡自动化测试和手工测试
- 确保测试的可重复性和稳定性
- 测试数据的管理和清理

### 性能基准
- 建立性能基线数据
- 持续的性能回归测试
- 关键指标的趋势监控
- 性能瓶颈的识别和优化

### 质量保证
- 测试用例的评审和维护
- 缺陷跟踪和修复验证
- 测试覆盖率的监控
- 质量门禁的设置

---

**状态**: 待开始  
**创建人**: John (Product Manager)  
**最后更新**: 2025-01-30  

*此Story是数据流功能质量保证的最后一环，确保功能满足用户期望和生产环境要求*