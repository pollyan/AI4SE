import { FENCE } from '../../utils/constants';
export const CONVERGE_PROMPT = `对每个创意，引导用户评估影响力/信心/实施难度并换算为 ICE 分数，>3 个选项时执行 Kill Your Darlings 收敛，生成 quadrantChart 象限图。
【重要】：
1. 创意合并触发条件：当两个创意的目标用户相同且痛点互补时，建议合并。
2. 通过对话间接获取评分，AI 先给初始建议分+理由，用户修正。
3. 如果创意>3个，强制收敛到前三（Kill Your Darlings 原则：即使某个创意"看起来不错"，如果资源有限也必须割舍）。

【ICE 评分标准（乘法公式，Score = I x C x E）】：
- Impact 影响力 (1-5)：如果成功了，影响有多大？
  1分 = 几乎无影响 | 2分 = 小幅改善 | 3分 = 中等影响 | 4分 = 显著改善核心指标 | 5分 = 颠覆性影响
- Confidence 信心 (1-5)：有多大把握能成功？
  1分 = 纯直觉 | 2分 = 有间接证据 | 3分 = 有类比案例 | 4分 = 有初步验证数据 | 5分 = 有强有力证据
- Ease 容易度 (1-5)：实施起来有多容易？
  1分 = 需要>6个月或大量资源 | 2分 = 3-6个月中等资源 | 3分 = 1-3个月小团队 | 4分 = 2-4周可交付 | 5分 = 1周内可验证
`;

export const CONVERGE_TEMPLATE = `# 收敛聚焦 (Converge)

## 决策矩阵
\${FENCE}mermaid
quadrantChart
    title 创意价值 x 可行性矩阵
    x-axis "低可行性" --> "高可行性"
    y-axis "低价值" --> "高价值"
    quadrant-1 "Quick Wins (优先做)"
    quadrant-2 "Major Projects (战略投入)"
    quadrant-3 "Fill-ins (有空再做)"
    quadrant-4 "Time Sink (直接淘汰)"
    "创意A": [0.8, 0.9]
    "创意B": [0.2, 0.6]
\${FENCE}

> 坐标映射规则：x = Ease/5, y = Impact/5

## ICE 评估表
| 编号 | 创意名称 | Impact (1-5) | Confidence (1-5) | Ease (1-5) | ICE (IxCxE) | 排名 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C-01 | [创意名称] | [分数+一句话理由] | [分数+一句话理由] | [分数+一句话理由] | [乘积] | [1/2/3...] | [入选/淘汰/合并至C-xx] |

> ICE 总分 = Impact x Confidence x Ease（满分 125），高于 [阈值] 入选。

## 整合演进路径（如果触发合并）
\${FENCE}mermaid
flowchart LR
    A["创意A"] --> C{"合并产生"}
    B["创意B"] --> C
    C --> D["更强的概念方案"]
\${FENCE}

> 合并理由：[说明为什么这两个创意适合合并，以及合并后的新价值主张]
`;
