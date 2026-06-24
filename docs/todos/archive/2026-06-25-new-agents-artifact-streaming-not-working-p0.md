# New Agents 右侧产出物未流式渲染 P0 Bug Todo

状态：已完成，待归档  
创建日期：2026-06-25  
相关模块：`tools/new-agents/`

## 完成记录

- 完成日期：2026-06-25
- 目标模式产物：
  - `docs/superpowers/specs/2026-06-25-new-agents-artifact-data-real-streaming-design.md`
  - `docs/superpowers/plans/2026-06-25-new-agents-artifact-data-real-streaming.md`
- 实现摘要：
  - `tools/new-agents/backend/agent_runtime.py` 在共享 raw JSON streaming 路径中识别完整 `artifact_data` JSON 对象。
  - 局部对象只有在能完整解析并通过既有 deterministic renderer 校验时，才会作为正式 `agent_delta.artifact_update.replace` 发出。
  - 半截 `artifact_data` 继续保持静默，不生成假进度页、裸 JSON 或调试 Markdown。
  - `TEST_DESIGN/CLARIFY` 和 `TEST_DESIGN/STRATEGY` 已覆盖 final 前 artifact delta 回归测试。
- 验证：
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "artifact_data_before_final_output or incomplete_artifact_data" -q`
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -q`
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_stream_services.py -q`
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_endpoint.py -q`
  - `npm run test -- src/core/__tests__/llm.test.ts` in `tools/new-agents/frontend`
  - `git diff --check`
  - `./scripts/test/test-local.sh all` 先在沙箱内因端口监听和 Chromium Mach service 权限失败；提升权限重跑后通过，最终汇总为“所选测试执行完成，未发现失败”。

## 背景

用户反馈：New Agents 右侧产出物仍然没有按预期流式渲染。这个问题影响主链路体验，用户在等待模型生成时无法看到产出物逐步出现，会误以为系统卡住、流式中断或没有真正生成内容。

这不同于“流式位置提示”体验优化。位置提示是在已有正式内容逐步出现的基础上，补充下一段正在生成的位置感；当前问题更严重：右侧产出物本身没有稳定流式更新。

## 当前问题

- 右侧 Artifact 产出物没有在生成过程中逐步显示。
- 用户只能等待最终结果，或看到不连续 / 不可感知的更新。
- 左侧聊天流式响应和右侧 artifact 流式渲染体验不一致。
- 如果后端已经发送 `agent_delta.artifact_update`，则可能是前端 SSE parser、store 更新、ArtifactPane 渲染或状态覆盖问题。
- 如果后端没有发送有效 artifact delta，则可能是 Agent Runtime、structured artifact renderer、SSE schema 或 stream orchestration 问题。

## 优先级

这是第一优先级，进入后续实现时应优先于普通体验优化和长期框架深化事项处理。

原因：

- 它直接影响用户对生成过程是否正常的判断。
- 它是 New Agents 主工作区的核心体验，不是边缘功能。
- 后续“位置提示”“文档信息密度”“批注”等体验优化都建立在右侧产出物能稳定流式更新的前提上。

## 目标能力包

恢复右侧 Artifact 的真实流式渲染：

- 生成过程中，右侧产出物应随着后端有效增量逐步更新。
- 已生成的正式内容应保持可读，不显示调试式进度页。
- 最终 `agent_turn` 到达后，右侧内容应与最终 artifact 收敛一致。
- 截断或失败时，应保留最后一个有效 artifact delta，并明确显示错误或截断状态。

## 架构约束

- 必须继续复用共享 `/api/agent/runs/stream`、typed SSE、Agent Runtime、artifact renderer、run persistence 和共享 ArtifactPane。
- 不新增 Lisa、Alex、DeepSeek、visa 或单个 workflow 专属流式渲染分支。
- 不通过假进度、字符计数、静态 loading 页或本地模拟内容掩盖真实 artifact delta 缺失。
- 不破坏最终 artifact contract、Mermaid / `ai4se-visual` 渲染、artifact version 和 run snapshot。

## 复现场景

候选复现路径：

1. 打开 New Agents 任意会生成右侧 Artifact 的 workflow。
2. 发起一次生成。
3. 观察右侧 Artifact 是否在模型生成期间逐步出现正式内容。
4. 捕获 `/api/agent/runs/stream` SSE 事件，确认是否存在 `agent_delta.artifact_update` 或等价 artifact delta。
5. 对比后端 SSE、前端 parser、store 中的 `artifactContent` / stage artifact 更新和 ArtifactPane 实际显示。

## 排查方向

1. 捕获真实 SSE 流，确认后端是否持续发送 artifact 增量事件。
2. 检查 `stream_services.py` / `agent_runtime.py` 是否在 final 前生成并转发 artifact delta。
3. 检查前端 `llm.ts` 是否正确解析 artifact delta，且没有过滤掉有效 markdown。
4. 检查 store 是否在流式期间把 artifact delta 写入当前 stage artifact，而不是只在 final turn 写入。
5. 检查 ArtifactPane 是否被最终/旧状态覆盖，导致增量写入后没有渲染。
6. 检查不同 workflow/stage 是否行为一致，避免只修 CLARIFY 或单个阶段。

## 验收标准

- 至少一个代表性 workflow 的右侧 Artifact 在生成过程中稳定逐段更新。
- 后端 SSE 测试能证明 final 前存在有效 artifact delta。
- 前端 parser / store 测试能证明 artifact delta 会驱动右侧内容变化。
- UI 验证能证明用户在 final 前看到正式 artifact 内容逐步出现。
- 最终 artifact 与流式中间状态收敛一致，不出现调试占位、裸 JSON 或破碎 markdown。
- 第一阶段和第二阶段等关键阶段都不能退化为只在最终结果到达后更新。

## 建议测试

- 后端流式测试：mock structured artifact data 分块输出，断言 SSE final 前发送 artifact delta。
- 前端 service 测试：解析多个 artifact delta 并按顺序产出 artifact update。
- Store 测试：流式 artifact update 会更新当前 stage 的 artifact 内容。
- ArtifactPane 组件测试：生成中接收部分 artifact 时立即显示正式内容。
- 浏览器 / E2E smoke：发起一次生成，截图或事件断言 final 前右侧内容发生可见变化。

## 非目标

- 不先做流式位置 indicator；那是该 P0 修复后的体验增强。
- 不重做整个 ArtifactPane 信息架构。
- 不新增 workflow 专属渲染器。
- 不用本地假内容模拟流式成功。
