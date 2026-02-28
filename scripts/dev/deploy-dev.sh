#!/bin/bash
set -e

# ========================================
# 本地开发环境增量部署脚本
# ========================================

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "📂 项目根目录: $PROJECT_ROOT"

# ========================================
# 1. 环境检查
# ========================================

# 检查 .env 文件
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "⚠️  未找到 .env，从 .env.example 复制..."
        cp .env.example .env
        echo "✅ .env 已创建，请稍后检查配置"
    else
        echo "❌ 未找到 .env 或 .env.example，无法继续"
        exit 1
    fi
fi

# ========================================
# 2. 启动服务
# ========================================

MODE="incremental"
DOCKER_BUILD_ARGS="--build"
SKIP_FRONTEND=false

# 解析参数
for arg in "$@"; do
    case $arg in
        full|--full)
            MODE="full-rebuild"
            ;;
        --no-frontend|--skip-frontend)
            SKIP_FRONTEND=true
            ;;
    esac
done

if [[ "$MODE" == "full-rebuild" ]]; then
    echo "🧹 检测到全量重建模式，正在清理旧资源..."
    docker-compose -f docker-compose.dev.yml down --rmi local --remove-orphans
    DOCKER_BUILD_ARGS="--build --force-recreate"
fi

# ========================================
# 3. 前端构建 (本地代码同步)
# ========================================

if [ "$SKIP_FRONTEND" = false ]; then
    echo "🏗️  正在准备项目构建..."
    
    # 定义所有包含 package.json 的项目路径
    JS_PROJECTS=("tools/frontend" "tools/intent-tester" "tools/new-agents")
    
    for PROJECT_PATH in "${JS_PROJECTS[@]}"; do
        if [ -d "$PROJECT_PATH" ] && [ -f "$PROJECT_PATH/package.json" ]; then
            echo "📦 处理项目: $PROJECT_PATH"
            (
                cd "$PROJECT_PATH"
                # 1. 检查 node_modules
                if [ ! -d "node_modules" ]; then
                    echo "   📥 正在安装依赖..."
                    npm install
                fi
                
                # 2. 检查并运行 build 脚本
                if grep -q "\"build\":" package.json; then
                    echo "   🔨 正在执行构建 (npm run build)..."
                    npm run build
                else
                    echo "   ℹ️  项目无 build 脚本，跳过构建步骤"
                fi
            )
        fi
    done

    # 特殊处理：意图测试工具的代理包构建
    if [ -f "scripts/ci/build-proxy-package.js" ]; then
        echo "📦 正在构建意图测试工具代理包..."
        node scripts/ci/build-proxy-package.js
        # 将产物复制到 intent-tester 的静态目录，以便本地下载
        mkdir -p tools/intent-tester/frontend/static
        cp dist/intent-test-proxy.zip tools/intent-tester/frontend/static/ 2>/dev/null || true
    fi

    echo "✅ 项目构建/准备完成"
else
    echo "⏭️  跳过构建模式"
fi

echo "🚀 正在启动本地 Docker 环境..."
echo "   配置文件: docker-compose.dev.yml"
echo "   模式: $MODE"

if [[ "$MODE" == "full-rebuild" ]]; then
    echo "   ⚠️ 全量模式下会强制重新构建所有镜像（不使用缓存）"
    # 全量模式我们显式使用 build --no-cache
    docker-compose -f docker-compose.dev.yml build --no-cache
    docker-compose -f docker-compose.dev.yml up -d
else
    # 增量模式
    echo "   (仅在 Dockerfile 变更时重建)"
    docker-compose -f docker-compose.dev.yml up -d --build
fi

# 5. 重启 Nginx (确保获取最新的 Upstream IP)
echo "🔄 重启 Nginx 以刷新 DNS 解析..."
docker-compose -f docker-compose.dev.yml restart nginx

# ========================================
# 3. 健康检查
# ========================================

echo ""
echo "⏳ 等待服务启动..."
sleep 5

docker-compose -f docker-compose.dev.yml ps

echo ""
echo "🏥 执行部署后健康检查..."
echo ""

# 执行健康检查脚本
if [ -f "$PROJECT_ROOT/scripts/health/health_check.sh" ]; then
    chmod +x "$PROJECT_ROOT/scripts/health/health_check.sh"
    if bash "$PROJECT_ROOT/scripts/health/health_check.sh" local; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "✅ 部署成功！健康检查通过"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📍 访问入口:"
        echo "   🏠 主页: http://localhost"
        echo "   🧪 意图测试: http://localhost/intent-tester"
        echo "   🆕 新 Agent: http://localhost/new-agents"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "💡 常用命令:"
        echo "   查看日志: docker-compose -f docker-compose.dev.yml logs -f"
        echo "   停止服务: docker-compose -f docker-compose.dev.yml down"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    else
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "❌ 部署失败！健康检查未通过"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "💡 请检查日志: docker-compose -f docker-compose.dev.yml logs"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        exit 1
    fi
else
    echo "⚠️  健康检查脚本不存在，跳过检查"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ 服务启动完成！"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📍 访问入口:"
    echo "   🏠 主页: http://localhost"
    echo "   🧪 意图测试: http://localhost/intent-tester"
    echo "   🆕 新 Agent: http://localhost/new-agents"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 常用命令:"
    echo "   查看日志: docker-compose -f docker-compose.dev.yml logs -f"
    echo "   停止服务: docker-compose -f docker-compose.dev.yml down"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

