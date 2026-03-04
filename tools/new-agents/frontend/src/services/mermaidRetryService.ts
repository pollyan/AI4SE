import { collectLlmResponse } from '../core/utils/llmClient';
import { useStore } from '../store';
import OpenAI from 'openai';

/**
 * 修正因解析失败而出错的 Mermaid 图表代码
 *
 * @param brokenCode 出错的 Mermaid 代码
 * @param errorMessage Mermaid 抛出的错误信息
 * @param blockIndex 当前图表在所有图表中的索引顺序（用于上下文反馈，可选）
 * @returns {Promise<string | null>} 返回修正后的纯 Mermaid 代码，若网络请求失败等则返回 null
 */
export async function retryMermaidGeneration(
    brokenCode: string,
    errorMessage: string,
    blockIndex?: number
): Promise<string | null> {
    // 获取首行，通常包含图表类型如 `graph TD`，作为给 LLM 的上下文提示
    const lines = brokenCode.split('\n');
    const firstLine = lines.find((l) => l.trim() !== '') || 'unknown type';

    const { workflow, stageIndex } = useStore.getState();
    const stageName = workflow ? `${workflow} - stage ${stageIndex}` : 'unknown stage';
    const truncatedCode = brokenCode.length > 5000 ? brokenCode.substring(0, 5000) + '\n...[TRUNCATED]' : brokenCode;

    const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [
        {
            role: 'system',
            content: `你是 Mermaid 图表修正专家。用户给你一段有语法错误的 Mermaid 代码和验证器抛出的错误信息。
请分析错误并修复语法。
必须遵循以下原则：
1. 仅输出修正后的完整 Mermaid 代码，不要附带任何解释文字。
2. 不要包含 \`\`\`mermaid 围栏标记（仅纯文本代码）。
3. 确保特殊字符（如 <>()[]{}"）在节点文本中被合法转义或用双引号包裹。`
        },
        {
            role: 'user',
            content: `【图表预期类型上下文】：${firstLine}
【当前位置】：第 ${blockIndex !== undefined ? blockIndex + 1 : '未知'} 个图表
【错误信息】：
${errorMessage}

【错误代码】：
${truncatedCode}`
        }
    ];

    try {
        const rawResponse = await collectLlmResponse(messages);

        let cleanedCode = rawResponse.trim();

        // 如果 LLM 依然不听话输出了围栏，需要剥离
        // Use regex to securely extract code if the LLM output fenced block with conversational text
        const match = cleanedCode.match(/```(?:mermaid)?\n?([\s\S]*?)```/);
        if (match) {
            cleanedCode = match[1].trim();
        } else {
            // Fallback for simpler cases or if no full fence is found but partial ones exist
            cleanedCode = cleanedCode.replace(/^```mermaid\n?/, '');
            cleanedCode = cleanedCode.replace(/^```[a-z]*\n?/, '');
            cleanedCode = cleanedCode.replace(/\n?```$/, '');
        }

        return cleanedCode.trim();
    } catch (err) {
        console.error(`[mermaidRetryService] Failed to retry diagram ${blockIndex ?? ''}:`, err);
        return null;
    }
}
