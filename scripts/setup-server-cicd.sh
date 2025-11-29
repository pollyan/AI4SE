#!/bin/bash

# 服务器部署配置脚本
# 服务器: 120.53.220.231

SERVER_IP="120.53.220.231"
SERVER_USER="root"  # 如果不是 root，请修改

echo "=========================================="
echo "🔧 配置服务器用于 CI/CD 部署"
echo "服务器: $SERVER_IP"
echo "=========================================="

# 询问是否继续
read -p "将连接到服务器 $SERVER_IP，是否继续？(y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

# 1. 连接服务器并执行配置
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'

echo ""
echo "1️⃣  生成部署专用 SSH 密钥..."
if [ ! -f ~/.ssh/github_deploy ]; then
    ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy -N ""
    echo "✅ 密钥对已生成"
else
    echo "✅ 密钥对已存在"
fi

echo ""
echo "2️⃣  配置 authorized_keys..."
if ! grep -q "github-actions-deploy" ~/.ssh/authorized_keys 2>/dev/null; then
    cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
    echo "✅ 公钥已添加到 authorized_keys"
else
    echo "✅ 公钥已存在于 authorized_keys"
fi

echo ""
echo "3️⃣  检查 Docker..."
if command -v docker &> /dev/null; then
    echo "✅ Docker 已安装: $(docker --version)"
else
    echo "❌ Docker 未安装，开始安装..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl start docker
    systemctl enable docker
    echo "✅ Docker 安装完成"
fi

echo ""
echo "4️⃣  检查/创建项目目录..."
if [ ! -d "/opt/intent-test-framework" ]; then
    echo "📥 克隆代码仓库..."
    echo "请先在 GitHub 上确保代码已推送！"
    echo "然后手动克隆: cd /opt && git clone YOUR_REPO_URL"
    echo "⚠️  暂时跳过克隆，请手动执行"
else
    echo "✅ 项目目录已存在"
    cd /opt/intent-test-framework
    git pull || echo "⚠️  无法拉取，可能需要配置 Git"
fi

echo ""
echo "5️⃣  配置防火墙..."
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw allow 5001/tcp
    echo "✅ 防火墙规则已添加"
else
    echo "⚠️  未找到 ufw，请手动配置防火墙"
fi

echo ""
echo "=========================================="
echo "✅ 服务器配置完成！"
echo "=========================================="

echo ""
echo "📋 下一步操作："
echo "1. 复制以下私钥内容到 GitHub Secrets (SSH_PRIVATE_KEY):"
echo "----------------------------------------"
cat ~/.ssh/github_deploy
echo "----------------------------------------"
echo ""
echo "2. 配置项目环境（如果项目目录已存在）:"
echo "   cd /opt/intent-test-framework"
echo "   nano .env  # 配置数据库等信息"
echo ""
echo "3. 修改 docker-compose.prod.yml（注释 postgres 服务）"

ENDSSH

echo ""
echo "🎉 本地脚本执行完成！"
echo "请按照上面的提示完成后续配置。"
