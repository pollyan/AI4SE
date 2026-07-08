# New Agents Artifact 批注新增 500 Bug Todo

状态：已归档
创建日期：2026-06-25
完成日期：2026-06-25
相关模块：`tools/new-agents/`

## 完成记录

2026-06-25 已修复：Artifact 批注继续通过共享 `/api/agent/runs/{runId}/artifact-collaboration` 整体协作状态接口保存，不新增单条批注或 workflow 专属 API。后端现在要求非空批注/章节锁引用的 stage 已有持久化 artifact version；缺失 artifact 返回明确 400，数据库保存异常会 rollback 并返回 `{ "error": "协作状态保存失败" }`，避免默认 Flask 500 HTML。前端 service 会透出后端错误消息，`ArtifactPane` 在协作状态同步失败时回滚本次 optimistic comments / sectionLocks 更新，避免本地显示未成功保存的批注。

验证覆盖：

- 有效 collaboration payload 保存和 run snapshot 恢复仍通过。
- 缺失 artifact version 的批注保存返回明确 400。
- 数据库异常返回统一 JSON 诊断。
- 前端非 2xx 响应展示后端错误消息。
- 前端新增批注同步失败后不保留本地假批注。

## 背景

New Agents 的 Artifact 区域已经加入批注能力，用户期望可以在产出物内容上添加批注，用于审阅、反馈、修订和后续协作。

用户反馈：每次新增批注时都会失败，并出现 500 错误。这说明批注功能入口已经可见，但新增批注链路在前端请求、后端 API、持久化模型、数据库迁移或错误处理中的某一环存在服务端异常。

## 当前问题

- 用户尝试新增 Artifact 批注时，请求返回 500。
- 批注无法保存，导致 Artifact 审阅闭环不可用。
- 500 错误属于服务端未被正确归因的失败，用户无法判断是输入问题、状态问题、run/artifact 缺失、数据库 schema 不匹配，还是后端异常。
- 如果失败发生在批注持久化或 run snapshot 协作状态替换路径，可能影响刷新后恢复、历史版本审阅和协作状态同步。

## 目标能力包

定位并修复 Artifact 批注新增时的 500 错误，让用户可以稳定添加批注，并在失败时看到可诊断错误。

修复应继续复用现有共享 Artifact 协作状态、run persistence、snapshot API、typed frontend service 和共享 UI，不新增 Lisa、Alex 或单个 workflow 专属的批注 API / store / renderer。

## 复现场景

候选复现路径：

1. 打开 New Agents 任意可生成 Artifact 的 workflow。
2. 生成或恢复一个包含右侧产出物的 run。
3. 在 Artifact 区域选择内容或点击批注入口。
4. 输入批注内容并提交。
5. 观察请求返回 500，批注未保存。

排查时需要记录：

- 触发请求的 URL、method、payload 和响应体。
- 后端日志中的异常堆栈。
- 当前 run 是否已经持久化，artifact 是否存在 version。
- 批注 API 使用的是单条新增语义，还是整体替换 collaboration state。
- 本地数据库是否完成了 artifact comment / collaboration 相关迁移。

## 排查方向

1. 检查前端批注提交 service 是否传入合法 `runId`、artifact/stage 标识、anchor、comment body 和当前协作状态。
2. 检查后端批注或 artifact collaboration route 是否正确校验请求，并把可预期的无效状态返回 4xx，而不是抛 500。
3. 检查 `run_persistence.py`、artifact comment / collaboration 数据表和迁移逻辑是否与当前代码字段一致。
4. 检查 run snapshot 恢复后的批注状态 shape 是否与保存接口期望一致。
5. 检查前端是否在没有 server run、没有 artifact version 或旧 run 状态下仍允许提交批注。

## 验收标准

- 对有效 run / artifact，新建批注请求成功，批注立即显示在 Artifact 审阅 UI 中。
- 刷新或恢复 run 后，新增批注仍存在。
- 对无效 run、缺失 artifact、非法 anchor 或空批注内容，接口返回明确 4xx 和可诊断错误，不返回 500。
- 前端能展示批注保存失败原因，不静默失败、不假装保存成功。
- 修复不得破坏现有 Artifact 编辑、版本历史、章节锁定、冲突处理、导出和 run snapshot 恢复能力。

## 建议测试

- 后端 API 测试：有效批注新增 / 协作状态保存成功。
- 后端 API 测试：缺失 run、缺失 artifact、非法 payload 返回明确 4xx。
- 后端持久化测试：批注保存后 run snapshot 能恢复批注状态。
- 前端 service 测试：批注提交 payload 与后端 contract 一致，失败时暴露错误。
- 前端组件测试：提交成功显示批注，提交失败显示错误且不污染本地状态。

## 非目标

- 不重新设计整个 Artifact 审阅系统。
- 不新增多人实时协作。
- 不新增 workflow / agent 专属批注链路。
- 不用前端假成功或本地-only 批注掩盖后端保存失败。
