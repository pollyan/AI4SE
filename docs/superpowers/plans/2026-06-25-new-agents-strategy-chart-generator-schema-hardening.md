# New Agents 策略图表生成器与 schema 强化计划

## 目标

完成 TEST_DESIGN / STRATEGY 阶段图表确定性生成强化：模型只填业务风险字段，后端派生 RPN 并固定生成 Mermaid / risk-board，降低正式产物格式失败率。

## 执行步骤

1. [x] 读取目标模式事实源、现有 STRATEGY renderer/runtime/tests 和相关历史 todo/spec。
2. [x] 记录本轮待办、CGA/spec 和实施计划。
3. [x] 按 TDD 增加红灯测试：
   - 缺省 `risks[].rpn` 时 STRATEGY artifact 仍可渲染并通过 contract。
   - 显式错误 `rpn` 仍失败。
   - Mermaid 标签包含双引号、反斜杠和换行时被规范化。
   - STRATEGY structured output instruction 说明 RPN 由后端计算。
   - raw JSON final/streaming 路径接受缺省 RPN。
4. [x] 实现后端 schema/renderer/runtime 改动：
   - `StrategyRisk.rpn` 改为可选输入。
   - validator 在缺省时写入计算值，在显式错误时失败。
   - Mermaid label helper 规范化空白、反斜杠和双引号。
   - STRATEGY prompt 示例去掉模型必填 `rpn`，改为后端计算说明。
5. [x] 跑聚焦验证：
   - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q`
   - 必要时补跑 `tools/new-agents/backend/tests/test_agent_contracts.py`。
6. [x] 跑提交前验证：
   - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py -q`
   - `git diff --check -- <本轮相关文件>`
   - `./scripts/test/test-local.sh all`，如环境权限阻塞则记录具体失败。
7. [x] 更新本计划和待办状态，审查 diff，只 stage 本轮相关文件。
8. [x] 形成聚焦 commit。

## 验证记录

- RED：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_artifact_data_computes_missing_rpn_for_generated_visuals tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_strategy_mermaid_labels_are_normalized_for_special_characters tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_strategy_artifact_data_without_model_rpn tools/new-agents/backend/tests/test_agent_runtime.py::test_strategy_structured_output_instruction_requests_artifact_data_not_markdown -q`，结果：4 failed，失败点为缺省 `rpn`、Mermaid 标签和 prompt 示例。
- GREEN：同一命令，结果：4 passed。
- 聚焦：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q`，结果：167 passed。
- 扩展：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_stream_services.py -q`，结果：106 passed。
- 语法：`.venv/bin/python -m py_compile tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/agent_runtime.py`，结果：通过。
- CI 等价聚焦：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_stream_services.py -q`，结果：273 passed。
- Diff 检查：`git diff --check -- <本轮相关文件>`，结果：通过。
- 全量沙箱：`./scripts/test/test-local.sh all`，结果：失败，MidScene proxy `listen EPERM: operation not permitted 0.0.0.0:3002`，New Agents Browser E2E Chromium `bootstrap_check_in ... Permission denied (1100)`。
- 全量非沙箱含可选 judge：`./scripts/test/test-local.sh all`，结果：失败于 `test_lisa_final_artifact_passes_optional_llm_judge`，judge 返回 JSON 含未转义控制字符，`json.loads` 报 `Invalid control character`。
- 全量非沙箱关闭可选 judge：`env NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`，结果：通过；Browser E2E 为 3 passed、3 skipped、9 deselected。
