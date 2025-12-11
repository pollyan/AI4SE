#!/bin/bash

# ========================================
# 腾讯云服务器初始化脚本
# ========================================
# 在新安装的 Ubuntu 服务器上执行此脚本
# 用法: bash setup_tencent_cloud.sh
# ========================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_info "=========================================="
log_info "腾讯云服务器初始化开始"
log_info "=========================================="

# 1. 更新系统
log_info "更新系统包..."
sudo apt-get update
sudo apt-get upgrade -y

# 2. 安装基础工具
log_info "安装基础工具..."
sudo apt-get install -y \
    curl \
    wget \
    git \
    rsync \
    vim \
    htop \
    ca-certificates \
    gnupg \
    lsb-release

# 3. 安装 Docker
log_info "检查 Docker 是否已安装..."
if command -v docker &> /dev/null; then
    log_warn "Docker 已安装，跳过安装步骤"
    docker --version
else
    log_info "安装 Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    
    # 将当前用户添加到 docker 组
    sudo usermod -aG docker $USER
    log_info "✅ Docker 安装完成"
    docker --version
fi

# 4. 安装 Docker Compose
log_info "检查 Docker Compose 是否已安装..."
if command -v docker-compose &> /dev/null; then
    log_warn "Docker Compose 已安装，跳过安装步骤"
    docker-compose --version
else
    log_info "安装 Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    log_info "✅ Docker Compose 安装完成"
    docker-compose --version
fi

# 5. 创建部署目录
log_info "创建部署目录..."
sudo mkdir -p /opt/intent-test-framework
sudo chown -R $USER:$USER /opt/intent-test-framework
log_info "✅ 部署目录已创建: /opt/intent-test-framework"

# 6. 创建备份目录
log_info "创建备份目录..."
sudo mkdir -p /opt/intent-test-framework-backup
sudo chown -R $USER:$USER /opt/intent-test-framework-backup
log_info "✅ 备份目录已创建"

# 7. 配置防火墙（如果使用 ufw）
if command -v ufw &> /dev/null; then
    log_info "配置防火墙..."
    sudo ufw allow 22/tcp    # SSH
    sudo ufw allow 80/tcp    # HTTP
    sudo ufw allow 443/tcp   # HTTPS
    sudo ufw allow 5001/tcp  # Flask App
    log_info "✅ 防火墙规则已配置"
else
    log_warn "未检测到 ufw，跳过防火墙配置"
fi

# 8. 创建环境变量模板
log_info "创建环境变量模板..."
cat > /opt/intent-test-framework/.env.template << 'EOF'
# 数据库配置
DB_USER=intent_user
DB_PASSWORD=CHANGE_ME_IN_PRODUCTION

# Flask 配置
SECRET_KEY=CHANGE_ME_IN_PRODUCTION
FLASK_ENV=production

# 可选：AI 配置
# OPENAI_API_KEY=your_key_here
EOF

log_info "✅ 环境变量模板已创建: /opt/intent-test-framework/.env.template"
log_warn "请手动编辑 .env 文件并设置实际的密码和密钥"

# 9. 设置 SSH 目录权限
log_info "配置 SSH 目录..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
log_info "✅ SSH 目录已配置"

# 10. 显示系统信息
log_info "=========================================="
log_info "系统信息:"
log_info "=========================================="
echo "操作系统: $(lsb_release -d | cut -f2)"
echo "内核版本: $(uname -r)"
echo "Docker 版本: $(docker --version)"
echo "Docker Compose 版本: $(docker-compose --version)"
echo "磁盘空间:"
df -h / | tail -1
echo "内存信息:"
free -h | grep Mem

log_info "=========================================="
log_info "✅ 服务器初始化完成！"
log_info "=========================================="
log_info "下一步操作："
log_info "1. 配置 SSH 公钥认证（将公钥添加到 ~/.ssh/authorized_keys）"
log_info "2. 编辑 /opt/intent-test-framework/.env 文件"
log_info "3. 重新登录以使 Docker 组权限生效: exit 后重新 ssh 登录"
log_info "4. 测试 Docker: docker run hello-world"
log_info "=========================================="
