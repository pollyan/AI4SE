好的，这是 `WARP.md` 中文翻译全文的 Markdown 代码：

````markdown
# WARP.md

该文件为 WARP (warp.dev) 在处理此代码仓库中的代码时提供指导。

## 项目概述
- **意图测试框架 (Intent Test Framework)**: 一个由 AI 驱动的 Web 自动化测试平台，包含一个 Flask Web UI 和一个用于视觉/自然语言测试的 Node.js AI 引擎 (MidSceneJS)。通过 Socket.IO 实现实时状态更新；采用 API 优先设计的分层架构。
- **两个智能体**: 需求分析智能体 (Alex Chen) 和测试分析智能体 (Lisa Song)，用于提供结构化的工作流指导。
- 更完整的功能列表和快速入门指南，请参阅 `README.md`。

## 约定和重要规则 (来自 CLAUDE.md 和代码仓库)
- 文档/UI 的主要语言：中文 (Chinese)。
- **禁止硬编码配置**: 所有配置项必须来自环境变量 (.env)、数据库或配置文件。源代码中禁止硬编码 API 密钥、URL、模型名称或业务逻辑。
- **架构约束**: 服务层抽象 (`web_gui/services/*`)；生产环境中禁止使用模拟/占位的业务逻辑；采用 API 优先和模块化蓝图设计；通过 `DatabaseService` 访问数据库；保持 UI 与 minimal-preview 模式一致。
- **测试策略**: 重点是 API 集成测试；除非有明确要求，否则不要添加单元测试。

## 常用命令

