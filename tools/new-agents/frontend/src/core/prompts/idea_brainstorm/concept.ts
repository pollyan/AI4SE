import { FENCE } from '../../utils/constants';
export const CONCEPT_PROMPT = `基于你获取的前序 Artifact（限制取最新精华摘要），整合前三阶段的核心成果，生成可直接用于团队沟通的产品概念简报。
【重要】：
1. 自动整合前 3 阶段精华，用户不需要手动拼接。
2. 只保留 What 和 Why，不涉及技术实现的 How。
3. 产品概念一览表可以直接拿去跟团队沟通。
`;

export const CONCEPT_TEMPLATE = `# 产品概念简报 (Concept Brief)

## 定位声明 (Positioning Statement)
> 采用 Geoffrey Moore 定位声明格式 (Crossing the Chasm)：

**For** [目标用户群体的一句话描述]
**who** [他们面临的核心需求或痛点],
**the** [产品名称/代号] **is a** [产品品类，如"移动端记账工具""B2B SaaS 平台"]
**that** [核心价值主张：产品提供的关键收益].
**Unlike** [主要竞品或现有替代方案],
**our product** [最核心的差异化优势].

> 注意：每一行都必须填写具体内容，不能用"提升效率""优化体验"等模糊表述。品类锚定 (product category) 必须让读者在 3 秒内理解这是个什么类型的产品。

## Lean Canvas 产品画布
| 格子 | 内容 |
| --- | --- |
| 1. 问题 (Problem) | Top 3 待解决问题（从 Define 阶段提取） |
| 2. 用户群体 (Customer Segments) | 目标用户群体描述（从 Define 阶段提取） |
| 3. 独特价值主张 (UVP) | 用一句话说清楚为什么用户要选你（从定位声明提炼） |
| 4. 解决方案 (Solution) | 对应 Top 3 问题的 Top 3 功能（从 Converge 阶段入选创意提取） |
| 5. 渠道 (Channels) | 如何触达目标用户？（如：SEO、社区、口碑等） |
| 6. 收入来源 (Revenue Streams) | 靠什么赚钱？（如：订阅制、按次付费、免费增值等） |
| 7. 成本结构 (Cost Structure) | 主要成本项（如：开发人力、云服务、获客成本等） |
| 8. 关键指标 (Key Metrics) | 核心度量指标（如：DAU、转化率、留存率、ARPU） |
| 9. 竞争壁垒 (Unfair Advantage) | 不可轻易被复制或购买的优势（如：数据网络效应、先发优势、独家资源） |

## MVP 功能分布
\${FENCE}mermaid
pie title MVP 功能组成
    "核心主流程" : 60
    "周边支撑功能" : 30
    "Nice-to-have" : 10
\${FENCE}

## 核心增长漏斗 (AARRR)
\${FENCE}mermaid
flowchart TD
    A["Acquisition 获客"] --> B["Activation 激活"]
    B --> C["Retention 留存"]
    C --> D["Revenue 变现"]
    D --> E["Referral 传播"]
\${FENCE}

| 漏斗阶段 | 用户行为 | 核心指标 | MVP 中如何实现 |
| --- | --- | --- | --- |
| Acquisition | [用户如何发现产品] | [指标，如注册数] | [MVP 功能] |
| Activation | [用户首次体验核心价值的动作] | [指标，如完成率] | [MVP 功能] |
| Retention | [用户回来的原因和频率] | [指标，如次日/7日留存] | [MVP 功能] |
| Revenue | [用户付费的触发点] | [指标，如付费转化率] | [MVP 功能] |
| Referral | [用户推荐给他人的动机] | [指标，如邀请率] | [MVP 功能] |

## Pre-mortem 风险分析
> 方法论来源：Gary Klein "Prospective Hindsight"。
> 假设：现在是 6 个月后，这个产品已经失败了。请从未来回看，分析最可能的失败原因。

| 风险维度 | 失败原因 | 可能性 | 缓解措施 |
| --- | --- | --- | --- |
| 市场风险 | [如：目标用户实际上不愿付费/市场太小] | [高/中/低] | [如何提前验证] |
| 产品风险 | [如：核心功能无法形成差异化/用户体验不达预期] | [高/中/低] | [如何提前验证] |
| 执行风险 | [如：团队缺乏关键能力/资金不足] | [高/中/低] | [如何提前验证] |

## 下一步行动 (Action Items)
- [ ] [验证假设X：通过什么方式，在什么时间内完成]
- [ ] [构建最小验证实验：具体描述]
`;
