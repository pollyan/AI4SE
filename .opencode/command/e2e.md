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

### 5. 清理浏览器 (重要!)

**测试完成后必须关闭浏览器页面**，避免下次测试启动失败：

```
chrome-devtools_close_page
```

如果不清理，下次运行 `/e2e` 时会报错：
> "The browser is already running... Use --isolated to run multiple browser instances."

**故障恢复**（如果忘记清理导致阻塞）：
```bash
# 移除锁文件
rm -f ~/.cache/chrome-devtools-mcp/chrome-profile/SingletonLock
```

### 6. 输出报告

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
- **测试结束后务必调用 `chrome-devtools_close_page` 清理浏览器**

## 相关文件

- 场景定义: `tests/e2e/scenarios/*.md`
- 命令定义: `.opencode/command/e2e.md` (本文件)
