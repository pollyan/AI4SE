---
title: 'New-Agents 模块代码结构重构'
slug: 'new-agents-code-restructure'
created: '2026-03-03T00:37:00+08:00'
status: 'in-progress'
stepsCompleted: [1]
tech_stack:
  - React
  - Vite
  - TypeScript
  - Zustand
  - Vitest
files_to_modify: []
code_patterns: []
test_patterns: []
---

# Tech-Spec: New-Agents 模块代码结构重构

**Created:** 2026-03-03T00:37:00+08:00

## Overview

### Problem Statement

`tools/new-agents` 模块的 `src/` 目录将前端 UI 代码（React 组件、页面、Zustand Store）和 Agent 核心业务逻辑（工作流定义、Prompt 模板、LLM 调用、流式响应解析）混杂在一起。这与同项目中 `tools/intent-tester` 的清晰 `backend/` + `frontend/` 分层结构不一致，导致：

- 新开发者理解模块边界的认知成本高
- Agent 核心逻辑（纯 TS）与 React UI 紧耦合，难以独立测试和复用
- `chatService.ts` 同时承担 UI Hook 和 Agent 控制流两个职责，违反单一职责原则

### Solution

新建 `frontend/` 目录承载所有前端应用代码和构建配置（`package.json`、`vite.config.ts`、`tsconfig.json`、`index.html`）。在 `frontend/src/` 下新建 `core/` 子目录，将 Agent 核心逻辑（`workflows.ts`、`prompts/`、`llm.ts`、`config/`、`utils/`）分离为独立层，形成清晰的 UI / Core / Backend 三层边界。

### Scope

**In Scope:**
- 创建 `frontend/` 目录，迁移前端文件和构建配置
- 在 `frontend/src/core/` 下分离 Agent 核心逻辑
- 更新所有 import 路径
- 调整 `vite.config.ts`、`tsconfig.json` 中的路径配置
- 更新 `docker/Dockerfile`、`docker/nginx.conf` 中的构建路径
- 更新 GitHub Actions CI/CD 工作流中涉及 `tools/new-agents` 的路径
- 确保所有现有测试通过

**Out of Scope:**
- 任何功能变更或新功能开发
- 后端 Python 代码（`backend/`）的改动
- 重写或重构业务逻辑代码本身
- 修改 `chatService.ts` 的职责拆分（可作为后续优化）

## Context for Development

### Codebase Patterns

- **模块化单体架构**：项目采用 `tools/` 下按功能模块组织，每个模块有独立的 `backend/` 和 `frontend/`
- **Vite + React + TypeScript**：前端构建使用 Vite，UI 框架为 React 19，状态管理为 Zustand
- **路径别名**：`vite.config.ts` 中配置了 `@` 指向项目根目录的别名
- **Docker 部署**：通过 `docker/Dockerfile` 构建前端静态资源，`nginx.conf` 配置反向代理

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `tools/new-agents/src/` | 当前混杂的前端 + Agent 源码目录 |
| `tools/new-agents/vite.config.ts` | Vite 构建配置，含路径别名和环境变量定义 |
| `tools/new-agents/tsconfig.json` | TypeScript 配置，含路径映射 |
| `tools/new-agents/docker/Dockerfile` | Docker 构建文件，引用了前端构建路径 |
| `tools/new-agents/docker/nginx.conf` | Nginx 反向代理配置 |
| `tools/intent-tester/` | 参考的清晰分层结构 |

### Technical Decisions

- `core/` 放在 `frontend/src/core/` 内而非平级目录，避免跨包引用的构建复杂度
- 维持 `__tests__/` 命名约定（Jest/Vitest 生态标准）
- 冒烟测试（`smoke/`）跟随 Agent 核心逻辑移入 `core/__tests__/`
- 纯目录迁移 + import 路径更新，零功能变更

## Implementation Plan

### Tasks

{tasks}

### Acceptance Criteria

{acceptance_criteria}

## Additional Context

### Dependencies

- 无新增依赖，仅文件迁移和路径更新

### Testing Strategy

- 重构后运行 `npm test`（单元测试）验证
- 运行 `npm run test:smoke`（冒烟测试）验证
- 运行 `npx tsc --noEmit`（类型检查）验证
- 通过 `./scripts/deploy-dev.sh` 本地 Docker 部署后浏览器验证完整流程

### Notes

- 这是一次纯结构重构，不改变任何运行时行为
- 后续可考虑进一步拆分 `chatService.ts` 的职责（UI Hook vs Agent 控制流）
