import { describe, it, expect } from 'vitest';
import { smokeClient, modelName, evaluateWithLLM } from './llmJudge';
import { getSystemPrompt } from '../../prompts/systemPrompt';
import { WORKFLOWS } from '../../workflows';

// ---------------------------------------------------------------------------
// AgentConversationRunner — 自动维护对话历史与阶段上下文的状态机
// ---------------------------------------------------------------------------

type Role = 'system' | 'user' | 'assistant';

interface HistoryMessage {
    role: Role;
    content: string;
}

class AgentConversationRunner {
    private history: HistoryMessage[] = [];
    private currentStageIndex: number;
    private workflowKey: keyof typeof WORKFLOWS; // Using keyof typeof WORKFLOWS
    private currentArtifact: string;

    constructor(workflowKey: keyof typeof WORKFLOWS, initialStage: number = 0, initialArtifact: string = '') {
        this.currentStageIndex = initialStage;
        this.workflowKey = workflowKey;
        this.currentArtifact =
            initialArtifact ||
            '# 欢迎使用 Lisa 测试专家\n\n请在左侧输入您的需求，我将为您生成测试文档。';
        this.rebuildSystemPrompt();
    }

    /** 重建 / 更新 System Prompt（始终位于 history[0]） */
    private rebuildSystemPrompt() {
        const prompt = getSystemPrompt(
            this.workflowKey,
            this.currentStageIndex,
            this.currentArtifact,
        );
        if (this.history.length === 0) {
            this.history.push({ role: 'system', content: prompt });
        } else {
            this.history[0] = { role: 'system', content: prompt };
        }
    }

    /** 发送用户消息，获取 LLM 回复，自动推进上下文 */
    async sendMessage(userMessage: string): Promise<string> {
        this.history.push({ role: 'user', content: userMessage });

        const response = await smokeClient.chat.completions.create({
            model: modelName,
            messages: this.history,
            temperature: 0.7,
        });

        const reply = response.choices[0].message.content || '';
        this.history.push({ role: 'assistant', content: reply });

        // 提取 <ARTIFACT> 并更新当前产出物
        const artifactMatch = reply.match(/<ARTIFACT>([\s\S]*?)<\/ARTIFACT>/);
        if (artifactMatch && artifactMatch[1].trim() !== 'NO_UPDATE') {
            this.currentArtifact = artifactMatch[1].trim();
            this.rebuildSystemPrompt();
        }

        // 如果发生了阶段跳转，推进 stageIndex（不超出最大阶段数）
        if (reply.includes('<ACTION>NEXT_STAGE</ACTION>')) {
            const maxStage = WORKFLOWS[this.workflowKey].stages.length - 1;
            if (this.currentStageIndex < maxStage) {
                this.currentStageIndex += 1;
                this.rebuildSystemPrompt();
            }
        }

        return reply;
    }

    get stageIndex() {
        return this.currentStageIndex;
    }
}

// ---------------------------------------------------------------------------
// 通用格式断言条件（每一轮都会拼入）
// ---------------------------------------------------------------------------
const FORMAT_CRITERIA = `
- 输出中必须包含 <CHAT> 和 </CHAT> 标签。
- 输出中必须包含 <ARTIFACT> 和 </ARTIFACT> 标签。
- <CHAT> 中的内容应当对用户的输入有针对性的回应，不能答非所问。
`;

// ---------------------------------------------------------------------------
// 工作流阶段名称（用于生成动态断言）
// ---------------------------------------------------------------------------
const stages = WORKFLOWS.TEST_DESIGN.stages;

