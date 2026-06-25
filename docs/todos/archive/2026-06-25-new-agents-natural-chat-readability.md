# New Agents 左侧自然聊天可读性优化记录

状态：已完成
创建日期：2026-06-25
完成日期：2026-06-25
相关模块：`tools/new-agents/`
用户反馈来源：本地 UI 使用反馈，Lisa 左侧对话阅读体验

## 背景

用户希望左侧对话在保留自然聊天和顾问式同步感的基础上，适度突出重点信息并增加条目化表达。上一轮把回复强制成固定格式后，实际效果变成“八股文”：每次都像模板化机器人回复，破坏了自然对话体验。

当前需要避免两个极端：

- 不要回到一整段长文本，导致重点、风险、确认项和右侧更新点难以扫读。
- 不要强制每次回复都套用固定数量 bullet、固定“重点标签”或固定段式结构，导致所有回复都像机械模板。

## 完成内容

- 前端 shared system prompt 改为按内容复杂度组织 chat：简单同步可以使用自然短段落；信息较多、存在风险或需要用户确认时，再使用短列表、少量重点加粗或引用块。
- 前端 prompt 明确禁止每轮固定 bullet 数量、每条固定标签和固定字段模板。
- 后端 artifact contract prompt 同步加入固定 bullet 数量、固定标签、固定栏目和固定字段模板的禁止要求。
- 后端 raw structured output instruction 移除重复的“2 到 4 个短段落或短列表”固定长度建议，改为按复杂度自然组织。
- 补充前端 prompt 测试和后端 contract/runtime 指令测试，防止再次回归到固定模板。

## 验收结果

- Prompt 不包含“每次必须输出固定数量 bullet”“每条必须以固定标签开头”等硬性模板规则。
- 简单场景可保持自然短段落，复杂场景可自然使用列表和加粗重点。
- 右侧产出物更新时，左侧仍要求说明右侧已更新，但不复制完整正文。
- UI 对 Markdown 加粗、列表、链接、引用、代码等内容保持可读。

## 验证

- `cd tools/new-agents/frontend && npm run test -- src/core/prompts/__tests__/buildSystemPrompt.test.ts`：通过，24 tests。
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py -q`：通过，87 tests。
- `cd tools/new-agents/frontend && npm run test -- src/components/__tests__/ChatPane.markdown.test.tsx`：通过，1 test。
- `cd tools/new-agents/frontend && npm run lint`：通过。
- `.venv/bin/python -m py_compile tools/new-agents/backend/agent_contracts.py tools/new-agents/backend/agent_runtime.py`：通过。

## 非目标

- 不要求逐字或逐句流式渲染左侧 chat。
- 不重写右侧 ArtifactPane 的产物格式。
- 不把所有 assistant 回复统一改成固定模板、固定标题或固定 bullet 数量。
