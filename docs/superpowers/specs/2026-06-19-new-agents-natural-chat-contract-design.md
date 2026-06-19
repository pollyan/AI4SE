# New Agents 左侧自然对话契约设计

## 背景

用户希望左侧对话继续像聊天，不要升级成固定字段化摘要。当前 artifact contract prompt 中出现“本轮总结”等固定栏目词，容易让模型把每轮回复写成僵硬模板。

## 目标

- 左侧 `chat` 保持自然顾问式表达。
- 引导模型使用短段落、适度 bullet、少量重点强调，提升可扫描性。
- 不引入固定字段化 chat schema，不强制“本轮结论 / 已更新内容 / 需要确认”等每轮栏目。
- 继续保持 chat / artifact 职责分离，禁止把完整文档正文放入 chat。

## 验收

- 后端 contract prompt 明确自然顾问式表达要求。
- contract prompt 不再要求固定“本轮总结”栏目词。
- 现有 chat / artifact 分离校验继续有效。
