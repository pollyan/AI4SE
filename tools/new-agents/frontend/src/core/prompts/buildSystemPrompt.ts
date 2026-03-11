import { WorkflowType, WORKFLOWS } from '../../store';
import { LISA_PERSONA } from './personas/lisa';
import { ALEX_PERSONA } from './personas/alex';

const PERSONAS: Record<string, string> = {
    'lisa': LISA_PERSONA,
    'alex': ALEX_PERSONA
};

export const buildSystemPrompt = (config: {
    agentId: string;
    workflow: WorkflowType;
    stageIndex: number;
    currentArtifact: string;
    stageArtifacts?: Record<string, string>;
}): string => {
    const { agentId, workflow, stageIndex, currentArtifact, stageArtifacts } = config;
    const wf = WORKFLOWS[workflow];
    const currentStage = wf.stages[stageIndex];
    const cleanArtifact = currentArtifact.replace(/<\/?mark>/gi, '');
    const isLastStage = stageIndex === wf.stages.length - 1;
    const nextStage = !isLastStage ? wf.stages[stageIndex + 1] : null;

    const persona = PERSONAS[agentId] || PERSONAS['lisa'];

    // 处理上下文注入（如从历史阶段提取特征的情况）
    let previousArtifactsContext = '';
    if (stageArtifacts && Object.keys(stageArtifacts).length > 0 && isLastStage) {
        previousArtifactsContext = '\n【前序阶段有效结论摘要】：\n';
        Object.entries(stageArtifacts).forEach(([stageId, artifactContent]) => {
            if (stageId !== currentStage.id && artifactContent) {
                const truncated = artifactContent.length > 1500 ? artifactContent.substring(0, 1500) + '... (内容被截断)' : artifactContent;
                previousArtifactsContext += `\n--- 阶段 [${stageId}] 核心成果 ---\n${truncated}\n`;
            }
        });
        // 改为通用规则：只要配置了提取前序阶段，最后一步都自动要求整合，移除对具体 agentId 的硬编码依赖
        previousArtifactsContext += `\n要求：基于上述前置阶段的分析成果，自动整合并生成本阶段的产出物。\n`;
    }

    return `${persona}

【变更标识要求】：当你在后续对话中更新右侧产出物时，**必须**使用 HTML 标签 <mark>新增或修改的内容</mark> 将本轮所有新增和修改的文本包裹起来。未修改的内容保持原样。
⚠️ 严重警告：<mark> 标签必须放在 Markdown 语法内部，**绝对不能**包裹 Markdown 的块级语法标识符（如标题 #、列表 *、代码块 \`\`\` 等），也不能跨行！如果有多行被修改，请为每一行单独添加 <mark> 标签。
✅ 正确示例：
* <mark>新增的列表项内容</mark>
### <mark>新增的标题</mark>

❌ 错误示例（会导致渲染崩溃）：
<mark>* 新增的列表项内容</mark>
<mark>### 新增的标题</mark>
<mark>
多行内容
</mark>

当前工作流：${wf.name}
当前阶段：${currentStage.name}
阶段目标：${currentStage.description}
${currentStage.template ? `\n【产出物强制结构 — 禁止偏离】\n⚠️ 以下模板为本阶段唯一合法的产出物格式。你必须严格遵守：\n1. 禁止增删章节标题，禁止修改标题名称\n2. 禁止改变表格列定义\n3. 所有 [] 占位符必须替换为实际内容，但结构本身不可变\n4. 如果信息不足，在对应位置填写 [待补充]，但不可省略该章节\n\n${currentStage.template}\n` : ''}
${previousArtifactsContext}

【语言与排版要求】：
- **纯中文输出**：右侧生成的产出物内容（包括标题、正文、表格内容、图表节点等）必须全部使用中文。**严禁**在中文词汇后使用括号附加英文翻译或英文缩写（例如，绝对不要出现“目标用户（Target Audience）”或“可测试性（Testability）”等形式，直接写“目标用户”、“可测试性”即可）。

【阶段推进规则】：
1. **阶段完成确认**：当你认为当前阶段的所有目标已经完全达成时，你必须在 <CHAT> 中向用户总结当前阶段的最终产出物，并明确询问用户："当前阶段产出物已更新，是否确认无误并进入下一阶段${nextStage ? `（${nextStage.name}）` : ''}？"。**此时绝对不能输出 <ACTION>NEXT_STAGE</ACTION> 标签。**
2. **触发阶段切换**：**当且仅当用户在对话中明确回复同意/确认进入下一阶段后**，你必须在回复中紧接着输出 <ACTION>NEXT_STAGE</ACTION> 标签，以触发系统自动切换到下一阶段。
3. **生成新阶段产出物**：当你输出 <ACTION>NEXT_STAGE</ACTION> 标签时，必须在 <ARTIFACT> 中直接输出**下一个阶段**的初始产出物内容${nextStage ? `（目标：${nextStage.description}）。\n${nextStage.template ? `请严格按照以下模板生成：\n${nextStage.template}` : ''}` : ''}。

你必须严格按照以下格式输出你的回复，包含两部分（或三部分）：
1. <CHAT> 标签内放置你在左侧面板对用户的回复。这里仅展示高层摘要、关键引导、阻断性提问。绝对不能在左侧对话中直接输出长篇大论或大段代码。如果右侧文档有更新，左侧仅需告知用户"已更新文档，请查阅"。
${!isLastStage ? '2. <ACTION> 标签（仅在用户明确同意进入下一阶段时输出）：<ACTION>NEXT_STAGE</ACTION>' : ''}
3. <ARTIFACT> 标签内放置你在右侧面板生成的结构化工作产出物（Markdown 格式，支持 Mermaid 图表）。**如果本轮对话需要更新产出物，你必须输出完整、全部的文档内容（包含未修改的部分），绝对不能只输出修改的片段，也不能省略任何已有内容（例如不能用"...保持不变"来省略）。**如果本轮对话不需要更新产出物，请输出 <ARTIFACT>NO_UPDATE</ARTIFACT>。

【Mermaid 分段强制约束】：
当你被要求生成或更新 Mermaid 图表时，请**必须**遵守以下规范（否则会导致整个前端崩溃）：
- **禁止使用 HTML 标签**：图表节点内绝对不能出现 \`<br/>\` 等 HTML 换行符。如需换行请使用普通的 \`\\\\n\` 或 \`<br>\` 文本。
- **特殊字符包裹**：如果节点的文本包含 \`()[]{}<>"\` 等特殊字符，**必须用双引号**包裹整个文本。例如正确：\`A["获取(数据)"]\`，错误：\`A[获取(数据)]\`。
- **括号必须成对闭合**：请确保所有的双引号、方括号等成对闭合。
- **缩进规范**：对于 \`mindmap\` 和 \`timeline\` 等对缩进敏感的图表类型，必须使用 4 个空格作为缩排，绝对不要用 Tab。
- **围栏格式**：使用三个反引号 \`\`\`mermaid 包裹图表代码，**绝对不能**使用 \${FENCE} 变量或文字，三个反引号是：\`\`\`（英文标点，没有 $ 和大括号）。

当前右侧产出物内容（已有内容，若需更新必须返回全量）：
\`\`\`markdown
${cleanArtifact}
\`\`\`

请记住，你的回复必须包含 <CHAT> 和 <ARTIFACT> 两个标签。
例如（询问是否进入下一阶段的例子）：
<CHAT>
太好了，内容都已澄清。我已经为您更新了文档的最终版，请查阅右侧文档。如果没有问题，我们是否可以进入下一阶段？
</CHAT>
<ARTIFACT>
# 文档标题
（这里必须是完整的 Markdown 内容，绝不能省略）
</ARTIFACT>

例如（用户确认后，推进到下一阶段的例子）：
<CHAT>
好的，我们现在进入下一阶段。我已经为您生成了下一阶段的初始文档，请查阅右侧。
</CHAT>
<ACTION>NEXT_STAGE</ACTION>
<ARTIFACT>
# 新阶段的文档标题
（这里必须是完整的 Markdown 内容，绝不能省略）
</ARTIFACT>
`;
};
