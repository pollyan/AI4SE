# STORY-012: 集成智能提示到测试用例编辑器

**Story ID**: STORY-012  
**Epic**: EPIC-001 数据流核心功能  
**Sprint**: Sprint 3  
**优先级**: High  
**估算**: 5 Story Points  
**分配给**: Frontend Developer + UX Designer  
**创建日期**: 2025-01-30  
**产品经理**: John  

---

## 📖 故事描述

**作为** 测试工程师  
**我希望** 在测试用例编辑器中使用智能变量提示功能  
**以便** 我可以在编辑步骤参数时获得IDE级的变量引用体验  
**这样** 我就能高效准确地配置复杂的数据驱动测试用例，避免变量引用错误  

---

## 🎯 验收标准

### AC-1: 步骤编辑器集成SmartVariableInput
**给定** 我在测试用例编辑器中编辑步骤参数  
**当** 我在支持变量引用的输入字段中输入时  
**那么** 应该自动使用SmartVariableInput组件提供智能提示  

**集成要求**:
- 所有文本类型的参数字段都支持智能提示
- 自动检测当前执行上下文或测试用例上下文
- 提示菜单位置自适应，避免被遮挡
- 保持原有的参数验证和错误提示功能

### AC-2: 上下文感知的变量提示
**给定** 我正在编辑测试用例的第N个步骤  
**当** 智能提示激活时  
**那么** 应该只显示第N步之前可用的变量  

**上下文感知特性**:
- 根据当前编辑的步骤索引过滤变量
- 实时预览模式：基于当前测试用例的模拟执行上下文
- 历史执行模式：基于历史执行数据提供建议
- 清晰标识变量来源步骤

### AC-3: 参数字段智能识别
**给定** 不同的Action类型有不同的参数字段  
**当** 我编辑参数时  
**那么** 系统应该智能识别哪些字段支持变量引用  

**智能识别规则**:
```javascript
const VARIABLE_SUPPORTED_FIELDS = {
  'ai_input': ['text', 'locate'],
  'ai_tap': ['locate'],
  'ai_assert': ['condition'],
  'aiQuery': ['query'],
  'aiString': ['query'],
  'aiNumber': ['query'],
  'aiBoolean': ['query'],
  'aiAsk': ['query'],
  'navigate': ['url'],
  'wait': [] // 不支持变量引用
};
```

### AC-4: 实时参数预览
**给定** 我在参数中使用了变量引用  
**当** 我完成输入时  
**那么** 应该显示解析后的参数值预览  

**预览功能**:
- 在输入框下方显示"预览值：搜索iPhone 15，价格999元"
- 支持复杂嵌套对象的预览
- 变量解析失败时显示错误提示
- 实时更新预览内容

### AC-5: 表单验证增强
**给定** 步骤参数包含变量引用  
**当** 我保存步骤配置时  
**那么** 应该验证变量引用的有效性  

**验证增强**:
- 实时验证变量引用语法
- 检查引用的变量是否存在
- 验证属性路径的正确性
- 提供具体的修复建议

### AC-6: 批量编辑支持
**给定** 我需要为多个步骤设置相似的变量引用  
**当** 我使用批量编辑功能时  
**那么** 智能提示应该在批量编辑模式下正常工作  

**批量编辑特性**:
- 支持同时编辑多个步骤的参数
- 变量建议基于所有步骤的上下文
- 批量替换变量引用
- 统一的验证和错误提示

---

## 🔧 技术实现要求

