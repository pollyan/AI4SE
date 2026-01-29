# E2E Testing Framework Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 创建 `/e2e` 命令，使用 Chrome DevTools MCP 在本地 Docker 环境中对 AI 智能体进行端到端测试。

**Architecture:** 
- `/e2e` slash command 作为入口，调用 e2e-runner agent
- Agent 读取 `tests/e2e/scenarios/` 下的场景定义文件
- 使用 Chrome DevTools MCP 执行浏览器操作，验证用户流程
- 场景文件定义"测什么"，AI 动态决定"怎么操作"

**Tech Stack:** OpenCode commands, Chrome DevTools MCP, Markdown 场景定义

---

## 需求摘要

| 项目 | 说明 |
|------|------|
| **目标** | 验证 Lisa 智能体在 Docker 环境中的完整用户流程 |
| **测试方式** | 浏览器 E2E，使用 Chrome DevTools MCP |
| **触发方式** | `/e2e` 或 `/e2e lisa` 命令 |
| **LLM** | 使用本地配置的真实 LLM API |
| **CI** | 暂不集成，仅手动触发 |

---

## Task 1: 创建 `/e2e` 命令定义

**Files:**
- Create: `.opencode/command/e2e.md`

**Step 1: 创建命令文件**

```markdown
---
description: Run end-to-end tests for AI4SE using Chrome DevTools MCP. Validates complete user journeys in local Docker environment.
---

# E2E Testing Command

运行 AI4SE 智能体的端到端测试。

## 使用方式

| 命令 | 说明 |
|------|------|
| `/e2e` | 运行默认冒烟测试 (Lisa) |
| `/e2e lisa` | 运行 Lisa 智能体 E2E 测试 |
| `/e2e alex` | 运行 Alex 智能体 E2E 测试 (未来) |
| `/e2e all` | 运行所有 E2E 测试 |

## 前置条件

1. Docker 环境已启动: `./scripts/dev/deploy-dev.sh`
2. Chrome 浏览器已打开并连接到 DevTools MCP
3. 服务健康: http://localhost/ai-agents 可访问

## 执行流程

当用户调用 `/e2e` 时，你需要：

### 1. 环境检查

使用 Bash 工具验证 Docker 服务运行状态：

```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep ai4se
```

预期看到 `ai4se-agents`, `ai4se-gateway` 等容器运行中。

如果服务未运行，提示用户执行：
```bash
./scripts/dev/deploy-dev.sh
```

### 2. 读取测试场景

从 `tests/e2e/scenarios/` 目录读取对应的场景文件：
- `/e2e` 或 `/e2e lisa` → 读取 `tests/e2e/scenarios/lisa-smoke.md`
- `/e2e alex` → 读取 `tests/e2e/scenarios/alex-smoke.md`
- `/e2e all` → 依次读取所有场景文件

### 3. 执行测试

使用 Chrome DevTools MCP 工具执行场景中定义的步骤：

1. `chrome-devtools_new_page` - 打开目标 URL
2. `chrome-devtools_take_snapshot` - 获取页面元素快照
3. `chrome-devtools_click` - 点击元素
4. `chrome-devtools_fill` - 填写输入框
5. `chrome-devtools_wait_for` - 等待内容出现
6. `chrome-devtools_take_screenshot` - 截图记录

### 4. 验证结果

根据场景文件中的验证项，检查：
- 页面是否正常加载
- 预期内容是否出现
- 没有 JavaScript 错误

### 5. 输出报告

```
╔══════════════════════════════════════════════════════════════╗
║                    E2E 测试结果                               ║
╠══════════════════════════════════════════════════════════════╣
║ 场景:       Lisa 冒烟测试                                     ║
║ 状态:       ✅ 通过 / ❌ 失败                                 ║
║ 用时:       X 秒                                              ║
╠══════════════════════════════════════════════════════════════╣
║ 测试步骤:                                                     ║
║   ✅ 打开智能体页面                                           ║
║   ✅ 选择 Lisa 智能体                                         ║
║   ✅ 发送测试消息                                             ║
║   ✅ 收到 AI 回复                                             ║
╚══════════════════════════════════════════════════════════════╝
```

## 注意事项

- 测试使用真实 LLM API，会消耗 API 额度
- 每个测试场景约需 30-60 秒完成
- 如遇到超时，可能是 LLM 响应慢，重试即可
- 截图保存在当前工作目录

## 相关文件

- 场景定义: `tests/e2e/scenarios/*.md`
- 命令定义: `.opencode/command/e2e.md` (本文件)
```

**Step 2: 验证文件创建成功**

Run: `cat .opencode/command/e2e.md | head -20`

Expected: 显示命令文件头部内容

**Step 3: Commit**

```bash
git add .opencode/command/e2e.md
git commit -m "feat(e2e): add /e2e slash command definition"
```

---

## Task 2: 创建测试场景目录结构

**Files:**
- Create: `tests/e2e/scenarios/.gitkeep`
- Create: `tests/e2e/README.md`

**Step 1: 创建目录结构**

```bash
mkdir -p tests/e2e/scenarios
```

**Step 2: 创建 README**

```markdown
# E2E 测试

本目录包含 AI4SE 智能体的端到端测试。

## 目录结构

```
tests/e2e/
├── scenarios/          # 测试场景定义
│   ├── lisa-smoke.md   # Lisa 冒烟测试
│   └── alex-smoke.md   # Alex 冒烟测试 (未来)
└── README.md           # 本文件
```

## 运行测试

```bash
# 在 opencode/claude 中执行
/e2e           # 运行默认测试
/e2e lisa      # 运行 Lisa 测试
/e2e all       # 运行所有测试
```

## 前置条件

1. Docker 环境运行中
2. Chrome 浏览器已连接 DevTools MCP

## 场景文件格式

每个场景文件使用 Markdown 格式定义：
- 前置条件
- 测试步骤 (自然语言描述)
- 验证项

AI 会根据场景描述动态执行浏览器操作。
```

**Step 3: 创建 .gitkeep**

```bash
touch tests/e2e/scenarios/.gitkeep
```

**Step 4: Commit**

```bash
git add tests/e2e/
git commit -m "feat(e2e): create e2e test directory structure"
```

---

## Task 3: 创建 Lisa 冒烟测试场景

**Files:**
- Create: `tests/e2e/scenarios/lisa-smoke.md`

**Step 1: 创建场景文件**

```markdown
# Lisa 智能体冒烟测试

## 测试目标

验证 Lisa 测试专家智能体的基本对话功能在 Docker 环境中正常工作。

## 前置条件

- [ ] Docker 环境已启动 (`docker ps | grep ai4se-agents`)
- [ ] 服务健康 (http://localhost/ai-agents 可访问)
- [ ] Chrome DevTools MCP 已连接

---

## TC-001: 基本对话流程

**优先级:** P0 (核心路径)

**目标:** 验证用户可以与 Lisa 完成一轮完整对话

### 测试步骤

1. **打开智能体页面**
   - 导航到 `http://localhost/ai-agents`
   - 等待页面加载完成

2. **选择 Lisa 智能体**
   - 在页面中找到 Lisa 智能体卡片
   - 点击进入对话界面

3. **发送测试消息**
   - 找到消息输入框
   - 输入: `你好，请帮我分析一下登录功能的测试点`
   - 点击发送按钮

4. **等待 AI 回复**
   - 等待页面显示 AI 回复内容
   - 超时时间: 60 秒

### 验证项

- [ ] 页面正常加载，无 JavaScript 错误
- [ ] 成功进入 Lisa 对话界面
- [ ] 消息成功发送（输入框清空）
- [ ] AI 回复出现在对话区域
- [ ] 回复内容非空且有意义

### 成功标准

所有验证项通过即为测试通过。

---

## TC-002: 多轮对话 (可选)

**优先级:** P1

**目标:** 验证多轮对话的上下文保持

### 测试步骤

1. 完成 TC-001 后继续
2. 发送追问: `请详细说明边界值测试应该怎么设计`
3. 等待回复

### 验证项

- [ ] 第二轮消息成功发送
- [ ] AI 回复与之前上下文相关（提到登录、测试点等）

---

## 故障排查

### 页面无法加载
- 检查 Docker 服务: `docker ps`
- 检查 nginx 网关: `curl http://localhost/health`

### 发送消息后无响应
- 检查后端服务: `docker logs ai4se-agents --tail 50`
- 检查 LLM API Key 配置

### 超时
- LLM 响应可能较慢，增加等待时间
- 检查网络连接
```

**Step 2: 验证文件创建成功**

Run: `cat tests/e2e/scenarios/lisa-smoke.md | head -30`

Expected: 显示场景文件头部内容

**Step 3: Commit**

```bash
git add tests/e2e/scenarios/lisa-smoke.md
git commit -m "feat(e2e): add Lisa smoke test scenario"
```

---

## Task 4: 更新 AGENTS.md 添加 E2E 测试说明

**Files:**
- Modify: `AGENTS.md`

**Step 1: 在快速命令速查表后添加 E2E 测试部分**

在 `### DevOps (Docker)` 表格后，添加：

```markdown
### E2E 测试 (浏览器)

| 任务 | 命令 | 说明 |
|------|------|------|
| **运行冒烟测试** | `/e2e` | 使用 Chrome DevTools MCP 测试 Lisa |
| **测试 Lisa** | `/e2e lisa` | Lisa 智能体完整测试 |
| **测试全部** | `/e2e all` | 运行所有 E2E 测试 |

> **前置条件**: Docker 环境运行中 + Chrome DevTools MCP 连接
```

**Step 2: 在测试标记部分添加 e2e 说明**

确认 `pytest.ini` 中已有 `e2e` 标记定义 (已确认存在)。

**Step 3: Commit**

```bash
git add AGENTS.md
git commit -m "docs: add E2E testing section to AGENTS.md"
```

---

## Task 5: 手动验证 /e2e 命令

**无需代码修改，验证流程**

**Step 1: 确保 Docker 环境运行**

```bash
./scripts/dev/deploy-dev.sh
```

**Step 2: 在 opencode 中测试命令**

输入: `/e2e`

**Step 3: 验证 AI 执行流程**

观察 AI 是否：
1. 读取了场景文件
2. 使用 Chrome DevTools MCP 打开浏览器
3. 执行了测试步骤
4. 输出了测试报告

**Step 4: 根据实际执行结果调整**

如果发现问题，迭代修改：
- 命令定义 `.opencode/command/e2e.md`
- 场景文件 `tests/e2e/scenarios/lisa-smoke.md`

---

## 完成标准

- [ ] `/e2e` 命令可被识别和执行
- [ ] AI 能读取场景文件
- [ ] AI 能使用 Chrome DevTools MCP 执行浏览器操作
- [ ] 测试成功时输出通过报告
- [ ] 测试失败时有明确的错误信息

---

## 未来扩展

1. **添加 Alex 测试场景**: `tests/e2e/scenarios/alex-smoke.md`
2. **添加错误场景测试**: 验证错误处理
3. **添加性能基准**: 记录响应时间
4. **CI 集成**: GitHub Actions 中运行 (需要 headless 浏览器)
