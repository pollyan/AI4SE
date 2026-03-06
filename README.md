# AI4SE - AI for Software Engineering

> AI 辅助软件工程工具平台

## 项目简介

AI4SE 是一个面向软件工程的 AI 辅助工具平台，采用模块化单体仓库（Modular Monorepo）架构。平台集成了多种 AI 驱动的软件工程工具，包括意图测试框架、AI 智能体工作台等。

## 项目结构

```
AI4SE/
├── tools/
│   ├── frontend/              # 统一门户前端 (React SPA)
│   ├── intent-tester/         # 意图测试工具 (Flask + MidScene)
│   ├── new-agents/
│   │   ├── frontend/          # AI Agent 工作台 (React SPA)
│   │   └── backend/           # LLM 代理后端 (Flask)
│   └── shared/                # 共享 Python 库
├── docs/                      # 项目文档
├── scripts/                   # 开发脚本
├── tests/                     # E2E 测试
├── nginx/                     # Nginx 配置
└── dist/                      # 构建产物
```

## 技术栈

| 类别 | 技术 |
|------|------|
| 前端 | React 19, TypeScript, Tailwind CSS, Vite |
| 后端 | Flask, SQLAlchemy, PostgreSQL |
| 自动化 | Playwright, MidSceneJS |
| 容器化 | Docker, Docker Compose, Nginx |

## 快速开始

### 开发环境

```bash
# 启动所有服务
./scripts/dev/deploy-dev.sh

# 查看日志
docker-compose -f docker-compose.dev.yml logs -f
```

### 运行测试

```bash
# Python 测试
pytest

# 前端测试
cd tools/new-agents/frontend && npm test
```

## 文档

- [架构设计](docs/architecture.md)
- [开发指南](docs/development-guide.md)
- [部署指南](docs/deployment-guide.md)
- [API 契约](docs/api-contracts.md)
- [完整文档索引](docs/index.md)

## License

MIT