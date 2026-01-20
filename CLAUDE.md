# AI4SE 项目上下文记忆 (ACE)

## 项目背景

### 领域知识

- **项目核心**: 用于 AI 驱动的软件工程工具的 Python/TypeScript 单体仓库 (Monorepo)。
- **关键组件**:
    - **intent-tester**: 集成 MidSceneJS 的意图测试框架 (端口 5001)。
    - **ai-agents**: 基于 LangGraph 的 AI 助手 (Alex, Lisa)，使用 Vercel AI SDK (端口 5002)。
    - **frontend**: 基于 React + Vite + Tailwind 的共享前端。
- **环境**: 开发环境运行在 **本地 Docker 容器** 中。
- **用户画像**: 使用 AI 助手进行需求分析和测试生成的开发人员及 QA 工程师。

### 架构决策

- **模块化单体**: 核心业务逻辑位于 `tools/` 模块中；共享代码位于 `tools/shared`。
- **后端技术栈**: Flask + SQLAlchemy + LangGraph。
- **前端技术栈**: React + Vite + Vercel AI SDK (已从 `@assistant-ui/react` 迁移)。
- **数据流**: 使用 Vercel AI SDK Data Stream Protocol (Server-Sent Events) 实现实时 Agent 响应。

---

## 代码质量标准

### 死代码清理 (Dead Code)

**背景**: 当重构或替换库时（例如从 `@assistant-ui/react` 迁移）。

**模式**: 激进地删除不再使用的组件及其测试。
- **规则**: 如果组件不再被导入，立即删除，**不要注释掉**。
- **验证**: 在删除前运行 `grep_search` 确认零引用。
- **示例**:
  ```bash
  # 删除前检查
  grep -r "CustomAssistantMessage" tools/ai-agents/frontend
  # 如果结果为 0，删除组件和测试
  rm CustomAssistantMessage.tsx CustomAssistantMessage.test.tsx
  ```

### 遗留特性清理 (Feature Deprecation)

**背景**: 完全移除废弃的智能体或主要特性（如 "Alex" 智能体）。

**模式**: 深度清理所有相关层级，不仅仅是入口点。
- **Schema**: 删除 Pydantic 模型 (`AlexStructuredOutput`)。
- **Docstrings**: 更新服务级文档字符串 (`service.py`) 以反映当前支持的特性，移除过时提及。
- **Tests**: 删除针对已移除特性的特定测试文件，防止 CI 失败。
- **验证**: 必须搜索（grep）特性名称的所有变体，确保无残留引用。

### 单一事实来源 (SSOT)

**背景**: 配置 Assistant 能力（例如欢迎建议），这些配置同时存在于后端 Prompt 和前端 UI 中。

**反模式**: 在前端硬编码重复后端的逻辑配置。
- **风险**: 前端 `LISA_SUGGESTIONS` 与后端 Prompt 选项不一致。
- **缓解措施**: MVP 阶段记录此重复。生产阶段应通过 API 暴露配置。

---

## 开发指南

### 本地 Docker 环境

**背景**: 在本地运行和测试应用程序。

**硬性规则**: **永远不要假设本地源码修改会立即生效。**
- **事实**: 测试环境运行在 Docker 容器内部。
- **行动**: 必须运行 `./scripts/dev/deploy-dev.sh <component>` 将更改应用到容器中。
- **禁止**: 不要尝试在宿主机直接运行 `npm run dev` 或 `flask run` 进行集成测试。

### 测试修复

**背景**: 依赖变更后修复前端测试。

**模式**: 更新 Mock 以匹配新的库 API。
- **示例**: 当用 `react-markdown` 替换 `@assistant-ui/react-markdown` 时：
  ```typescript
  # 在测试设置中更新 Mock
  vi.mock('react-markdown', () => ({
    default: ({ content }: any) => <div data-testid="markdown-primitive">{content}</div>
  }));
  ```

### Prompt 维护 (Prompt Maintenance)

**背景**: 随着工作流机制变更（如从 JSON-in-Markdown 转为 Tool Calls），旧的 Prompt 辅助函数会过时。

**模式**: 立即移除不再使用的 Prompt 构建函数。
- **规则**: 如果一个 Prompt 辅助函数（如 `get_plan_sync_instruction`）的逻辑已废弃，不要保留它“以防万一”。
- **风险**: 保留废弃的 Prompt 逻辑会导致 LLM 接收矛盾的指令（如同时要求 Tool Call 和 JSON 文本）。
- **行动**: 删除函数定义、文件 (`workflow_engine.py`) 以及所有 Prompt 模板中的引用。

---

## 验证检查清单

### 预计算参考
- [ ] **环境检查**: 我是否在本地 Docker 中运行？如果是，我部署了吗？
- [ ] **库检查**: 我是否验证了导入的库在 `package.json` 中实际存在？
- [ ] **SSOT 检查**: 我是否在前端和后端之间重复了逻辑（如 Prompt 或配置）？

### 实施后
- [ ] **死代码**: 我是否删除了不再使用的文件？
- [ ] **全部清理**: 如果移除了特性，是否更新了所有相关的 Docstrings 和 Schemas？
- [ ] **测试对齐**: 我是否更新了测试以反映 API 变更（例如 Prop 名称）？