### 环境设置
- Python 依赖: 使用你选择的虚拟环境，然后安装：
  ```bash
  pip install -r requirements.txt
````

  - Node 依赖 (用于代理/Jest 测试和 MidScene 服务器):
    ```bash
    npm install
    ```
  - 可选: 如果你的平台需要，请安装 Playwright 浏览器
    ```bash
    python -m playwright install
    ```
  - 一键式辅助脚本 (如果你偏好使用脚本进行设置):
    ```bash
    bash scripts/install-test-deps.sh
    python scripts/setup_dev_env.py
    cp .env.example .env  # 然后编辑 .env 文件，填入你的 AI 密钥/模型
    ```

### 在本地运行应用

  - 启动 Flask Web UI (模板/静态文件已内置于 `web_gui/`):
    ```bash
    python web_gui/run_enhanced.py
    # UI: http://localhost:5001
    # API: http://localhost:5001/api/
    # 需求智能体: http://localhost:5001/requirements
    # 测试智能体: 可通过测试用例管理 UI 访问
    ```
  - 当 AI 步骤需要时，启动 AI 引擎服务器 (Node/MidSceneJS):
    ```bash
    node midscene_server.js
    ```
  - 健康检查和便捷性: 有一个辅助脚本 `dev.sh`，但它引用的 `start.py` 可能不在此代码树中；建议使用上述明确的命令。

### 测试 (pytest; 重点为 API 集成)

  - 运行完整测试套件:
    ```bash
    pytest -v
    ```
  - 运行测试并生成覆盖率报告:
    ```bash
    pytest --cov=web_gui --cov-report=term --cov-report=html
    ```
  - 运行单个测试文件 / 测试用例 / 关键词:
    ```bash
    pytest tests/api/test_testcase_api.py -v
    pytest tests/api/test_testcase_api.py::TestClassName::test_method -v
    pytest -k "dashboard and not slow" -v
    ```
  - 标记和配置: 请参阅 `pytest.ini` (严格标记、asyncio 自动模式、python\>=3.11)。

### 代理/Node 端测试 (Jest)

如果你修改了 `midscene_service` 或代理逻辑，请运行以下测试:

```bash
npm run test:proxy
npm run test:proxy:watch
npm run test:proxy:coverage
```

### 代码风格检查/格式化和质量

  - 使用仓库的质量门禁脚本:
    ```bash
    python scripts/quality_check.py --fix
    ```
  - 该脚本内部使用了 black/flake8；为保持一致性，请优先使用此脚本。项目还提供性能基准测试:
    ```bash
    python scripts/benchmark.py --parallel --save
    ```

## 关键架构和流程

### Web 应用 (Flask)

  - **入口**: `web_gui/app_enhanced.py` 暴露了 `create_app`；静态文件和模板位于 `web_gui/static` 和 `web_gui/templates` 下。
  - **蓝图**: 通过 `web_gui/api/base.register_blueprints` 注册；API 端点包括测试用例、执行、统计、仪表盘、需求等。
  - **数据库**: SQLAlchemy 在 `web_gui/app_enhanced.py` 中配置。模型定义在 `web_gui/models.py`。数据库引擎选项会根据是 Postgres 还是 SQLite 进行适配。
  - **实时通信**: `web_gui/core/extensions` 初始化 Socket.IO；执行生命周期事件会被触发 (如 `execution_started`, `step_completed`, `execution_completed`)。

### 服务 (业务逻辑)

  - **ExecutionService (`web_gui/services/execution_service.py`)**
      - 编排异步执行线程，持久化 `ExecutionHistory` 和 `StepExecution`，更新步骤计数并触发实时事件。
      - 集成 AI 服务以执行步骤；支持无头/有浏览器模式；通过 `get_variable_manager` 支持变量解析。
  - **AI 服务**
      - `get_ai_service` 和 `ai_step_executor` 通过 Node 服务器和 Python 桥接 (`midscene_python.py`) 与 MidSceneJS 集成。
  - **变量解析**
      - `variable_resolver_service` 支持 `${var}` 语法，以及在步骤之间传递 `output_variable`。
  - **DatabaseService** 抽象了数据库访问；保持控制器（controller）轻量，将逻辑推迟到服务层处理。

### AI 引擎和桥接

  - **Node 服务器**: `midscene_server.js` 暴露了执行器所使用的 AI/视觉能力。
  - **Python 桥接**: `midscene_python.py` 用于 Python 与 Node 之间的互操作。

### 智能体系统

  - **需求分析智能体 (Alex Chen)**: `web_gui/services/requirements_ai_service.py` 提供了 `IntelligentAssistantService`，用于结构化地澄清需求。
      - **四步法**: 电梯演讲 → 用户画像 → 用户旅程 → 商业需求文档 (BRD)
      - **人设包**: `intelligent-requirements-analyzer/dist/intelligent-requirements-analyst-bundle.txt`
  - **测试分析智能体 (Lisa Song)**: 使用相同的服务架构，专注于测试策略和测试用例生成。
      - **四步法**: 测试范围分析 → 测试策略设计 → 测试用例生成 → 测试计划文档 (TPD)
      - **人设包**: `intelligent-requirements-analyzer/dist/testmaster-song-bundle.txt`
  - **智能体配置**: `intelligent-requirements-analyzer/config.yaml` 定义了文档位置和工作流设置。

### 测试结构

  - **重点**: API 集成测试，位于 `tests/api/` 下 (包括健康检查、仪表盘、统计、需求、测试用例、执行、错误场景、midscene 端点)。
  - **全局配置**: pytest 的全局配置在 `pytest.ini` 中；fixture 在 `tests/conftest.py` 和 `tests/api/conftest.py` 中。
  - **迁移验证**: `test_migrations.py` 以及 `scripts/validate_migration*.py` 脚本。

## 需要了解的重要仓库文件

  - `README.md`: 快速入门 (克隆、环境设置、启动 MidScene 服务器和 Flask UI、打开 http://localhost:5001)、架构图、自然语言步骤示例、贡献指南和 CI 徽章。
  - `CLAUDE.md`: 强制要求服务层抽象、生产环境中无模拟代码、API 集成优先的测试策略、minimal-preview UI 标准。
  - `requirements*.txt`, `package.json`: 权威的依赖项列表和 Node 测试脚本。
  - `scripts/`: 丰富的运维辅助脚本 (如 `quality_check.py`, `benchmark.py`, `migrate_to_supabase.py`, `test-local.sh`, `install-test-deps.sh`, `init_default_config.py`, `validate_migration.py` 等)。如果可用，请优先使用这些脚本。
  - `intelligent-requirements-analyzer/`: 包含智能体系统，其人设包在 `dist/` 中，工作流配置在 `config.yaml` 中。

## 与此代码库相关的实用技巧

  - **端口**: Flask 默认使用 `5001`；MidScene Node 服务器通常在 `3001` (见 `dev.sh` 默认值)。如有需要，可通过环境变量调整。
  - **数据库**: 如果未设置 `DATABASE_URL`，则默认使用 SQLite；支持 Postgres 并可进行连接池调优。对于开发，SQLite 简化了设置过程。
  - **实时 UI**: 如果你更改了服务中执行事件的负载 (payload)，请相应地更新 `web_gui/templates/static` 下的前端消费者。
- **智能体系统**: 两个智能体 (Alex/Song) 都使用同一个 `IntelligentAssistantService`，但加载了不同的人设包。智能体对话会话通过 `RequirementsSession` 和 `RequirementsMessage` 模型进行管理。
- **提示词存放**: 运行时从 `assistant-bundles/` 目录加载提示词文件（不再依赖 intelligent-requirements-analyzer/dist）。
- **智能体 UI 访问**: 需求分析器地址为 `/requirements`，配置管理地址为 `/config-management`。UI 设计模式请参考 `minimal-preview/`。

## 配置管理 (反硬编码)

  - **环境变量**: 所有配置必须在 `.env` 文件中定义。
      - API 密钥: `OPENAI_API_KEY`
      - Base URL: `OPENAI_BASE_URL`
      - 模型名称: `MIDSCENE_MODEL_NAME`
      - 配置名称: `DEFAULT_AI_CONFIG_NAME`
  - **数据库优先**: `scripts/init_default_config.py` 从环境变量中读取配置，并且绝不会覆盖用户已有的配置。
  - **无硬编码值**: API 密钥、URL、模型名称等绝不能出现在源代码中。
  - **配置优先级**: 数据库配置 \> 环境变量 \> 默认值 (如果缺少必需值则会失败)。

## 智能体使用方法

  - **需求分析智能体 (Alex Chen)** - 4步需求澄清法:
      - **访问**: http://localhost:5001/requirements
      - **命令**: `*start` (完整工作流), `*elevator` (步骤1), `*persona` (步骤2), `*journey` (步骤3), `*help`
      - **输出**: 带有进度跟踪的结构化商业需求文档 (BRD)。
  - **测试分析智能体 (Lisa Song)** - 4步测试分析法:
      - **命令**: `*start` (完整工作流), `*scope` (步骤1), `*strategy` (步骤2), `*cases` (步骤3), `*help`
      - **输出**: 带有测试用例生成的综合性测试计划文档 (TPD)。
  - 两个智能体都通过 `RequirementsSession`/`RequirementsMessage` 模型来维护会话状态。
  - 智能体人设从 `intelligent-requirements-analyzer/dist/` 目录下的包文件中加载。

## 附录：单命令流程

  - **最小化开发环境启动** (需要两个终端):
    ```bash
    # 终端 
    ./dev.sh start

    ```
  - **提交代码前的完整测试和质量检查**:
    ```bash
    pytest -v
    python scripts/quality_check.py --fix
    pytest --cov=web_gui --cov-report=term --cov-report=html
    ```

<!-- end list -->

```
```