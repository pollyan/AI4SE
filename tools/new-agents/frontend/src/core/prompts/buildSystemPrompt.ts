import { WorkflowType, WORKFLOWS } from '../../store';
import { buildProfessionalMethodPromptSection } from '../professionalMethods';
import { LISA_PERSONA } from './personas/lisa';
import { ALEX_PERSONA } from './personas/alex';

const PERSONAS: Record<string, string> = {
    'lisa': LISA_PERSONA,
    'alex': ALEX_PERSONA
};

const removeMarkTags = (artifact: string): string => artifact.replace(/<\/?mark>/gi, '');

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
    const professionalMethodSection = buildProfessionalMethodPromptSection(currentStage.methodIds);
    const cleanArtifact = removeMarkTags(currentArtifact);
    const isLastStage = stageIndex === wf.stages.length - 1;
    const nextStage = !isLastStage ? wf.stages[stageIndex + 1] : null;
    const stageActionInstruction = nextStage
        ? `当你判断当前阶段产出物已经完整、可以建议进入下一阶段时，必须在同一轮返回 stage_action: {"type":"request_next_stage","target_stage_id":"${nextStage.id}"}，用于让前端显示确认控件。target_stage_id 只能填写内部阶段 ID "${nextStage.id}"，不要填写阶段中文名称“${nextStage.name}”。`
        : '当前已经是最后阶段，结构化输出的 stage_action 必须为 null。';
    const nextStageGenerationInstruction = nextStage
        ? `stage_action 只表示“请求用户确认进入下一阶段”，不会自动切换阶段；不要在同一轮生成下一阶段产出物，artifact_update 继续返回当前阶段的完整产出物。用户点击前端确认控件后，系统才会切换阶段并自动触发下一阶段生成。`
        : '当前已经是最后阶段，不存在下一阶段产出物生成。';

    const persona = PERSONAS[agentId];
    if (!persona) {
        throw new Error(`Unknown agent persona: ${agentId}`);
    }

    // P0-8: 处理上下文注入 — 提升截断阈值到 5000，并添加明确的截断标记
    let previousArtifactsContext = '';
    if (stageArtifacts && Object.keys(stageArtifacts).length > 0 && stageIndex > 0) {
        const TRUNCATION_THRESHOLD = 5000;
        const previousStageArtifacts = wf.stages
            .slice(0, stageIndex)
            .map((stage) => [stage.id, stageArtifacts[stage.id]] as const)
            .filter(([, artifactContent]) => Boolean(artifactContent));

        previousStageArtifacts.forEach(([stageId, artifactContent], index) => {
            if (index === 0) {
                previousArtifactsContext = '\n【前序阶段有效结论摘要】：\n';
            }

            const cleanPreviousArtifact = removeMarkTags(artifactContent);
            const isTruncated = cleanPreviousArtifact.length > TRUNCATION_THRESHOLD;
            const truncated = isTruncated
                ? cleanPreviousArtifact.substring(0, TRUNCATION_THRESHOLD) + `\n\n⚠️ [内容因长度限制被截断，原文共 ${cleanPreviousArtifact.length} 字符，仅展示前 ${TRUNCATION_THRESHOLD} 字符。请基于已展示的部分内容进行推理，如果关键信息可能缺失，请在产出物中标注。]`
                : cleanPreviousArtifact;
            previousArtifactsContext += `\n--- 阶段 [${stageId}] 核心成果 ${isTruncated ? '(已截断)' : ''} ---\n${truncated}\n`;
        });

        if (previousStageArtifacts.length > 0) {
            // 改为通用规则：只要配置了提取前序阶段，最后一步都自动要求整合，移除对具体 agentId 的硬编码依赖
            previousArtifactsContext += `\n要求：基于上述前置阶段的分析成果，自动整合并生成本阶段的产出物。\n`;
        }
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
${professionalMethodSection}
${previousArtifactsContext}

【语言与排版要求】：
- **纯中文输出**：右侧生成的产出物内容（包括标题、正文、表格内容、图表节点等）必须全部使用中文。**严禁**在中文词汇后使用括号附加英文翻译或英文缩写（例如，绝对不要出现“目标用户（Target Audience）”或“可测试性（Testability）”等形式，直接写“目标用户”、“可测试性”即可）。

【左侧对话与右侧产出物协同】：
- 左侧对话的 chat 必须像一次自然的工作对话，不要只用一两句模板化提示。请用适度展开的中文本轮总结串联“我本轮已经做了什么”“本轮确认或假定的关键点”“右侧产出物更新了哪些部分”“接下来需要用户确认或补充什么”。
- chat 应该让左侧对话有独立阅读价值，但不要把完整文档正文复制到左侧；建议保留 2 到 4 个短段落或短列表，语气像顾问在和用户同步进展。
- 如果本轮更新了右侧产出物，chat 必须明确提示“详细内容已在右侧产出物中更新/展示”，不要把完整文档正文复制到左侧。
- 如果当前阶段可推进，chat 必须引导用户检查右侧产出物，并使用“确认后继续”这类表达提示用户确认后进入下一阶段。

【阶段推进规则】：
1. **阶段完成确认**：当你认为当前阶段的所有目标已经完全达成时，向用户总结当前阶段的最终产出物，并明确询问用户："当前阶段产出物已更新，是否确认无误并进入下一阶段${nextStage ? `（${nextStage.name}）` : ''}？"。
2. **触发阶段确认控件**：当你已经在 chat 中建议用户进入下一阶段时，必须同一轮返回 stage_action，让前端显示确认控件；不要让用户再手动回复“确认”后才显示控件。
   - ${stageActionInstruction}
3. **生成新阶段产出物**：${nextStageGenerationInstruction}
4. **产出物更新原则**：如果本轮需要更新右侧产出物，必须提供完整、全部的 Markdown 文档内容（包含未修改的部分），绝对不能只输出修改片段，也不能用“...保持不变”省略已有内容。

当前右侧产出物内容（已有内容，若需更新必须返回全量）：
\`\`\`markdown
${cleanArtifact}
\`\`\`
`;
};
