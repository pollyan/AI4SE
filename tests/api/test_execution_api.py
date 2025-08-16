"""
测试执行历史管理API测试
"""

import pytest
import json
from datetime import datetime, timedelta


class TestCreateExecutionAPI:
    """创建执行任务API测试 (POST /api/executions)"""
    
    def test_should_create_execution_with_valid_data(self, api_client, create_test_testcase, sample_execution_data, assert_api_response):
        """测试使用有效数据创建执行任务"""
        testcase = create_test_testcase(name='测试执行创建')
        execution_data = sample_execution_data.copy()
        execution_data['testcase_id'] = testcase.id
        
        response = api_client.post('/api/executions',
                                 json=execution_data,
                                 content_type='application/json')
        
        data = assert_api_response(response, 200)
        
        # 验证返回的执行数据
        created_execution = data['data']
        assert 'execution_id' in created_execution
        assert created_execution['status'] == 'pending'
    
    def test_should_create_execution_with_optional_params(self, api_client, create_test_testcase, assert_api_response):
        """测试使用可选参数创建执行任务"""
        testcase = create_test_testcase(name='测试可选参数执行')
        
        execution_data = {
            'testcase_id': testcase.id,
            'mode': 'browser',
            'browser': 'firefox',
            'executed_by': 'test_user'
        }
        
        response = api_client.post('/api/executions',
                                 json=execution_data,
                                 content_type='application/json')
        
        data = assert_api_response(response, 200)
        
        created_execution = data['data']
        assert 'execution_id' in created_execution
        assert created_execution['status'] == 'pending'
    
    def test_should_validate_required_testcase_id(self, api_client, assert_api_response):
        """测试验证必需的testcase_id字段"""
        execution_data = {
            'mode': 'headless',
            'browser': 'chrome'
        }
        
        response = api_client.post('/api/executions',
                                 json=execution_data,
                                 content_type='application/json')
        
        assert_api_response(response, 400)
    
    def test_should_validate_testcase_exists(self, api_client, assert_api_response):
        """测试验证测试用例存在"""
        execution_data = {
            'testcase_id': 99999  # 不存在的测试用例ID
        }
        
        response = api_client.post('/api/executions',
                                 json=execution_data,
                                 content_type='application/json')
        
        assert_api_response(response, 404)
    
    def test_should_reject_inactive_testcase(self, api_client, create_test_testcase, assert_api_response):
        """测试拒绝已删除的测试用例"""
        testcase = create_test_testcase(name='已删除测试用例', is_active=False)
        
        execution_data = {
            'testcase_id': testcase.id
        }
        
        response = api_client.post('/api/executions',
                                 json=execution_data,
                                 content_type='application/json')
        
        assert_api_response(response, 404)


class TestGetExecutionAPI:
    """获取执行详情API测试 (GET /api/executions/<execution_id>)"""
    
    def test_should_get_execution_by_valid_id(self, api_client, create_execution_history, assert_api_response):
        """测试使用有效ID获取执行详情"""
        execution = create_execution_history(status='success')
        
        response = api_client.get(f'/api/executions/{execution.execution_id}')
        data = assert_api_response(response, 200)
        
        execution_data = data['data']
        assert execution_data['execution_id'] == execution.execution_id
        assert execution_data['status'] == 'success'
        assert execution_data['test_case_id'] == execution.test_case_id
        
        # 验证返回的数据结构
        required_fields = [
            'execution_id', 'test_case_id', 'test_case_name', 'status', 
            'mode', 'browser', 'start_time', 'executed_by', 'created_at'
        ]
        for field in required_fields:
            assert field in execution_data, f"执行数据缺少字段: {field}"
    
    def test_should_get_running_execution(self, api_client, create_execution_history, assert_api_response):
        """测试获取运行中的执行"""
        execution = create_execution_history(status='running', end_time=None, duration=None)
        
        response = api_client.get(f'/api/executions/{execution.execution_id}')
        data = assert_api_response(response, 200)
        
        execution_data = data['data']
        assert execution_data['status'] == 'running'
        assert execution_data['end_time'] is None
        assert execution_data['duration'] is None
    
    def test_should_get_failed_execution_with_error(self, api_client, create_execution_history, assert_api_response):
        """测试获取失败的执行（包含错误信息）"""
        execution = create_execution_history(
            status='failed',
            error_message='测试错误消息',
            error_stack='错误堆栈信息'
        )
        
        response = api_client.get(f'/api/executions/{execution.execution_id}')
        data = assert_api_response(response, 200)
        
        execution_data = data['data']
        assert execution_data['status'] == 'failed'
        assert execution_data['error_message'] == '测试错误消息'
    
    def test_should_return_404_for_nonexistent_execution(self, api_client, assert_api_response):
        """测试不存在的执行ID返回404"""
        response = api_client.get('/api/executions/nonexistent-id')
        assert_api_response(response, 404)


