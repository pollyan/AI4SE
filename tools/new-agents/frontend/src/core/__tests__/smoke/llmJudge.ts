import OpenAI from 'openai';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

// 解决 dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 加载项目根目录的 .env
// 此时 process.cwd() 通常是 tools/new-agents/frontend
dotenv.config({ path: path.resolve(process.cwd(), '../../../.env') });

export const smokeClient = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
    baseURL: process.env.OPENAI_BASE_URL,
    dangerouslyAllowBrowser: true,
});

export const modelName = process.env.MODEL_NAME || 'qwen3.5-plus';

export interface JudgeResult {
    pass: boolean;
    reason: string;
}

/**
 * 核心的 LLM-as-a-Judge 断言函数。
 * 我们把要测试的 Agent 返回结果包裹在一个打分 prompt 中，
 * 交给模型进行规则校验，避免生硬的字符串包含断言导致的脆弱测试。
 * 
 * @param actualResponse 智能体实际返回的答案（字符串）
 * @param criteria       用于评判的通过标准（一堆具体的要求）
 */
export async function evaluateWithLLM(actualResponse: string, criteria: string): Promise<JudgeResult> {
    const judgePrompt = `
您是一位资深的 QA 工程师和自动化测试判卷官，负责校验 AI Agent 的行为契约。

下面是待测 Agent 的一次实际文本输出：
=== 实际输出 (Actual Output) ===
${actualResponse}
=============================

请判断这段输出是否满足以下**所有**验收标准 (Criteria)：
=== 验收标准 (Criteria) ===
${criteria}
=============================

您必须保持客观，不放过瑕疵，但如果满足了规则精神也请予以通过。
请**严格使用 JSON 格式**回复。不要包含 markdown 代码块(\`\`\`json)等额外字符，只返回原生 JSON 对象。

要求 JSON 具备以下字段：
{
  "pass": true / false,
  "reason": "简明扼要的一句话理由，解释通过或失败的原因"
}
`;

    try {
        const response = await smokeClient.chat.completions.create({
            model: modelName,
            messages: [
                { role: 'user', content: judgePrompt }
            ],
            temperature: 0.1 // 我们需要判卷的一致性，所以让模型表现更稳定
        });

        let content = response.choices[0].message.content || '{}';

        // 防止大模型硬要在外面套一块 markdown code block
        const match = content.match(/{[\s\S]*}/);
        if (match) {
            content = match[0];
        }

        const result = JSON.parse(content);
        return {
            pass: !!result.pass,
            reason: result.reason || '无理由'
        };
    } catch (error: any) {
        return {
            pass: false,
            reason: `判卷模型发生异常或无法解析 JSON: ${error.message}`
        };
    }
}
