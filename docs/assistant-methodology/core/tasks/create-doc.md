<!-- Powered by BMAD™ Core -->

# Create Document from Template (YAML Driven)

## ⚠️ CRITICAL EXECUTION NOTICE ⚠️

**THIS IS AN EXECUTABLE WORKFLOW - NOT REFERENCE MATERIAL**

当此任务被调用时：

1. **禁用所有效率优化** - 此工作流程需要完整的用户交互
2. **强制逐步执行** - 每个章节必须顺序处理并获得用户反馈
3. **澄清是必需的** - 当 `elicit: true` 时，您必须使用1-9格式并等待用户响应
4. **不允许捷径** - 不能在没有遵循此工作流程的情况下创建完整文档

**VIOLATION INDICATOR:** 如果您在没有用户交互的情况下创建完整文档，您已违反此工作流程。

## Critical: Template Discovery

如果没有提供YAML模板，请从core/templates目录列出所有模板或要求用户提供其他模板。

## CRITICAL: Mandatory Elicitation Format

**当 `elicit: true` 时，这是需要用户交互的硬停止：**

**您必须：**

1. 呈现章节内容
2. 提供详细理由（解释权衡、假设、做出的决定）
3. **停止并呈现编号选项1-9：**
   - **选项1：** 总是"继续下一章节"
   - **选项2-9：** 从data/clarification-methods选择8种方法
   - 结尾："选择1-9或直接输入您的问题/反馈："
4. **等待用户响应** - 在用户选择选项或提供反馈之前不要继续

**工作流程违规：** 在没有用户交互的情况下为elicit=true章节创建内容违反了此任务。

**永远不要问是/否问题或使用任何其他格式。**

## Processing Flow

1. **解析YAML模板** - 加载模板元数据和章节
2. **设置偏好** - 显示当前模式（交互式），确认输出文件
3. **处理每个章节：**
   - 如果条件不满足则跳过
   - 检查代理权限（owner/editors） - 如果章节限制给特定代理则注明
   - 使用章节指令起草内容
   - 呈现内容 + 详细理由
   - **如果 elicit: true** → 强制1-9选项格式
   - 如果可能保存到文件
   - 继续下一章节或等待用户指导

## 模板处理规则

### Variable Substitution
- `{{variable_name}}` - 在处理过程中替换为实际值
- 从用户输入或之前章节中收集变量值
- 未定义的变量提示用户输入

### Conditional Sections  
- `condition: "Has secondary user segment"` - 仅在条件满足时处理
- 根据之前收集的信息评估条件
- 跳过不适用的条件章节

### Repeatable Sections
- `repeatable: true` - 章节可以重复多次
- 询问用户是否需要添加更多实例
- 为每个实例使用相同的模板结构

## 交互模式

### Interactive Mode (默认)
- 每个elicit=true章节都需要用户确认
- 提供详细解释和改进选项
- 允许逐步完善和调整

### YOLO Mode  
- 快速生成完整草稿
- 仍然在elicit=true章节停止
- 减少解释，专注于内容生成

## 质量保证

### 内容验证
- 确保所有必需章节都已完成
- 验证章节之间的逻辑一致性
- 检查模板变量的正确替换

### 用户确认
- 每个关键章节获得用户批准
- 收集改进建议和修改
- 确保最终文档满足用户期望

## 文档输出

### 文件管理
- 根据模板output.filename设置保存文档
- 创建必要的目录结构
- 保持markdown格式和结构

### 版本控制
- 在重大修改时创建备份
- 跟踪文档变更历史
- 支持回滚到之前版本

## Error Handling

### 模板错误
- 无效YAML语法的优雅处理
- 缺少必需字段的警告
- 提供修复建议

### 用户输入错误
- 验证用户响应格式
- 处理无效选择
- 提供清晰的错误消息

## 与其他任务的集成

此任务被以下场景调用：
- `*create-prd` - 使用intelligent-prd-tmpl.yaml
- `*create-epics` - 使用epic-tmpl.yaml  
- `*create-stories` - 使用story-tmpl.yaml

确保与调用任务的无缝集成和数据传递。
