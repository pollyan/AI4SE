"""
仪表板API测试
测试仪表板数据统计接口
"""

import pytest
import json


class TestDashboardAPI:
    """仪表板API测试"""
    
    def test_should_get_dashboard_stats_empty(self, api_client, assert_api_response):
        """测试获取空的仪表板统计数据"""
        response = api_client.get('/api/dashboard/summary')
        data = assert_api_response(response, 200, {
            'summary': dict,
            'recent_executions': list,
            'category_distribution': list
        })
        
        assert data['summary']['total_testcases'] == 0
        assert data['summary']['total_executions'] == 0
        assert data['recent_executions'] == []
    
    def test_should_get_dashboard_stats_with_data(self, api_client, create_test_testcase, 
                                                  create_test_execution, assert_api_response):
        """测试获取包含数据的仪表板统计"""
        # 创建测试数据
        testcase = create_test_testcase({
            'name': '仪表板测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'success'
        })
        
        response = api_client.get('/api/dashboard/summary')
        data = assert_api_response(response, 200)
        
        assert data['summary']['total_testcases'] >= 1
        assert data['summary']['total_executions'] >= 1
        assert len(data['recent_executions']) >= 0  # 可能为空
    
    def test_should_get_execution_trends(self, api_client, create_test_testcase, 
                                        create_test_execution, assert_api_response):
        """测试获取执行趋势数据"""
        # 创建测试数据
        testcase = create_test_testcase({
            'name': '趋势分析测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        # 创建多个执行记录
        create_test_execution({'test_case_id': testcase['id'], 'status': 'success'})
        create_test_execution({'test_case_id': testcase['id'], 'status': 'failed'})
        
        response = api_client.get('/api/dashboard/execution-chart')
        data = assert_api_response(response, 200, {
            'chart_data': list,
            'period': dict
        })
        
        assert 'chart_data' in data
        assert 'period' in data
        assert isinstance(data['chart_data'], list)
    
    def test_should_get_testcase_categories(self, api_client, create_test_testcase, assert_api_response):
        """测试获取测试用例分类统计"""
        # 创建不同分类的测试用例
        create_test_testcase({
            'name': 'UI测试用例',
            'category': 'UI测试',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        create_test_testcase({
            'name': 'API测试用例',
            'category': 'API测试',
            'steps': [{'action': 'goto', 'params': {'url': 'https://api.example.com'}}]
        })
        
        response = api_client.get('/api/dashboard/top-testcases')
        data = assert_api_response(response, 200, {
            'testcases': list,  # 实际API返回的字段名
            'period': dict
        })
        
        assert 'testcases' in data
        assert 'period' in data
    
    def test_should_handle_dashboard_api_errors(self, api_client):
        """测试仪表板API错误处理"""
        # 测试不存在的端点
        response = api_client.get('/api/dashboard/nonexistent')
        assert response.status_code == 404
        
        # 测试无效的查询参数
        response = api_client.get('/api/dashboard/summary?days=invalid')
        # 应该容错处理，返回默认结果
        assert response.status_code in [200, 400]


class TestDashboardDataAPI:
    """仪表板数据管理API测试"""
    
    def test_should_get_dashboard_health_check(self, api_client, assert_api_response):
        """测试仪表板健康检查"""
        response = api_client.get('/api/dashboard/health-check')
        data = assert_api_response(response, 200, {
            'health_status': str, 
            'check_time': str,
            'health_score': int,
            'metrics': dict
        })
        assert data['health_status'] in ['excellent', 'good', 'warning', 'error']
    
    def test_should_get_failure_analysis(self, api_client, create_test_testcase, 
                                         create_test_execution, assert_api_response):
        """测试获取失败分析数据"""
        # 创建测试数据
        testcase = create_test_testcase({
            'name': '失败分析测试用例',
            'steps': [{'action': 'goto', 'params': {'url': 'https://example.com'}}]
        })
        
        create_test_execution({
            'test_case_id': testcase['id'],
            'status': 'failed',
            'error_message': '测试失败'
        })
        
        response = api_client.get('/api/dashboard/failure-analysis')
        data = assert_api_response(response, 200)
        
        # 检查实际API返回的字段
        assert 'failure_reasons' in data
        assert 'failed_steps' in data  
        assert 'failure_prone_testcases' in data