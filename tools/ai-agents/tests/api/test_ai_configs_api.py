"""
AI 配置 API 测试

测试 /api/ai-configs 端点的 CRUD 操作
"""

import pytest
import json


class TestAIConfigsAPI:
    """AI 配置 API 测试套件"""
    
    # ==================== 列表和获取测试 ====================
    
    def test_list_configs_empty(self, client, app):
        """测试获取空的配置列表"""
        with app.app_context():
            response = client.get('/api/ai-configs/')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['code'] == 200
            assert 'data' in data
            assert isinstance(data['data'], list)
    
    def test_list_configs_with_data(self, client, app, create_ai_config):
        """测试获取包含数据的配置列表"""
        with app.app_context():
            # 创建测试配置
            config = create_ai_config(name="测试配置1")
            
            response = client.get('/api/ai-configs/')
            assert response.status_code == 200
            
            data = response.get_json()
            assert len(data['data']) >= 1
            
            # 验证配置数据结构
            config_data = next(
                (c for c in data['data'] if c['name'] == "测试配置1"), 
                None
            )
            assert config_data is not None
            assert 'id' in config_data
            assert 'name' in config_data
            assert 'base_url' in config_data
            assert 'model_name' in config_data
    
    # ==================== 创建测试 ====================
    
    def test_create_config_success(self, client, app, sample_ai_config):
        """测试成功创建配置"""
        with app.app_context():
            response = client.post(
                '/api/ai-configs/',
                data=json.dumps(sample_ai_config),
                content_type='application/json'
            )
            assert response.status_code == 201
            
            data = response.get_json()
            assert data['code'] == 201
            assert 'data' in data
            assert data['data']['name'] == sample_ai_config['name']
            assert data['data']['base_url'] == sample_ai_config['base_url']
            assert data['data']['model_name'] == sample_ai_config['model_name']
            # API key 不应该在响应中返回完整值
    
    def test_create_config_missing_required_fields(self, client, app):
        """测试缺少必填字段时创建配置失败"""
        with app.app_context():
            # 缺少 name
            response = client.post(
                '/api/ai-configs/',
                data=json.dumps({
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "test-key"
                }),
                content_type='application/json'
            )
            assert response.status_code == 400
    
    def test_create_config_duplicate_name(self, client, app, create_ai_config):
        """测试创建重复名称的配置"""
        with app.app_context():
            # 先创建一个配置
            create_ai_config(name="重复名称配置")
            
            # 尝试创建同名配置
            response = client.post(
                '/api/ai-configs/',
                data=json.dumps({
                    "name": "重复名称配置",
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "test-key",
                    "model_name": "gpt-4o"
                }),
                content_type='application/json'
            )
            # 应该失败（400 或 409）
            assert response.status_code in [400, 409]
    
    # ==================== 更新测试 ====================
    
    def test_update_config_success(self, client, app, create_ai_config):
        """测试成功更新配置"""
        with app.app_context():
            config = create_ai_config(name="待更新配置")
            
            response = client.put(
                f'/api/ai-configs/{config.id}',
                data=json.dumps({
                    "name": "已更新配置",
                    "model_name": "gpt-4o"
                }),
                content_type='application/json'
            )
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['data']['name'] == "已更新配置"
            assert data['data']['model_name'] == "gpt-4o"
    
    def test_update_config_not_found(self, client, app):
        """测试更新不存在的配置"""
        with app.app_context():
            response = client.put(
                '/api/ai-configs/99999',
                data=json.dumps({"name": "新名称"}),
                content_type='application/json'
            )
            assert response.status_code == 404
    
    # ==================== 删除测试 ====================
    
    def test_delete_config_success(self, client, app, create_ai_config):
        """测试成功删除配置"""
        with app.app_context():
            config = create_ai_config(name="待删除配置")
            config_id = config.id
            
            response = client.delete(f'/api/ai-configs/{config_id}')
            assert response.status_code == 200
            
            # 验证已删除
            response = client.get('/api/ai-configs/')
            data = response.get_json()
            assert not any(c['id'] == config_id for c in data['data'])
    
    def test_delete_config_not_found(self, client, app):
        """测试删除不存在的配置"""
        with app.app_context():
            response = client.delete('/api/ai-configs/99999')
            assert response.status_code == 404
    
    # ==================== 默认配置测试 ====================
    
    def test_set_default_config(self, client, app, create_ai_config):
        """测试设置默认配置"""
        with app.app_context():
            config = create_ai_config(name="待设为默认")
            
            response = client.post(f'/api/ai-configs/{config.id}/set-default')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['data']['is_default'] == True
    
    def test_get_default_config(self, client, app, create_ai_config):
        """测试获取默认配置"""
        with app.app_context():
            # 创建并设置默认配置
            config = create_ai_config(name="默认配置", is_default=True)
            
            response = client.get('/api/ai-configs/default')
            assert response.status_code == 200
            
            data = response.get_json()
            assert data['data']['name'] == "默认配置"
    
    def test_get_default_config_none(self, client, app):
        """测试没有默认配置时的响应"""
        with app.app_context():
            response = client.get('/api/ai-configs/default')
            # 应该返回 404 或者空数据
            assert response.status_code in [200, 404]
    
    # ==================== 获取示例配置测试 ====================
    
    def test_get_config_examples(self, client, app):
        """测试获取配置示例"""
        with app.app_context():
            response = client.get('/api/ai-configs/examples')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'data' in data
            # 应该有预定义的示例
            assert len(data['data']) > 0


class TestAIConfigsAPIStats:
    """AI 配置统计 API 测试"""
    
    def test_get_config_stats(self, client, app, create_ai_config):
        """测试获取配置统计信息"""
        with app.app_context():
            # 创建几个配置
            create_ai_config(name="配置1", is_active=True)
            create_ai_config(name="配置2", is_active=True)
            create_ai_config(name="配置3", is_active=False)
            
            response = client.get('/api/ai-configs/stats')
            assert response.status_code == 200
            
            data = response.get_json()
            assert 'data' in data
            # 验证统计数据结构
            stats = data['data']
            assert 'total' in stats or 'total_count' in stats
