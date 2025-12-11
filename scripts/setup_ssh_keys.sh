#!/bin/bash

# ========================================
# SSH 密钥配置脚本
# ========================================
# 用于生成 SSH 密钥并配置到腾讯云服务器
# 用法: bash setup_ssh_keys.sh <SERVER_IP>
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

# 检查参数
if [ -z "$1" ]; then
    log_error "请提供服务器 IP 地址"
    echo "用法: $0 <SERVER_IP>"
    exit 1
fi

SERVER_IP=$1
SERVER_USER="ubuntu"
KEY_NAME="tencent_cloud_deploy"
KEY_PATH="$HOME/.ssh/$KEY_NAME"

log_info "=========================================="
log_info "SSH 密钥配置开始"
log_info "=========================================="
log_info "服务器 IP: $SERVER_IP"
log_info "用户名: $SERVER_USER"
log_info "密钥路径: $KEY_PATH"

# 1. 检查密钥是否已存在
if [ -f "$KEY_PATH" ]; then
    log_warn "密钥已存在: $KEY_PATH"
    read -p "是否覆盖现有密钥? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "跳过密钥生成"
    else
        log_info "删除旧密钥..."
        rm -f "$KEY_PATH" "$KEY_PATH.pub"
    fi
fi

# 2. 生成新密钥
if [ ! -f "$KEY_PATH" ]; then
    log_info "生成新的 SSH 密钥..."
    ssh-keygen -t ed25519 -C "github-actions-deploy-$(date +%Y%m%d)" -f "$KEY_PATH" -N ""
    log_info "✅ SSH 密钥已生成"
fi

# 3. 显示公钥
log_info "=========================================="
log_info "公钥内容（需要添加到服务器）:"
log_info "=========================================="
cat "$KEY_PATH.pub"
echo ""

# 4. 复制公钥到服务器
log_info "=========================================="
log_info "正在复制公钥到服务器..."
log_info "请输入服务器密码: Shunlian04!!"
log_info "=========================================="

# 使用 ssh-copy-id
if command -v ssh-copy-id &> /dev/null; then
    ssh-copy-id -i "$KEY_PATH.pub" "$SERVER_USER@$SERVER_IP"
    log_info "✅ 公钥已复制到服务器"
else
    log_warn "ssh-copy-id 未安装，请手动复制公钥"
    log_info "手动步骤:"
    log_info "1. ssh $SERVER_USER@$SERVER_IP"
    log_info "2. mkdir -p ~/.ssh && chmod 700 ~/.ssh"
    log_info "3. echo '$(cat $KEY_PATH.pub)' >> ~/.ssh/authorized_keys"
    log_info "4. chmod 600 ~/.ssh/authorized_keys"
fi

# 5. 测试 SSH 连接
log_info "=========================================="
log_info "测试 SSH 连接..."
log_info "=========================================="

if ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no "$SERVER_USER@$SERVER_IP" "echo '连接成功'" 2>/dev/null; then
    log_info "✅ SSH 密钥认证成功！"
else
    log_error "SSH 连接测试失败"
    log_warn "请检查:"
    log_warn "1. 服务器 IP 是否正确"
    log_warn "2. 公钥是否已正确添加到服务器"
    log_warn "3. 服务器 SSH 服务是否运行"
    exit 1
fi

# 6. 显示私钥内容（用于 GitHub Secrets）
log_info "=========================================="
log_info "私钥内容（用于 GitHub Secrets）:"
log_info "=========================================="
log_warn "请将以下内容复制到 GitHub Secrets 的 SSH_PRIVATE_KEY"
echo ""
cat "$KEY_PATH"
echo ""

# 7. 创建 GitHub Secrets 配置说明
log_info "=========================================="
log_info "GitHub Secrets 配置说明"
log_info "=========================================="
cat << EOF

请在 GitHub 仓库设置中配置以下 Secrets:

1. SSH_PRIVATE_KEY
   值: 上面显示的私钥内容（完整复制，包括 BEGIN 和 END 行）

2. SERVER_HOST
   值: $SERVER_IP

3. SERVER_USER
   值: $SERVER_USER

4. DB_PASSWORD
   值: 您的数据库密码（建议使用强密码）

5. SECRET_KEY
   值: Flask 密钥（可以使用以下命令生成）:
   python3 -c "import secrets; print(secrets.token_hex(32))"

配置路径:
GitHub 仓库 -> Settings -> Secrets and variables -> Actions -> New repository secret

EOF

log_info "=========================================="
log_info "✅ SSH 密钥配置完成！"
log_info "=========================================="
