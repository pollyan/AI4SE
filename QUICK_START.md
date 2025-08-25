# AI4SE工具集 - 快速启动指南

## 🚀 一键启动

```bash
# 启动完整开发环境（自动配置Qwen AI）
./dev.sh

# 或者不自动打开浏览器
./dev.sh start --no-browser
```

## 🤖 内置AI配置

启动时会自动配置**阿里云通义千问(Qwen)**作为默认AI助手：
- **模型**: qwen-plus
- **配置名称**: Qwen  
- **状态**: 已激活并设为默认

无需手动配置即可直接使用智能需求分析功能！

## 📋 常用命令

```bash
./dev.sh start          # 启动开发环境
./dev.sh stop           # 停止所有服务
./dev.sh restart        # 重启服务
./dev.sh status         # 查看服务状态
./dev.sh logs           # 查看实时日志
./dev.sh health         # 健康检查
./dev.sh clean          # 清理环境
./dev.sh --help         # 显示帮助信息
```

## 🌐 访问地址

启动成功后，可以访问以下页面：

- **主页**: http://localhost:5001
- **需求分析**: http://localhost:5001/requirements
- **配置管理**: http://localhost:5001/config-management  ⭐ 新功能
- **测试用例**: http://localhost:5001/testcases
- **执行报告**: http://localhost:5001/reports

## ⚡ 功能特点

### 🔧 智能问题解决
- **端口占用自动清理** - 不再需要手动杀进程
- **进程管理** - 智能检测和清理僵尸进程
- **健康检查** - 确保服务完全启动后才提示成功

### 🎛️ 便捷操作
- **一键启动/停止** - 简化开发环境管理
- **实时日志查看** - 方便调试问题
- **服务状态监控** - 随时了解服务运行情况

### 🛠️ 开发友好
- **自动打开浏览器** - 启动后直接进入开发状态
- **详细状态反馈** - 清晰的彩色输出和进度提示
- **错误处理** - 友好的错误提示和解决建议

## 🆘 故障排除

### 问题：页面加载慢或无响应
```bash
./dev.sh health    # 检查服务健康状态
./dev.sh restart   # 重启服务
```

### 问题：端口被占用
```bash
./dev.sh clean     # 清理所有相关进程和端口
./dev.sh start     # 重新启动
```

### 问题：服务无法启动
```bash
./dev.sh status    # 查看详细状态
./dev.sh logs      # 查看错误日志
```

## 📁 脚本文件说明

- `dev.sh` - 主启动脚本（项目根目录）
- `scripts/local-dev/start-local-dev.sh` - 详细环境检查脚本
- `scripts/local-dev/README.md` - 详细文档

## 🎯 配置管理新功能

现在可以通过独立的配置管理页面来：
- ✅ 管理所有AI配置
- ✅ 测试配置连接
- ✅ 选择使用的配置
- ✅ 删除不需要的配置
- ✅ 批量测试所有配置

访问地址：http://localhost:5001/config-management
