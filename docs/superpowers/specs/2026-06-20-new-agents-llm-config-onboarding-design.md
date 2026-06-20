# New Agents 首次模型配置自检与修复闭环设计

## 用户故事

作为首次部署或默认模型配置异常后的 New Agents 用户，当我进入 Lisa / Alex 工作区并发现默认 LLM 未配置时，我希望不用离开产品页面，就能打开模型设置、维护 Base URL / 模型名称 / API Key、保存配置、检测连接，并在配置可用后继续当前工作流。

## 当前问题

`SettingsModal` 已经支持读取、保存和检测后端默认 LLM 配置，后端 `/api/config` 也支持创建、更新和检测默认配置。但 `Workspace` 的首次缺配置遮罩仍停留在静态说明，只告诉用户检查后端 `llm_config` 或环境变量，并只提供“我知道了”。这会让用户在产品内已有设置能力的情况下仍被引导到产品外处理，形成首次使用断点。

## 范围

- `Workspace` 默认 LLM 缺失遮罩必须提供可操作路径：
  - 打开模型设置。
  - 重新检查配置状态。
  - 展示检查中、成功和失败状态。
- `SettingsModal` 保存成功和连接检测成功后，应通知 `Workspace` 重新检查默认配置状态。
- 保存或检测失败时，不关闭缺配置遮罩，不伪装成功，保留明确错误。
- 继续复用共享 `/new-agents/api/config`、`/new-agents/api/config/check` 和全局设置弹窗，不新增 Lisa / Alex / workflow 专属模型分支。

## 非目标

- 不新增多 provider 管理页。
- 不在前端保存个人 API Key。
- 不为不同 workflow 增加模型选择。
- 不运行真实供应商 smoke；该验证需要外部凭证、网络和额度。
- 不改变后端配置契约，除非测试证明现有契约无法支撑本闭环。

## 用户场景

### 场景 1：首次进入缺配置工作区

Given `/new-agents/api/config` 返回 `hasDefault: false`
When 用户进入 `/new-agents/workspace/lisa/test-design`
Then 缺配置遮罩显示当前阻断原因，并提供“打开模型设置”和“重新检查配置”操作。

### 场景 2：保存配置后解除阻断

Given 缺配置遮罩正在显示
When 用户在设置中填写 Base URL、模型名称和 API Key 并保存成功
Then `Workspace` 重新检查默认配置；如果后端返回 `hasDefault: true`，缺配置遮罩关闭，用户回到当前工作区。

### 场景 3：检测连接后解除阻断

Given 缺配置遮罩正在显示
When 用户在设置中点击检测连接且结果为成功
Then `Workspace` 重新检查默认配置；如果后端返回 `hasDefault: true`，缺配置遮罩关闭。

### 场景 4：失败反馈

Given 用户保存或检测失败
When 后端返回错误或网络失败
Then 设置弹窗显示失败原因，缺配置遮罩仍保留，用户可以修正后重试。

## 验收条件

1. `Workspace` 在默认 LLM 缺失时提供打开设置和重新检查配置的操作入口。
2. `Workspace` 能响应设置保存成功事件并重新检查 `/new-agents/api/config`。
3. `Workspace` 能响应设置检测成功事件并重新检查 `/new-agents/api/config`。
4. 配置仍缺失、保存失败、检测失败或接口异常时，遮罩不会误关闭。
5. 前端测试覆盖 onboarding、设置保存回调、设置检测回调和失败保持阻断。
6. 后端 API 契约不改变；既有 config API 测试仍然有效。

## 风险

- `Workspace` 和 `SettingsModal` 都使用全局 store，事件通知如果持久化会污染工作区状态。设计上应使用轻量内存事件或回调状态，不进入持久化数据。
- `Workspace` 已有“对话开始后不显示旧 onboarding”的保护，新增复检逻辑不能重新打开过期遮罩。
- 缺配置遮罩不能在保存成功但后端仍返回 `hasDefault: false` 时关闭。

## 验证计划

- 先写失败测试：
  - `tools/new-agents/frontend/src/pages/__tests__/Workspace.test.tsx`
  - `tools/new-agents/frontend/src/components/__tests__/SettingsModal.test.tsx`
- 聚焦验证：
  - `cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/Workspace.test.tsx src/components/__tests__/SettingsModal.test.tsx`
- 扩大验证：
  - `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/configService.test.ts src/components/__tests__/Header.test.tsx src/components/__tests__/ChatPane.test.tsx`
  - `cd tools/new-agents/frontend && npm run lint`
  - `cd tools/new-agents/frontend && npm run build`
  - `git diff --check`