### React组件集成
```tsx
// web_gui/static/js/components/StepEditor.tsx

import React, { useState, useEffect, useCallback } from 'react';
import { SmartVariableInput } from './SmartVariableInput';
import { StepParameterForm } from './StepParameterForm';

interface StepEditorProps {
  step: TestStep;
  stepIndex: number;
  testCaseId?: number;
  executionId?: string;
  onStepChange: (step: TestStep) => void;
}

export const StepEditor: React.FC<StepEditorProps> = ({
  step,
  stepIndex, 
  testCaseId,
  executionId,
  onStepChange
}) => {
  const [parameterValues, setParameterValues] = useState(step.params || {});
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [previewValues, setPreviewValues] = useState<Record<string, string>>({});

  // 检查字段是否支持变量引用
  const isVariableSupportedField = useCallback((fieldName: string): boolean => {
    const supportedFields = VARIABLE_SUPPORTED_FIELDS[step.action] || [];
    return supportedFields.includes(fieldName);
  }, [step.action]);

  // 渲染参数输入字段
  const renderParameterField = (fieldName: string, fieldConfig: ParameterFieldConfig) => {
    const value = parameterValues[fieldName] || '';
    const hasError = validationErrors[fieldName];
    const previewValue = previewValues[fieldName];

    if (isVariableSupportedField(fieldName)) {
      return (
        <div key={fieldName} className="parameter-field">
          <label className="form-label">
            {fieldConfig.label}
            {fieldConfig.required && <span className="required">*</span>}
          </label>
          
          <SmartVariableInput
            value={value}
            onChange={(newValue) => handleParameterChange(fieldName, newValue)}
            executionId={executionId}
            currentStepIndex={stepIndex}
            placeholder={fieldConfig.placeholder}
            className={hasError ? 'error' : ''}
          />
          
          {hasError && (
            <div className="error-message">{hasError}</div>
          )}
          
          {previewValue && previewValue !== value && (
            <div className="preview-value">
              <span className="preview-label">预览值：</span>
              <span className="preview-content">{previewValue}</span>
            </div>
          )}
        </div>
      );
    } else {
      // 普通输入字段
      return (
        <div key={fieldName} className="parameter-field">
          <label className="form-label">{fieldConfig.label}</label>
          <input
            type={fieldConfig.type || 'text'}
            value={value}
            onChange={(e) => handleParameterChange(fieldName, e.target.value)}
            placeholder={fieldConfig.placeholder}
            className={hasError ? 'form-input error' : 'form-input'}
          />
          {hasError && <div className="error-message">{hasError}</div>}
        </div>
      );
    }
  };

  // 处理参数变更
  const handleParameterChange = useCallback(async (fieldName: string, value: string) => {
    const newParams = { ...parameterValues, [fieldName]: value };
    setParameterValues(newParams);

    // 实时验证和预览
    if (isVariableSupportedField(fieldName) && value.includes('${')) {
      try {
        // 调用变量验证API
        const validationResult = await validateVariableReference(value, executionId, stepIndex);
        
        if (validationResult.is_valid) {
          setPreviewValues(prev => ({ ...prev, [fieldName]: validationResult.resolved_value }));
          setValidationErrors(prev => ({ ...prev, [fieldName]: '' }));
        } else {
          setValidationErrors(prev => ({ ...prev, [fieldName]: validationResult.error }));
          setPreviewValues(prev => ({ ...prev, [fieldName]: '' }));
        }
      } catch (error) {
        console.warn('变量验证失败:', error);
      }
    } else {
      setPreviewValues(prev => ({ ...prev, [fieldName]: '' }));
      setValidationErrors(prev => ({ ...prev, [fieldName]: '' }));
    }

    // 通知父组件
    onStepChange({
      ...step,
      params: newParams
    });
  }, [parameterValues, step, stepIndex, executionId, onStepChange]);

  return (
    <div className="step-editor">
      <div className="step-header">
        <h3>步骤 {stepIndex + 1}: {getActionDisplayName(step.action)}</h3>
      </div>
      
      <div className="step-parameters">
        {getParameterFields(step.action).map(([fieldName, fieldConfig]) => 
          renderParameterField(fieldName, fieldConfig)
        )}
      </div>
      
      <div className="step-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          取消
        </button>
        <button type="button" className="btn btn-primary" onClick={onSave}>
          保存
        </button>
      </div>
    </div>
  );
};
```

### 上下文管理服务
```typescript
// web_gui/static/js/services/VariableContextService.ts

export class VariableContextService {
  private testCaseId?: number;
  private executionId?: string;
  private cachedVariables: Map<number, VariableData[]> = new Map();

  constructor(testCaseId?: number, executionId?: string) {
    this.testCaseId = testCaseId;
    this.executionId = executionId;
  }

  async getAvailableVariables(stepIndex: number): Promise<VariableData[]> {
    // 缓存检查
    if (this.cachedVariables.has(stepIndex)) {
      return this.cachedVariables.get(stepIndex)!;
    }

    let variables: VariableData[] = [];

    if (this.executionId) {
      // 基于实际执行数据
      variables = await this.fetchExecutionVariables(stepIndex);
    } else if (this.testCaseId) {
      // 基于历史执行数据的预测
      variables = await this.predictVariables(stepIndex);
    }

    // 缓存结果
    this.cachedVariables.set(stepIndex, variables);
    return variables;
  }

  private async fetchExecutionVariables(stepIndex: number): Promise<VariableData[]> {
    const response = await fetch(
      `/api/v1/executions/${this.executionId}/variable-suggestions?step_index=${stepIndex}`
    );
    
    if (!response.ok) {
      throw new Error('获取执行变量失败');
    }
    
    const data = await response.json();
    return data.variables || [];
  }

  private async predictVariables(stepIndex: number): Promise<VariableData[]> {
    // 基于测试用例的历史执行记录预测可能的变量
    const response = await fetch(
      `/api/v1/testcases/${this.testCaseId}/predicted-variables?step_index=${stepIndex}`
    );
    
    if (!response.ok) {
      return []; // 预测失败时返回空数组
    }
    
    const data = await response.json();
    return data.predicted_variables || [];
  }

  clearCache(): void {
    this.cachedVariables.clear();
  }
}
```

