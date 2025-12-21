# Lisa v2 已知问题

## 1. Workflow A 递归限制问题

**问题描述：**
当意图识别通过门控，进入 workflow A（新需求/功能测试设计）后，会触发递归限制错误：
```
Recursion limit of 25 reached without hitting a stop condition
```

**原因：**
`clarification_node` 在执行后没有正确设置 `gate_passed = True`，导致图一直在 clarification_node 和自身之间循环。

**临时解决方案：**
暂时只使用意图识别功能，不进入具体工作流。

**待修复：**
1. 检查 `clarification_node` 的门控逻辑
2. 确保在需求澄清完成后设置 `gate_passed = True`
3. 测试 workflow_a 的完整流程

## 2. 更新日志

### 2025-12-21
- ✅ 实现了 LLM 驱动的意图识别（使用 HTML 注释标记）
- ✅ 改进了欢迎语，包含服务范围介绍
- ⚠️ 发现 workflow A 递归问题（待修复）
