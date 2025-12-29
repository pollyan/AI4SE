# 意图测试工具

## 简介

AI 驱动的浏览器自动化测试工具，基于 MidScene 框架实现智能测试用例管理和执行。

## 目录结构

```
intent-tester/
├── backend/           # Flask 后端
│   ├── api/          # REST API 路由
│   ├── services/     # 业务逻辑服务
│   ├── models/       # 数据模型
│   └── app.py        # 应用入口
├── frontend/         # 前端资源
│   ├── templates/    # Jinja2 模板
│   └── static/       # CSS/JS 静态资源
├── browser-automation/  # 浏览器自动化
│   ├── midscene_framework/
│   └── midscene_server.js
├── docker/           # Docker 配置
└── requirements.txt
```

## 快速开始

```bash
# 启动服务
cd docker
docker-compose up -d

# 访问
http://localhost:5001
```

## 功能模块

- 测试用例管理（CRUD）
- 测试执行引擎
- 执行历史追踪
- 测试报告生成
- 本地代理管理
