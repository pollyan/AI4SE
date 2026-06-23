# E04 Lisa 测试资产质量闭环 Spec

## 背景

Lisa `TEST_DESIGN/CASES` 产物已经可以物化为测试资产集合，当前系统支持测试用例编辑、测试点覆盖状态更新、资产 issue 状态更新、风险矩阵编辑以及 intent-tester 映射记录。缺口在于这些动作还没有形成集合级“资产质量状态”：用户能处理局部项，但不能一眼判断测试资产是否仍有阻断缺口、哪些动作优先、处理后质量状态是否变化。

本 milestone 继续复用现有 New Agents test assets API、前端资产中心、持久化模型和共享 UI，不新增 Lisa 专属 runtime、SSE/API transport、store 或 renderer。

## 目标

为 Lisa 测试资产集合增加质量闭环：

- 后端在测试资产集合 payload 中返回集合级 `assetQuality` 摘要。
- 摘要聚合 pending/confirmed/ignored issue、未覆盖/部分覆盖测试点、风险处置状态、覆盖率和下一步动作。
- 前端资产中心展示“资产质量状态”，让用户能看到当前是否需要处理、需要关注或已就绪。
- 用户确认 issue、调整测试点覆盖、缓解/接受/关闭风险后，前端刷新集合并展示新的质量状态。

## 状态规则

`assetQuality.status` 使用三档：

- `needs_action`: 存在待处理 issue、未覆盖测试点或 open 风险。
- `monitoring`: 没有上述阻断项，但仍存在已确认 issue、部分覆盖测试点或 mitigating 风险。
- `ready`: 没有待处理/确认 issue，没有未覆盖/部分覆盖测试点，没有 open/mitigating 风险。

`assetQuality.nextActions` 使用确定性规则输出最多三条动作：

1. 有 pending issue 时，提示先确认或忽略资产问题。
2. 有未覆盖测试点时，提示补齐测试点覆盖。
3. 有 open 风险时，提示分配 owner 并进入缓解/接受/关闭。
4. 有部分覆盖测试点时，提示复核部分覆盖测试点。
5. 有 mitigating 风险时，提示跟踪缓解中的风险。
6. 没有动作时，提示测试资产质量已就绪。

## 非目标

- 不新增 intent-tester 自动执行或导入能力。
- 不新增数据库字段；质量状态由已持久化的 issue、test point、risk 和 coverage 数据派生。
- 不引入 LLM judge 或主观评分。
- 不改变 artifact contract、Agent Runtime、typed SSE 或 run persistence 主链路。

## 验收标准

- 后端 collection payload 包含 `assetQuality`。
- `assetQuality` 能随 issue status、test point status、risk status 改变。
- 前端 service 严格解析 `assetQuality`，异常 payload 显式失败。
- `TestAssetsPage` 展示资产质量状态、阻断统计和下一步动作。
- issue 状态更新后页面刷新集合并更新资产质量状态。
- 聚焦后端和前端测试通过，lint 和 diff check 通过。
