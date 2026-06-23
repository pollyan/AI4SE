# DeepSeek V4 格式化失败处置队列设计

## 背景

DeepSeek V4 结构化产物链路已经完成全 workflow 本地 readiness、`artifact_data` renderer、formatted-output 失败分类、retry prompt 诊断上下文，以及 Header 运行统计中的聚合 drilldown。当前剩余缺口不是再迁移某个 stage，而是当真实运行出现 formatted-output failure 时，用户只能看到总数、最高频类型、受影响 stage/provider，仍需要从“最近运行”里人工识别哪些错误属于格式化输出失败。

本轮把 DeepSeek V4 格式化输出需求推进为可操作的处置闭环：在共享运行统计中新增最近格式化失败队列，让用户按已有 workflow/stage 过滤后逐条看到失败类型、供应商、模型、重试次数、发生时间和行动建议。

## 用户故事

作为 New Agents 使用者，当 DeepSeek V4 生成出现 JSON、`artifact_data` schema、renderer 或 artifact contract 格式化失败时，我希望在运行统计中直接看到最近失败队列，并知道每一条应该检查 JSON mode、schema 字段、renderer 配置还是 artifact contract，从而能定位问题并决定重试、补充输入或修复配置。

## 范围

本轮包含：

1. 扩展共享 `/api/agent/observability` 响应中的 `formatFailureDiagnostics`，新增 `recentFailures`。
2. `recentFailures` 从现有 persisted turn metrics 派生，不新增表、不新增 DeepSeek 专属 API。
3. 每条失败包含 `turnId`、`runId`、`workflowId`、`stageId`、`provider`、`model`、`kind`、`label`、`errorCode`、`retryCount`、`createdAt`、`action`。
4. 前端 `observabilityService` 和 core types 严格解析新增字段。
5. Header 运行统计的“格式化输出诊断”区域展示处置队列，空态明确说明当前筛选范围没有格式化失败。
6. 更新 DeepSeek todo，记录格式化输出从聚合 drilldown 推进到逐条处置队列。

本轮不包含：

- 真实 DeepSeek API smoke；该验证仍需要用户提供凭证、网络和额度。
- 自动修复 `artifact_data` 或自动重试当前 run。
- 长期趋势图、LLM judge evidence、跨 run 产品质量评分。
- 新增 Lisa/Alex/DeepSeek 专属 runtime、API path、store 或 renderer。

## 行为契约

后端：

- `formatFailureDiagnostics.recentFailures` 只包含 formatted-output error code 对应的失败。
- 该队列受现有 `limit`、`workflowId`、`stageId` 查询约束影响。
- 队列按 `created_at desc, id desc` 排序，最多返回与 observability `limit` 一致的条目。
- 每条的 `kind` 来自现有 formatted-output error code mapping。
- `label` 和 `action` 复用现有 kind/provider 行动建议，不创建另一套文案来源。

前端：

- 解析缺失或类型错误的 `recentFailures` 时抛出 `Invalid observability summary response`。
- 当 `formatFailureDiagnostics.total > 0` 但 `recentFailures` 为空时展示空态，避免用户误以为没有失败。
- 每条失败在 Header 中显示 workflow/stage、provider/model、错误 label、重试次数、runId、时间和 action。

## 验收

1. 后端 endpoint test 证明 `recentFailures` 包含最近 formatted-output failures，并排除普通 schema/provider 错误。
2. 后端 endpoint test 证明 `workflowId`/`stageId` filter 会同步作用于 `recentFailures`。
3. 前端 service test 证明新增字段被严格解析，缺失字段会失败。
4. Header component test 证明运行统计弹窗显示处置队列和行动建议。
5. DeepSeek todo/README 记录本轮消化结果和真实 smoke 的外部依赖。

## 风险

- 现有 observability response contract 会新增字段；前端 parser 同步更新，旧测试需要补齐 payload。
- 如果 `limit` 很小，聚合 total 可能大于 recent queue 长度；UI 必须用“最近失败”措辞，不暗示全量列表。
- 真实 DeepSeek 是否减少失败频率不能由本轮证明；本轮只证明失败发生后的定位和处置闭环。
