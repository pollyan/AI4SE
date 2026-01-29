# E2E 测试

本目录包含 AI4SE 智能体的端到端测试。

## 目录结构

```
tests/e2e/
├── scenarios/              # 测试场景定义
│   ├── lisa-smoke.md       # Lisa 冒烟测试 (P0)
│   ├── lisa-artifacts.md   # Lisa 产出物测试 (P0)
│   └── alex-smoke.md       # Alex 冒烟测试 (未来)
└── README.md               # 本文件
```

## 运行测试

```bash
# 在 opencode/claude 中执行
/e2e           # 运行默认测试 (lisa-smoke)
/e2e lisa      # 运行 Lisa 所有测试
/e2e all       # 运行所有测试
```

## 前置条件

1. Docker 环境运行中 (`docker ps | grep ai4se-agents`)
2. Chrome 浏览器已连接 DevTools MCP

## 场景索引

### Lisa 智能体

| 场景文件 | 优先级 | 测试内容 | 用例数 |
|----------|--------|----------|--------|
| `lisa-smoke.md` | P0 | 基本对话流程、多轮对话 | 2 |
| `lisa-artifacts.md` | P0 | 产出物生成、Mermaid渲染、阶段流转 | 8 |

### 待开发场景

| 场景文件 | 优先级 | 测试内容 |
|----------|--------|----------|
| `lisa-workflow-entry.md` | P0 | 工作流入口 A-F、意图路由 |
| `lisa-ui-interaction.md` | P1 | 进度条点击、TOC导航、附件上传 |
| `lisa-config.md` | P2 | AI配置管理 CRUD |
| `lisa-error-handling.md` | P1 | 初始化失败、网络错误恢复 |
| `alex-smoke.md` | P1 | Alex 需求分析师基本流程 |

## 场景文件格式

每个场景文件使用 Markdown 格式定义：

```markdown
# 场景标题

## 测试目标
简要描述测试目的

## 前置条件
- [ ] 条件 1
- [ ] 条件 2

---

## TC-XXX: 测试用例名称

**优先级:** P0/P1/P2

**目标:** 一句话描述

### 测试步骤
1. 步骤描述（自然语言）
2. ...

### 验证项
- [ ] 验证点 1
- [ ] 验证点 2
```

AI 会根据场景描述动态执行浏览器操作。

## 技术说明

### 使用的工具

- **Chrome DevTools MCP**: 浏览器自动化
- **真实 LLM API**: 测试使用真实 AI 响应

### 产出物 Key 参考

| 阶段 | Key | 说明 |
|------|-----|------|
| clarify | `test_design_requirements` | 需求分析文档 |
| strategy | `test_design_strategy` | 测试策略蓝图 |
| cases | `test_design_cases` | 测试用例集 |
| delivery | `test_design_final` | 测试设计文档 |

### UI 元素选择器

| 元素 | 选择器/定位方式 |
|------|-----------------|
| 产出物面板 | `div.prose.prose-sm` |
| 工作流进度条 | `WorkflowProgress` 组件 |
| TOC 导航项 | 包含 `truncate` 类名的 span |
| Mermaid 图表 | ID: `mermaid-diagram-{n}` |
