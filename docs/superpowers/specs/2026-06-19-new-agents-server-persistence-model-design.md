# New Agents Server Persistence Model Design

## Current State Gap Analysis

- 当前 New Agents 会话、消息和产物版本主要停留在前端运行态与浏览器存储侧，后端只有 `LlmConfig` 持久化模型，无法为恢复、审计、分享或 LLM judge 复用提供稳定数据源。
- 后端已使用 Flask-SQLAlchemy，并在 `create_app()` 中通过 `db.create_all()` 初始化表；现有测试用临时 SQLite 数据库隔离。
- 工作流和阶段合法性已经由 `agent_contracts.WORKFLOW_STAGES` 维护，持久化层应复用该事实源，不新增 agent-specific runtime 或独立 API/SSE 分支。
- 当前切片只建立服务端数据模型和 repository，不接入 `/api/agent/runs/stream`、前端 localStorage 迁移、分享 API 或 judge 自动读取链路。

## Scope

This slice builds the first reusable backend persistence layer for agent runs:

- `agent_runs`: one run/session per workflow execution.
- `agent_messages`: ordered user/assistant messages for a run.
- `agent_artifacts`: one current artifact container per run and stage.
- `agent_artifact_versions`: append-only artifact content versions.

## Requirements

- A repository can create a run for a known workflow/stage and reject unknown workflow/stage pairs.
- A repository can append ordered user/assistant messages and reject unsupported roles.
- A repository can record artifact versions for a known run/stage, incrementing version numbers per run/stage.
- A repository can return a deterministic snapshot containing run metadata, ordered messages, current artifacts, and artifact version metadata.
- The data model remains generic for all workflows and agents; workflow-specific behavior stays in workflow/stage data and contracts.

## Non-Goals

- No new REST endpoints in this slice.
- No SSE integration in this slice.
- No frontend migration from localStorage in this slice.
- No database migration framework introduction in this slice.

## Verification

- Backend unit tests cover run creation, message ordering, artifact versioning, snapshot shape, and validation failures.
- Existing model/config tests continue to pass against the expanded metadata.
