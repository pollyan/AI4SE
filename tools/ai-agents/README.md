# AI 智能体应用

## 简介

基于 Google ADK 的 AI 智能体平台，提供需求分析和测试策略规划服务。

## 目录结构

```
ai-agents/
├── backend/          # Flask 后端
│   ├── api/         # REST API 路由
│   ├── agents/      # 智能体实现
│   │   ├── alex/   # 需求分析师
│   │   ├── lisa/   # 测试分析师
│   │   └── base/   # 基类
│   ├── models/      # 数据模型
│   └── app.py       # 应用入口
├── frontend/        # 前端资源（未来迁移到 React）
│   ├── templates/   # Jinja2 模板（临时）
│   └── static/      # CSS/JS 静态资源
├── docker/          # Docker 配置
└── requirements.txt
```

## 快速开始

```bash
# 启动服务
cd docker
docker-compose up -d

# 访问
http://localhost:5002
```

## 智能体

### Alex - 需求分析师
- 需求澄清
- 共识提取
- PRD 生成

### Lisa - 测试分析师
- 测试策略规划
- 用例设计
- 覆盖率分析
