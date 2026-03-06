---
title: '智能体测试策略改进计划'
slug: 'agent-test-strategy-improvement'
created: '2026-03-06'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4, 8, 9]
tech_stack:
  - pytest
  - pytest-asyncio
  - pytest-mock
  - pytest-cov
  - Vitest
  - Playwright
  - Flask test client
files_to_modify:
  # 服务层测试文件（新建）
  - 'tools/intent-tester/tests/services/test_database_service.py'
  - 'tools/intent-tester/tests/services/test_variable_resolver_service.py'
  - 'tools/intent-tester/tests/services/test_execution_service.py'
  - 'tools/intent-tester/tests/services/test_ai_step_executor.py'
  # new-agents 后端测试扩展
  - 'tools/new-agents/backend/tests/test_chat_history.py'
  - 'tools/new-agents/backend/tests/test_error_handling.py'
  # E2E 自动化测试（新建）
  - 'tests/e2e/test_lisa_smoke.py'
  - 'tests/e2e/test_alex_smoke.py'
  - 'tests/e2e/conftest.py'
  # 前端组件测试（新建）
  - 'tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx'
  - 'tools/new-agents/frontend/src/components/__tests__/SettingsModal.test.tsx'
  # CI/CD 配置
  - '.github/workflows/deploy.yml'
  - 'pytest.ini'
code_patterns:
  - '服务层测试: Mock db.session, Model.query'
  - 'API测试: Flask test client + fixture工厂'
  - '异步测试: pytest-asyncio (strict mode) + asyncio.to_thread mock'
  - 'E2E测试: Playwright + Docker环境'
  - '数据库隔离: 事务回滚 (db.session.begin_nested())'
test_patterns:
  - 'Given/When/Then 格式验收标准'
  - '工厂模式 fixture (create_test_testcase, create_execution_history)'
  - 'assert_api_response 响应断言助手'
  - 'LLM Judge 模式评估输出质量'
---

# Tech-Spec: 智能体测试策略改进计划

**Created:** 2026-03-06

## Overview

### Problem Statement

当前 AI4SE 智能体项目测试体系存在明显短板：
- **后端服务层测试覆盖率仅约 20%**（5个服务文件仅1个有测试）
- **new-agents 后端测试覆盖极低**，仅覆盖基础 API 端点（健康检查、配置、聊天流）
- **E2E 自动化测试缺失**，仅有手动测试场景文档（lisa-smoke.md, lisa-artifacts.md）
- **缺乏测试覆盖率监控和阈值控制**

具体缺失的服务层测试：
- `database_service.py` - 数据库服务
- `variable_resolver_service.py` - 变量解析服务
- `execution_service.py` - 执行服务
- `ai_step_executor.py` - AI 步骤执行器

### Solution

分三个优先级阶段系统化提升测试覆盖率：

**Phase 1 (高优先级):**
1. 补充后端服务层单元测试（目标覆盖率 70%）
2. 建立 Playwright E2E 自动化测试体系
3. 扩展 new-agents 后端测试
4. 补充前端核心组件测试

**Phase 2 (中优先级):**
1. 补充 MidScene 集成测试
2. 配置 CI/CD 覆盖率监控与阈值

**Phase 3 (低优先级):**
1. 性能测试（并发请求、SSE 稳定性）
2. 安全测试（API Key 存储、XSS 防护）

### Scope

**In Scope:**
- 后端服务层单元测试（database_service, variable_resolver_service, execution_service, ai_step_executor）
- new-agents 后端测试扩展（对话历史、错误处理）
- Playwright E2E 自动化测试脚本（Lisa、Alex 智能体核心流程）
- CI/CD 覆盖率监控配置（pytest-cov, vitest coverage）
- 前端核心组件测试（ChatPane, SettingsModal）

**Out of Scope:**
- 性能压力测试
- 安全渗透测试
- 第三方库测试
- 前端 UI 视觉回归测试

## Context for Development

### Codebase Patterns

**现有测试模式:**
- Python 测试使用 pytest + pytest-asyncio + pytest-mock
- 前端测试使用 Vitest + @testing-library/react
- API 测试通过 Flask test client 进行
- Fixture 设计采用工厂模式（conftest.py）
- 冒烟测试引入 LLM Judge 模式评估输出质量

