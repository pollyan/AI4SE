# 编码规范与代码质量标准 (Coding Standards)

## 代码风格与模式

### Python (`intent-tester`, `new-agents/backend`, `shared`)

| 方面 | 规则 |
|--------|------|
| **风格** | PEP 8, Black 格式化器 |
| **类型** | **强制** 所有参数/返回值的类型提示 |
| **命名** | `snake_case` (变量/函数), `PascalCase` (类), `UPPER_SNAKE` (常量) |
| **导入** | 标准库 -> 第三方 -> 本地。使用从包根目录的绝对导入。 |
| **错误处理** | 仅特定异常。切勿使用裸露的 `except Exception:` 而不重新抛出/记录日志。 |
| **提示词** | 存储在 `prompts/` 目录中。逻辑文件中没有硬编码的提示词。 |
| **模式** | 使用带有 `Field` 验证器的 Pydantic `BaseModel` 用于结构化数据。 |

### TypeScript/React (`frontend`, `new-agents`)

| 方面 | 规则 |
|--------|------|
| **风格** | TypeScript 严格模式 |
| **组件** | 仅使用 Hooks 的函数式组件 |
| **文件命名** | `PascalCase.tsx` (组件), `camelCase.ts` (工具) |
| **状态** | Zustand (new-agents) / React Context > 全局 Store |
| **路由** | React Router v7 |
| **样式** | Tailwind CSS v4 |
| **动画** | Motion (Framer Motion) |
| **图标** | Lucide React |

### Node.js (`intent-tester/browser-automation`)

| 方面 | 规则 |
|--------|------|
| **运行时** | Node.js 20+ |
| **测试** | Jest |
| **浏览器自动化** | Playwright + MidSceneJS |

---

## 代码质量标准

### 死代码清理

重构或替换库时:
- **验证零引用**: `grep -r "ComponentName" tools/`
- **立即删除**: 删除未使用的文件，不要注释掉
- **清理测试**: 删除相关测试文件以防止 CI 失败

### 特性废弃协议

移除特性时:
1. 删除 Pydantic schemas/models
2. 更新服务级 docstrings 以移除提及
3. 删除特性专属的测试文件
4. 搜索特性名称的所有变体: `grep -ri "feature_name" tools/`

### 单一事实来源 (SSOT)

**反模式**: 在前端常量中复制后端 prompt 逻辑

### Prompt 维护

当工作流机制改变时:
- **立即移除过时的 prompt 辅助函数**: 不要"以防万一"保留
- **风险**: 废弃的 prompts 会产生矛盾的 LLM 指令
- **行动**: 删除函数定义、文件和所有模板引用
