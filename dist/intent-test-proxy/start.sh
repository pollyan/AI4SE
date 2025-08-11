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

# 检查Node.js
echo -e "${BLUE}[1/4]${NC} 检查Node.js环境..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ 错误: 未检测到Node.js${NC}"
    echo ""
    echo "请先安装Node.js:"
    echo "https://nodejs.org/"
    echo ""
    echo "建议安装LTS版本 (16.x或更高)"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js版本: $NODE_VERSION${NC}"

# 检查npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ 错误: npm未找到${NC}"
    exit 1
fi

# 检查和安装依赖
echo ""
echo -e "${BLUE}[2/4]${NC} 检查依赖包..."

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
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 依赖安装失败${NC}"
        echo ""
        echo "可能的解决方案:"
        echo "1. 检查网络连接"
        echo "2. 清理npm缓存: npm cache clean --force"
        echo "3. 使用国内镜像: npm config set registry https://registry.npmmirror.com"
        exit 1
    fi
    
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

# 检查配置文件
echo ""
echo -e "${BLUE}[3/4]${NC} 检查配置文件..."
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

# 启动服务器
echo ""
echo -e "${BLUE}[4/4]${NC} 启动服务器..."
echo ""
echo -e "${GREEN}🚀 正在启动Intent Test Framework本地代理服务器...${NC}"
echo ""
echo "启动成功后，请返回Web界面选择"本地代理模式""
echo "按 Ctrl+C 可停止服务器"
echo ""

node midscene_server.js

echo ""
echo "服务器已停止"
