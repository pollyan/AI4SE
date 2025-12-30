"""
API测试数据管理器
提供统一的测试数据创建、管理和清理功能
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .models import db, TestCase, ExecutionHistory, StepExecution


class TestCaseProxy:
    """测试用例代理对象，提供字典和对象两种访问方式"""

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        for key, value in data.items():
            setattr(self, key, value)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        setattr(self, key, value)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def to_dict(self):
        return self._data.copy()

    def __repr__(self):
        return f"TestCaseProxy({self._data})"


class ExecutionProxy:
    """执行记录代理对象"""

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        for key, value in data.items():
            setattr(self, key, value)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        setattr(self, key, value)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def to_dict(self):
        return self._data.copy()

    def __repr__(self):
        return f"ExecutionProxy({self._data})"


class APITestDataManager:
    """API测试数据管理器"""

    def __init__(self, db_session):
        self.db_session = db_session
        self.created_items = {
            "testcases": [],
            "executions": [],
            "step_executions": [],
            "templates": [],
        }

    def create_testcase(self, data: Optional[Dict[str, Any]] = None) -> "TestCaseProxy":
        """创建测试用例"""
        default_data = {
            "name": f"测试用例_{uuid.uuid4().hex[:8]}",
            "description": "自动创建的测试用例",
            "steps": [
                {
                    "action": "goto",
                    "params": {"url": "https://example.com"},
                    "description": "导航到示例网站",
                }
            ],
            "category": "API测试",
            "priority": 3,
            "tags": ["api", "auto-test"],
            "created_by": "test-system",
        }

        if data:
            default_data.update(data)

        # 确保steps是JSON字符串
        if isinstance(default_data["steps"], list):
            default_data["steps"] = json.dumps(default_data["steps"])

        # 确保tags是逗号分隔的字符串
        if isinstance(default_data.get("tags"), list):
            default_data["tags"] = ",".join(default_data["tags"])

        testcase = TestCase(
            name=default_data["name"],
            description=default_data["description"],
            steps=default_data["steps"],
            category=default_data.get("category"),
            priority=default_data.get("priority", 3),
            tags=default_data.get("tags", ""),
            created_by=default_data.get("created_by", "test-system"),
            is_active=default_data.get("is_active", True),  # 支持设置is_active
        )

        self.db_session.add(testcase)
        self.db_session.commit()

        # 转换为字典格式
        testcase_dict = testcase.to_dict(include_stats=False)
        self.created_items["testcases"].append(testcase_dict)

        return TestCaseProxy(testcase_dict)

    def create_execution(
        self, data: Optional[Dict[str, Any]] = None
    ) -> "ExecutionProxy":
        """创建执行记录"""
        if not data or "test_case_id" not in data:
            # 如果没有指定测试用例，创建一个
            testcase = self.create_testcase()
            test_case_id = testcase.id
        else:
            test_case_id = data["test_case_id"]

        default_data = {
            "execution_id": f"exec_{uuid.uuid4().hex[:12]}",
            "test_case_id": test_case_id,
            "status": "pending",
            "mode": "headless",
            "browser": "chrome",
            "start_time": datetime.utcnow(),
            "executed_by": "test-system",
        }

        if data:
            default_data.update(data)

        execution = ExecutionHistory(
            execution_id=default_data["execution_id"],
            test_case_id=default_data["test_case_id"],
            status=default_data["status"],
            mode=default_data["mode"],
            browser=default_data["browser"],
            start_time=default_data["start_time"],
            end_time=default_data.get("end_time"),
            duration=default_data.get("duration"),
            steps_total=default_data.get("steps_total", 1),
            steps_passed=default_data.get("steps_passed", 0),
            steps_failed=default_data.get("steps_failed", 0),
            result_summary=json.dumps(default_data.get("result_summary", {})),
            screenshots_path=default_data.get("screenshots_path"),
            logs_path=default_data.get("logs_path"),
            error_message=default_data.get("error_message"),
            error_stack=default_data.get("error_stack"),
            executed_by=default_data["executed_by"],
        )

        self.db_session.add(execution)
        self.db_session.commit()

        execution_dict = execution.to_dict()
        self.created_items["executions"].append(execution_dict)

        return ExecutionProxy(execution_dict)

    def create_step_execution(
        self, execution_id: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """创建步骤执行记录"""
        default_data = {
            "step_index": 0,
            "action": "goto",
            "status": "success",
            "start_time": datetime.utcnow(),
            "duration": 1000,
            "result_data": json.dumps({"url": "https://example.com"}),
        }

        if data:
            default_data.update(data)

        # 确保result_data是JSON字符串
        if isinstance(default_data.get("result_data"), dict):
            default_data["result_data"] = json.dumps(default_data["result_data"])

        step_execution = StepExecution(
            execution_id=execution_id,
            step_index=default_data["step_index"],
            action=default_data["action"],
            params=default_data.get("params", "{}"),
            status=default_data["status"],
            start_time=default_data["start_time"],
            end_time=default_data.get(
                "end_time",
                default_data["start_time"]
                + timedelta(milliseconds=default_data["duration"]),
            ),
            duration=default_data["duration"],
            result_data=default_data["result_data"],
            error_message=default_data.get("error_message"),
            screenshot_path=default_data.get("screenshot_path"),
            logs=default_data.get("logs", ""),
        )

        self.db_session.add(step_execution)
        self.db_session.commit()

        step_dict = step_execution.to_dict()
        self.created_items["step_executions"].append(step_dict)

        return step_dict

    def create_bulk_testcases(
        self, count: int, name_prefix: str = "批量测试用例"
    ) -> List[TestCaseProxy]:
        """批量创建测试用例"""
        testcases = []

        for i in range(count):
            testcase_data = {
                "name": f"{name_prefix}_{i+1}",
                "description": f"批量创建的测试用例 #{i+1}",
                "category": "API测试",
                "priority": (i % 3) + 1,  # 轮换优先级1-3
                "steps": [
                    {
                        "action": "goto",
                        "params": {"url": f"https://example{i}.com"},
                        "description": f"访问网站{i}",
                    }
                ],
            }

            testcase = self.create_testcase(testcase_data)
            testcases.append(testcase)

        return testcases

    def create_execution_with_steps(
        self, testcase_id: int, step_count: int = 3
    ) -> Dict[str, Any]:
        """创建包含多个步骤的完整执行记录"""
        # 创建执行记录
        execution = self.create_execution(
            {
                "test_case_id": testcase_id,
                "status": "success",
                "steps_total": step_count,
                "steps_passed": step_count,
                "steps_failed": 0,
                "duration": step_count * 1000,
            }
        )

        # 创建步骤执行记录
        step_executions = []
        for i in range(step_count):
            step_data = {
                "step_index": i,
                "action": ["goto", "ai_input", "ai_tap", "ai_assert"][i % 4],
                "status": "success",
                "duration": 1000,
                "result_data": {"step": f"step_{i}", "success": True},
            }

            step_execution = self.create_step_execution(
                execution["execution_id"], step_data
            )
            step_executions.append(step_execution)

        execution["step_executions"] = step_executions
        return execution

    def create_test_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """创建完整的测试场景（测试用例+执行记录+步骤）"""
        # 创建测试用例
        testcase = self.create_testcase(
            {
                "name": f"{scenario_name}_测试用例",
                "description": f"{scenario_name}的完整测试场景",
                "steps": [
                    {"action": "goto", "params": {"url": "https://example.com"}},
                    {
                        "action": "ai_input",
                        "params": {"text": "test", "locate": "输入框"},
                    },
                    {"action": "ai_tap", "params": {"locate": "提交按钮"}},
                    {
                        "action": "ai_assert",
                        "params": {"condition": "页面显示成功消息"},
                    },
                ],
            }
        )

        # 创建多个执行记录（成功和失败的）
        executions = []

        # 成功执行
        success_execution = self.create_execution_with_steps(testcase["id"], 4)
        executions.append(success_execution)

        # 失败执行
        failed_execution = self.create_execution(
            {
                "test_case_id": testcase["id"],
                "status": "failed",
                "steps_total": 4,
                "steps_passed": 2,
                "steps_failed": 2,
                "error_message": "Element not found: 提交按钮",
                "duration": 3000,
            }
        )
        executions.append(failed_execution)

        return {
            "testcase": testcase,
            "executions": executions,
            "scenario_name": scenario_name,
        }

    def cleanup_all(self):
        """清理所有创建的测试数据"""
        try:
            # 按依赖关系顺序清理
            for step_execution in self.created_items["step_executions"]:
                step = self.db_session.query(StepExecution).get(step_execution["id"])
                if step:
                    self.db_session.delete(step)

            for execution in self.created_items["executions"]:
                exec_record = self.db_session.query(ExecutionHistory).get(
                    execution["id"]
                )
                if exec_record:
                    self.db_session.delete(exec_record)

            for testcase in self.created_items["testcases"]:
                tc = self.db_session.query(TestCase).get(testcase["id"])
                if tc:
                    self.db_session.delete(tc)

            self.db_session.commit()

            # 清空记录
            for key in self.created_items:
                self.created_items[key].clear()

        except Exception as e:
            self.db_session.rollback()
            print(f"清理测试数据时出错: {e}")

    def get_stats(self) -> Dict[str, int]:
        """获取创建的测试数据统计"""
        return {
            "testcases": len(self.created_items["testcases"]),
            "executions": len(self.created_items["executions"]),
            "step_executions": len(self.created_items["step_executions"]),
            "templates": len(self.created_items["templates"]),
        }
