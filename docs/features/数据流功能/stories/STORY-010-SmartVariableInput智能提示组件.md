# STORY-010: 开发SmartVariableInput智能提示组件

**Story ID**: STORY-010  
**Epic**: EPIC-001 数据流核心功能  
**Sprint**: Sprint 3  
**优先级**: High  
**估算**: 8 Story Points  
**分配给**: Frontend Developer + UX Designer  
**创建日期**: 2025-01-30  
**产品经理**: John  

---

## 📖 故事描述

**作为** 测试工程师  
**我希望** 在输入步骤参数时获得智能的变量引用提示  
**以便** 我可以快速准确地选择可用变量，避免拼写错误  
**这样** 我就能提高测试用例配置效率，减少因变量名错误导致的执行失败  

---

## 🎯 验收标准

### AC-1: 自动触发智能提示
**给定** 我在参数输入框中输入`${`  
**当** 系统检测到触发字符时  
**那么** 应该在200ms内弹出智能提示菜单  

**触发条件**:
- 输入`${`时立即触发
- 光标位置在`${`之后时继续显示
- 提示菜单显示在输入框下方适当位置

### AC-2: 显示可用变量列表
**给定** 智能提示菜单已打开  
**当** 系统加载变量数据时  
**那么** 应该显示当前测试用例中所有可用的变量  

**显示内容**:
- 变量名称
- 变量数据类型 (string, number, object, array)
- 来源步骤信息 ("步骤 2", "步骤 5")
- 变量值预览（简化显示）

**显示格式**:
```
🏷️ product_info          步骤 2    [object]
   预览: {name: "iPhone", price: 999}

🏷️ user_name             步骤 1    [string]  
   预览: "张三"

🏷️ item_count            步骤 3    [number]
   预览: 5
```

### AC-3: 实时搜索和过滤
**给定** 智能提示菜单已显示变量列表  
**当** 我继续输入变量名的部分字符  
**那么** 菜单应该实时过滤显示匹配的变量  

**搜索特性**:
- 模糊搜索：输入"prod"匹配"product_info"
- 大小写不敏感搜索
- 高亮显示匹配的字符
- 无匹配结果时显示"未找到匹配变量"

### AC-4: 嵌套属性智能提示
**给定** 我输入`${object_var.`  
**当** 系统检测到对象变量后的点号  
**那么** 应该显示该对象的可用属性列表  

**示例**:
输入`${product_info.`后显示：
```
📋 name        [string]  "iPhone 15"
📋 price       [number]  999
📋 category    [string]  "电子产品"
📋 stock       [number]  100
```

### AC-5: 键盘导航支持
**给定** 智能提示菜单已打开  
**当** 我使用键盘操作时  
**那么** 应该支持完整的键盘导航功能  

**键盘操作**:
- `↑` `↓` 箭头键：上下选择变量
- `Enter`：确认选择并插入变量引用
- `ESC`：关闭提示菜单
- `Tab`：快速选择第一个匹配项
- `Ctrl+Space`：强制打开提示菜单

### AC-6: 自动补全和格式化
**给定** 我选择了一个变量  
**当** 我按Enter确认选择时  
**那么** 系统应该自动完成变量引用格式  

**自动补全行为**:
- 选择`product_info`时自动插入`product_info}`
- 如果已有部分输入，智能替换匹配部分
- 光标自动定位到`}`之后，便于继续输入

---

## 🔧 技术实现要求

### React组件架构
```tsx
interface SmartVariableInputProps {
  value: string;
  onChange: (value: string) => void;
  executionId?: string;
  currentStepIndex?: number;
  placeholder?: string;
  disabled?: boolean;
}

interface VariableData {
  name: string;
  dataType: 'string' | 'number' | 'boolean' | 'object' | 'array';
  value: any;
  sourceStepIndex: number;
  sourceApiMethod: string;
  properties?: VariableProperty[]; // 对象类型的属性列表
}

interface VariableProperty {
  name: string;
  type: string;
  value: any;
}
```

### 核心组件结构
```tsx
export const SmartVariableInput: React.FC<SmartVariableInputProps> = ({
  value,
  onChange,
  executionId,
  currentStepIndex,
  ...props
}) => {
  const [suggestions, setSuggestions] = useState<VariableData[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [filterText, setFilterText] = useState('');

  // 智能提示逻辑
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    
    // 检测是否应该显示提示
    const shouldShowSuggestions = detectTrigger(newValue, e.target.selectionStart);
    setShowSuggestions(shouldShowSuggestions);
    
    if (shouldShowSuggestions) {
      loadVariableSuggestions();
    }
  }, [onChange]);

  return (
    <div className="smart-variable-input">
      <input
        type="text"
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        {...props}
      />
      {showSuggestions && (
        <VariableSuggestionDropdown
          suggestions={filteredSuggestions}
          selectedIndex={selectedIndex}
          onSelect={handleVariableSelect}
          onClose={closeSuggestions}
        />
      )}
    </div>
  );
};
```

