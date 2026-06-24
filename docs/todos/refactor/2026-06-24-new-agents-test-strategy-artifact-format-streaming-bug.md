# New Agents 测试策略阶段产物格式与流式渲染 Bug Todo

状态：活跃 Bug  
创建日期：2026-06-24  
相关模块：`tools/new-agents/`

## 背景

在用户称为 visa 的测试用例生成流程中，第二步“测试策略制定”阶段的右侧产出物存在固定复现的格式错误。用户观察到该阶段几乎每次生成都会出现格式异常。

同时，第一个阶段的右侧产出物可以按段落逐步流式渲染，但进入第二阶段后，右侧产出物不再按段落逐步生成，疑似与该阶段产物格式错误、结构化产物 contract 不稳定，或前端无法识别增量 artifact patch 有关。

## 当前问题

该问题同时影响两个用户体验层面：

- 产物质量：第二阶段“测试策略制定”的内容固定出现格式错误，最终右侧产物不像正式产物应有的结构。
- 流式体验：第一阶段可以一段一段生成，但第二阶段右侧产物无法按同样方式逐步渲染，可能退化为不连续、一次性显示或异常中断。

这类问题不能只在前端做展示兜底，因为格式错误可能源于后端 agent contract、prompt 模板、artifact_data schema、typed SSE payload 或前端 artifact renderer 之间的不一致。

## 目标能力包

定位并修复测试用例生成流程第二阶段“测试策略制定”的产物格式错误，并恢复右侧产物与第一阶段一致的增量流式渲染体验。

该能力包必须继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run / artifact 模型和共享 UI 渲染基础设施，不允许为 visa、Lisa、Alex、DeepSeek 或未来 agent 新增专属 runtime、API path、store 或 renderer。

## 复现场景

候选复现路径：

1. 打开 New Agents 测试用例生成流程。
2. 选择或输入一个测试用例生成需求。
3. 完成第一阶段并进入第二阶段“测试策略制定”。
4. 观察右侧产出物生成过程和最终格式。

预期应重点记录：

- 第二阶段是否每次都出现固定格式错误。
- 错误具体表现是 markdown 标题错乱、列表/表格断裂、JSON/结构化字段不合法，还是 artifact renderer 显示异常。
- typed SSE 中是否持续发送 artifact 增量事件。
- 后端最终持久化的 artifact_data 是否已经格式错误。
- 前端接收到的数据是否正确但渲染层丢失增量。

## 排查方向

需要按系统化调试方式先定位根因，再实现修复：

1. 对比第一阶段和第二阶段的 workflow manifest、stage prompt、artifact template、artifact contract 和 backend contract。
2. 捕获第二阶段 typed SSE 流，确认是否有 artifact delta / artifact_data 分段事件。
3. 检查后端生成的第二阶段 `artifact_data` 是否能通过 schema / contract 校验。
4. 检查前端 stream parser 是否因为第二阶段字段名、section id、artifact kind 或 patch shape 不一致而放弃增量渲染。
5. 对比第一阶段工作样例，找出第二阶段与可流式渲染产物之间的结构差异。
6. 检查最终持久化 artifact 与前端实时渲染 artifact 是否一致。

## 验收标准

- 第二阶段“测试策略制定”的右侧产物不再出现固定格式错误。
- 第二阶段产物在生成过程中能够像第一阶段一样按结构段落逐步渲染。
- 最终右侧产物格式与正式产物渲染一致，不出现临时调试文本、裸 JSON、破碎 markdown 或缺失 section。
- 后端输出的第二阶段 `artifact_data` 通过共享 artifact contract 校验。
- 前端 typed SSE parser 能正确处理第二阶段 artifact 增量事件，并在最终 artifact 到达时平滑替换或收敛。
- 修复不得引入 workflow 专属渲染分支或绕过共享 Agent Runtime。

## 建议测试

- 后端 contract 测试：第二阶段“测试策略制定”样例输出必须通过 artifact_data schema 和阶段 contract 校验。
- SSE 流测试：第二阶段运行过程中应产生可识别的 artifact 增量事件，而不只是最终完整产物。
- 前端 stream parser 测试：第二阶段 artifact delta 能逐段更新右侧产物视图。
- 前端 renderer 测试：第二阶段最终 artifact 使用与正式产物一致的 renderer，格式稳定。
- 回归测试：第一阶段现有段落级流式渲染不被破坏。
- 端到端或等价验收：完整跑一次测试用例生成流程，确认第一阶段和第二阶段右侧产物都能逐步渲染且最终格式正确。

## 非目标

- 不重新设计所有阶段的产物格式。
- 不把第二阶段改成专属前端 renderer。
- 不通过隐藏格式错误、降级为纯文本或展示数字进度来掩盖结构化产物问题。
- 不改变阶段推进成熟度门禁；该问题由单独的阶段推进成熟度门禁 todo 处理。

## 待决策问题

- “visa 测试用例生成流程”的正式 workflow / agent id 名称是什么，是否需要在 todo 消化时先统一命名？
- 第二阶段格式错误的最小可复现输入是什么？
- 该阶段应采用段落级流式、section 级流式，还是 artifact_data patch 级流式作为验收口径？
- 如果模型输出天然不稳定，是否需要在 prompt contract 之外增加后端结构化校验与拒绝重试机制？
