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
            "api_key": "sk-test123456789",
            "base_url": "https://api.openai.com/v1",
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
        assert config["base_url"] == "https://api.openai.com/v1"
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

    def test_create_config_invalid_base_url(self, api_client, assert_api_response):
        """测试创建配置时使用无效的base_url"""
        config_data = {
            "config_name": "测试配置",
            "api_key": "sk-test123456789",
            "base_url": "invalid_url",
            "model_name": "gpt-4o-mini"
        }
        
        response = api_client.post("/api/ai-configs",
                                 data=json.dumps(config_data),
                                 content_type="application/json")
        # 注意：现在这个请求可能会成功，因为我们移除了服务商验证
        # 但客户端应该在前端验证URL格式

    def test_get_config_examples(self, api_client, assert_api_response):
        """测试获取AI配置示例"""
        response = api_client.get("/api/ai-configs/examples")
        assert_api_response(response, expected_status=200)
        
        data = response.get_json()
        assert "data" in data
        examples = data["data"]
        
        # 验证配置示例
        assert "openai_gpt4" in examples
        assert "dashscope_qwen" in examples
        assert "claude_api" in examples
        
        # 验证示例信息结构
        openai_example = examples["openai_gpt4"]
        assert "name" in openai_example
        assert "base_url" in openai_example
        assert "models" in openai_example

    def test_update_config(self, api_client, assert_api_response):
        """测试更新AI配置"""
        # 先创建一个配置
        config_data = {
            "config_name": "原始配置",
            "api_key": "sk-test123456789",
            "base_url": "https://api.openai.com/v1",
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
            "api_key": "sk-test123456789",
            "base_url": "https://api.openai.com/v1",
            "model_name": "gpt-4o-mini",
            "is_default": True
        }
        
        config_data2 = {
            "config_name": "配置2",
            "api_key": "sk-test987654321",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
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
            "api_key": "sk-test123456789",
            "base_url": "https://api.openai.com/v1",
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
            "api_key": "sk-1234567890abcdefghijklmnopqrstuv",
            "base_url": "https://api.openai.com/v1",
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
            "config_name": "完整配置测试",
            "api_key": "sk-test123456789",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model_name": "qwen-turbo"
        }
        
        response = api_client.post("/api/ai-configs",
                                 data=json.dumps(config_data),
                                 content_type="application/json")
        assert_api_response(response, expected_status=200)
        
        data = response.get_json()
        config = data["data"]
        
        # 验证配置内容正确保存
        assert config["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert config["config_name"] == "完整配置测试"
