# New Agents Artifact add_after Patch 设计

## Current State Gap Analysis

- 前端已支持 `artifact_patch` typed SSE 消费，但 patch operation 只有 `replace`，只能替换 base 中已存在且安全的章节。
- 后端 partial `artifact_data` renderer 的常见流式形态是逐步追加章节，例如先输出“需求事实清单”，随后追加“被测系统与边界”。
- 若后端把新增章节伪装成 `replace`，前端会因锚点不存在而降级，不能形成真实局部更新。
- 因此本切片扩展共享 patch contract：新增 `add_after` operation，用 `afterSectionAnchor` 明确插入位置，同时继续携带完整 `artifact_update.markdown` 作为事实源和 fallback。

## Selected Slice

实现端到端 `add_after` patch：

- 前端 `ArtifactSectionPatch` 支持 `replace | add_after`。
- 前端 `applyArtifactSectionPatch(...)` 对 `add_after` 执行 base 校验、锚点校验、单章节校验和插入。
- 前端 typed SSE parser 校验 `add_after` 必须包含非空 `afterSectionAnchor`。
- 后端 `AgentTurnOutput` / `AgentTurnDeltaOutput` 支持可选 `artifact_patch`。
- 后端 partial renderer 在当前 partial markdown 相对上一个 partial markdown 只追加一个章节时生成 `add_after` patch。
- 不新增 agent/workflow 专属 runtime、SSE path、store 或渲染管线。

## Contract

```json
{
  "operation": "add_after",
  "sectionAnchor": "h2:2. 被测系统与边界:1",
  "afterSectionAnchor": "h2:1. 需求事实清单:1",
  "replacementMarkdown": "## 2. 被测系统与边界\n...",
  "baseContent": "# 需求分析文档\n\n## 1. 需求事实清单\n..."
}
```

Rules:

- `artifact_patch` remains optional and must appear with `artifact_update.type="replace"` and full markdown.
- `replace` keeps current semantics and must not require `afterSectionAnchor`.
- `add_after` requires `afterSectionAnchor`; `sectionAnchor` is the new section anchor.
- Patch application is best-effort. Any mismatch falls back to full markdown replacement.
- For `add_after`, inserting a complete table or Mermaid section is allowed because the patch does not edit inside existing structured blocks.

## Acceptance

- Frontend store can apply an `add_after` patch and keep full artifact content as source of truth.
- Frontend parser rejects malformed `add_after` patches.
- Backend SSE schema serializes patch fields using frontend camelCase names.
- Backend raw JSON paragraph-level CLARIFY stream emits an `add_after` patch when the second partial frame appends “## 2. 被测系统与边界”.
- Stream service preserves patch metadata in both `agent_delta` and final `agent_turn`.
- Existing full markdown fallback remains intact.

## Non-goals

- Do not support arbitrary insertion before a section.
- Do not generate patches for multi-section additions in this slice.
- Do not remove full markdown payloads.
- Do not implement ReactMarkdown memoized section rendering here.
