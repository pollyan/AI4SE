#!/bin/bash

# AI4SE工具集 - 本地开发环境启动脚本
# 功能：智能处理端口占用、进程管理、服务启动和健康检查
# 作者：Claude AI Assistant
# 版本：1.0

set -e  # 遇到错误时退出

# =============================================================================
# 配置参数
# =============================================================================

FLASK_PORT=5001
MIDSCENE_PORT=3001
PROJECT_ROOT=$(pwd)
FLASK_APP="start.py"
PID_FILE="/tmp/ai4se_flask.pid"
LOG_FILE="/tmp/ai4se_flask.log"
HEALTH_CHECK_TIMEOUT=45
HEALTH_CHECK_INTERVAL=3

# 关键健康检查端点（可在此数组中增删）
# 提示：如需增加创建型接口，请谨慎使用POST，避免在健康检查中产生副作用
HEALTH_ENDPOINTS=(
  "/api/requirements/assistants"
  "/api/requirements/assistants/alex/bundle"
  "/api/testcases"
  "/api/executions"
)

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# =============================================================================
# 工具函数
# =============================================================================

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 打印分割线
print_separator() {
    echo "========================================================================================="
}

# 打印标题
print_title() {
    print_separator
    print_message $CYAN "🚀 AI4SE工具集 - 本地开发环境管理"
    print_message $WHITE "项目路径: $(pwd)"
    print_message $WHITE "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    print_separator
}

# 显示帮助信息
show_help() {
    cat << EOF
AI4SE工具集 - 本地开发环境启动脚本

使用方法:
    ./dev.sh [命令] [选项]

命令:
    start      启动完整的开发环境 (默认)
    stop       停止所有服务
    restart    重启所有服务
    status     查看服务状态
    logs       查看实时日志
    clean      清理端口和临时文件
    health     健康检查

示例:
    ./dev.sh           # 启动完整环境
    ./dev.sh start     # 启动完整环境
    ./dev.sh stop      # 停止所有服务
    ./dev.sh restart   # 重启服务
    ./dev.sh status    # 查看状态
    ./dev.sh logs      # 查看日志

选项:
    --port PORT        指定Flask端口 (默认: 5001)
    --no-browser       不自动打开浏览器
    --verbose          详细输出
    --help, -h         显示此帮助信息

EOF
}

# 检查必要的依赖
check_dependencies() {
    print_message $BLUE "🔍 检查系统依赖..."
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_message $RED "❌ Python3 未安装"
        exit 1
    fi
    
    # 检查lsof
    if ! command -v lsof &> /dev/null; then
        print_message $YELLOW "⚠️ lsof 未安装，将使用 netstat 替代"
    fi
    
    # 检查关键文件
    if [[ ! -f "$FLASK_APP" ]]; then
        print_message $RED "❌ Flask应用文件 '$FLASK_APP' 不存在"
        exit 1
    fi
    
    print_message $GREEN "✅ 系统依赖检查通过"
}

# 检查端口占用
check_port() {
    local port=$1
    if command -v lsof &> /dev/null; then
        lsof -ti:$port 2>/dev/null || true
    else
        netstat -tulpn 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 || true
    fi
}

# 强制清理端口
force_cleanup_port() {
    local port=$1
    print_message $YELLOW "🧹 清理端口 $port..."
    
    local pids=$(check_port $port)
    if [[ -n "$pids" ]]; then
        print_message $YELLOW "发现占用端口 $port 的进程: $pids"
        echo "$pids" | while read pid; do
            if [[ -n "$pid" ]] && [[ "$pid" =~ ^[0-9]+$ ]]; then
                print_message $YELLOW "终止进程 $pid..."
                kill -9 $pid 2>/dev/null || true
                sleep 1
            fi
        done
        
        # 再次检查
        local remaining_pids=$(check_port $port)
        if [[ -n "$remaining_pids" ]]; then
            print_message $RED "⚠️ 端口 $port 仍被占用，可能需要手动处理"
        else
            print_message $GREEN "✅ 端口 $port 已释放"
        fi
    else
        print_message $GREEN "✅ 端口 $port 未被占用"
    fi
}