class TestListExecutionsAPI:
    """获取执行列表API测试 (GET /api/executions)"""
    
    def test_should_get_empty_executions_list(self, api_client, assert_api_response):
        """测试获取空的执行列表"""
        response = api_client.get('/api/executions')
        data = assert_api_response(response, 200, {
            'items': list,
            'total': int,
            'page': int,
            'size': int,
            'pages': int
        })
        
        assert data['data']['total'] == 0
        assert data['data']['items'] == []
        assert data['data']['page'] == 1
        assert data['data']['size'] == 20
    
    def test_should_get_executions_list_with_data(self, api_client, create_execution_history, assert_api_response):
        """测试获取包含数据的执行列表"""
        # 创建测试执行记录
        execution1 = create_execution_history(status='success')
        execution2 = create_execution_history(status='failed')
        
        response = api_client.get('/api/executions')
        data = assert_api_response(response, 200)
        
        assert data['data']['total'] == 2
        assert len(data['data']['items']) == 2
        
        # 验证执行数据结构
        execution_data = data['data']['items'][0]
        expected_fields = [
            'execution_id', 'test_case_id', 'test_case_name', 'status',
            'start_time', 'duration', 'executed_by'
        ]
        for field in expected_fields:
            assert field in execution_data, f"执行列表数据缺少字段: {field}"
    
    def test_should_support_pagination(self, api_client, create_execution_history, assert_api_response):
        """测试分页功能"""
        # 创建多个执行记录
        for i in range(5):
            create_execution_history(status='success')
        
        # 测试第一页，每页2条
        response = api_client.get('/api/executions?page=1&size=2')
        data = assert_api_response(response, 200)
        
        assert data['data']['total'] == 5
        assert data['data']['page'] == 1
        assert data['data']['size'] == 2
        assert data['data']['pages'] == 3
        assert len(data['data']['items']) == 2
        
        # 测试第二页
        response = api_client.get('/api/executions?page=2&size=2')
        data = assert_api_response(response, 200)
        
        assert data['data']['page'] == 2
        assert len(data['data']['items']) == 2
        
        # 测试最后一页
        response = api_client.get('/api/executions?page=3&size=2')
        data = assert_api_response(response, 200)
        
        assert data['data']['page'] == 3
        assert len(data['data']['items']) == 1
    
    def test_should_support_testcase_filter(self, api_client, create_test_testcase, create_execution_history, assert_api_response):
        """测试按测试用例过滤功能"""
        testcase1 = create_test_testcase(name='测试用例1')
        testcase2 = create_test_testcase(name='测试用例2')
        
        # 为不同测试用例创建执行记录
        create_execution_history(test_case_id=testcase1.id, status='success')
        create_execution_history(test_case_id=testcase1.id, status='failed')
        create_execution_history(test_case_id=testcase2.id, status='success')
        
        # 按testcase1过滤
        response = api_client.get(f'/api/executions?testcase_id={testcase1.id}')
        data = assert_api_response(response, 200)
        
        assert data['data']['total'] == 2
        for item in data['data']['items']:
            assert item['test_case_id'] == testcase1.id
        
        # 按testcase2过滤
        response = api_client.get(f'/api/executions?testcase_id={testcase2.id}')
        data = assert_api_response(response, 200)
        
        assert data['data']['total'] == 1
        assert data['data']['items'][0]['test_case_id'] == testcase2.id
    
    def test_should_order_by_created_at_desc(self, api_client, create_execution_history, assert_api_response):
        """测试按创建时间倒序排列"""
        # 创建执行记录，确保时间不同
        execution1 = create_execution_history(status='success')
        execution2 = create_execution_history(status='failed')
        
        response = api_client.get('/api/executions')
        data = assert_api_response(response, 200)
        
        items = data['data']['items']
        assert len(items) == 2
        
        # 第一个应该是最新创建的
        assert items[0]['execution_id'] == execution2.execution_id
        assert items[1]['execution_id'] == execution1.execution_id


