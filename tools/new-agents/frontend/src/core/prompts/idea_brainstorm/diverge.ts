import { FENCE } from '../../utils/constants';
export const DIVERGE_PROMPT = `不加评判，抛出 3-5 个具体的种子方向，引导采用创新技术进行发散思考，产出创意卡片。
【重要】：
1. 种子方向必须基于阶段 1 的问题域分析结合行业常见解决模式生成，不能凭空编造。
2. AI 根据问题类型自动选取 1-2 种最适合的创意技术（见下方可选列表）。
3. 对话式：抛出 3-5 个方向，让用户选择感兴趣的后再深入展开。
4. 每个创意必须以 "How Might We..." (HMW) 问句格式命名。
5. 严格不评判：只收集，不评分（评分在下一阶段执行）。

【可选创意技术】（AI 根据场景自动选取，必须在创意卡片中标注所用技术及其具体维度）：
- SCAMPER 七维度法：
  S(Substitute 替代) - 哪些要素可以被替换？
  C(Combine 组合) - 哪些功能或服务可以合并？
  A(Adapt 适配) - 其他行业有什么可以借鉴的方案？
  M(Modify/Magnify 修改/放大) - 哪些特性可以强化或弱化？
  P(Put to other use 另做他用) - 现有资源能否服务新场景？
  E(Eliminate 消除) - 哪些环节可以去掉？
  R(Reverse/Rearrange 逆转/重组) - 流程能否倒过来或重新组合？
- 类比迁移法 (Analogy Transfer)：从不相关行业寻找已验证的模式，跨界迁移。
- 极端用户法 (Extreme Users)：从极端场景出发倒推方案。
- 逆向思维法 (Reverse Thinking)："如果我们要让问题更严重，应该怎么做？" 再反转。
`;

export const DIVERGE_TEMPLATE = `# 创意发散 (Diverge)

## 发散全景图
\${FENCE}mermaid
mindmap
  root(("核心方向"))
    ("方向1")
      ["创意A"]
    ("方向2")
      ["创意B"]
\${FENCE}

## 创意卡片库
| 编号 | HMW 问句 | 所用创意技术 | 具体维度 | 方案概述 | 差异化亮点 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| C-01 | How might we [问题]? | SCAMPER | E(消除) | [方案概述] | [与现有方案的差异] | [Active] |
| C-02 | How might we [问题]? | 类比迁移 | [参照行业+模式] | [方案概述] | [差异点] | [Active] |

状态说明：[Active] 活跃 / [Parked] 搁置（有潜力但暂不深入） / [Killed] 毙掉（明确排除）
`;