**服务层代码结构:**
```
tools/intent-tester/backend/services/
├── database_service.py       # DatabaseService 类 - CRUD 操作
├── variable_resolver_service.py  # VariableManager + Factory - 变量管理
├── execution_service.py      # ExecutionService - 异步测试执行
├── ai_step_executor.py       # AIStepExecutor - AI 步骤执行
└── query_optimizer.py        # QueryOptimizer - 已有测试
```

**服务间依赖关系:**
```
ExecutionService
    ├── DatabaseService (数据访问)
    ├── VariableResolverService (变量管理)
    └── AIService (AI 调用)

AIStepExecutor
    ├── VariableManager (变量管理)
    ├── MidSceneDataExtractor (外部库)
    └── StepExecution Model (数据库记录)
```

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `tools/intent-tester/tests/conftest.py` | pytest fixture 设计参考 |
| `tools/intent-tester/tests/api/test_execution_api.py` | API 测试模式参考 |
| `tools/intent-tester/tests/services/test_query_optimizer.py` | 服务层测试模式参考 |
| `tools/intent-tester/backend/services/database_service.py` | 待测试：CRUD 操作 |
| `tools/intent-tester/backend/services/variable_resolver_service.py` | 待测试：变量管理 |
| `tools/intent-tester/backend/services/execution_service.py` | 待测试：异步执行 |
| `tools/intent-tester/backend/services/ai_step_executor.py` | 待测试：AI 步骤执行 |
| `tools/new-agents/backend/app.py` | 待测试：聊天代理、配置管理 |
| `tools/new-agents/frontend/src/core/__tests__/llm.test.ts` | 前端 LLM 模块测试参考 |
| `tools/new-agents/frontend/src/core/__tests__/smoke/workflow.smoke.test.ts` | LLM Judge 模式参考 |
| `tests/e2e/scenarios/lisa-smoke.md` | E2E 手动场景参考 |
| `pytest.ini` | pytest 配置 |
| `.github/workflows/deploy.yml` | CI/CD 配置 |

### Technical Decisions

1. **测试框架选择:**
   - 后端继续使用 pytest 生态（pytest-asyncio 处理异步）
   - E2E 使用 Playwright（已在 requirements.txt 中配置 pytest-playwright）

2. **覆盖率目标与阈值 (F1 修复):**
   - 后端服务层: 20% → 70%
   - new-agents 后端: 30% → 60%
   - CI 阈值策略: 采用分阶段阈值
     - 初期阈值: `--cov-fail-under=50`（确保不倒退）
     - 目标阈值: `--cov-fail-under=70`（Phase 1 完成后）
   - E2E 自动化: 0 → 5 个核心场景

3. **E2E 自动化策略:**
   - 将手动场景文档转换为 Playwright 脚本
   - 优先覆盖核心对话流程
   - 需要 Docker 环境支持

4. **Mock 策略 (F9 修复):**
   - 数据库操作：Mock `db.session`, `Model.query`
   - **数据库隔离策略**: 使用 `db.session.begin_nested()` 创建保存点，测试后自动回滚，防止测试间状态污染
   - 外部服务：Mock OpenAI client, MidScene client
   - 异步操作：Mock `threading.Thread`, `asyncio.to_thread`

5. **异步测试配置 (F5 修复):**
   - pytest-asyncio 使用 `strict` 模式
   - 配置: `asyncio_mode = strict`
   - 所有异步测试必须使用 `@pytest.mark.asyncio` 装饰器

6. **测试数据策略 (F6 修复):**
   - 使用工厂模式 fixture 创建测试数据
   - 数据库测试使用事务回滚隔离
   - 不依赖外部数据，所有测试数据自包含

7. **CI/CD 覆盖率阈值:**
   - 添加 `--cov-fail-under=50` 参数（初期）
   - 生成覆盖率报告作为 CI artifact

## Implementation Plan

### Tasks

#### Phase 1: 高优先级 - 服务层单元测试

