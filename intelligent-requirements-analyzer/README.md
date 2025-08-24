# 🎯 智能需求分析框架

基于BMAD-METHOD架构的AI驱动需求分析和产品文档生成系统

## 概述

该框架采用纯自然语言提示词架构，通过智能对话澄清将模糊的用户需求转化为清晰、完整、可执行的产品需求文档、Epic和用户故事。

## 核心特性

- 🤖 **智能澄清引擎** - 无预设问题库，AI动态生成最合适的澄清问题
- 🔄 **强制交互机制** - 关键节点必须用户确认，保证需求质量
- 📋 **文档自动生成** - 从澄清结果直接生成标准化PRD、Epic、Story
- 🎯 **全流程覆盖** - 从模糊想法到开发就绪的完整需求工程流程

## 项目结构

```
intelligent-requirements-analyzer/
├── core/
│   ├── agents/           # AI代理定义
│   ├── tasks/            # 可执行任务工作流
│   ├── templates/        # 文档生成模板
│   ├── data/             # 澄清方法和模式库
│   ├── checklists/       # 质量检查清单
│   └── workflows/        # 完整工作流编排
├── config.yaml           # 核心配置
└── README.md             # 项目说明
```

## 快速开始

1. **激活需求分析师**
   ```
   @requirements-analyst
   ```

2. **开始需求澄清**
   ```
   *analyze
   ```

3. **生成PRD文档**
   ```
   *create-prd
   ```

4. **分解Epic和Story**
   ```
   *create-epics
   *create-stories
   ```

## 工作流程

```
模糊需求 → 智能澄清 → PRD文档 → Epic分解 → 用户故事 → 开发就绪
```

## 与BMAD-METHOD的关系

本框架完全遵循BMAD-METHOD的设计原则：
- 纯自然语言架构，无代码逻辑
- 模块化组件设计
- 强制交互保证质量
- 标准化工作流程

## 许可证

MIT License - 基于BMAD-METHOD框架构建
