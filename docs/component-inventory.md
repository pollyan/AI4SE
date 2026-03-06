# 组件清单

> 生成日期: 2026-03-06 | 扫描级别: Deep Scan

## 统一门户前端 (tools/frontend)

### 页面组件

| 组件 | 路径 | 说明 |
|------|------|------|
| `Home` | `pages/Home/index.tsx` | 首页容器 |
| `HeroSection` | `pages/Home/HeroSection.tsx` | Hero 横幅 |
| `ModulesSection` | `pages/Home/ModulesSection.tsx` | 模块介绍卡片 |
| `VideoSection` | `pages/Home/VideoSection.tsx` | 视频演示区 |
| `UseCasesSection` | `pages/Home/UseCasesSection.tsx` | 使用场景展示 |
| `QuickLinksSection` | `pages/Home/QuickLinksSection.tsx` | 快速链接导航 |
| `Profile` | `pages/Profile/index.tsx` | 个人中心 |

### 布局组件

| 组件 | 路径 | 说明 |
|------|------|------|
| `Layout` | `components/Layout.tsx` | 通用布局 |
| `CompactLayout` | `components/CompactLayout.tsx` | 紧凑布局（含移动端菜单） |
| `Navbar` | `components/Navbar.tsx` | 顶部导航栏 |
| `Footer` | `components/Footer.tsx` | 页脚 |

---

## AI 智能体前端 (tools/new-agents/frontend)

### 页面组件

| 组件 | 路径 | 路由 | 说明 |
|------|------|------|------|
| `AgentSelect` | `pages/AgentSelect.tsx` | `/` | 智能体选择页（Lisa/Alex 卡片） |
| `WorkflowSelect` | `pages/WorkflowSelect.tsx` | `/workflows/:agentId` | 工作流选择列表 |
| `Workspace` | `pages/Workspace.tsx` | `/workspace/:a/:w` | 主工作台（对话+产出物） |

### 核心组件

| 组件 | 路径 | 类别 | 说明 |
|------|------|------|------|
| `ChatPane` | `components/ChatPane.tsx` | 交互 | 左侧对话面板（消息列表、输入框、附件） |
| `ArtifactPane` | `components/ArtifactPane.tsx` | 展示 | 右侧产出物面板（Markdown 预览、版本历史） |
| `Header` | `components/Header.tsx` | 导航 | 顶部栏（返回、工作流、阶段切换、导出） |
| `SettingsModal` | `components/SettingsModal.tsx` | 配置 | 设置弹窗（API Key、Base URL、模型选择） |
| `WorkflowDropdown` | `components/WorkflowDropdown.tsx` | 导航 | 工作流切换下拉（带确认弹窗） |
| `Mermaid` | `components/Mermaid.tsx` | 渲染 | Mermaid 图表渲染（含容错与 LLM 重试） |

### 核心逻辑模块

| 模块 | 路径 | 说明 |
|------|------|------|
| `store` | `core/store.ts` | Zustand 全局状态（含 localStorage 持久化） |
| `types` | `core/types.ts` | TypeScript 类型定义 |
| `workflows` | `core/workflows.ts` | 5 个工作流定义（阶段、prompt 模板） |
| `llm` | `core/llm.ts` | LLM 双模式调用封装 |
| `buildSystemPrompt` | `core/buildSystemPrompt.ts` | 系统提示词动态构建 |

### 服务模块

| 模块 | 路径 | 说明 |
|------|------|------|
| `chatService` | `services/chatService.ts` | `useChatService` Hook：发送、重试、停止 |
| `mermaidRetryService` | `services/mermaidRetryService.ts` | Mermaid 语法错误 LLM 修复 |

### 工具模块

| 模块 | 路径 | 说明 |
|------|------|------|
| `llmParser` | `core/utils/llmParser.ts` | 解析流式输出中的 `<CHAT>`, `<ARTIFACT>`, `<ACTION>` |
| `mermaidSanitizer` | `core/utils/mermaidSanitizer.ts` | Mermaid 代码清洗 |
| `markdownUtils` | `core/utils/markdownUtils.ts` | Markdown 预处理 |
| `llmClient` | `core/utils/llmClient.ts` | LLM 客户端封装 |

### 配置模块

| 模块 | 路径 | 说明 |
|------|------|------|
| `agents` | `core/config/agents.ts` | 智能体定义（Alex, Lisa 的名称、头像、描述） |
| `agentWorkflows` | `core/config/agentWorkflows.ts` | 各智能体的工作流列表与状态 |

### 提示词模块

| 目录 | 工作流 | 阶段 |
|------|--------|------|
| `prompts/personas/` | - | `lisa.ts`, `alex.ts`（智能体人设） |
| `prompts/test_design/` | 测试设计 | clarify, strategy, cases, delivery |
| `prompts/req_review/` | 需求评审 | review, report |
| `prompts/incident_review/` | 故障复盘 | timeline, root_cause, improvement |
| `prompts/idea_brainstorm/` | 创意风暴 | define, diverge, converge, concept |
| `prompts/value_discovery/` | 价值发现 | elevator, persona, journey, blueprint |

---

## Intent-Tester 前端 (tools/intent-tester/frontend)

### Jinja2 模板

| 模板 | 说明 |
|------|------|
| `base_layout.html` | 基础布局（导航、页脚、全局样式） |
| `index.html` | 首页 |
| `testcases.html` | 测试用例列表与管理 |
| `testcase_edit.html` | 测试用例编辑 |
| `execution.html` | 执行控制台（双栏布局、日志、截图） |
| `step_editor.html` | 步骤编辑器 |
| `local_proxy.html` | 本地代理配置 |

### JavaScript 模块

| 模块 | 路径 | 说明 |
|------|------|------|
| `ApplicationCore` | `static/js/core/` | 应用核心框架 |
| `StateManager` | `static/js/core/` | 状态管理 |
| `EventBus` | `static/js/core/` | 事件总线 |
| `ComponentFactory` | `static/js/core/` | 组件工厂 |
| `EnhancedStepEditor` | `static/js/components/` | 增强步骤编辑器 |
| `VariableContextService` | `static/js/services/` | 变量上下文服务 |
| `variableValidation` | `static/js/utils/` | 变量验证 |
| `smart-variable-input` | `static/js/` | 智能变量输入 |

### UI 特点

- 自定义 CSS（无 Bootstrap/Tailwind）
- 极简白底设计
- 响应式布局
- 外部依赖通过 CDN：Axios、Socket.IO

---

## Intent-Tester Python 框架 (midscene_framework)

| 模块 | 路径 | 说明 |
|------|------|------|
| `config` | `midscene_framework/config.py` | 框架配置 |
| `validators` | `midscene_framework/validators.py` | 数据验证器 |
| `data_extractor` | `midscene_framework/data_extractor.py` | 数据提取 |
| `retry_handler` | `midscene_framework/retry_handler.py` | 重试处理 |
| `mock_service` | `midscene_framework/mock_service.py` | Mock 服务（测试用） |