- [ ] Task 1: 创建 database_service 测试文件
  - File: `tools/intent-tester/tests/services/test_database_service.py`
  - Action: 创建新文件，测试 DatabaseService 类的所有公共方法
  - Notes:
    - Mock `db.session` 和 `TestCase.query`
    - 使用 `db.session.begin_nested()` 事务隔离
    - 测试方法: `get_testcases()`, `get_testcase_by_id()`, `create_testcase()`, `update_testcase()`, `delete_testcase()`, `create_execution()`, `get_execution_by_id()`, `get_executions()`, `stop_execution()`
    - 参考 `test_query_optimizer.py` 的测试模式
  - **示例测试用例:**
    ```python
    def test_get_testcases_with_pagination(mocker, db_session):
        # Given: 数据库中有 25 条测试用例
        for i in range(25):
            db_session.add(TestCase(name=f"test_{i}", steps=[]))
        db_session.commit()

        # When: 请求第 2 页，每页 10 条
        service = DatabaseService()
        result, total = service.get_testcases(page=2, per_page=10)

        # Then: 返回正确的分页结果
        assert len(result) == 10
        assert total == 25
    ```

- [ ] Task 2: 创建 variable_resolver_service 测试文件
  - File: `tools/intent-tester/tests/services/test_variable_resolver_service.py`
  - Action: 创建新文件，测试 VariableManager 和 VariableManagerFactory 类
  - Notes:
    - 测试方法: `store_variable()`, `get_variable()`, `list_variables()`, `clear_variables()`, `export_variables()`, `_detect_data_type()`
    - **LRU 缓存测试 (F8 修复):**
      - 缓存大小: 默认 100 条（可配置）
      - 测试缓存命中/未命中场景
      - 测试缓存满时淘汰最老条目
    - 测试线程安全性（可选，使用 pytest-xdist）
  - **示例测试用例:**
    ```python
    def test_lru_cache_eviction():
        # Given: 缓存大小为 3，已存储 3 个变量
        manager = VariableManager(cache_size=3)
        manager.store_variable("var1", "value1")
        manager.store_variable("var2", "value2")
        manager.store_variable("var3", "value3")

        # When: 存储第 4 个变量
        manager.store_variable("var4", "value4")

        # Then: 最老的变量被淘汰
        assert manager.get_variable("var1") is None
        assert manager.get_variable("var4") == "value4"
    ```

- [ ] Task 3: 创建 execution_service 测试文件
  - File: `tools/intent-tester/tests/services/test_execution_service.py`
  - Action: 创建新文件，测试 ExecutionService 类
  - Notes:
    - Mock `threading.Thread`, `socketio.emit()`, `get_ai_service()`, `get_variable_manager()`
    - 测试方法: `execute_testcase_async()`, `_execute_single_step()`, `_resolve_variables()`, `_handle_step_error()`
    - 使用 `@pytest.mark.asyncio` 装饰器（strict 模式）
  - **示例测试用例:**
    ```python
    @pytest.mark.asyncio
    async def test_execute_testcase_async_returns_execution_id(mocker):
        # Given: 一个有效的测试用例
        mock_db = mocker.patch('backend.services.execution_service.db')
        mock_db.session.add.return_value = None
        mock_db.session.commit.return_value = None

        service = ExecutionService()

        # When: 异步执行测试用例
        execution_id = await service.execute_testcase_async(testcase_id=1)

        # Then: 返回执行 ID
        assert execution_id is not None
        assert isinstance(execution_id, int)
    ```

- [ ] Task 4: 创建 ai_step_executor 测试文件
  - File: `tools/intent-tester/tests/services/test_ai_step_executor.py`
  - Action: 创建新文件，测试 AIStepExecutor 类
  - Notes:
    - Mock `MidSceneDataExtractor`, `VariableManager`, `db.session`
    - 测试方法: `execute_step()`, `_execute_ai_extraction_step()`, `_process_variable_references()`, `execute_test_case()`
    - 使用 `@pytest.mark.asyncio` 装饰器（strict 模式）

#### Phase 1: 高优先级 - E2E 自动化测试

- [ ] Task 5: 创建 E2E 测试配置文件
  - File: `tests/e2e/conftest.py`
  - Action: 创建 E2E 测试专用的 pytest fixtures
  - Notes:
    - 提供 `playwright_page` fixture
    - 提供 `docker_environment` fixture（检查 Docker 是否运行）
    - 提供 `base_url` 配置
    - **CI 跳过策略 (F3 修复):** 提供 `skip_if_no_docker` 装饰器