class TestDeleteExecutionAPI:
    """删除执行报告API测试 (DELETE /api/executions/<execution_id>)"""
    
    def test_should_delete_execution(self, api_client, create_execution_history, db_session, assert_api_response):
        """测试删除执行记录"""
        execution = create_execution_history(status='success')
        execution_id = execution.execution_id
        
        response = api_client.delete(f'/api/executions/{execution_id}')
        assert_api_response(response, 200)
        
        # 验证记录已被删除
        from web_gui.models import ExecutionHistory
        deleted_execution = ExecutionHistory.query.filter_by(execution_id=execution_id).first()
        assert deleted_execution is None
    
    def test_should_delete_execution_with_step_executions(self, api_client, create_execution_history, create_step_execution, db_session, assert_api_response):
        """测试删除包含步骤执行的执行记录"""
        execution = create_execution_history(status='success')
        step_execution = create_step_execution(execution_id=execution.execution_id)
        
        response = api_client.delete(f'/api/executions/{execution.execution_id}')
        assert_api_response(response, 200)
        
        # 验证执行记录和步骤执行都被删除
        from web_gui.models import ExecutionHistory, StepExecution
        
        deleted_execution = ExecutionHistory.query.filter_by(execution_id=execution.execution_id).first()
        assert deleted_execution is None
        
        deleted_step = StepExecution.query.filter_by(execution_id=execution.execution_id).first()
        assert deleted_step is None
    
    def test_should_return_404_for_nonexistent_execution(self, api_client, assert_api_response):
        """测试删除不存在的执行记录返回404"""
        response = api_client.delete('/api/executions/nonexistent-id')
        assert_api_response(response, 404)


class TestExportExecutionAPI:
    """导出执行报告API测试"""
    
    def test_should_export_single_execution_report(self, api_client, create_execution_history):
        """测试导出单个执行报告"""
        execution = create_execution_history(
            status='success',
            result_summary='{"total_steps": 3, "passed": 2, "failed": 1}'
        )
        
        response = api_client.get(f'/api/executions/{execution.execution_id}/export')
        assert response.status_code == 200
        
        # 验证导出数据包含执行信息（API直接返回报告数据）
        export_data = response.get_json()
        assert export_data['execution_id'] == execution.execution_id
        assert export_data['status'] == 'success'
        assert 'exported_at' in export_data
    
    def test_should_export_execution_with_step_details(self, api_client, create_execution_history, create_step_execution):
        """测试导出包含步骤详情的执行报告"""
        execution = create_execution_history(status='success')
        step_execution = create_step_execution(
            execution_id=execution.execution_id,
            step_description='测试步骤',
            status='success'
        )
        
        response = api_client.get(f'/api/executions/{execution.execution_id}/export')
        assert response.status_code == 200
        
        export_data = response.get_json()
        assert 'step_executions' in export_data
        assert len(export_data['step_executions']) == 1
        assert export_data['step_executions'][0]['step_description'] == '测试步骤'
    
    def test_should_return_404_for_nonexistent_execution_export(self, api_client, assert_api_response):
        """测试导出不存在的执行报告返回404"""
        response = api_client.get('/api/executions/nonexistent-id/export')
        assert_api_response(response, 404)
    
    def test_should_export_all_executions(self, api_client, create_execution_history):
        """测试导出所有执行报告"""
        # 创建多个执行记录
        execution1 = create_execution_history(status='success')
        execution2 = create_execution_history(status='failed')
        
        response = api_client.get('/api/executions/export-all')
        assert response.status_code == 200
        
        # 验证导出数据包含所有执行
        export_data = response.get_json()
        assert 'reports' in export_data
        assert len(export_data['reports']) == 2
        assert 'exported_at' in export_data
        
        execution_ids = [exec['execution_id'] for exec in export_data['reports']]
        assert execution1.execution_id in execution_ids
        assert execution2.execution_id in execution_ids
    
    def test_should_support_pagination_in_export_all(self, api_client, create_execution_history):
        """测试导出所有报告的分页功能"""
        # 创建多个执行记录
        for i in range(5):
            create_execution_history(status='success')
        
        # 测试分页导出
        response = api_client.get('/api/executions/export-all?page=1&size=2')
        assert response.status_code == 200
        
        export_data = response.get_json()
        assert len(export_data['reports']) == 2
        assert export_data['total_reports'] == 2  # 当前页的报告数量
        assert export_data['page'] == 1
        assert export_data['size'] == 2


