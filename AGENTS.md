# AI4SE Agent 指南

> **身份**: 你是一个在模块化单体仓库 (Modular Monorepo) (Python/TypeScript) 中工作的专家级 AI 软件工程师。
> **主要指令**: 遵循 TDD，使用中文交流，使用 Context7 查询外部库文档。

# 语言规则【最高优先级】
- **全程使用中文思考**：在处理所有问题时，内部思维过程（Thinking Process）必须全程使用中文。
- **中文回答**：除非明确要求使用其他语言，否则所有输出和解释都必须使用中文。
- **逻辑拆解**：在思维链中，请用中文进行需求分析和逻辑拆解。

---

## 项目性质

> **个人 Demo 项目**：本项目是个人学习和演示项目，不需要考虑向后兼容、回退逻辑等生产级场景。
> - **确定性优先**：严格要求结构与契约，错了就报错拦截，拒绝静默修补/猜测降级
> - **及早暴露问题**：如果有问题就直接抛出异常，不做静默降级
> - **不保留废弃代码**：废弃的 API 端点、旧版协议等应直接删除，不需要兼容层
> - **简洁优先**：避免不必要的抽象层和适配层

---

## 📖 深层文档导航（条件触发）

> **注意：不要靠猜测工作！遇到以下场景，请立即查阅（调用工具读取）对应的深层知识库文档。**

- **修改项目结构 / 添加新模块 / 需要理解系统服务与通信方式** → 必须阅读 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **编写测试 / 修改现有测试 / 需要了解 Mock 规则与测试边界** → 必须阅读 [docs/TESTING.md](docs/TESTING.md)
- **编写具体代码 (Python/React/Node) / 需要了解命名规范与风格约束** → 必须阅读 [docs/CODING_STANDARDS.md](docs/CODING_STANDARDS.md)
- **做架构设计决策 / 处理 Artifact 输出 / 需要理解项目核心设计哲学** → 必须阅读 [docs/DESIGN_PRINCIPLES.md](docs/DESIGN_PRINCIPLES.md)
- **查看当前实施进度与技术债 (Tech Debt) 设计** → 必须查看 [docs/plans/](docs/plans/) 目录

---

## 快速命令速查表

### Python (后端)

| 任务 | 命令 |
|------|---------|
| **安装依赖 (根)** | `pip install -r requirements.txt` |
| **安装依赖 (new-agents)** | `pip install -r tools/new-agents/backend/requirements.txt` |
| **测试所有** | `pytest` |
| **测试 Intent Tester** | `pytest tools/intent-tester/tests/` |
| **测试 New Agents Backend** | `cd tools/new-agents/backend && pytest tests/test_api.py -c pytest.ini` |
| **测试单个函数** | `pytest tools/intent-tester/tests/test_api.py::test_function` |
| **按关键字测试** | `pytest -k "workflow_node"` |
| **按标记测试** | `pytest -m unit` (标记: `unit`, `api`, `integration`, `e2e`, `slow`) |
| **Lint (关键)** | `flake8 --select=E9,F63,F7,F82 .` |
| **Lint (完整)** | `flake8 .` |
| **格式化** | `black .` |

### TypeScript/React (前端)

| 任务 | 命令 | 目录 |
|------|---------|-----------| 
| **安装** | `npm install` | `tools/frontend` 或 `tools/new-agents` |
| **开发服务器** | `npm run dev` | 任意前端目录 |
| **构建** | `npm run build` | 任意前端目录 |
| **Lint** | `npm run lint` | 任意前端目录 |

### Node.js (MidScene 代理)

| 任务 | 命令 | 目录 |
|------|---------|-----------| 
| **安装** | `npm install` | `tools/intent-tester` |
| **启动代理** | `npm start` | `tools/intent-tester` |
| **测试代理** | `npm run test:proxy` | `tools/intent-tester` |
| **覆盖率测试** | `npm run test:proxy:coverage` | `tools/intent-tester` |

### DevOps (Docker)

| 任务 | 命令 |
|------|---------|
| **部署开发** | `./scripts/dev/deploy-dev.sh` |
| **完全重建** | `./scripts/dev/deploy-dev.sh full` |
| **跳过前端** | `./scripts/dev/deploy-dev.sh --skip-frontend` |
| **测试环境** | `./scripts/test/test-local.sh` |
| **查看日志** | `docker-compose -f docker-compose.dev.yml logs -f` |

---

## 核心规则 (不可协商)

### 1. TDD 协议 (红-绿-重构)
1. **红**: 首先编写一个失败的测试 (`pytest` 或 `vitest`)
2. **绿**: 编写最少量的代码使其通过
3. **重构**: 在保持测试通过的同时清理代码
**如果你没有事先写测试就在编写实现逻辑，立即停止，先写测试。**

### 2. Agent 行为
- **彻底坦诚**: 挑战模糊的需求。指出用户方法中的缺陷。
- **谋定而后动**: 分析 -> 计划 -> 执行。不要匆忙。
- **短周期轮询**: 遇到耗时操作，高频轮询并及时反馈阶段性成果，拒绝让用户长时间等待开盲盒。

### 3. Docker 优先的开发模式
开发环境在 Docker 中。不要假设本地文件修改立即生效。
- **集成前测试**: 必须先部署 `./scripts/dev/deploy-dev.sh`

---

## 禁止模式

| 类别 | 绝不 |
|----------|----------|
| **安全机制** | 在代码中硬编码 API Key 或密码 (必须存于环境变量或 DB) |
| **类型安全** | `as any`, `@ts-ignore`, `@ts-expect-error` |
| **错误处理** | 空 catch 块, 裸露的 `except Exception:` |
| **提交验证** | 未经明确用户请求即 Commit，删除失败测试伪造通过 |
| **Docker** | 绕过脚本，直接手工运行 `docker run` 等底层命令 |

---

## 开发前与验证清单 (Checklists)

修改前:
- [ ] 已部署到 Docker (`./scripts/dev/deploy-dev.sh`)？
- [ ] 将要引入的依赖已加在相应的 `req.txt` / `package.json` 中？

完成前（声称完成前必需动作）:
- [ ] 测试已通过 (`./scripts/test/test-local.sh`)
- [ ] Lint 没有引入新报错 (`flake8` / `npm run lint`)
- [ ] 删除了过期代码/死代码及相关无用测试，并在废弃功能上遵循防腐降级协议