- [ ] Task 6: 创建 Lisa 智能体冒烟测试
  - File: `tests/e2e/test_lisa_smoke.py`
  - Action: 将 `lisa-smoke.md` 手动场景转换为 Playwright 自动化脚本
  - Notes:
    - 测试场景: TC-001 基本对话流程, TC-002 多轮对话
    - 使用 `pytest.mark.e2e` 标记
    - 超时设置: 60秒等待 AI 回复
    - **CI 策略:** 使用 `@pytest.mark.skipif(os.environ.get("CI") == "true")` 跳过

- [ ] Task 7: 创建 Alex 智能体冒烟测试
  - File: `tests/e2e/test_alex_smoke.py`
  - Action: 创建 Alex 智能体的基本对话流程测试
  - Notes:
    - 参考 Lisa 测试的结构
    - 测试需求评审工作流
    - **CI 策略:** 使用 `@pytest.mark.skipif(os.environ.get("CI") == "true")` 跳过

#### Phase 1: 高优先级 - new-agents 后端测试扩展

- [x] Task 8: 扩展 new-agents 后端测试 - 对话历史
  - File: `tools/new-agents/backend/tests/test_chat_history.py`
  - Action: 添加对话历史管理相关测试
  - Notes:
    - 测试多轮对话的消息历史注入
    - 测试会话状态管理

- [x] Task 9: 扩展 new-agents 后端测试 - 错误处理
  - File: `tools/new-agents/backend/tests/test_error_handling.py`
  - Action: 添加错误处理边界测试
  - Notes: **(F10 修复 - 扩展测试场景)**
    - 测试 OpenAI API 超时处理
    - 测试无效消息格式处理
    - 测试配置缺失场景
    - 测试网络中断处理
    - 测试 API 限流 (429) 处理
    - 测试响应格式异常处理

#### Phase 1: 高优先级 - 前端组件测试 (F4 修复)