### API验证集成
```typescript
// web_gui/static/js/utils/variableValidation.ts

export interface ValidationResult {
  is_valid: boolean;
  resolved_value?: string;
  error?: string;
  suggestion?: string;
}

export async function validateVariableReference(
  reference: string,
  executionId?: string,
  stepIndex?: number
): Promise<ValidationResult> {
  if (!executionId) {
    // 没有执行上下文时的基础语法验证
    return validateSyntaxOnly(reference);
  }

  try {
    const response = await fetch(`/api/v1/executions/${executionId}/variables/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        references: [reference],
        step_index: stepIndex
      })
    });

    if (!response.ok) {
      throw new Error('验证请求失败');
    }

    const data = await response.json();
    return data.validation_results[0] || { is_valid: false, error: '验证失败' };
  } catch (error) {
    console.warn('变量验证API调用失败:', error);
    return validateSyntaxOnly(reference);
  }
}

function validateSyntaxOnly(reference: string): ValidationResult {
  const variablePattern = /^\$\{[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*(\[\d+\])*\}$/;
  
  if (variablePattern.test(reference)) {
    return { is_valid: true };
  } else {
    return {
      is_valid: false,
      error: '变量引用语法错误',
      suggestion: '使用格式: ${variable_name} 或 ${object.property}'
    };
  }
}
```

### CSS样式增强
```css
/* web_gui/static/css/step-editor.css */

.step-editor {
  background: white;
  border-radius: 8px;
  border: 1px solid #e1e5e9;
  padding: 20px;
  margin-bottom: 16px;
}

.step-parameters {
  margin: 16px 0;
}

.parameter-field {
  margin-bottom: 16px;
}

.parameter-field .form-label {
  display: block;
  margin-bottom: 4px;
  font-weight: 500;
  color: #374151;
}

.parameter-field .required {
  color: #ef4444;
  margin-left: 4px;
}

.parameter-field .smart-variable-input {
  width: 100%;
}

.preview-value {
  margin-top: 4px;
  padding: 8px 12px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  font-size: 14px;
}

.preview-label {
  color: #64748b;
  font-weight: 500;
}

.preview-content {
  color: #1e293b;
  font-family: 'Monaco', 'Menlo', monospace;
}

.error-message {
  margin-top: 4px;
  color: #ef4444;
  font-size: 14px;
}

.step-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

/* 智能提示菜单在编辑器中的位置调整 */
.step-editor .variable-suggestion-dropdown {
  z-index: 1001; /* 确保在编辑器模态框之上 */
}

/* 批量编辑模式样式 */
.batch-edit-mode .step-editor {
  border-left: 4px solid #3b82f6;
}

.batch-edit-mode .parameter-field {
  position: relative;
}

.batch-edit-mode .parameter-field::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 20px;
  height: 20px;
  background: #3b82f6;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

---

## 🧪 测试计划

### 组件集成测试
1. **SmartVariableInput集成测试**
   ```tsx
   test('SmartVariableInput在步骤编辑器中正常工作', () => {
     render(
       <StepEditor 
         step={{ action: 'ai_input', params: {} }}
         stepIndex={2}
         executionId="test-exec"
         onStepChange={mockOnChange}
       />
     );
     
     const textInput = screen.getByPlaceholderText('输入文本内容');
     user.type(textInput, '${');
     
     expect(screen.getByTestId('suggestion-dropdown')).toBeVisible();
   });
   ```

2. **上下文感知测试**
3. **参数验证测试**
4. **预览功能测试**

### 用户体验测试
1. **键盘导航测试**
2. **响应式布局测试**
3. **错误处理测试**
4. **性能测试**

### 端到端测试
1. **完整编辑流程测试**
2. **复杂变量引用测试**
3. **批量编辑测试**

---

## 📊 Definition of Done

- [ ] **功能集成**: SmartVariableInput完全集成到步骤编辑器
- [ ] **上下文感知**: 根据步骤索引正确过滤变量建议
- [ ] **实时预览**: 变量引用的实时解析和预览功能
- [ ] **参数验证**: 增强的表单验证和错误提示
- [ ] **用户体验**: 流畅的编辑体验，无明显性能问题
- [ ] **测试覆盖**: 组件测试和端到端测试通过
- [ ] **浏览器兼容**: 支持主流浏览器
- [ ] **响应式设计**: 移动设备和小屏幕适配

---

## 🔗 依赖关系

**前置依赖**:
- STORY-010: SmartVariableInput智能提示组件已完成
- STORY-011: 变量提示API已实现
- 现有的测试用例编辑器架构稳定

**后续依赖**:
- 用户培训和文档更新
- 性能监控和优化

---

## 💡 实现注意事项

### 用户体验
- 保持编辑器的响应速度
- 避免智能提示干扰正常输入
- 提供清晰的视觉反馈

### 性能优化
- 智能提示的防抖处理
- 变量数据的缓存策略
- 组件的懒加载和内存管理

### 兼容性
- 与现有编辑器功能的兼容
- 不同浏览器的一致性
- 移动设备的触摸友好性

---

**状态**: 待开始  
**创建人**: John (Product Manager)  
**最后更新**: 2025-01-30  

*此Story将智能提示功能完整集成到用户的日常工作流程中，提供完整的端到端体验*