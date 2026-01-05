# 数据库设计文档 (Data Models)

> **生成日期**: {{date}}
> **数据库**: PostgreSQL
> **ORM框架**: Flask-SQLAlchemy

AI4SE 平台使用统一的 PostgreSQL 数据库 (`ai4se`)，不同模块共享同一个数据库实例，但在逻辑上使用不同的表空间。

## 1. 意图测试工具 (Intent Tester)

主要负责管理测试资产和执行记录。

### 核心表结构

#### `test_cases` (测试用例)
存储自然语言描述的测试流程。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer (PK) | 主键 |
| `name` | String | 用例名称 |
| `description` | Text | 用例描述 |
| `steps` | JSON | 测试步骤列表 (自然语言指令) |
| `created_at` | DateTime | 创建时间 |

#### `executions` (执行记录)
记录测试用例的每一次运行状态。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer (PK) | 主键 |
| `test_case_id` | Integer (FK) | 关联的测试用例 |
| `status` | String | 状态 (running, passed, failed) |
| `logs` | JSON | 执行日志和截图路径 |
| `started_at` | DateTime | 开始时间 |

---

## 2. AI 智能体 (AI Agents)

负责存储对话上下文和用户需求配置。

### 核心表结构

#### `requirements_sessions` (需求会话)
管理用户与 AI (Alex) 的对话 Session。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | String (UUID) | 会话唯一标识 |
| `status` | String | 会话状态 (active, archived) |
| `project_context` | Text | 项目背景信息 |
| `created_at` | DateTime | 创建时间 |

#### `requirements_messages` (会话消息)
存储对话历史记录。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer (PK) | 主键 |
| `session_id` | String (FK) | 关联的会话 |
| `role` | String | 角色 (user, assistant, system) |
| `content` | Text | 消息内容 |
| `sequence` | Integer | 消息顺序号 |

#### `requirements_ai_configs` (AI 配置)
用户自定义的 LLM 参数配置。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer (PK) | 主键 |
| `user_id` | String | 用户标识 |
| `api_key` | String | (加密存储) LLM API Key |
| `base_url` | String | LLM Base URL |
| `model` | String | 模型名称 (e.g. gpt-4) |
| `temperature` | Float | 生成随机性参数 |

---

## 3. 数据库迁移

项目目前主要依赖 `db.create_all()` 进行初始化，尚未使用 Alembic 进行版本化迁移管理。

**建议**:
随着生产环境数据的积累，建议引入 `Flask-Migrate` (基于 Alembic) 来管理数据库 schema 的变更，避免直接修改表结构导致的数据丢失风险。
