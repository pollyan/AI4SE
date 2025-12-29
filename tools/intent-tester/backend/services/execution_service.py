"""
Execution Service - 执行服务
从app_enhanced.py中提取的测试执行逻辑
"""

import json
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..core.extensions import db, socketio
from ..models import TestCase, ExecutionHistory, StepExecution
from .ai_service import get_ai_service
from .variable_resolver_service import get_variable_manager

logger = logging.getLogger(__name__)


class ExecutionService:
    """测试执行服务"""

    def __init__(self):
        self.execution_manager = {}

    def execute_testcase_async(self, testcase_id: int, mode: str = "headless") -> str:
        """
        异步执行测试用例

        Args:
            testcase_id: 测试用例ID
            mode: 执行模式（headless/browser）

        Returns:
            执行ID
        """
        # 获取测试用例
        testcase = TestCase.query.get(testcase_id)
        if not testcase:
            raise ValueError("测试用例不存在")

        # 创建执行记录
        execution_id = str(uuid.uuid4())
        execution = ExecutionHistory(
            execution_id=execution_id,
            test_case_id=testcase_id,
            status="running",
            mode=mode,
            start_time=datetime.utcnow(),
            executed_by="web_user",
        )

        db.session.add(execution)
        db.session.commit()

        # 启动异步执行线程
        thread = threading.Thread(
            target=self._execute_testcase_thread, args=(execution_id, testcase, mode)
        )
        thread.daemon = True
        thread.start()

        return execution_id

    def _execute_testcase_thread(
        self, execution_id: str, testcase: TestCase, mode: str
    ):
        """执行测试用例的线程函数"""
        ai = None
        try:
            # 获取AI服务
            ai = get_ai_service()
            ai.set_browser_mode(mode)

            # 发送执行开始事件
            socketio.emit(
                "execution_started",
                {"execution_id": execution_id, "testcase_name": testcase.name},
            )

            # 解析测试步骤
            steps = json.loads(testcase.steps) if testcase.steps else []
            if not steps:
                raise ValueError("测试用例没有定义执行步骤")

            # 更新步骤总数
            execution = ExecutionHistory.query.filter_by(
                execution_id=execution_id
            ).first()
            execution.steps_total = len(steps)
            db.session.commit()

            steps_passed = 0
            steps_failed = 0

            # 执行每个步骤
            for i, step in enumerate(steps):
                try:
                    # 检查步骤是否被跳过
                    if step.get("skip", False):
                        self._handle_skipped_step(execution_id, i, step)
                        continue

                    # 执行步骤
                    result = self._execute_single_step(ai, step, mode, execution_id, i)

                    if result["success"]:
                        steps_passed += 1
                        socketio.emit(
                            "step_completed",
                            {
                                "execution_id": execution_id,
                                "step_index": i,
                                "status": "success",
                                "duration": result.get("duration", 0),
                                "screenshot": result.get("screenshot"),
                                "total_steps": len(steps),
                            },
                        )
                    else:
                        steps_failed += 1
                        socketio.emit(
                            "step_completed",
                            {
                                "execution_id": execution_id,
                                "step_index": i,
                                "status": "failed",
                                "error_message": result.get("error_message"),
                                "duration": result.get("duration", 0),
                                "screenshot": result.get("screenshot"),
                                "total_steps": len(steps),
                            },
                        )

                        if mode == "headless":
                            break

                    time.sleep(1)  # 步骤间延迟

                except Exception as e:
                    steps_failed += 1
                    self._handle_step_error(execution_id, i, step, str(e))
                    if mode == "headless":
                        break

            # 更新执行结果
            execution.end_time = datetime.utcnow()
            execution.duration = int(
                (execution.end_time - execution.start_time).total_seconds()
            )
            execution.steps_passed = steps_passed
            execution.steps_failed = steps_failed
            execution.status = "success" if steps_failed == 0 else "failed"

            db.session.commit()

            # 发送执行完成事件
            socketio.emit(
                "execution_completed",
                {
                    "execution_id": execution_id,
                    "status": execution.status,
                    "duration": execution.duration,
                    "steps_passed": steps_passed,
                    "steps_failed": steps_failed,
                    "total_steps": len(steps),
                },
            )

        except Exception as e:
            self._handle_execution_error(execution_id, str(e))
        finally:
            if ai:
                ai.cleanup()

    def _execute_single_step(
        self, ai, step: Dict, mode: str, execution_id: str, step_index: int
    ) -> Dict:
        """执行单个测试步骤"""
        try:
            action = step.get("action")
            params = step.get("params", {})
            description = step.get("description", action)
            output_variable = step.get("output_variable")

            result = {
                "success": False,
                "step_index": step_index,
                "step_name": description,
                "output_data": None,
            }

            # 变量解析
            try:
                variable_manager = get_variable_manager(execution_id)
                resolved_params = self._resolve_variables(params, variable_manager)
            except Exception as e:
                logger.warning(f"变量解析失败，使用原始参数: {e}")
                resolved_params = params

            # 根据操作类型执行相应的AI操作
            if action == "goto" or action == "navigate":
                url = resolved_params.get("url")
                if not url:
                    raise ValueError("goto操作缺少url参数")
                ai.goto(url)
                result["success"] = True

            elif action == "ai_input" or action == "aiInput":
                text = resolved_params.get("text")
                locate = resolved_params.get("locate")
                if not text or not locate:
                    raise ValueError("ai_input操作缺少text或locate参数")
                ai.ai_input(text, locate)
                result["success"] = True

            elif action == "ai_tap" or action == "aiTap":
                prompt = resolved_params.get("prompt") or resolved_params.get("locate")
                if not prompt:
                    raise ValueError("ai_tap操作缺少prompt或locate参数")
                ai.ai_tap(prompt)
                result["success"] = True

            elif action == "ai_assert" or action == "aiAssert":
                prompt = resolved_params.get("prompt") or resolved_params.get(
                    "condition"
                )
                if not prompt:
                    raise ValueError("ai_assert操作缺少prompt或condition参数")
                ai.ai_assert(prompt)
                result["success"] = True

            elif action == "ai_wait_for" or action == "aiWaitFor":
                prompt = resolved_params.get("prompt")
                timeout = resolved_params.get("timeout", 10000)
                if not prompt:
                    raise ValueError("ai_wait_for操作缺少prompt参数")
                ai.ai_wait_for(prompt, timeout)
                result["success"] = True

            elif action == "ai_scroll":
                direction = resolved_params.get("direction", "down")
                scroll_type = resolved_params.get("scroll_type", "once")
                locate_prompt = resolved_params.get("locate_prompt")
                ai.ai_scroll(direction, scroll_type, locate_prompt)
                result["success"] = True

            else:
                raise ValueError(f"不支持的操作类型: {action}")

            # 截图
            timestamp = int(time.time())
            screenshot_filename = f"exec_{execution_id}_step_{step_index}_{timestamp}"

            try:
                screenshot_path = ai.take_screenshot(screenshot_filename)
                result["screenshot"] = {
                    "path": f"/static/screenshots/{screenshot_filename}.png",
                    "filename": f"{screenshot_filename}.png",
                    "timestamp": timestamp,
                    "step_index": step_index,
                    "step_name": description,
                }
            except Exception as e:
                logger.warning(f"截图失败: {e}")
                result["screenshot"] = None

            # 记录步骤执行
            step_execution = StepExecution(
                execution_id=execution_id,
                step_index=step_index,
                step_description=description,
                status="success" if result["success"] else "failed",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration=1,  # 简化，实际应该计算真实时间
                screenshot_path=result.get("screenshot", {}).get("path"),
                ai_confidence=0.8,  # 模拟置信度
                ai_decision=json.dumps({"action": action, "params": resolved_params}),
            )

            db.session.add(step_execution)
            db.session.commit()

            return result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"步骤执行失败: {error_msg}")
            return {
                "success": False,
                "error_message": error_msg,
                "step_index": step_index,
                "step_name": description,
            }

    def _resolve_variables(self, params: Dict, variable_manager) -> Dict:
        """基础变量解析"""
        import re

        def resolve_value(value):
            if isinstance(value, str):
                pattern = r"\$\{([^}]+)\}"
                matches = re.findall(pattern, value)

                resolved_value = value
                for match in matches:
                    try:
                        var_value = variable_manager.get_variable(match)
                        if var_value is not None:
                            resolved_value = resolved_value.replace(
                                f"${{{match}}}", str(var_value)
                            )
                    except:
                        pass

                return resolved_value
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            else:
                return value

        return resolve_value(params)

    def _handle_skipped_step(self, execution_id: str, step_index: int, step: Dict):
        """处理跳过的步骤"""
        socketio.emit(
            "step_skipped",
            {
                "execution_id": execution_id,
                "step_index": step_index,
                "step_description": step.get(
                    "description", step.get("action", f"步骤 {step_index + 1}")
                ),
                "message": "此步骤已被标记为跳过",
            },
        )

        # 记录跳过的步骤
        step_execution = StepExecution(
            execution_id=execution_id,
            step_index=step_index,
            step_description=step.get(
                "description", step.get("action", f"步骤 {step_index + 1}")
            ),
            status="skipped",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            duration=0,
            error_message="步骤被跳过",
        )
        db.session.add(step_execution)
        db.session.commit()

    def _handle_step_error(
        self, execution_id: str, step_index: int, step: Dict, error_message: str
    ):
        """处理步骤错误"""
        step_execution = StepExecution(
            execution_id=execution_id,
            step_index=step_index,
            step_description=step.get(
                "description", step.get("action", f"步骤 {step_index + 1}")
            ),
            status="failed",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            error_message=error_message,
        )
        db.session.add(step_execution)
        db.session.commit()

        socketio.emit(
            "step_completed",
            {
                "execution_id": execution_id,
                "step_index": step_index,
                "status": "failed",
                "error_message": error_message,
                "screenshot": None,
                "screenshot_path": None,
            },
        )

    def _handle_execution_error(self, execution_id: str, error_message: str):
        """处理执行错误"""
        execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        if execution:
            execution.status = "failed"
            execution.end_time = datetime.utcnow()
            execution.error_message = error_message
            db.session.commit()

        socketio.emit(
            "execution_error",
            {
                "execution_id": execution_id,
                "message": f"执行过程中发生错误: {error_message}",
            },
        )


# 全局执行服务实例
_execution_service = None


def get_execution_service() -> ExecutionService:
    """获取执行服务实例（单例模式）"""
    global _execution_service
    if _execution_service is None:
        _execution_service = ExecutionService()
    return _execution_service
