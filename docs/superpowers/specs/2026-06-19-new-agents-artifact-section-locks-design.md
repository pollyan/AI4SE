# New Agents Artifact Section Locks Design

## Current State Gap Analysis

ArtifactPane 已支持人工编辑、历史、冲突处理和前端批注，但用户仍无法保护已经确认的章节。todo 中的“章节锁定”适合先作为人工编辑保护能力落地：锁定当前 Markdown 标题章节后，手工保存时如果改动该章节，系统阻止保存并提示。

候选能力包：

- 章节锁定 MVP：在 ArtifactPane 中列出当前 artifact 的 Markdown 标题章节，支持锁定/解锁；保存人工编辑时校验锁定章节内容未被修改。
- 逐行接受/拒绝：需要 diff hunk 应用与版本合并语义，后续单独切片。
- PDF Mermaid 图形渲染：需要图形渲染或 canvas/svg 捕获，后续单独切片。

本轮选择章节锁定 MVP。

## User Story

作为工作区用户，当某个产出物章节已经被业务确认后，我可以锁定该章节。之后人工编辑时如果误改了锁定章节，系统会阻止保存并提示，从而避免已确认内容被覆盖。

## Scope

- 解析当前 artifact 的 Markdown `#` / `##` / `###` 标题章节。
- 批注工具条旁新增章节锁定入口。
- 用户可以锁定和解锁当前阶段的章节。
- 锁定记录绑定 workflow stage，包含 heading、content、createdAt。
- 保存人工编辑时，如果锁定章节缺失或内容变化，阻止保存并显示错误。
- 清空历史、切换 workflow、handoff 和恢复服务端 snapshot 时清理锁定记录。

## Non-Goals

- 不约束模型后续生成。
- 不写入服务端 run snapshot。
- 不处理重复标题的精确锚点。
- 不做局部只读编辑器或文本选区级锁定。

## Verification

- `npm run test -- --run src/__tests__/store.test.ts src/components/__tests__/ArtifactPane.test.tsx`
- `npm run lint`
- `npm run build`
- `git diff --check`