### API集成
```typescript
// 获取变量建议的API调用
const fetchVariableSuggestions = async (executionId: string, stepIndex?: number): Promise<VariableData[]> => {
  const response = await fetch(`/api/v1/executions/${executionId}/variable-suggestions`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  
  return response.json();
};

// 获取对象属性建议的API调用
const fetchObjectProperties = async (executionId: string, variableName: string): Promise<VariableProperty[]> => {
  const response = await fetch(`/api/v1/executions/${executionId}/variables/${variableName}/properties`);
  return response.json();
};
```

### 样式设计 (CSS)
```css
.smart-variable-input {
  position: relative;
  width: 100%;
}

.smart-variable-input input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-family: 'Monaco', 'Menlo', monospace;
}

.variable-suggestion-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 1000;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  max-height: 200px;
  overflow-y: auto;
}

.suggestion-item {
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f3f4f6;
}

.suggestion-item:hover,
.suggestion-item.selected {
  background-color: #f3f4f6;
}

.suggestion-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.suggestion-item-name {
  font-weight: 500;
  font-family: 'Monaco', 'Menlo', monospace;
}

.suggestion-item-meta {
  font-size: 12px;
  color: #6b7280;
}

.suggestion-item-preview {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 2px;
  font-family: 'Monaco', 'Menlo', monospace;
}
```

---

## 🧪 测试计划

### 单元测试
1. **组件渲染测试**
   ```tsx
   test('renders input with placeholder', () => {
     render(<SmartVariableInput value="" onChange={() => {}} placeholder="输入参数值" />);
     expect(screen.getByPlaceholderText('输入参数值')).toBeInTheDocument();
   });
   ```

2. **触发逻辑测试**
   ```tsx
   test('shows suggestions when typing ${', () => {
     const { user } = setup();
     const input = screen.getByRole('textbox');
     
     user.type(input, '${');
     expect(screen.getByTestId('suggestion-dropdown')).toBeVisible();
   });
   ```

3. **键盘导航测试**
   ```tsx
   test('keyboard navigation works correctly', () => {
     const { user } = setup();
     user.type(screen.getByRole('textbox'), '${');
     
     user.keyboard('{ArrowDown}');
     expect(screen.getByTestId('suggestion-item-1')).toHaveClass('selected');
     
     user.keyboard('{Enter}');
     expect(screen.getByRole('textbox')).toHaveValue('${variable_name}');
   });
   ```

### 集成测试
1. **API集成测试**
   - 测试变量数据的正确加载
   - 测试网络错误的处理
   - 测试加载状态的显示

2. **用户交互测试**
   - 端到端的变量选择流程
   - 复杂嵌套变量的提示
   - 多个变量引用的处理

### 性能测试
- 大量变量时的渲染性能
- 快速输入时的响应性能
- 内存泄漏检测

---

## 🎨 用户体验设计

### 视觉设计要求
1. **极简设计风格**
   - 遵循项目的minimal design系统
   - 使用系统字体和中性色彩
   - 避免使用图标，采用文本标识

2. **状态反馈**
   - 加载状态：显示"加载中..."文本
   - 空状态：显示"暂无可用变量"
   - 错误状态：显示"加载失败，请重试"

3. **可访问性**
   - 支持屏幕阅读器
   - 键盘导航完整支持
   - 高对比度颜色方案

### 交互设计细节
1. **智能定位**
   - 提示菜单自动调整位置避免超出视口
   - 在屏幕底部时向上弹出
   - 宽度自适应内容长度

2. **响应式设计**
   - 移动设备上适配触摸操作
   - 小屏幕设备上优化显示密度
   - 支持横屏和竖屏模式

---

## 📊 Definition of Done

- [ ] **核心功能**: 所有验收标准功能正常工作
- [ ] **性能要求**: 提示响应时间<200ms
- [ ] **浏览器兼容**: 支持主流浏览器最新版本
- [ ] **可访问性**: 通过WCAG 2.1 AA标准检查
- [ ] **单元测试**: 测试覆盖率>90%
- [ ] **集成测试**: 与后端API集成测试通过
- [ ] **代码审查**: 前端代码质量审查通过
- [ ] **用户测试**: 可用性测试反馈积极

---

## 🔗 依赖关系

**前置依赖**:
- STORY-007: output_variable参数解析和存储（需要变量数据）
- STORY-008: 变量引用语法解析（需要语法规则）
- 后端API `/api/v1/executions/{id}/variable-suggestions` 已实现

**后续依赖**:
- STORY-012: 集成智能提示到测试用例编辑器
- 其他需要变量输入的组件可复用此组件

---

## 💡 实现注意事项

### 性能优化
- 使用React.memo优化重复渲染
- 实现虚拟滚动处理大量变量
- 防抖处理用户输入，避免频繁API请求

### 用户体验
- 提供键盘快捷键说明
- 支持变量预览功能
- 记住用户的常用变量选择

### 扩展性
- 支持自定义变量引用格式
- 预留插件系统接口
- 支持主题定制

---

**状态**: 待开始  
**创建人**: John (Product Manager)  
**最后更新**: 2025-01-30  

*此组件是用户体验的核心，将显著提升测试用例配置的效率和准确性*