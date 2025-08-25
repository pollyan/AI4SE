# 默认AI配置说明

## 📋 配置详情

本地测试环境已内置**阿里云通义千问(Qwen)**配置：

| 配置项 | 值 |
|-------|-----|
| **配置名称** | Qwen |
| **API密钥** | sk-0b7ca376cfce4e2f82986eb5fea5124d |
| **Base URL** | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| **模型** | qwen-plus |
| **状态** | 默认激活 |

## 🔧 自动初始化

每次使用 `./dev.sh start` 启动开发环境时，系统会：

1. **检查数据库表** - 自动创建 `requirements_ai_configs` 表（如不存在）
2. **配置管理** - 检查是否存在默认Qwen配置
3. **智能更新** - 如果配置存在则更新，不存在则创建
4. **设为默认** - 确保Qwen配置为默认AI助手

## 📄 相关文件

- `scripts/init_default_config.py` - 配置初始化脚本
- `dev.sh` - 启动脚本（集成配置初始化）

## 🔄 配置管理

可通过以下方式管理配置：

1. **Web界面**: 智能需求分析 → 配置管理
2. **直接访问**: http://localhost:5001/config-management
3. **脚本运行**: `python3 scripts/init_default_config.py`

## ⚠️ 注意事项

- 配置信息包含真实API密钥，仅用于本地开发测试
- 生产环境请使用自己的API密钥
- 可以在配置管理页面添加其他AI配置
