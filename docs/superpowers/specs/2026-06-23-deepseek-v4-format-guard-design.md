# DeepSeek V4 格式输出防回退门禁设计

## Current State Gap Analysis 摘要

- 用户最新明确要求 DeepSeek V4 的“格式化输出”需求优先级很高。
- `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md` 显示 5 个在线 workflow、17 个 stage 都已完成 `artifact_data` 垂直迁移。
- 当前风险已经从“继续迁移某个 stage”转为“防止未来新增或改动 stage 时，runtime 静默回退到要求模型输出完整 Markdown/Mermaid/表格”。
- `agent_runtime.py` 目前有两份手写映射：`supports_artifact_data_rendering()` 的 stage set，以及 `build_structured_output_instruction()` 的 if 分支；两者与 `artifact_data_renderers.py` 的 renderer 分支没有统一门禁。

## 用户故事

作为使用 DeepSeek V4 Flash 运行 New Agents 的用户，我希望所有在线 workflow stage 都稳定走“模型只输出 JSON 业务数据，后端确定性渲染最终 artifact”的链路。这样后续新增 stage 或调整 prompt 时，不会因为漏配而悄悄退回让模型拼完整 Markdown、Mermaid 和表格，导致格式不完整错误重新出现。

## 设计

本轮不新增任何 Lisa、Alex 或 DeepSeek 专属 runtime、API、store 或 renderer。改动只在共享 New Agents 后端 runtime 和 renderer registry 内完成：

1. 在 `artifact_data_renderers.py` 暴露 `ARTIFACT_DATA_RENDERER_STAGE_KEYS` 和 `get_artifact_data_renderer_stage_keys()`，作为 renderer 实际支持的 stage key 来源。
2. 在 `agent_runtime.py` 用 `ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTIONS` 字典集中声明 stage -> instruction 的映射。
3. `supports_artifact_data_rendering()` 改为同时要求 renderer key 和 instruction key 存在，避免任一侧漏配仍返回 true。
4. `build_structured_output_instruction()` 对已支持 artifact_data 的 stage 返回对应 instruction；对未知或未支持 stage 保留旧文本指令，避免改变非目标调用方行为。
5. 新增测试枚举 `workflow_manifest.json` 的所有在线 stage，要求每个 stage 都命中 artifact_data 支持、renderer key 和 instruction key，并且 instruction 不包含 `artifact_update.markdown` 或要求模型输出完整 Markdown 的旧格式职责。

## 验收条件

- 所有 manifest 在线 stage 都被 artifact_data renderer 和 structured output instruction 覆盖。
- renderer stage keys 与 instruction stage keys 必须一致；新增 stage 时只改一边会有测试失败。
- 所有在线 stage 的 structured output instruction 必须要求 `artifact_data`，且不得要求 `artifact_update.markdown`。
- DeepSeek retry prompt 对在线 stage 继续要求修正 `artifact_data`，不得要求重写 Markdown、Mermaid 或表格。
- 不改变 typed SSE、run persistence、artifact contract 或前端状态协议。

## 非目标

- 不新增新的 workflow stage。
- 不迁移真实模型 smoke 到默认门禁。
- 不修改前端 UI。
- 不替换已有每个 stage 的 Pydantic schema 或 renderer 输出结构。

## 验证计划

- 后端 RED/GREEN：`test_agent_runtime.py` 增加 manifest 覆盖、防 Markdown 回退、retry prompt 覆盖测试。
- Renderer contract：`test_artifact_data_renderers.py` 增加 renderer key 与 runtime instruction key 同步测试。
- 运行聚焦后端测试：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py -q`
- 语法检查：`.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py`
- 格式检查：`.venv/bin/python -m black --check ...`
- diff 检查：`git diff --check`
