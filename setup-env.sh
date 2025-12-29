#!/bin/bash
# 环境配置向导 - 帮助用户快速配置.env文件

echo "==================================="
echo "意图测试平台 - 环境配置向导"
echo "==================================="
echo ""

# 检查是否已有.env文件
if [ -f ".env" ]; then
    echo "⚠️  检测到已有.env文件"
    read -p "是否覆盖现有配置？(y/N): " overwrite
    if [ "$overwrite" != "y" ] && [ "$overwrite" != "Y" ]; then
        echo "配置已取消"
        exit 0
    fi
fi

# 复制模板
cp .env.docker.example .env
echo "✅ 已创建.env文件"
echo ""

echo "====================================="
echo "📝 请配置以下必填项："
echo "====================================="
echo ""

# 配置AI API密钥
echo "1. AI服务配置（MidScene需要）"
echo "   支持的AI服务："
echo "   a) 阿里云DashScope（推荐）"
echo "   b) OpenAI"
echo "   c) Google Gemini"
echo ""
read -p "请选择AI服务 (a/b/c) [默认a]: " ai_choice
ai_choice=${ai_choice:-a}

if [ "$ai_choice" = "a" ]; then
    echo ""
    echo "请访问：https://dashscope.console.aliyun.com/"
    echo "获取您的API Key"
    echo ""
    read -p "请输入DashScope API Key (sk-开头): " api_key
    
    sed -i '' "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$api_key/" .env
    echo "✅ 已配置DashScope API Key"
    
elif [ "$ai_choice" = "b" ]; then
    echo ""
    read -p "请输入OpenAI API Key: " api_key
    
    sed -i '' "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$api_key/" .env
    sed -i '' "s|OPENAI_BASE_URL=.*|OPENAI_BASE_URL=https://api.openai.com/v1|" .env
    sed -i '' "s/MIDSCENE_MODEL_NAME=.*/MIDSCENE_MODEL_NAME=gpt-4o/" .env
    echo "✅ 已配置OpenAI API Key"
    
else
    echo ""
    read -p "请输入Gemini API Key: " api_key
    
    sed -i '' "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$api_key/" .env
    sed -i '' "s|OPENAI_BASE_URL=.*|OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/|" .env
    sed -i '' "s/MIDSCENE_MODEL_NAME=.*/MIDSCENE_MODEL_NAME=gemini-2.5-pro/" .env
    echo "✅ 已配置Gemini API Key"
fi

echo ""
echo "2. 数据库配置"
read -p "数据库密码 [默认: local_dev_password]: " db_password
db_password=${db_password:-local_dev_password}
sed -i '' "s/DB_PASSWORD=.*/DB_PASSWORD=$db_password/" .env
echo "✅ 已配置数据库密码"

echo ""
echo "3. Flask应用密钥"
# 生成随机SECRET_KEY
secret_key=$(openssl rand -base64 32 2>/dev/null || echo "dev-secret-$(date +%s)")
sed -i '' "s/SECRET_KEY=.*/SECRET_KEY=$secret_key/" .env
echo "✅ 已自动生成SECRET_KEY"

echo ""
echo "====================================="
echo "✅ 配置完成！"
echo "====================================="
echo ""
echo "查看配置文件："
echo "  cat .env"
echo ""
echo "下一步："
echo "  1. 启动Docker服务:"
echo "     docker-compose -f docker-compose.yml -f docker-compose.dev.yml up"
echo ""
echo "  2. 启动MidScene Server（新终端）:"
echo "     node tools/intent-tester/browser-automation/midscene_server.js"
echo ""
echo "  3. 访问应用:"
echo "     http://localhost:5001"
echo "====================================="
