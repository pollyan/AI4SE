#!/bin/bash
docker-compose -f /opt/intent-test-framework/docker-compose.prod.yml exec -T postgres psql -U intent_user -d ai4se -c "
INSERT INTO llm_config (config_key, api_key, base_url, model, description, is_active)
VALUES (
  'default',
  'sk-0b7ca376cfce4e2f82986eb5fea5124d',
  'https://dashscope.aliyuncs.com/compatible-mode/v1',
  'qwen3.5-plus',
  '正式环境：系统默认配置',
  true
) ON CONFLICT (config_key) DO UPDATE SET
  api_key = EXCLUDED.api_key,
  base_url = EXCLUDED.base_url,
  model = EXCLUDED.model,
  is_active = EXCLUDED.is_active,
  description = EXCLUDED.description,
  updated_at = NOW();"
