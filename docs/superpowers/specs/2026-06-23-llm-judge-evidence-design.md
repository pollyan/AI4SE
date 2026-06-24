# LLM Judge Evidence 设计

## 背景

New Agents 已有规则型 workflow 质量治理和跨 run deterministic 质量趋势，`tests/e2e/new_agents_browser/llm_judge.py` 也已经具备可选 LLM judge prompt、JSON verdict parser 和 artifact / handoff judge 断言。但当前 judge 结果只存在于一次性断言中：通过时没有证据文件，失败时缺少稳定 evidence path，后续无法审计“当时 judge 看到了什么、打了多少分、问题和建议是什么”。

本轮交付 E08 剩余的 LLM judge evidence 闭环：当维护者显式启用可选 judge 时，judge verdict 会被记录为本地 evidence artifact，并在 pytest 输出或失败信息中展示可读摘要。默认未启用或缺少 judge API env 时继续明确 skip，不把 mock 或 skip 当作真实外部评审。

## 自问自答式头脑风暴

问：真实用户意图是什么？
答：维护者想用外部 LLM judge 评审 New Agents E2E 产物质量，并留下可追溯证据，而不是只看到一次性 pass/fail。

问：完成后用户多完成了什么？
答：用户运行可选 judge 后，可以获得包含 workflow/handoff 名称、score、dimension_scores、issues、evidence、recommendations 和 verdict 的 JSON evidence 文件；失败时 assertion message 会显示 score、issues、recommendations 和 evidence path。

问：哪些相邻小缺口应合并？
答：配置诊断、verdict 记录模型、evidence 写入、摘要展示、失败解释、artifact/handoff 两类 judge 复用、测试和 todo 记录必须合并。只改 parser 或只加一个字段不形成 evidence 闭环。

问：哪些内容必须排除？
答：不做产品 UI 展示，不新增后端持久化表/API，不调用真实 judge 作为默认本地门禁，不把 fake verdict 当真实 judge 证据。当前 evidence 是 E2E 测试证据，不是 New Agents runtime 数据。

问：可行路径有哪些？
答：
1. 只打印 verdict 到 pytest 输出。实现小，但不能审计。
2. 在现有 `llm_judge.py` 增加 evidence record、默认 artifact 目录、summary 和失败消息，复用现有可选 judge 入口。边界清晰，可本地 TDD。
3. 接入 run persistence 或 observability API。产品化更强，但会触及 runtime/API/UI，超出本轮 evidence 边界。

推荐路径：选择 2。它补齐可选 judge 的触发、记录、展示、失败解释和本地验证，同时不引入 frontend 依赖或 runtime 风险。

问：主要风险是什么？
答：evidence 生成物不能误提交；默认目录应是 `artifacts/new-agents-llm-judge/`，测试使用 `tmp_path`。judge 失败前必须先记录 evidence，否则失败本身会丢证据。HTTP 或 JSON 解析异常仍应显式失败，不吞掉异常或伪造 verdict。

问：TDD 验收证据是什么？
答：先写 `test_llm_judge.py` 失败测试：evidence JSON 写入、summary 展示、artifact judge 失败消息包含 evidence path、缺 env 诊断。再实现最小改动，运行 deterministic unit tests 和 optional E2E skip 验证。

## 用户故事

作为 New Agents 质量维护者，当我启用可选 LLM judge 评审 E2E workflow 产物时，我可以获得可追溯的 judge evidence 文件和清晰失败解释，从而把外部质量评判从一次性断言升级为可审计证据闭环。

## 功能设计

新增或扩展以下能力：

- `JudgeEvidenceRecord`：封装 judge kind、subject、passed、score、dimension_scores、issues、evidence、recommendations 和可选 evidence path。
- `write_judge_evidence(record, evidence_dir)`：把 verdict 写成 JSON 文件，文件名稳定可读，默认目录为 `artifacts/new-agents-llm-judge/`，可由 `NEW_AGENTS_E2E_JUDGE_EVIDENCE_DIR` 覆盖。
- `format_judge_evidence_summary(record)`：生成一行或多行可读摘要，包含 subject、score、visual score、issues 和 evidence path。
- `judge_configuration_status()`：返回 enabled、missing env 和 evidence dir，用于测试和 skip 诊断。
- `assert_llm_judges_artifact_quality()` / `assert_llm_judges_handoff_quality()`：在解析 verdict 后先写 evidence，再执行 pass/score/visual score 断言；失败消息包含 summary 和 evidence path。

## 文件范围

修改：
- `tests/e2e/new_agents_browser/llm_judge.py`
- `tests/e2e/new_agents_browser/test_llm_judge.py`
- `docs/todos/refactor/README.md`
- `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

创建：
- `docs/superpowers/specs/2026-06-23-llm-judge-evidence-design.md`
- `docs/superpowers/plans/2026-06-23-llm-judge-evidence.md`

不修改：
- `tools/new-agents/frontend/`。本轮不做产品 UI 展示，避免在缺少 `node_modules` 时触发无法满足的前端 CI 等价门禁。
- `tools/new-agents/backend/` runtime/API/persistence。LLM judge evidence 是 E2E 测试证据，不进入产品运行时。

## 验收条件

1. Given 合格 judge verdict  
   When 写入 evidence  
   Then 生成 JSON 文件，包含 kind、subject、score、dimension_scores、issues、evidence、recommendations，并返回可读 path。

2. Given judge verdict 分数不合格或 `pass=false`  
   When artifact/handoff judge 断言失败  
   Then assertion message 包含 subject、score、issues、recommendations 和 evidence path。

3. Given verdict 含可视化质量维度  
   When 格式化 summary  
   Then summary 展示 visual score；缺失可视化维度仍由现有 parser/visual assertion 显式失败。

4. Given `NEW_AGENTS_E2E_LLM_JUDGE` 未启用或 judge API env 缺失  
   When optional judge 测试运行  
   Then 明确 skip 或返回配置诊断，不进行网络调用。

## 验证计划

聚焦验证：
- `python3 -m pytest tests/e2e/new_agents_browser/test_llm_judge.py -q`
- `python3 -m pytest -o addopts='' tests/e2e/new_agents_browser/test_lisa_test_design_workflow.py::test_lisa_final_artifact_passes_optional_llm_judge tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py::test_alex_final_artifact_passes_optional_llm_judge -q`
- `python3 -m py_compile tests/e2e/new_agents_browser/llm_judge.py`
- `git diff --check`

CI 等价门禁：
- 本轮只改 Python E2E judge helper/tests 和文档，不触碰前端 TypeScript、shared runtime、SSE/API、artifact contract 或持久化模型；CI 等价本地门禁以相关 pytest、py_compile 和 diff check 为准。
- 不运行真实 LLM judge：当前 `NEW_AGENTS_E2E_LLM_JUDGE` 和 judge API env 未设置；真实外部 judge 证据必须在具备 env、网络和额度时另行执行。
