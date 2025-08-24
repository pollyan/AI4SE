"""
AI配置管理API测试
测试AI配置的CRUD操作和配置管理功能
"""
import json
import pytest
from web_gui.models import RequirementsAIConfig


class TestAIConfigsAPI:
    """AI配置管理API测试套件"""

    def test_list_configs_empty(self, api_client, assert_api_response):
        """测试获取空的AI配置列表"""
        response = api_client.get("/api/ai-configs")
        assert_api_response(response, expected_status=200)
        
        data = response.get_json()
        assert "data" in data
        assert "configs" in data["data"]
        assert data["data"]["total"] >= 0

    def test_create_config_success(self, api_client, assert_api_response):
        """测试成功创建AI配置"""
        config_data = {
            "config_name": "测试配置",
            "provider": "openai",
            "api_key": "sk-test123456789",
            "model_name": "gpt-4o-mini",
            "is_default": True
        }
        
        response = api_client.post("/api/ai-configs", 
                                 data=json.dumps(config_data),
                                 content_type="application/json")
        assert_api_response(response, expected_status=200)
        
        data = response.get_json()
        assert "data" in data
        config = data["data"]
        assert config["config_name"] == "测试配置"
        assert config["provider"] == "openai"
        assert config["model_name"] == "gpt-4o-mini"
        assert config["is_default"] is True
        assert "api_key_masked" in config  # API密钥应该被掩码处理

    def test_create_config_missing_required_fields(self, api_client, assert_api_response):
        """测试创建配置时缺少必要字段"""
        incomplete_data = {
            "config_name": "测试配置"
            # 缺少其他必要字段
        }
        
        response = api_client.post("/api/ai-configs",
                                 data=json.dumps(incomplete_data),
                                 content_type="application/json")
        assert_api_response(response, expected_status=400)

    def test_create_config_invalid_provider(self, api_client, assert_api_response):
        """测试创建配置时使用不支持的服务商"""
        config_data = {
            "config_name": "测试配置",
            "provider": "invalid_provider",
            "api_key": "sk-test123456789",
            "model_name": "gpt-4o-mini"
        }
        
        response = api_client.post("/api/ai-configs",
                                 data=json.dumps(config_data),
                                 content_type="application/json")
        assert_api_response(response, expected_status=400)

    def test_get_providers(self, api_client, assert_api_response):
        """测试获取支持的AI服务商信息"""
        response = api_client.get("/api/ai-configs/providers")
        assert_api_response(response, expected_status=200)
        
        data = response.get_json()
        assert "data" in data
        providers = data["data"]
        
        # 验证支持的服务商
        assert "openai" in providers
        assert "dashscope" in providers
        assert "claude" in providers
        
        # 验证服务商信息结构
        openai_info = providers["openai"]
        assert "name" in openai_info
        assert "default_base_url" in openai_info
        assert "default_models" in openai_info

    def test_update_config(self, api_client, assert_api_response):
        """测试更新AI配置"""
        # 先创建一个配置
        config_data = {
            "config_name": "原始配置",
            "provider": "openai",
            "api_key": "sk-test123456789",
            "model_name": "gpt-4o-mini"
        }
        
        create_response = api_client.post("/api/ai-configs",
                                        data=json.dumps(config_data),
                                        content_type="application/json")
        assert_api_response(create_response, expected_status=200)
        
        created_config = create_response.get_json()["data"]
        config_id = created_config["id"]
        
        # 更新配置
        update_data = {
            "config_name": "更新后的配置",
            "model_name": "gpt-4o"
        }
        
        response = api_client.put(f"/api/ai-configs/{config_id}",
                                data=json.dumps(update_data),
                                content_type="application/json")
        assert_api_response(response, expected_status=200)
        
        data = response.get_json()
        updated_config = data["data"]
        assert updated_config["config_name"] == "更新后的配置"
        assert updated_config["model_name"] == "gpt-4o"

    def test_update_nonexistent_config(self, api_client, assert_api_response):
        """测试更新不存在的配置"""
        update_data = {
            "config_name": "不存在的配置"
        }
        
        response = api_client.put("/api/ai-configs/99999",
                                data=json.dumps(update_data),
                                content_type="application/json")
        assert_api_response(response, expected_status=404)

    def test_delete_config(self, api_client, assert_api_response):
        """测试删除AI配置"""
        # 先创建两个配置
        config_data1 = {
            "config_name": "配置1",
            "provider": "openai",
            "api_key": "sk-test123456789",
            "model_name": "gpt-4o-mini",
            "is_default": True
        }
        
        config_data2 = {
            "config_name": "配置2",
            "provider": "dashscope",
            "api_key": "sk-test987654321",
            "model_name": "qwen-turbo"
        }
        
        create_response1 = api_client.post("/api/ai-configs",
                                         data=json.dumps(config_data1),
                                         content_type="application/json")
        assert_api_response(create_response1, expected_status=200)
        
        create_response2 = api_client.post("/api/ai-configs",
                                         data=json.dumps(config_data2),
                                         content_type="application/json")
        assert_api_response(create_response2, expected_status=200)
        
        config_id2 = create_response2.get_json()["data"]["id"]
        
        # 删除非默认配置
        response = api_client.delete(f"/api/ai-configs/{config_id2}")
        assert_api_response(response, expected_status=200)
        
        data = response.get_json()
        assert data["data"]["deleted_id"] == config_id2

    def test_delete_last_config_should_fail(self, api_client, assert_api_response):
        """测试删除最后一个配置应该失败"""
        # 获取当前所有配置
        list_response = api_client.get("/api/ai-configs")
        assert_api_response(list_response, expected_status=200)
        
        configs = list_response.get_json()["data"]["configs"]
        
        if len(configs) == 1:
            # 如果只有一个配置，删除应该失败
            config_id = configs[0]["id"]
            response = api_client.delete(f"/api/ai-configs/{config_id}")
            assert_api_response(response, expected_status=400)

    def test_set_default_config(self, api_client, assert_api_response):
        """测试设置默认配置"""
        # 先创建一个配置
        config_data = {
            "config_name": "待设为默认的配置",
            "provider": "openai",
            "api_key": "sk-test123456789",
            "model_name": "gpt-4o-mini"
        }
        
        create_response = api_client.post("/api/ai-configs",
                                        data=json.dumps(config_data),
                                        content_type="application/json")
        assert_api_response(create_response, expected_status=200)
        
        config_id = create_response.get_json()["data"]["id"]
        
        # 设置为默认配置
        response = api_client.post(f"/api/ai-configs/{config_id}/set-default")
        assert_api_response(response, expected_status=200)
        
        data = response.get_json()
        assert data["data"]["is_default"] is True

    def test_get_default_config(self, api_client, assert_api_response):
        """测试获取默认配置"""
        response = api_client.get("/api/ai-configs/default")
        
        # 可能有默认配置也可能没有，都是正常情况
        if response.status_code == 200:
            assert_api_response(response, expected_status=200)
            data = response.get_json()
            assert "data" in data
            assert data["data"]["is_default"] is True
        else:
            assert_api_response(response, expected_status=404)

    def test_api_key_masking(self, api_client, assert_api_response):
        """测试API密钥掩码功能"""
        config_data = {
            "config_name": "密钥掩码测试",
            "provider": "openai",
            "api_key": "sk-1234567890abcdefghijklmnopqrstuv",
            "model_name": "gpt-4o-mini"
        }
        
        response = api_client.post("/api/ai-configs",
                                 data=json.dumps(config_data),
                                 content_type="application/json")
        assert_api_response(response, expected_status=200)
        
        data = response.get_json()
        config = data["data"]
        
        # API密钥应该被掩码处理
        assert config["api_key_masked"] != "sk-1234567890abcdefghijklmnopqrstuv"
        assert "sk-" in config["api_key_masked"]
        assert "*" in config["api_key_masked"]  # 包含掩码字符

    def test_auto_set_default_base_url(self, api_client, assert_api_response):
        """测试自动设置默认base_url"""
        config_data = {
            "config_name": "默认URL测试",
            "provider": "dashscope",
            "api_key": "sk-test123456789",
            "model_name": "qwen-turbo"
            # 没有提供base_url
        }
        
        response = api_client.post("/api/ai-configs",
                                 data=json.dumps(config_data),
                                 content_type="application/json")
        assert_api_response(response, expected_status=200)
        
        data = response.get_json()
        config = data["data"]
        
        # 应该自动设置了DashScope的默认base_url
        assert config["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"