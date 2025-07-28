# 用户故事 US003: 增强 AI 查询功能 (Options 参数支持)

**创建日期**: 2025-01-28  
**优先级**: 高  
**状态**: 需求分析完成  
**预估工作量**: 3-4天  
**MidScene 版本要求**: 0.23.4+

## 📋 需求概述

**背景**: MidScene 0.23.4 版本对现有的 AI 查询方法 (`aiQuery`, `aiBoolean`, `aiNumber`, `aiString`) 进行了重大增强，新增了 `options` 参数支持，可以控制是否向 AI 模型传递 DOM 信息和截图信息。

**目标**: 在 Intent Test Framework 中集成增强的 AI 查询功能，使测试工程师能够提取页面上不可见的属性信息（如图片链接、元素ID、数据属性等），大幅提升数据验证测试的能力和精度。

## 🎯 业务价值

- **数据提取能力提升**: 支持获取页面 DOM 中的隐藏信息，提升数据验证准确性 80%+
- **测试覆盖完整性**: 填补属性级验证空白，实现完整的数据一致性测试
- **成本效益优化**: 通过 domIncluded 选项减少不必要的截图传输，降低 AI token 消耗 30%+
- **调试效率提升**: 提供更丰富的数据源，帮助测试工程师快速定位数据问题

## 👥 用户画像

**主要用户**: 数据验证测试工程师、API 测试专家、质量保证工程师  
**技术水平**: 具备前端基础知识，理解 HTML DOM 结构  
**工作场景**: 负责复杂数据展示页面的准确性测试、API 与前端数据一致性验证  
**痛点**: 无法验证页面元素的隐藏属性，数据测试覆盖不全面

## 📊 业务场景分析

### 核心业务场景

1. **电商产品页面测试**: 验证商品图片的实际链接、价格的数据属性、库存状态等
2. **数据报表验证**: 提取图表背后的原始数据、验证数值准确性和数据来源
3. **用户信息验证**: 验证用户头像链接、ID 属性、权限标识等隐藏信息
4. **链接完整性测试**: 批量提取页面中所有链接的 href 属性进行有效性验证
5. **表单数据验证**: 验证表单字段的默认值、验证规则、数据绑定等属性

### 技术增强特点
- **DOM 信息访问**: 可获取元素的 id、class、data-* 属性等 HTML 属性
- **性能优化选项**: 可选择性传递截图信息以优化 token 使用
- **灵活配置**: 根据具体需求动态选择数据源（DOM + 截图 vs 仅 DOM vs 仅截图）

## 🚀 用户故事

### 故事1: 隐藏属性提取
**作为** 测试工程师  
**我希望** 能够提取页面元素的 HTML 属性信息  
**以便** 验证数据绑定和元素配置的正确性  

**验收条件**:
```gherkin
Given 我正在创建一个 aiQuery 测试步骤
When 我在参数中启用 domIncluded 选项
And 我设置查询内容为提取元素的 HTML 属性
Then 系统应该在执行时将 DOM 信息传递给 AI 模型
And AI 应该能够返回元素的 id、class、data-* 等属性信息
And 返回的数据应该包含在页面截图中不可见的属性值
And 查询响应时间应该在 5 秒以内完成
```

### 故事2: 批量链接验证
**作为** 测试工程师  
**我希望** 能够批量提取页面中所有链接的 href 属性  
**以便** 进行链接有效性和一致性验证  

**验收条件**:
```gherkin
Given 页面包含多个不同类型的链接元素
When 我创建一个 aiQuery 步骤查询所有链接信息
And 参数中设置 domIncluded: true 和 screenshotIncluded: false
Then 应该返回包含以下信息的数组：
  | 字段 | 类型 | 描述 |
  | linkText | string | 链接显示文本 |
  | href | string | 实际链接地址 |
  | target | string | 打开方式 |
  | id | string | 元素ID（如果有） |
And 查询结果应该包含页面中所有可点击的链接
And 由于不使用截图，token 消耗应该比标准查询减少约 30%
And 返回的 href 属性应该是完整的绝对路径
```

### 故事3: 表单数据完整性验证
**作为** 测试工程师  
**我希望** 能够验证表单字段的配置和默认值  
**以便** 确保表单的数据绑定和验证规则正确  