class TestMidSceneIntegrationAPI:
    """MidScene集成API测试"""
    
    def test_should_receive_execution_start_notification(self, api_client, create_test_testcase, assert_api_response):
        """测试接收执行开始通知"""
        # 先创建一个测试用例
        testcase = create_test_testcase(name='MidScene执行测试用例')
        
        start_data = {
            'execution_id': 'test-exec-start-001',
            'testcase_id': testcase.id,
            'mode': 'headless',
            'browser': 'chrome',
            'executed_by': 'midscene_user'
        }
        
        response = api_client.post('/api/midscene/execution-start',
                                 json=start_data,
                                 content_type='application/json')
        
        data = assert_api_response(response, 200)
        
        # 验证创建了执行记录
        from web_gui.models import ExecutionHistory
        execution = ExecutionHistory.query.filter_by(
            execution_id=start_data['execution_id']
        ).first()
        
        assert execution is not None
        assert execution.status == 'running'
        assert execution.test_case_id == testcase.id
    
    def test_should_validate_execution_start_data(self, api_client, assert_api_response):
        """测试验证执行开始数据"""
        # 缺少必需字段
        invalid_data = {
            'execution_id': 'test-exec-001'
            # 缺少testcase_id
        }
        
        response = api_client.post('/api/midscene/execution-start',
                                 json=invalid_data,
                                 content_type='application/json')
        
        assert_api_response(response, 400)
    
    def test_should_receive_execution_result(self, api_client, create_execution_history, assert_api_response):
        """测试接收执行结果"""
        # 先创建一个运行中的执行记录
        execution = create_execution_history(
            execution_id='test-exec-result-001',
            status='running'
        )
        
        from datetime import datetime
        result_data = {
            'execution_id': 'test-exec-result-001',
            'testcase_id': execution.test_case_id,
            'status': 'success',
            'mode': 'headless',
            'start_time': execution.start_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'duration': 1500,
            'steps_total': 3,
            'steps_passed': 3,
            'steps_failed': 0
        }
        
        response = api_client.post('/api/midscene/execution-result',
                                 json=result_data,
                                 content_type='application/json')
        
        data = assert_api_response(response, 200)
        
        # 验证执行记录已更新
        from web_gui.models import ExecutionHistory
        updated_execution = ExecutionHistory.query.filter_by(
            execution_id='test-exec-result-001'
        ).first()
        
        assert updated_execution is not None
        assert updated_execution.status == 'success'
        assert updated_execution.end_time is not None
    
    def test_should_create_step_executions_from_result(self, api_client, sample_execution_result_with_steps, create_execution_history, assert_api_response):
        """测试从执行结果创建步骤执行记录"""
        execution = create_execution_history(
            execution_id=sample_execution_result_with_steps['execution_id'],
            status='running'
        )
        
        # 添加API要求的必需字段
        result_data = sample_execution_result_with_steps.copy()
        result_data['testcase_id'] = execution.test_case_id
        result_data['mode'] = 'headless'
        
        response = api_client.post('/api/midscene/execution-result',
                                 json=result_data,
                                 content_type='application/json')
        
        assert_api_response(response, 200)
        
        # 验证创建了步骤执行记录
        from web_gui.models import StepExecution
        step_executions = StepExecution.query.filter_by(
            execution_id=result_data['execution_id']
        ).all()
        
        expected_steps = len(result_data['steps'])
        assert len(step_executions) == expected_steps
        
        # 验证步骤执行数据
        first_step = step_executions[0]
        first_step_data = result_data['steps'][0]
        assert first_step.step_index == first_step_data['index']
        assert first_step.status == first_step_data['status']
    
    def test_should_return_404_for_nonexistent_execution_result(self, api_client, assert_api_response):
        """测试接收不存在执行的结果返回404"""
        result_data = {
            'execution_id': 'nonexistent-execution',
            'testcase_id': 99999,  # 不存在的测试用例ID
            'status': 'success',
            'mode': 'headless',
            'end_time': datetime.utcnow().isoformat(),
            'duration': 1000
        }
        
        response = api_client.post('/api/midscene/execution-result',
                                 json=result_data,
                                 content_type='application/json')
        
        assert_api_response(response, 404)
    
    def test_should_validate_execution_result_data(self, api_client, create_execution_history, assert_api_response):
        """测试验证执行结果数据"""
        execution = create_execution_history(status='running')
        
        # 缺少必需字段
        invalid_data = {
            'execution_id': execution.execution_id
            # 缺少status等字段
        }
        
        response = api_client.post('/api/midscene/execution-result',
                                 json=invalid_data,
                                 content_type='application/json')
        
        assert_api_response(response, 400)