# 清理所有相关进程
cleanup_processes() {
    print_message $BLUE "🧹 清理相关进程..."
    
    # 清理Python进程 (包含start.py)
    print_message $YELLOW "清理 Python Flask 进程..."
    pkill -f "python.*start\.py" 2>/dev/null || true
    
    # 清理可能的僵尸进程
    ps aux | grep -i "python.*start" | grep -v grep | awk '{print $2}' | while read pid; do
        if [[ -n "$pid" ]]; then
            kill -9 $pid 2>/dev/null || true
        fi
    done
    
    # 清理端口
    force_cleanup_port $FLASK_PORT
    force_cleanup_port $MIDSCENE_PORT
    
    # 清理PID文件
    rm -f "$PID_FILE"
    
    print_message $GREEN "✅ 进程清理完成"
}

# 初始化默认配置
init_default_config() {
    print_message $BLUE "⚙️ 初始化默认AI配置..."
    
    if python3 scripts/init_default_config.py; then
        print_message $GREEN "✅ 默认AI配置初始化成功"
        return 0
    else
        print_message $YELLOW "⚠️ 默认AI配置初始化失败，但不影响服务启动"
        return 1
    fi
}

# 启动Flask服务
start_flask() {
    print_message $BLUE "🚀 启动 Flask 服务 (端口: $FLASK_PORT)..."
    
    # 确保端口可用
    force_cleanup_port $FLASK_PORT
    
    # 启动服务
    nohup python3 "$FLASK_APP" > "$LOG_FILE" 2>&1 &
    local flask_pid=$!
    echo $flask_pid > "$PID_FILE"
    
    print_message $GREEN "✅ Flask 服务已启动 (PID: $flask_pid)"
    print_message $WHITE "日志文件: $LOG_FILE"
    
    # 给Flask一些时间完全启动
    print_message $YELLOW "⏳ 等待Flask完全启动..."
    sleep 5
    
    # 返回成功状态
    return 0
}

