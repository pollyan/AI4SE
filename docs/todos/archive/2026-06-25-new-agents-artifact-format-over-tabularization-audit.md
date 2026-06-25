# New Agents 产出物过度表格化格式审计记录

状态：已完成
创建日期：2026-06-25
完成日期：2026-06-25
相关模块：`tools/new-agents/`
用户反馈来源：本地 UI 截图，Lisa / 测试策略产物右侧内容

## 背景

用户观察到当前很多右侧产出物内容都变成了 Markdown 表格，整体阅读体验“放眼望去很枯燥”。截图中的《测试策略蓝图》在 `1. 策略摘要` 下使用 `字段 / 内容` 二列表格承载短结论、依据和阶段判断；类似“附件”“输入材料”“文档信息”等辅助信息也可能被渲染成表格，但这类内容未必需要表格化。

## 完成内容

- 在后端 deterministic renderer 的 `_markdown_table(...)` 出口增加窄规则：仅 `字段/内容`、`维度/内容`、`格子/内容`、`属性/详情` 这类说明性二列表头改为 Markdown 定义列表。
- 新增 `_definition_list(...)` 和 `_format_definition_value(...)` helper，输出形态为 `- **字段名**：字段内容`。
- 保留所有其他 Markdown 表格输出，包括风险 FMEA、质量目标、测试点、用例、覆盖追溯、矩阵、状态看板和多列结构化数据。
- 补充 renderer 测试，证明 `策略摘要` 和 `附录：文档信息` 不再输出 `| 字段 | 内容 |`，同时风险明细表仍保留 `| 风险 ID | 风险名称 |`。

## 验收结果

- 截图同类的 `策略摘要` 不再默认渲染为 `字段 / 内容` 二列表格。
- “文档信息”这类辅助信息不再默认使用大表格。
- 核心追溯类和风险类多列表格仍保留。
- 未改变 artifact_data schema、Agent Runtime SSE、前端 store、ArtifactPane 渲染管线或导出入口。

## 验证

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -q`：通过，75 tests。
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "artifact_data_before_final_output or paragraph_level" -q`：通过，18 tests。
- `cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts`：通过，72 tests。
- `.venv/bin/python -m py_compile tools/new-agents/backend/artifact_data_renderers.py`：通过。

## 保留表格范围

- 风险清单、FMEA、测试点追溯、用例清单、覆盖矩阵、决策对比、状态看板、多行多列结构化数据继续使用 Markdown 表格或 `ai4se-visual`。

## 非目标

- 不取消所有表格。
- 不降低结构化 artifact_data 契约严格性。
- 不绕过后端确定性渲染，不能让模型自由拼接不稳定 Markdown。
- 不改前端 ArtifactPane 渲染管线。