// ---------------------------------------------------------------------------
// 测试套件 — 10 分钟超时（6~7 轮真实 LLM 调用 + 6~7 轮 Judge 调用）
// ---------------------------------------------------------------------------
describe('Lisa Agent Workflow - E2E Full Lifecycle (Real LLM)', { timeout: 1200_000 }, () => {

    it('从需求澄清到文档交付的完整工作流', async () => {
        const runner = new AgentConversationRunner('TEST_DESIGN');

        // ============================================================
        // Round 1：模糊需求 → 初版文档 + P0 追问
        // ============================================================
        console.log('--- Round 1：发起模糊需求 ---');
        const reply1 = await runner.sendMessage(
            '帮我设计一份登录页面的测试',
        );

        const judge1 = await evaluateWithLLM(reply1, `
${FORMAT_CRITERIA}
- <ARTIFACT> 中的内容不能为 NO_UPDATE，必须有一份初版的 Markdown 需求分析文档大纲。
- <CHAT> 中必须向用户提出了 P0 级别的追问或澄清问题（如账号密码规则、安全需求等）。
- 绝对不能包含 <ACTION>NEXT_STAGE</ACTION>，因为需求信息明显不全。
        `);
        console.log('Round 1 Judge:', judge1.pass ? '✅ PASS' : '❌ FAIL', '-', judge1.reason);
        expect(judge1.pass).toBe(true);

        // ============================================================
        // Round 2：让 LLM 自行用最佳实践补全所有 P0
        // ============================================================
        console.log('--- Round 2：用最佳实践补全 P0 ---');
        const reply2 = await runner.sendMessage(
            '关于你提出的所有 P0 问题，请直接用行业最佳实践帮我回答，不需要再问我了。',
        );

        const judge2 = await evaluateWithLLM(reply2, `
${FORMAT_CRITERIA}
- <ARTIFACT> 不能为 NO_UPDATE，必须更新了需求分析文档，体现 P0 问题已被解答。
- <CHAT> 中应当明确告知用户产出物已更新，并询问是否可以进入下一阶段（${stages[1].name}）。
- 绝对不能包含 <ACTION>NEXT_STAGE</ACTION>，因为用户还没确认要推进。
        `);
        console.log('Round 2 Judge:', judge2.pass ? '✅ PASS' : '❌ FAIL', '-', judge2.reason);
        expect(judge2.pass).toBe(true);

        // ============================================================
        // Round 3 ~ N：逐步确认并流转后续阶段
        // 阶段 0→1 (需求澄清→策略制定)
        // 阶段 1→2 (策略制定→用例编写)
        // 阶段 2→3 (用例编写→文档交付)
        // ============================================================
        for (let i = 0; i < stages.length - 1; i++) {
            const fromStage = stages[i];
            const toStage = stages[i + 1];
            const roundNum = i + 3;

            console.log(`--- Round ${roundNum}：确认从「${fromStage.name}」→「${toStage.name}」---`);
            const reply = await runner.sendMessage(
                '没问题，确认完毕，请进入下一阶段。',
            );

            const judge = await evaluateWithLLM(reply, `
${FORMAT_CRITERIA}
- 由于用户明确确认跳到下一阶段，回答中必须包含 <ACTION>NEXT_STAGE</ACTION> 标签。
- <ARTIFACT> 中必须生成新阶段「${toStage.name}」的初始产出物内容，不能是 NO_UPDATE，也不能是简单照搬上一轮的文档。
- <CHAT> 中应当告知用户已进入新阶段「${toStage.name}」。
            `);
            console.log(`Round ${roundNum} Judge:`, judge.pass ? '✅ PASS' : '❌ FAIL', '-', judge.reason);
            if (!judge.pass) {
                console.error(`[Round ${roundNum} 实际输出]\n`, reply.substring(0, 500), '...');
            }
            expect(judge.pass).toBe(true);
        }

        // ============================================================
        // 最终轮：在末尾阶段（文档交付）确认，不能再有 NEXT_STAGE
        // ============================================================
        const lastStage = stages[stages.length - 1];
        const finalRoundNum = stages.length + 2;
        console.log(`--- Round ${finalRoundNum}：末尾阶段「${lastStage.name}」确认 ---`);
        const replyFinal = await runner.sendMessage(
            '文档确认完毕，谢谢。',
        );

        const judgeFinal = await evaluateWithLLM(replyFinal, `
${FORMAT_CRITERIA}
- 当前已是最后一个阶段「${lastStage.name}」，绝对不能输出 <ACTION>NEXT_STAGE</ACTION>。
- <CHAT> 中应有对用户的结束性确认答复。
        `);
        console.log(`Round ${finalRoundNum} Judge:`, judgeFinal.pass ? '✅ PASS' : '❌ FAIL', '-', judgeFinal.reason);
        expect(judgeFinal.pass).toBe(true);

        console.log('🎉 E2E 全流程测试通过！');
    });

    it('从深度评审到评审报告的完整需求评审工作流（REQ_REVIEW）', async () => {
        const runner = new AgentConversationRunner('REQ_REVIEW', 0);
        const reqStages = WORKFLOWS.REQ_REVIEW.stages;

        // ============================================================
        // Round 1：提供需求说明 → 输出第一阶段（REVIEW）评审报告
        // ============================================================
        console.log('--- REQ_REVIEW Round 1：发起需求文档评审 ---');
        const reply1 = await runner.sendMessage(
            '这是一份简单的需求文档：\n\n# 登录功能需求\n用户可以输入用户名和密码登录。如果密码错误提示“密码错误”。',
        );

        const judge1 = await evaluateWithLLM(reply1, `
${FORMAT_CRITERIA}
- <ARTIFACT> 中的内容不能为 NO_UPDATE，必须是一份按各个维度分段的 Markdown 评审问题清单。
- 由于只是初次接收需求，不能包含 <ACTION>NEXT_STAGE</ACTION>，用户还没确认流转。
        `);
        console.log('REQ_REVIEW Round 1 Judge:', judge1.pass ? '✅ PASS' : '❌ FAIL', '-', judge1.reason);
        expect(judge1.pass).toBe(true);

        // ============================================================
        // Round 2：明确跳到下一阶段（REPORT 评审报告阶段）
        // ============================================================
        console.log(`--- REQ_REVIEW Round 2：确认进入「${reqStages[1].name}」阶段 ---`);
        const reply2 = await runner.sendMessage(
            '问题很犀利，请基于这些直接生成完整的评审报告并进入下一阶段。',
        );

        const judge2 = await evaluateWithLLM(reply2, `
${FORMAT_CRITERIA}
- 必须包含 <ACTION>NEXT_STAGE</ACTION> 标签。
- <ARTIFACT> 中必须生成「${reqStages[1].name}」的文档内容（一定要包含图表和通过/不通过判定等）。
        `);
        console.log('REQ_REVIEW Round 2 Judge:', judge2.pass ? '✅ PASS' : '❌ FAIL', '-', judge2.reason);
        if (!judge2.pass) {
            console.error(`[REQ_REVIEW Round 2 实际输出]\n`, reply2.substring(0, 500), '...');
        }
        expect(judge2.pass).toBe(true);

        // ============================================================
        // 最终轮：验证在末尾阶段停止流转
        // ============================================================
        console.log('--- REQ_REVIEW Round 3：最终确认 ---');
        const replyFinal = await runner.sendMessage(
            '好的，这份需求评审报告看着没问题了。',
        );

        const judgeFinal = await evaluateWithLLM(replyFinal, `
${FORMAT_CRITERIA}
- 绝对不能再输出 <ACTION>NEXT_STAGE</ACTION>，因为这已经是最后一个阶段。
- <CHAT> 中应有确认且体贴的回复。
        `);
        console.log('REQ_REVIEW Final Round Judge:', judgeFinal.pass ? '✅ PASS' : '❌ FAIL', '-', judgeFinal.reason);
        expect(judgeFinal.pass).toBe(true);
    });
});
