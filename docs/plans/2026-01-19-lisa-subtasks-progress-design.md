# Lisa 二级进度展示设计

## 概述

在 Lisa 智能体的产出物面板右侧增加二级进度显示区域，展示：
1. **阶段全景**：所有阶段及其状态
2. **当前阶段任务**：当前进行中阶段的子任务列表及进度

## 需求

- **数据来源**：预定义阶段 + 动态子任务
- **展示形式**：顶部横向，双层结构
- **交互**：自动展开当前阶段的任务全景
- **范围**：仅 Lisa 智能体，Alex 不在本次范围内

## 技术方案

### 核心思路

1. 后端 Schema 扩展：`WorkflowStage` 增加 `sub_tasks` 字段
2. 管道打通：`get_progress_info` 透传 `sub_tasks` 到前端
3. 前端无修改：`WorkflowProgress.tsx` 已支持 `subTasks` 渲染

### 数据结构

```python
class WorkflowSubTask(BaseModel):
    """阶段内的细分任务"""
    id: str
    name: str
    status: Literal["pending", "active", "completed", "warning"] = "pending"

class WorkflowStage(BaseModel):
    """工作流阶段定义"""
    id: str
    name: str
    status: Literal["pending", "active", "completed"] = "pending"
    sub_tasks: List[WorkflowSubTask] = Field(default_factory=list)
```

### 变更清单

| 文件 | 变更 |
|------|------|
| `agents/shared/schemas.py` | 新增 `WorkflowSubTask`，`WorkflowStage` 增加 `sub_tasks` |
| `agents/shared/progress.py` | `get_progress_info` 透传 `sub_tasks` |
| 前端 | 无修改（已支持） |

### 进度更新机制

- **触发时机**：每次模型输出后由程序自动触发
- **子任务内容**：后续由 LLM 动态生成，本次仅打通管道

## 实施任务

1. [ ] 在 `schemas.py` 中新增 `WorkflowSubTask` 模型
2. [ ] 修改 `WorkflowStage` 模型，增加 `sub_tasks` 字段
3. [ ] 修改 `progress.py` 的 `get_progress_info`，透传 `sub_tasks`
4. [ ] 编写单元测试验证数据结构和透传逻辑
5. [ ] 本地 Docker 部署验证前端渲染

## 后续迭代

- LLM 动态生成子任务逻辑
- 基于 Prompt 引导的子任务状态更新
