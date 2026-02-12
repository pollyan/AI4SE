
# 2026-02-11 Retrospective - Epic 1: Inline Diff Implementation

## 1. 成功经验 (What Went Well)

- **Inline Diff 带来的体验提升**: 
    - Alice 反馈：新的 Diff 样式（红删绿增）极大提升了 Review 效率，尤其是在长文本字段 (`desc`) 的微小改动识别上。
    - **Key Takeaway**: 视觉化的增量信息对于 AI 辅助工作流至关重要，能显著降低用户的认知负荷。

- **`artifact_patch.py` 的可扩展设计**:
    - 我们在 Story 1.1 中设计的 `_merge_lists` 和递归 Patch 逻辑，在 Story 1.2 中几乎无缝扩展到了所有嵌套结构（Features, Assumptions）。
    - **Key Takeaway**: 在第一个 Story 中多花时间打磨核心算法（Backend Logic），会让后续的扩展 Story 变得非常轻松。

- **前端组件复用**:
    - `DiffField` 组件设计为纯展示组件，成功复用于 Rules, Features, Assumptions 等多个模块，保持了代码的 DRY (Don't Repeat Yourself)。

## 2. 遇到的挑战与教训 (Challenges & Lessons Learned)

- **瞬态状态管理的复杂性 (Story 1.3)**:
    - 问题：最初我们忽略了“未修改列表”的清理逻辑，导致跨轮次对话中出现了“幽灵 Diff”。
    - 根因：`deepcopy` 保留了旧的 `_diff` 标记，而 Patch 逻辑只处理了被修改的部分。
    - **Lesson**: 对于有状态的增量更新系统，**清理逻辑 (Cleanup Logic)** 和更新逻辑同样重要。必须在每次处理前进行全量的状态重置。

- **Schema 变更的权衡 (Story 1.2)**:
    - 挑战：`scope` 字段是 `string[]`，无法进行精确的 ID-based Diff。
    - 决策：为了 MVP 快速交付，我们放弃了对 `scope` 的 Inline Diff，选择了全量替换。
    - **Lesson**: 在数据结构设计初期（Planning 阶段），应考虑到未来 Diff/Merge 的需求。如果一开始将 `scope` 设计为对象数组 `[{id, content}]`，现在就不会有这个限制。**Future Architecture**: 建议后续重构 Artifact Schema，尽量减少 Primitive List 的使用。

## 3. 遗留问题与技术债务 (Technical Debt)

- **Known Issue**: `scope` 和 `out_of_scope` 列表目前不支持 Inline Diff，只能整行高亮。
- **Future Work**: `mermaid` 图表目前只支持全量替换，没有可视化的 Diff (如高亮变化的节点)。
- **Refactor**: `_remove_transient_tags` 目前是递归遍历整个 Artifact，对于超大文档可能会有性能损耗（虽然 NFR 要求 < 100ms，但在极大数据量下需监控）。

## 4. 下一步建议 (Action Items for Next Epic)

- **Refine Schema**: 在 Epic 2 或后续 Technical Task 中，考虑将 `scope` 等 Primitive List 迁移为 Object List。
- **Enhance Testing**: 可以在 CI 中加入更多跨轮次（Multi-turn）的集成测试，模拟真实的用户会话场景，而不仅仅是单元测试。
- **User Feedback**: 收集真实用户对 Diff 颜色的反馈，确认红/绿配色在暗色模式或色盲模式下的可用性（Accessibility）。
