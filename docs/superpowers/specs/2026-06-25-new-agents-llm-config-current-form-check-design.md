# New Agents LLM Config Current Form Check Design

## CGA 摘要

`docs/todos/refactor/2026-06-24-new-agents-llm-config-check-false-negative.md` 是当前活跃 Bug。当前设置弹窗点击“检测连接”只 POST `/new-agents/api/config/check` 且无 body；后端 `/api/config/check` 只读取已保存默认配置。用户在表单中输入一组可用配置但尚未保存时，检测到的是旧配置，因此会出现“测试失败但保存后 workflow 正常”的假失败。

## 用户故事

作为 New Agents 用户，我在设置弹窗输入一组模型配置后，点击“检测连接”应检测当前表单配置；如果留空 API Key，则复用已保存默认密钥，语义与保存配置保持一致；检测不会持久化临时配置，也不会回显密钥。

## 设计

前端 `SettingsModal` 构造与保存配置相同的 payload，并 POST 到 `/new-agents/api/config/check`。当 API Key 输入框为空时，不发送 `apiKey` 字段。

后端 `/api/config/check` 保持兼容：

- 无请求 body：检测已保存默认配置，供现有 `configService.checkDefaultLlmConfig()` 继续使用。
- 有请求 body：按默认配置 update schema 校验 `baseUrl`、`model`、`description` 和可选 `apiKey`，构造临时 `LlmConfig` 对象用于检测，不写入数据库。
- 有请求 body 且 `apiKey` 为空时，复用已保存默认配置的密钥；若没有已保存默认配置，则返回 400。

成功和失败响应仍不包含 `apiKey`。

## 非目标

- 不重做设置 UI。
- 不改变 `/api/agent/runs/stream` 的默认配置读取语义。
- 不跳过真实模型检测，不用假成功掩盖失败。
- 不新增 workflow、agent 或供应商专属检测路径。

## 验收

- 设置弹窗检测请求携带当前表单 `baseUrl`、`model`、`description` 和非空 `apiKey`。
- 设置弹窗检测成功不触发默认配置变更通知，只有保存配置触发。
- 后端用带 body 的临时配置调用检测 helper，且不会持久化临时字段。
- 后端带 body 但无 `apiKey` 时可以复用已保存密钥。
- 后端无 body 的默认配置检测保持兼容。
