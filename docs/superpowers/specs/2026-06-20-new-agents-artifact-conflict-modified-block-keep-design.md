# New Agents Artifact 冲突修改块保留服务端设计

## 背景

Artifact 保存冲突中已经支持识别相邻的服务端删除块和草稿新增块，并允许用户采纳草稿修改块。但用户也需要反向决策：当服务端较新版本更可信时，一键保留服务端修改块并放弃草稿对应修改。

## 目标

- 在修改块起始行提供 `保留服务端` 操作。
- 点击后以服务端当前版本作为编辑草稿，保留服务端该修改块和其他服务端更新。
- 记录 `artifact_merge_block_modified_kept` 活动轨迹，便于后续审计人工合并决策。
- 复用现有冲突 diff、Artifact 审计和手工编辑状态，不新增 workflow/agent 专属分支。

## 非目标

- 不实现完整三方 merge 自动推断。
- 不改变保存接口或服务端冲突检测协议。
- 不移除现有逐行采纳/丢弃、新增块采纳/丢弃和修改块采纳能力。

## 设计

1. 复用现有 `conflictDraftModifiedBlockByAddedStartIndex` 修改块识别结果。
2. 在修改块按钮组中增加 `保留服务端`。
3. 触发后将 `editDraft` 设置为 `conflictArtifact.content`。
4. 使用现有 Artifact 审计写入本地活动事件：
   - `eventType`: `artifact_merge_block_modified_kept`
   - `summary`: 包含服务端块与草稿块的对照标签。

## 验收

- 修改块旁同时存在 `采纳修改块` 和 `保留服务端`。
- 点击 `保留服务端` 后，编辑草稿等于服务端当前版本。
- 活动轨迹记录保留服务端修改块的人工决策。