**验收条件**:
```gherkin
Given 页面上有一个包含多种字段类型的表单
When 我创建 aiQuery 步骤提取表单字段信息
And 查询参数设置为：
  ```json
  {
    "domIncluded": true,
    "screenshotIncluded": true
  }
  ```
Then 应该返回表单字段的详细信息包括：
  - 字段名称和标签文本
  - 输入类型（text, email, password 等）
  - 默认值或占位符文本
  - 验证规则（required, pattern 等）
  - 数据绑定属性（name, data-bind 等）
And 对于选择字段应该包含所有选项的值和文本
And 查询结果应该区分可见文本和 HTML属性值
And 能够识别隐藏字段和禁用字段的状态
```

### 故事4: 图片资源验证
**作为** 测试工程师  
**我希望** 能够验证页面图片的完整信息  
**以便** 确保图片加载正确且无损显示  

**验收条件**:
```gherkin
Given 页面包含各种类型的图片元素
When 我创建 aiQuery 步骤查询图片信息
And 使用 domIncluded: true 选项
Then 应该返回图片的完整属性信息：
  - src 属性（实际图片地址）
  - alt 文本（可访问性描述）
  - 宽高属性或 CSS 尺寸设置
  - loading 属性（lazy、eager 等）
  - 图片加载状态（完成、失败、加载中）
And 对于响应式图片应该包含 srcset 信息
And 能够识别背景图片的 CSS background-image 属性
And 返回的图片 URL 应该是完整的可访问地址
And 查询应该能够区分装饰性图片和内容图片
```

### 故事5: 数据表格深度分析
**作为** 测试工程师  
**我希望** 能够提取数据表格的完整结构和数据  
**以便** 验证数据展示的准确性和完整性  

**验收条件**:
```gherkin
Given 页面包含一个复杂的数据表格
When 我创建 aiQuery 步骤分析表格数据
And 查询参数包含表格结构和数据要求
Then 应该返回表格的详细信息：
  - 表头信息（列名、排序状态、筛选状态）
  - 行数据（每行的完整数据，包括隐藏列）
  - 分页信息（当前页、总页数、每页条数）
  - 操作按钮（编辑、删除等按钮的状态和链接）
And 对于可编辑表格应该包含编辑状态信息
And 应该能够识别表格中的数据类型（数字、日期、文本等）
And 能够提取单元格的数据属性和格式信息
And 查询结果应该保持表格的行列对应关系
```

### 故事6: 性能优化配置
**作为** 测试工程师  
**我希望** 能够根据查询需求优化性能和成本  
**以便** 在保证准确性的前提下控制 AI 调用成本  

**验收条件**:
```gherkin
Given 我需要进行不同类型的数据查询
When 我根据查询类型配置不同的 options 选项
Then 应该支持以下配置策略：
  - 纯文本查询：domIncluded: true, screenshotIncluded: false
  - 视觉验证：domIncluded: false, screenshotIncluded: true  
  - 完整分析：domIncluded: true, screenshotIncluded: true
  - 快速检查：domIncluded: false, screenshotIncluded: false（仅缓存）
And 系统应该在执行前显示预计的 token 消耗量
And 不同配置的响应时间应该有明显差别：
  - 纯 DOM 查询：1-2 秒
  - 纯截图查询：2-3 秒
  - 混合查询：3-5 秒
And 查询结果的准确性应该与所选配置相匹配
```

## 🛠️ 功能集成要求

### 步骤编辑器增强
1. **查询参数扩展**
   - 为 aiQuery、aiBoolean、aiNumber、aiString 添加 options 配置区域
   - 提供 domIncluded 和 screenshotIncluded 的勾选框
   - 显示预计的性能和成本影响

2. **智能默认配置**
```json
{
  "aiQuery": {
    "domIncluded": true,
    "screenshotIncluded": true
  },
  "aiBoolean": {
    "domIncluded": false,
    "screenshotIncluded": true
  },
  "aiNumber": {
    "domIncluded": true,
    "screenshotIncluded": false
  },
  "aiString": {
    "domIncluded": false,
    "screenshotIncluded": true
  }
}
```

3. **参数验证和提示**
   - 实时显示配置的性能影响
   - 提供配置建议和最佳实践提示
   - 验证查询内容与配置选项的匹配度

### API 集成扩展
1. **midscene_server.js 增强**
```javascript
// 更新现有查询端点支持 options 参数
app.post('/ai-query', async (req, res) => {
  const { prompt, options = {} } = req.body;
  const {
    domIncluded = true,
    screenshotIncluded = true
  } = options;
  
  // 调用增强的 MidScene API
  const result = await agent.aiQuery(prompt, {
    domIncluded,
    screenshotIncluded
  });
});
```

