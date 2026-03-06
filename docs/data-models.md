# 数据模型文档

> 生成日期: 2026-03-06 | 扫描级别: Deep Scan

## 数据库架构

**数据库**: PostgreSQL 15  
**ORM**: Flask-SQLAlchemy / SQLAlchemy 2.0  
**共享实例**: 所有服务通过 `DATABASE_URL` 连接同一 PostgreSQL 实例

---

## Intent-Tester 数据模型

### TestCase（测试用例）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 主键 |
| `name` | String(255) | NOT NULL | 测试用例名称 |
| `description` | Text | - | 描述 |
| `steps` | Text | NOT NULL | 测试步骤 (JSON string) |
| `tags` | String(500) | - | 标签 (逗号分隔) |
| `category` | String(100) | - | 分类 |
| `priority` | Integer | default=3 | 优先级 (1-5) |
| `created_by` | String(100) | - | 创建者 |
| `created_at` | DateTime | auto | 创建时间 |
| `updated_at` | DateTime | auto | 更新时间 |
| `is_active` | Boolean | default=True | 是否启用（软删除标志） |

**索引**: `idx_testcase_active`, `idx_testcase_category`, `idx_testcase_created`, `idx_testcase_priority`

---

### ExecutionHistory（执行历史）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 主键 |
| `execution_id` | String(50) | UNIQUE, NOT NULL | 执行 UUID |
| `test_case_id` | Integer | FK → test_cases.id | 关联测试用例 |
| `status` | String(50) | NOT NULL | 状态: running/success/failed/stopped |
| `mode` | String(20) | default='headless' | 浏览器模式 |
| `browser` | String(50) | default='chrome' | 浏览器类型 |
| `start_time` | DateTime | NOT NULL | 开始时间 |
| `end_time` | DateTime | - | 结束时间 |
| `duration` | Integer | - | 执行时长 (秒) |
| `steps_total` | Integer | - | 总步骤数 |
| `steps_passed` | Integer | - | 通过步骤数 |
| `steps_failed` | Integer | - | 失败步骤数 |
| `result_summary` | Text | - | 结果摘要 (JSON) |
| `screenshots_path` | Text | - | 截图路径 |
| `error_message` | Text | - | 错误信息 |
| `executed_by` | String(100) | - | 执行者 |

**索引**: `idx_execution_testcase_status`, `idx_execution_start_time`, `idx_execution_status`, `idx_execution_executed_by`

---

### StepExecution（步骤执行详情）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 主键 |
| `execution_id` | String(50) | FK → execution_history.execution_id | 关联执行 |
| `step_index` | Integer | NOT NULL | 步骤序号 |
| `step_description` | Text | NOT NULL | 步骤描述 |
| `status` | String(20) | NOT NULL | 状态: success/failed/skipped |
| `start_time` | DateTime | NOT NULL | 开始时间 |
| `end_time` | DateTime | - | 结束时间 |
| `duration` | Integer | - | 执行时长 (秒) |
| `screenshot_path` | Text | - | 截图路径 |
| `ai_confidence` | Float | - | AI 置信度 |
| `ai_decision` | Text | - | AI 决策数据 (JSON) |
| `error_message` | Text | - | 错误信息 |

**索引**: `idx_step_execution_id_index`, `idx_step_status`, `idx_step_start_time`

---

### ExecutionVariable（执行变量）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 主键 |
| `execution_id` | String(50) | FK | 关联执行 |
| `variable_name` | String(255) | NOT NULL | 变量名 |
| `variable_value` | Text | - | 变量值 (JSON) |
| `data_type` | String(50) | NOT NULL | 类型: string/number/boolean/object/array |
| `source_step_index` | Integer | NOT NULL | 来源步骤 |
| `source_api_method` | String(100) | - | 来源 API 方法 |
| `source_api_params` | Text | - | 来源参数 (JSON) |
| `is_encrypted` | Boolean | default=False | 是否加密 |

**唯一约束**: `(execution_id, variable_name)`

---

### VariableReference（变量引用）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 主键 |
| `execution_id` | String(50) | FK | 关联执行 |
| `step_index` | Integer | NOT NULL | 使用步骤 |
| `variable_name` | String(255) | NOT NULL | 变量名 |
| `reference_path` | String(500) | - | 引用路径 (如 `product_info.price`) |
| `original_expression` | String(500) | - | 原始表达式 `${product_info.price}` |
| `resolved_value` | Text | - | 解析后的值 |
| `resolution_status` | String(20) | default='success' | 解析状态 |

---

### RequirementsSession（需求分析会话）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | String(50) | PK | UUID |
| `project_name` | String(255) | - | 项目名称 |
| `session_status` | String(50) | default='active' | 状态: active/paused/completed/archived |
| `current_stage` | String(50) | default='initial' | 阶段: initial/clarification/consensus/documentation |
| `user_context` | Text | - | 用户上下文 (JSON) |
| `ai_context` | Text | - | AI 分析上下文 (JSON) |
| `consensus_content` | Text | - | 共识内容 (JSON) |

---

### RequirementsMessage（需求分析消息）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 主键 |
| `session_id` | String(50) | FK → requirements_sessions.id | 关联会话 |
| `message_type` | String(20) | NOT NULL | 类型: user/assistant/system |
| `content` | Text | NOT NULL | 消息内容 |
| `message_metadata` | Text | - | 元数据 (JSON) |
| `attached_files` | Text | - | 附件信息 (JSON) |

---

### RequirementsAIConfig（需求分析 AI 配置）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 主键 |
| `config_name` | String(255) | NOT NULL | 配置名称 |
| `api_key` | Text | NOT NULL | API 密钥 |
| `base_url` | String(500) | NOT NULL | API 基础 URL |
| `model_name` | String(100) | NOT NULL | 模型名称 |
| `is_default` | Boolean | default=False | 是否默认 |
| `is_active` | Boolean | default=True | 是否启用 |

---

## New Agents Backend 数据模型

### LlmConfig（LLM 配置）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK | 主键 |
| `config_key` | String(64) | UNIQUE | 配置键 (如 `'default'`) |
| `api_key` | Text | - | LLM API 密钥 |
| `base_url` | Text | - | LLM API 基础 URL |
| `model` | String(128) | - | 模型名称 |
| `description` | Text | - | 描述 |
| `is_active` | Boolean | default=True | 是否启用 |
| `created_at` | DateTime | auto | 创建时间 |
| `updated_at` | DateTime | auto | 更新时间 |

**安全规则**: API Key 仅通过 SQL 手动插入，不通过 API 暴露，查询时脱敏。

---

## ER 关系图

```text
TestCase 1──N ExecutionHistory
                    │
                    ├── 1──N StepExecution
                    ├── 1──N ExecutionVariable
                    └── 1──N VariableReference

RequirementsSession 1──N RequirementsMessage

RequirementsAIConfig (独立表)
LlmConfig (独立表，new-agents-backend 使用)
```

## 数据库初始化

- **Intent-Tester**: `db.create_all()` 在 Flask `create_app()` 中自动执行
- **New-Agents-Backend**: `init_db()` 在应用启动时执行，检测并创建 `llm_config` 表
- **开发环境**: 通过 Docker Compose 的 PostgreSQL 容器自动初始化
- **测试环境**: 使用 SQLite `:memory:` 内存数据库
