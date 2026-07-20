import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useStore, type ChatState } from '../../store';
import { generateResponseStream } from '../llm';

type TestStreamChunk = {
    chatResponse: string;
    newArtifact: string;
    action: string;
    hasArtifactUpdate: boolean;
    artifactTruncated?: boolean;
};

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

function createSseStream(): ReadableStream<Uint8Array> {
    const encoder = new TextEncoder();
    const payload = [
        'data: {"type":"run_started","runId":"run-system-prompt-integration"}',
        'data: {"type":"agent_turn","output":{"chat":"继续生成策略内容","artifact_update":{"type":"none"},"stage_action":null,"warnings":[]}}',
        'data: [DONE]',
    ].join('\n') + '\n';

    return new ReadableStream({
        start(controller) {
            controller.enqueue(encoder.encode(payload));
            controller.close();
        },
    });
}

async function collectStream(
    gen: AsyncGenerator<TestStreamChunk, void, unknown>
): Promise<TestStreamChunk[]> {
    const results: TestStreamChunk[] = [];
    for await (const val of gen) {
        results.push(val);
    }
    return results;
}

function resetStore(overrides: Partial<ChatState> = {}) {
    useStore.setState({
        workflow: 'TEST_DESIGN',
        stageIndex: 1,
        chatHistory: [],
        artifactContent: '# 测试策略蓝图',
        artifactHistory: [],
        stageArtifacts: {
            CLARIFY: '# 需求分析文档\n\n## 1. 被测系统与边界\n登录支付链路',
            STRATEGY: '# 测试策略蓝图',
        },
        isSettingsOpen: false,
        isGenerating: false,
        pendingStageTransition: null,
        ...overrides,
    });
}

describe('generateResponseStream system prompt integration', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        resetStore();
        mockFetch.mockResolvedValue({
            ok: true,
            body: createSseStream(),
        });
    });

    it('sends next-stage Agent Runtime request with prior stage artifact context', async () => {
        await collectStream(generateResponseStream('请继续生成当前阶段产出物'));

        expect(mockFetch).toHaveBeenCalledTimes(1);
        const [, options] = mockFetch.mock.calls[0];
        const body = JSON.parse(options.body);

        expect(body).toMatchObject({
            prompt: '请继续生成当前阶段产出物',
            workflowId: 'TEST_DESIGN',
            stageId: 'STRATEGY',
        });
        expect(body.systemPrompt).toContain('当前阶段：策略制定');
        expect(body.systemPrompt).toContain('阶段 [CLARIFY] 核心成果');
        expect(body.systemPrompt).toContain('登录支付链路');
    });
});