- [x] Task 12: 创建 ChatPane 组件测试
  - File: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`
  - Action: 测试 ChatPane 组件的核心功能
  - Notes:
    - 测试消息渲染
    - 测试发送消息交互
    - 测试流式响应显示
    - Mock SSE 连接

- [x] Task 13: 创建 SettingsModal 组件测试
  - File: `tools/new-agents/frontend/src/components/__tests__/SettingsModal.test.tsx`
  - Action: 测试 SettingsModal 组件的核心功能
  - Notes:
    - 测试配置保存
    - 测试表单验证
    - 测试 API Key 输入安全性

#### Phase 2: 中优先级 - CI/CD 配置

- [x] Task 10: 配置覆盖率监控
  - File: `.github/workflows/deploy.yml`
  - Action: 在 CI 中添加覆盖率阈值检查和报告上传
  - Notes:
    - 添加 `--cov-fail-under=50` 参数（初期）
    - 上传 `coverage.xml` 作为 artifact
    - 失败时阻止部署
    - **E2E 测试跳过:** 设置环境变量 `CI=true`

- [x] Task 11: 更新 pytest 配置
  - File: `pytest.ini`
  - Action: 添加覆盖率相关配置
  - Notes:
    - 添加 `--cov=tools/intent-tester/backend` 默认参数
    - 配置覆盖率报告格式
    - **异步测试配置 (F5 修复):** 添加 `asyncio_mode = strict`
    - 配置 E2E 测试标记

### Acceptance Criteria

#### 服务层测试验收标准

- [ ] AC-1: Given 数据库中存在测试用例, When 调用 DatabaseService.get_testcases(), Then 返回正确的分页结果和总数
- [ ] AC-2: Given 数据库中不存在指定 ID, When 调用 DatabaseService.get_testcase_by_id(99999), Then 返回 None 或抛出适当异常
- [ ] AC-3: Given 有效的测试用例数据, When 调用 DatabaseService.create_testcase(), Then 成功创建并返回新记录 ID
- [ ] AC-4: Given 变量管理器已初始化, When 调用 store_variable() 后再调用 get_variable(), Then 返回正确的变量值
- [ ] AC-5: Given LRU 缓存已满 (缓存大小 100 条), When 存储第 101 个变量, Then 最老的缓存条目被移除
- [ ] AC-6: Given 测试用例已加载, When 调用 ExecutionService.execute_testcase_async(), Then 返回执行 ID 并在后台启动执行
- [ ] AC-7: Given AI 步骤执行器处于 mock 模式, When 调用 execute_step(), Then 返回模拟的执行结果

#### E2E 测试验收标准

- [ ] AC-8: Given Docker 环境已启动, When 运行 Playwright 测试, Then 成功导航到智能体页面并完成对话
- [ ] AC-9: Given Lisa 智能体页面已打开, When 发送测试消息, Then 在 60 秒内收到非空回复
- [ ] AC-10: Given 已完成第一轮对话, When 发送追问 "请继续", Then AI 回复包含上一轮对话的关键词 (F2 修复 - 可测试化)

#### 前端组件测试验收标准 (F4 修复)

- [x] AC-13: Given ChatPane 组件已渲染, When 用户输入消息并点击发送, Then 消息被添加到消息列表
- [x] AC-14: Given SettingsModal 组件已打开, When 用户输入有效配置并保存, Then 配置被正确存储

#### CI/CD 验收标准

- [x] AC-11: Given 代码提交到主分支, When CI 运行测试, Then 生成覆盖率报告并在覆盖率低于 50% 时失败
- [x] AC-12: Given 所有测试通过, When 部署流程执行, Then 成功部署到生产环境

## Additional Context

### Dependencies

**Python 测试依赖 (requirements.txt):**
- pytest >=8.4.0, <9.0.0
- pytest-asyncio 1.2.0
- pytest-cov >=3.0.0
- pytest-mock >=3.10.0
- pytest-playwright 0.7.1
- playwright 1.56.0

**前端测试依赖:**
- Vitest ^4.0.18
- @testing-library/react ^16.3.2

**任务依赖关系 (F7 修复):**
```
Task 5 (conftest.py) → Task 6, Task 7 (E2E 测试)
Task 1-4 (服务层测试) → Task 10 (覆盖率监控)
Task 8, 9 (new-agents 测试) → Task 10 (覆盖率监控) [可并行]
Task 12, 13 (前端测试) [独立，可并行]
Task 11 (pytest 配置) [独立，可最先执行]
```

### Testing Strategy

**多层次测试金字塔：**
```
        /\
       /E2E\      ← Playwright 自动化 (5 个核心场景)
      /------\
     /Integration\ ← MidScene 集成测试
    /----------\
   /  API Tests \   ← pytest + Flask test client
  /--------------\
 /  Unit Tests    \ ← pytest + Vitest (服务层 + 前端)
/------------------\
```

**测试执行命令:**
```bash
# 服务层单元测试
python -m pytest tools/intent-tester/tests/services/ -v --cov=tools/intent-tester/backend/services

# E2E 测试 (需要 Docker 环境，CI 中自动跳过)
python -m pytest tests/e2e/ -v -m e2e

# 全部测试 + 覆盖率报告
python -m pytest --cov --cov-report=html --cov-fail-under=50

# 跳过 E2E 测试
python -m pytest -v -m "not e2e"
```

**覆盖率监控流程:**
```
CI Pipeline:
1. 设置环境变量 CI=true
2. 运行 pytest --cov --cov-fail-under=50 -m "not e2e"
3. 生成 coverage.xml
4. 上传为 artifact
5. 失败时阻止合并
```

### Notes

**高风险项:**
- `ai_step_executor.py` 包含异步方法，需要正确配置 pytest-asyncio (strict 模式)
- `variable_resolver_service.py` 包含线程锁，并发测试可能不稳定
- E2E 测试依赖真实 LLM API，CI 中通过环境变量自动跳过

**已知限制:**
- 冒烟测试（smoke tests）需要真实 LLM API Key
- E2E 测试需要 Docker 环境运行
- Playwright 首次运行需要安装浏览器 (`playwright install`)

**回归测试策略 (F12 修复):**
- 所有测试使用事务回滚隔离，保证测试独立性
- 测试执行顺序随机化（pytest-randomly）以发现隐式依赖
- CI 中并行执行测试（pytest-xdist）

**未来考虑 (Out of Scope 但值得记录):**
- 前端组件快照测试
- API 契约测试
- 负载测试和性能基准