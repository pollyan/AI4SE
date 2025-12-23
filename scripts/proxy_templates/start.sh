#!/bin/bash

# Intent Test Framework 本地代理服务器启动脚本

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "========================================"
echo "  Intent Test Framework 本地代理服务器"
echo "========================================"
echo ""

# 步骤 1: 检查Node.js版本
echo -e "${BLUE}[1/5]${NC} 检查Node.js环境..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ 错误: 未检测到Node.js${NC}"
    echo ""
    echo "请先安装Node.js:"
    echo "  https://nodejs.org/"
    echo ""
    echo "推荐版本: Node.js 18.x - 22.x LTS"
    echo ""
    echo "💡 提示: 推荐使用 nvm 管理 Node.js 版本"
    echo "   安装 nvm: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash"
    echo "   安装 Node.js 20: nvm install 20"
    exit 1
fi

NODE_VERSION=$(node --version)
NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1 | sed 's/v//')

echo -e "${GREEN}✅ Node.js版本: $NODE_VERSION${NC}"

# 检查Node.js版本兼容性
if [ $NODE_MAJOR -lt 18 ]; then
    echo -e "${RED}❌ 错误: Node.js版本过低${NC}"
    echo ""
    echo "当前版本: $NODE_VERSION"
    echo "要求版本: Node.js 18.x - 22.x LTS"
    echo ""
    echo "请升级Node.js:"
    echo "  使用 nvm: nvm install 20 && nvm use 20"
    echo "  或访问: https://nodejs.org/"
    exit 1
elif [ $NODE_MAJOR -ge 24 ]; then
    echo -e "${YELLOW}⚠️  警告: Node.js版本过新 (v$NODE_MAJOR)${NC}"
    echo ""
    echo "检测到 Node.js v$NODE_MAJOR，部分依赖包可能存在兼容性问题"
    echo "推荐使用: Node.js 18.x - 22.x LTS"
    echo ""
    echo "如果遇到问题，建议切换到 Node.js 20:"
    echo "  nvm install 20 && nvm use 20"
    echo ""
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ 错误: npm未找到${NC}"
    exit 1
fi

# 步骤 2: 检查和安装依赖
echo ""
echo -e "${BLUE}[2/5]${NC} 检查依赖包..."

# 检查关键依赖是否存在
PLAYWRIGHT_TEST_MISSING=false
AXIOS_MISSING=false

if [ ! -d "node_modules/@playwright/test" ]; then
    PLAYWRIGHT_TEST_MISSING=true
fi

if [ ! -d "node_modules/axios" ]; then
    AXIOS_MISSING=true
fi

# 如果关键依赖缺失或node_modules不存在，则重新安装
if [ ! -d "node_modules" ] || [ "$PLAYWRIGHT_TEST_MISSING" = true ] || [ "$AXIOS_MISSING" = true ]; then
    echo -e "${YELLOW}📦 安装/更新依赖包...${NC}"
    echo "这可能需要几分钟时间，请耐心等待..."
    
    # 清理旧的依赖
    if [ -d "node_modules" ]; then
        echo -e "${YELLOW}🧹 清理旧依赖...${NC}"
        rm -rf node_modules package-lock.json
    fi
    
    # 安装依赖
    npm install 2>&1 | tee /tmp/npm_install.log
    NPM_EXIT_CODE=${PIPESTATUS[0]}
    
    if [ $NPM_EXIT_CODE -ne 0 ]; then
        echo -e "${RED}❌ 依赖安装失败${NC}"
        echo ""
        
        # 检查是否是权限问题
        if grep -q "EACCES" /tmp/npm_install.log; then
            echo -e "${RED}检测到 npm 权限错误 (EACCES)${NC}"
            echo ""
            echo "解决方法:"
            echo "  sudo chown -R $(whoami) "$HOME/.npm""
            echo "  sudo chown -R $(whoami) "$(pwd)""
            echo ""
            echo "修复后请重新运行此脚本"
        else
            echo "可能的解决方案:"
            echo "1. 检查网络连接"
            echo "2. 清理npm缓存: npm cache clean --force"
            echo "3. 使用国内镜像: npm config set registry https://registry.npmmirror.com"
        fi
        
        rm -f /tmp/npm_install.log
        exit 1
    fi
    
    rm -f /tmp/npm_install.log
    
    # 验证关键依赖
    if [ ! -d "node_modules/@playwright/test" ]; then
        echo -e "${RED}❌ @playwright/test 依赖安装失败${NC}"
        exit 1
    fi
    
    if [ ! -d "node_modules/axios" ]; then
        echo -e "${RED}❌ axios 依赖安装失败${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${GREEN}✅ 依赖包已存在${NC}"
fi

# 步骤 3: 检查 Playwright 浏览器
echo ""
echo -e "${BLUE}[3/5]${NC} 检查 Playwright 浏览器..."
echo "确保浏览器驱动已安装..."

# 检查 Playwright 浏览器是否已安装
if npx playwright --version &> /dev/null; then
    # 尝试安装浏览器（如果已安装会快速跳过）
    npx playwright install chromium --with-deps > /dev/null 2>&1 ||     npx playwright install chromium > /dev/null 2>&1 || true
    
    echo -e "${GREEN}✅ Playwright 浏览器就绪${NC}"
else
    echo -e "${YELLOW}⚠️  Playwright 未正确安装${NC}"
    echo "浏览器将在首次测试时自动下载"
fi

# 步骤 4: 检查配置文件
echo ""
echo -e "${BLUE}[4/5]${NC} 检查配置文件..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚙️ 首次运行，创建配置文件...${NC}"
    cp .env.example .env
    echo ""
    echo -e "${YELLOW}⚠️  重要: 请配置AI API密钥${NC}"
    echo ""
    echo "配置文件已创建: .env"
    echo "请编辑此文件，添加您的AI API密钥"
    echo ""
    echo "配置完成后，请重新运行此脚本"
    echo ""
    echo "编辑配置文件: nano .env"
    exit 0
fi

echo -e "${GREEN}✅ 配置文件存在${NC}"

# 步骤 5: 启动服务器
echo ""
echo -e "${BLUE}[5/5]${NC} 启动服务器..."
echo ""
echo -e "${GREEN}🚀 Starting Intent Test Framework Local Proxy Server...${NC}"
echo ""
echo "启动成功后，请返回Web界面选择本地代理模式"
echo "按 Ctrl+C 可停止服务器"
echo ""

node midscene_server.js

echo ""
echo "服务器已停止"
