# New Agents Artifact 历史 Diff 逐行审阅实施计划

## 范围

为 ArtifactPane 历史版本差异视图增加最小行级审阅能力：历史缺失行可恢复，当前新增行可丢弃。

## TDD 步骤

1. RED：在 `ArtifactPane.test.tsx` 增加测试，构造当前 artifact 与历史版本差异，点击 `恢复此行：旧结论`，断言当前 artifact/stage artifact 包含旧结论，并写入修改前备份。
2. RED：增加测试，点击 `丢弃当前行：新结论`，断言当前 artifact/stage artifact 删除新结论，并写入修改前备份。
3. GREEN：在 `ArtifactPane.tsx` 中实现 `applyHistoryLineReview`，统一处理更新 artifact、写 history 备份和保持历史 modal 打开。
4. GREEN：为 diff 中 `removed` 行渲染 `恢复此行`，为 `added` 行渲染 `丢弃当前行`。
5. REFACTOR：复用当前 stage id 和现有 `buildLineDiff`，不引入新 diff 算法。
6. 验证：运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`、组合测试、`npm run lint`、`npm run build`、`git diff --check`。

## 风险控制

- 每次行级操作都会先备份当前 artifact，避免用户丢失可恢复版本。
- 只处理非空行；空行不显示操作。
- 行恢复使用历史版本中的行位置作为插入参考，复杂冲突先保持可解释的保守行为。