2. **midscene_python.py 增强**
```python
def ai_query(self, prompt: str, dom_included: bool = True, 
             screenshot_included: bool = True) -> Any:
    """执行增强的 AI 查询"""
    options = {
        "domIncluded": dom_included,
        "screenshotIncluded": screenshot_included
    }
    # 实现细节
```

## ⚠️ 功能边界和性能考虑

### 性能影响分析
1. **Token 消耗变化**
   - 启用 domIncluded 会增加 20-40% 的 token 消耗
   - DOM 复杂度直接影响消耗量
   - 建议为大型页面设置 DOM 范围限制

2. **响应时间影响**
   - DOM 处理增加 0.5-1 秒处理时间
   - 复杂查询可能需要 5-8 秒完成
   - 建议设置合理的超时阈值

### 数据安全考虑
1. **敏感信息处理**
   - DOM 信息可能包含敏感的业务数据
   - 需要对传输的 DOM 内容进行脱敏处理
   - 建议添加敏感字段过滤机制

2. **数据范围控制**
   - 限制 DOM 信息的深度和范围
   - 过滤无关的脚本和样式信息
   - 只传递与查询相关的 DOM 部分

## 🔧 技术实现要点

### 前端实现增强
1. **参数配置界面**
```html
<div class="query-options">
  <label>
    <input type="checkbox" id="domIncluded" checked>
    包含 DOM 信息 (提取属性和结构)
  </label>
  <label>
    <input type="checkbox" id="screenshotIncluded" checked>
    包含截图信息 (视觉分析)
  </label>
  <div class="performance-hint">
    预计 Token 消耗: <span id="tokenEstimate">中等</span>
    预计响应时间: <span id="timeEstimate">3-5秒</span>
  </div>
</div>
```

2. **智能配置建议**
   - 根据查询内容推荐最优配置
   - 显示不同配置的性能权衡
   - 提供一键优化建议

### 后端处理优化
1. **DOM 预处理**
   - 清理无关的 DOM 节点
   - 压缩 DOM 结构表示
   - 提取关键属性信息

2. **缓存策略**
   - DOM 结构缓存机制
   - 查询结果智能缓存
   - 配置相关的缓存键策略

## 📈 实施优先级

### P0 (核心功能 - 必须实现)
- options 参数的基础支持
- domIncluded 和 screenshotIncluded 选项
- 现有查询方法的兼容性保持

### P1 (用户体验优化 - 强烈建议)
- 智能默认配置
- 性能影响提示和预估
- 查询结果的差异化展示

### P2 (高级功能 - 可选)
- 高级 DOM 过滤选项
- 批量查询优化
- 详细的性能分析报告

## 📊 成功指标

### 功能指标
- 隐藏属性提取准确率 >95%
- 查询响应时间平均提升 25%（通过配置优化）
- API 兼容性 100%（向后兼容）

### 业务指标
- 数据验证测试覆盖率提升 >60%
- 用户采用率 >85%（2个月内）
- AI 成本效率提升 >30%（通过合理配置）

## 🔍 风险评估

### 技术风险 (中)
- DOM 信息处理的复杂性可能影响稳定性
- 大型页面的 DOM 信息可能导致性能问题
- AI 模型对 DOM 结构的理解准确性需要验证

### 成本风险 (中)
- domIncluded 选项会增加 token 消耗
- 需要平衡功能丰富性与成本控制
- 用户可能需要培训来合理使用新选项

### 用户体验风险 (低)
- 新选项增加了配置复杂度
- 需要清晰的使用指导和最佳实践
- 兼容性保证减少了迁移风险

## 📝 测试策略

### 功能测试
- 各种 DOM 结构的提取准确性测试
- 不同配置组合的结果一致性测试
- 性能基准测试和瓶颈分析

### 兼容性测试
- 与现有测试用例的兼容性验证
- 不同浏览器的 DOM 处理差异测试
- API 升级的平滑迁移测试

### 性能测试
- 大型页面的 DOM 处理性能测试
- Token 消耗的准确性验证
- 并发查询的系统负载测试

---

**需求状态**: 业务分析完成，待技术实现  
**下一步**: 进行技术可行性评估和详细设计  
**负责人**: 开发团队  
**评审人**: 产品经理、技术架构师、测试团队