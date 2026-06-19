# New Agents Artifact 受控人工修改设计

## 背景

右侧 Artifact 已支持历史版本、diff、恢复和导出，但用户还不能直接校准产出物正文。用户此前也询问过是否支持人工修改产出物来校准优先级，因此需要先补一个最小可用的受控编辑闭环。

## 目标

- 用户可以在 ArtifactPane 进入编辑模式，修改当前阶段 Markdown。
- 保存时更新当前右侧产出物和当前阶段 `stageArtifacts`。
- 保存时把人工修改写入 `artifactHistory`，便于后续 diff / 恢复。
- 如果当前内容尚未在历史中，保存前先保留一个当前版本备份，避免人工修改覆盖掉唯一可恢复状态。
- 取消编辑不修改 artifact、stage artifact 或 history。

## 非目标

- 本切片不做服务端 artifact update API。
- 本切片不做章节锁定、批注、逐行接受/拒绝。
- 本切片不重做 Word/PDF 富排版导出。

## 验收

- ArtifactPane 测试覆盖进入编辑、保存、取消和 history/stageArtifacts 同步。
- 不新增 workflow-specific UI 或运行时分支。