# 健康检查
health_check() {
    local url="http://localhost:$FLASK_PORT"
    local timeout=${1:-$HEALTH_CHECK_TIMEOUT}
    
    print_message $BLUE "🏥 执行健康检查..."
    print_message $WHITE "检查地址: $url"
    print_message $WHITE "超时时间: ${timeout}秒"
    
    local count=0
    while [ $count -lt $((timeout / HEALTH_CHECK_INTERVAL)) ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            print_message $GREEN "✅ 服务健康检查通过!"
            print_message $GREEN "🌍 Web界面: $url"
            print_message $GREEN "🔌 API接口: $url/api/"
            break
        fi
        
        print_message $YELLOW "⏳ 等待服务启动... (${count}/${timeout}s)"
        sleep $HEALTH_CHECK_INTERVAL
        count=$((count + HEALTH_CHECK_INTERVAL))
    done
    
    if [ $count -ge $((timeout / HEALTH_CHECK_INTERVAL)) ]; then
        print_message $RED "❌ 健康检查失败 - 服务可能未正常启动"
        print_message $YELLOW "💡 请检查日志: tail -f $LOG_FILE"
        return 1
    fi

    # 关键接口探活（防止蓝图前缀错误导致的404）
    print_message $BLUE "🔎 校验关键接口..."
    local failed=0
    for ep in "${HEALTH_ENDPOINTS[@]}"; do
        if curl -s -f "$url$ep" > /dev/null 2>&1; then
            print_message $GREEN "✅ $ep 正常"
        else
            print_message $RED "❌ $ep 校验失败"
            failed=1
        fi
    done

    if [ $failed -eq 1 ]; then
        print_message $YELLOW "💡 可能的原因：重复叠加 /api 前缀或蓝图未注册"
        print_message $YELLOW "💡 建议：查看 web_gui/api/base.py 与 web_gui/api/__init__.py 中蓝图注册前缀配置"
        return 1
    fi

    return 0
}

# 显示服务状态
show_status() {
    print_message $BLUE "📊 服务状态检查..."
    
    # 检查Flask服务
    if [[ -f "$PID_FILE" ]]; then
        local flask_pid=$(cat "$PID_FILE")
        if ps -p $flask_pid > /dev/null 2>&1; then
            print_message $GREEN "✅ Flask服务运行中 (PID: $flask_pid)"
            local port_pid=$(check_port $FLASK_PORT)
            if [[ -n "$port_pid" ]]; then
                print_message $GREEN "✅ 端口 $FLASK_PORT 正常监听"
                print_message $GREEN "🌍 访问地址: http://localhost:$FLASK_PORT"
            else
                print_message $YELLOW "⚠️ Flask进程运行但端口未监听"
            fi
        else
            print_message $RED "❌ Flask服务未运行"
        fi
    else
        print_message $RED "❌ Flask服务未启动"
    fi
    
    # 检查端口占用情况
    print_message $WHITE "\n📡 端口占用情况:"
    for port in $FLASK_PORT $MIDSCENE_PORT; do
        local pid=$(check_port $port)
        if [[ -n "$pid" ]]; then
            print_message $GREEN "端口 $port: 被进程 $pid 占用"
        else
            print_message $YELLOW "端口 $port: 空闲"
        fi
    done
}

# 显示日志
show_logs() {
    if [[ -f "$LOG_FILE" ]]; then
        print_message $BLUE "📋 显示服务日志 (Ctrl+C 退出)..."
        tail -f "$LOG_FILE"
    else
        print_message $YELLOW "⚠️ 日志文件不存在: $LOG_FILE"
    fi
}

# 停止所有服务
stop_services() {
    print_message $BLUE "🛑 停止所有服务..."
    
    if [[ -f "$PID_FILE" ]]; then
        local flask_pid=$(cat "$PID_FILE")
        if ps -p $flask_pid > /dev/null 2>&1; then
            print_message $YELLOW "停止 Flask 服务 (PID: $flask_pid)..."
            kill $flask_pid 2>/dev/null || true
            sleep 2
            
            # 如果进程还在运行，强制终止
            if ps -p $flask_pid > /dev/null 2>&1; then
                kill -9 $flask_pid 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
    fi
    
    # 清理所有相关进程
    cleanup_processes
    
    print_message $GREEN "✅ 所有服务已停止"
}

# 启动开发环境
start_development() {
    local no_browser=${1:-false}
    
    print_title
    
    # 检查依赖
    check_dependencies
    
    # 清理环境
    cleanup_processes
    sleep 1
    
    # 启动Flask服务
    if start_flask; then
        print_message $GREEN "✅ Flask服务启动成功"
    else
        print_message $RED "❌ Flask服务启动失败"
        exit 1
    fi
    
    # 健康检查
    if health_check; then
        # 服务启动成功后，初始化AI配置
        print_message $BLUE "⚙️ 初始化默认AI配置..."
        init_default_config
        
        print_message $GREEN "🎉 开发环境启动成功!"
        print_separator
        print_message $CYAN "📍 访问地址:"
        print_message $WHITE "   主页: http://localhost:$FLASK_PORT"
        print_message $WHITE "   需求分析: http://localhost:$FLASK_PORT/requirements"
        print_message $WHITE "   配置管理: http://localhost:$FLASK_PORT/config-management"
        print_message $WHITE "   测试用例: http://localhost:$FLASK_PORT/testcases"
        print_separator
        
        # 自动打开浏览器
        if [[ "$no_browser" != true ]] && command -v open &> /dev/null; then
            print_message $BLUE "🌐 自动打开浏览器..."
            open "http://localhost:$FLASK_PORT" 2>/dev/null || true
        fi
        
        print_message $YELLOW "💡 使用 './dev.sh logs' 查看实时日志"
        print_message $YELLOW "💡 使用 './dev.sh stop' 停止服务"
        
    else
        print_message $RED "❌ 开发环境启动失败"
        print_message $YELLOW "💡 查看日志获取详细信息: tail -f $LOG_FILE"
        exit 1
    fi
}

# 清理临时文件和端口
clean_environment() {
    print_message $BLUE "🧹 清理开发环境..."
    
    # 停止服务
    stop_services
    
    # 清理临时文件
    rm -f "$PID_FILE" "$LOG_FILE"
    
    # 清理Python缓存
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    print_message $GREEN "✅ 环境清理完成"
}

# =============================================================================
# 主程序
# =============================================================================

main() {
    local command=${1:-start}
    local no_browser=false
    local verbose=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            start|stop|restart|status|logs|clean|health)
                command=$1
                ;;
            --port)
                FLASK_PORT="$2"
                shift
                ;;
            --no-browser)
                no_browser=true
                ;;
            --verbose)
                verbose=true
                set -x
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_message $RED "未知参数: $1"
                echo "使用 --help 查看帮助信息"
                exit 1
                ;;
        esac
        shift
    done
    
    # 执行命令
    case $command in
        start)
            start_development $no_browser
            ;;
        stop)
            stop_services
            ;;
        restart)
            print_message $BLUE "🔄 重启服务..."
            stop_services
            sleep 2
            start_development $no_browser
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        clean)
            clean_environment
            ;;
        health)
            health_check
            ;;
        *)
            print_message $RED "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 信号处理 - 优雅退出
trap 'print_message $YELLOW "\n🛑 收到中断信号，正在清理..."; stop_services; exit 0' INT TERM

# 运行主程序
main "$@"
