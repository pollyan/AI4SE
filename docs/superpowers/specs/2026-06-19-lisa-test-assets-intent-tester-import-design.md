# Lisa 测试资产导入 intent-tester 设计

## 背景

Lisa 测试资产已经能从 `TEST_DESIGN/CASES` artifact 生成 `intentTesterDrafts`，但当前只能只读展示，不能从 New Agents UI 写入 intent-tester。草稿本身也带有 `draftWarnings`，提示导入前仍需人工校准页面 URL、定位语义和可执行步骤，因此本轮不做自动批量写入。

## 用户故事

作为 Lisa 用户，我希望在“测试资产”弹层里对单条测试用例点击导入，把对应 intent-tester 草稿写入 `/intent-tester/api/testcases`，并看到导入成功的用例 ID，从而打通从测试设计到测试管理工具的第一步。

## 范围

进入本轮：

- 将 `intentTesterDrafts` 从松散 `Record<string, unknown>` 收紧为前端类型。
- 新增前端 service，POST 单条草稿到 `/intent-tester/api/testcases` 并校验标准响应。
- 在 Header 测试资产弹层中为有草稿的用例展示“导入 TC-xxx”按钮。
- 导入成功后显示 intent-tester 用例 ID；失败时显示错误状态。

不进入本轮：

- 不自动批量导入。
- 不启动 intent-tester 执行。
- 不反写 New Agents 后端资产状态。
- 不解决草稿 URL、定位语义和步骤可执行性校准。

## 验收条件

1. service 按 intent-tester 标准响应解析创建结果，协议异常显式失败。
2. 测试资产弹层能对 `sourceCaseId` 匹配的草稿触发导入。
3. 成功后 UI 显示 “已导入 intent-tester #id”。
4. 失败后 UI 显示 “无法导入 intent-tester”。
5. 相关前端测试、TypeScript 检查和 `git diff --check` 通过。
