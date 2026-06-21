import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useStore, type Attachment, type ChatState } from '../../store';
import agentRuntimeEventFixtures from '../../../../contract-fixtures/agent-runtime-events.json';

type TestStreamChunk = {
    chatResponse: string;
    newArtifact: string;
    action: string;
    hasArtifactUpdate: boolean;
    artifactTruncated?: boolean;
};

// ------------------------------------------------------------------
// Mock 外部依赖
// ------------------------------------------------------------------

const { mockMermaidParse } = vi.hoisted(() => ({
    mockMermaidParse: vi.fn(),
}));

vi.mock('mermaid', () => ({
    default: {
        parse: mockMermaidParse,
    },
}));

// 2. Mock systemPrompt
vi.mock('../prompts/buildSystemPrompt', () => ({
    buildSystemPrompt: vi.fn(
        () => 'mocked-system-prompt'
    ),
}));

// 3. Mock fetch (用于后端代理模式)
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// 导入被测模块（在 Mock 之后）
import { generateResponseStream } from '../llm';

// ------------------------------------------------------------------
// 辅助工具
// ------------------------------------------------------------------

/** 收集 async generator 的所有 yield 值 */
async function collectStream(
    gen: AsyncGenerator<TestStreamChunk, void, unknown>
): Promise<TestStreamChunk[]> {
    const results: TestStreamChunk[] = [];
    for await (const val of gen) {
        results.push(val);
    }
    return results;
}

/** 构造一个模拟的 SSE ReadableStream */
function createSSEStream(events: string[]): ReadableStream<Uint8Array> {
    const encoder = new TextEncoder();
    const fullPayload = events.join('\n') + '\n';
    return new ReadableStream({
        start(controller) {
            controller.enqueue(encoder.encode(fullPayload));
            controller.close();
        },
    });
}

/** 构造一个分块的 SSE ReadableStream（模拟网络分片） */
function createChunkedSSEStream(
    events: string[],
    chunkSize: number
): ReadableStream<Uint8Array> {
    const encoder = new TextEncoder();
    const fullPayload = events.join('\n') + '\n';
    const bytes = encoder.encode(fullPayload);
    let offset = 0;

    return new ReadableStream({
        pull(controller) {
            if (offset >= bytes.length) {
                controller.close();
                return;
            }
            const end = Math.min(offset + chunkSize, bytes.length);
            controller.enqueue(bytes.slice(offset, end));
            offset = end;
        },
    });
}

function createRawSSEStream(payload: string): ReadableStream<Uint8Array> {
    const encoder = new TextEncoder();
    return new ReadableStream({
        start(controller) {
            controller.enqueue(encoder.encode(payload));
            controller.close();
        },
    });
}

type AgentTestOutput = {
    chat: string;
    artifact_update: {
        type: 'replace' | 'none';
        markdown?: string;
    };
    stage_action: null | {
        type: 'request_next_stage';
        target_stage_id: string;
    };
    warnings: string[];
};

function createAgentTurnEvent(output: AgentTestOutput): string {
    return `data: ${JSON.stringify({ type: 'agent_turn', output })}`;
}

function createAgentDeltaEvent(output: Partial<AgentTestOutput>): string {
    return `data: ${JSON.stringify({ type: 'agent_delta', output })}`;
}

function createDefaultAgentTurnStream(chat = 'ok'): ReadableStream<Uint8Array> {
    return createSSEStream([
        createAgentTurnEvent({
            chat,
            artifact_update: { type: 'none' },
            stage_action: null,
            warnings: [],
        }),
        'data: [DONE]',
    ]);
}

function createFixtureEventStream(events: unknown[]): ReadableStream<Uint8Array> {
    return createSSEStream([
        ...events.map(event => `data: ${JSON.stringify(event)}`),
        'data: [DONE]',
    ]);
}

// ------------------------------------------------------------------
// 公共初始化
// ------------------------------------------------------------------

function resetStore(overrides: Partial<ChatState> = {}) {
    useStore.setState({
        workflow: 'VALUE_DISCOVERY',
        stageIndex: 0,
        chatHistory: [],
        artifactContent: '# Initial',
        artifactHistory: [],
        stageArtifacts: { ELEVATOR: '# Initial' },
        currentRunId: null,
        isSettingsOpen: false,
        isGenerating: false,
        ...overrides,
    });
}

// ------------------------------------------------------------------
// 测试开始
// ------------------------------------------------------------------

describe('llm.ts', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockMermaidParse.mockResolvedValue({});
        resetStore();
    });

    // ================================================================
    // A. 后端结构化 Agent Runtime
    // ================================================================
    describe('后端结构化 Agent Runtime', () => {
        it('应正确通过 fetch 调用结构化 Agent Runtime 并解析 typed SSE 流', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream('你好'),
            });

            const results = await collectStream(
                generateResponseStream('hello')
            );

            // 验证 fetch 被正确调用
            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, options] = mockFetch.mock.calls[0];
            expect(url).toBe('/new-agents/api/agent/runs/stream');
            expect(options.method).toBe('POST');
            expect(JSON.parse(options.body)).toMatchObject({
                prompt: 'hello',
                systemPrompt: 'mocked-system-prompt',
                workflowId: 'VALUE_DISCOVERY',
                stageId: 'ELEVATOR',
            });
            expect(JSON.parse(options.body)).not.toHaveProperty('runId');

            // 验证解析结果
            expect(results).toEqual([
                {
                    chatResponse: '你好',
                    newArtifact: '# Initial',
                    action: '',
                    hasArtifactUpdate: false,
                },
            ]);
        });

        it('不应在 prompt 中重复注入刚发送的当前用户消息', async () => {
            resetStore({
                workflow: 'VALUE_DISCOVERY',
                stageIndex: 0,
                chatHistory: [
                    {
                        id: 'current-user-message',
                        role: 'user',
                        content: 'hello',
                        timestamp: 1,
                    },
                ],
                artifactContent: '# Initial',
                stageArtifacts: { ELEVATOR: '# Initial' },
            });
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream('你好'),
            });

            await collectStream(generateResponseStream('hello'));

            const [, options] = mockFetch.mock.calls[0];
            expect(JSON.parse(options.body).prompt).toBe('hello');
        });

        it('TEST_DESIGN/CLARIFY 应走结构化 Agent Runtime 并解析 typed event', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 0,
                artifactContent: '# 需求分析文档\n\n初始内容',
                stageArtifacts: { CLARIFY: '# 需求分析文档\n\n初始内容' },
            });
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"已更新需求分析文档。","artifact_update":{"type":"replace","markdown":"# 需求分析文档\\n\\n## 1. 被测系统与边界\\n登录功能"},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('登录功能需要测试')
            );

            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, options] = mockFetch.mock.calls[0];
            expect(url).toBe('/new-agents/api/agent/runs/stream');
            expect(options.method).toBe('POST');
            expect(JSON.parse(options.body)).toMatchObject({
                prompt: '登录功能需要测试',
                systemPrompt: 'mocked-system-prompt',
                workflowId: 'TEST_DESIGN',
                stageId: 'CLARIFY',
            });

            expect(results.at(-1)).toEqual({
                chatResponse: '已更新需求分析文档。',
                newArtifact: '# 需求分析文档\n\n## 1. 被测系统与边界\n登录功能',
                action: '',
                hasArtifactUpdate: true,
            });
        });

        it('结构化 Agent Runtime warnings 包含 artifact_truncated 时应标记产出物截断', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentTurnEvent({
                        chat: '产出物内容可能不完整，请检查。',
                        artifact_update: {
                            type: 'replace',
                            markdown: '# 价值定位分析\n\n## 产品核心定位\n内容',
                        },
                        stage_action: null,
                        warnings: ['artifact_truncated'],
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('生成长文档')
            );

            expect(results.at(-1)).toEqual({
                chatResponse: '产出物内容可能不完整，请检查。',
                newArtifact: '# 价值定位分析\n\n## 产品核心定位\n内容',
                action: '',
                hasArtifactUpdate: true,
                artifactTruncated: true,
            });
        });

        it('长 agent_turn 回复应渐进拆分为多个累计聊天 chunk，并同步揭示产出物', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 0,
                artifactContent: '# 需求分析文档\n\n初始内容',
                stageArtifacts: { CLARIFY: '# 需求分析文档\n\n初始内容' },
            });
            const fullChat = [
                '需求太模糊了，没法直接出测试用例。',
                '我会先把边界和阻断问题梳理出来。',
                '请补充系统形态、登录方式、目标用户和安全要求。',
            ].join('\n\n');
            const nextArtifact = '# 需求分析文档\n\n## 1. 被测系统与边界\n登录功能\n\n## 2. 系统交互与核心链路\n待澄清\n\n## 3. 待澄清与阻断性问题\n系统形态未知\n\n## 4. 隐式需求与非功能性考量\n安全要求待确认';
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentTurnEvent({
                        chat: fullChat,
                        artifact_update: {
                            type: 'replace',
                            markdown: nextArtifact,
                        },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('帮我设计登录功能测试用例')
            );

            expect(results.length).toBeGreaterThan(1);
            expect(results.at(0)).toMatchObject({
                chatResponse: '需求太模糊了，没法直接出测试用例。',
                newArtifact: '# 需求分析文档\n\n## 1. 被测系统与边界\n登录功能',
                hasArtifactUpdate: true,
            });
            expect(results.at(-1)).toEqual({
                chatResponse: fullChat,
                newArtifact: nextArtifact,
                action: '',
                hasArtifactUpdate: true,
            });
        });

        it('中文单段 agent_turn 回复也应渐进拆分并同步揭示右侧产出物', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 0,
                artifactContent: '# 需求分析文档\n\n初始内容',
                stageArtifacts: { CLARIFY: '# 需求分析文档\n\n初始内容' },
            });
            const fullChat = '我会先梳理登录链路。然后补充边界条件。最后生成风险清单。';
            const nextArtifact = [
                '# 需求分析文档',
                '',
                '## 1. 被测系统与边界',
                '登录链路覆盖账号密码、验证码和锁定策略。',
                '',
                '## 2. 系统交互与核心链路',
                '用户提交凭证后进入鉴权、风控和会话创建。',
                '',
                '## 3. 待澄清与阻断性问题',
                '需要确认验证码触发条件。',
                '',
                '## 4. 隐式需求与非功能性考量',
                '需要覆盖安全、可用性和审计要求。',
            ].join('\n');
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentTurnEvent({
                        chat: fullChat,
                        artifact_update: {
                            type: 'replace',
                            markdown: nextArtifact,
                        },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('帮我设计登录功能测试用例')
            );

            expect(results.length).toBeGreaterThan(1);
            expect(results.at(0)).toMatchObject({
                chatResponse: '我会先梳理登录链路。',
                hasArtifactUpdate: true,
            });
            expect(results.at(0)?.newArtifact).toContain('# 需求分析文档');
            expect(results.at(0)?.newArtifact.length).toBeLessThan(nextArtifact.length);
            expect(results.at(-1)).toEqual({
                chatResponse: fullChat,
                newArtifact: nextArtifact,
                action: '',
                hasArtifactUpdate: true,
            });
        });

        it('应解析 run_started 和 agent_delta 以便首帧快速返回并实时更新草稿', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 0,
                artifactContent: '# 需求分析文档\n\n初始内容',
                stageArtifacts: { CLARIFY: '# 需求分析文档\n\n初始内容' },
            });
            const draftArtifact = '# 需求分析文档\n\n## 1. 被测系统与边界\n登录功能';
            const finalArtifact = [
                '# 需求分析文档',
                '',
                '## 1. 被测系统与边界',
                '登录功能',
                '',
                '## 2. 系统交互与核心链路',
                '待补充',
                '',
                '## 3. 待澄清与阻断性问题',
                '需要确认验证码策略',
                '',
                '## 4. 隐式需求与非功能性考量',
                '覆盖安全和审计要求',
            ].join('\n');
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"run_started"}',
                    createAgentDeltaEvent({
                        chat: '正在梳理需求。',
                    }),
                    createAgentDeltaEvent({
                        chat: '正在梳理需求。\n\n已生成初稿。',
                        artifact_update: {
                            type: 'replace',
                            markdown: draftArtifact,
                        },
                        stage_action: null,
                        warnings: [],
                    }),
                    createAgentTurnEvent({
                        chat: '正在梳理需求。\n\n已生成初稿。',
                        artifact_update: {
                            type: 'replace',
                            markdown: finalArtifact,
                        },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('帮我设计登录功能测试用例')
            );

            expect(results[0]).toEqual({
                chatResponse: '正在生成...',
                newArtifact: '# 需求分析文档\n\n初始内容',
                action: '',
                hasArtifactUpdate: false,
            });
            expect(results[1]).toEqual({
                chatResponse: '正在梳理需求。',
                newArtifact: '# 需求分析文档\n\n初始内容',
                action: '',
                hasArtifactUpdate: false,
            });
            expect(results[2]).toEqual({
                chatResponse: '正在梳理需求。\n\n已生成初稿。',
                newArtifact: draftArtifact,
                action: '',
                hasArtifactUpdate: true,
            });
            expect(results.at(-1)).toEqual({
                chatResponse: '正在梳理需求。\n\n已生成初稿。',
                newArtifact: finalArtifact,
                action: '',
                hasArtifactUpdate: true,
            });
        });

        it('应保存 run_started 返回的 runId', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"run_started","runId":"run-123"}',
                    createAgentTurnEvent({
                        chat: '你好',
                        artifact_update: { type: 'none' },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            await collectStream(generateResponseStream('hello'));

            expect(useStore.getState().currentRunId).toBe('run-123');
        });

        it('应解析共享 typed Agent Runtime SSE fixture 中的成功事件', async () => {
            const successEvents = agentRuntimeEventFixtures.events.filter(
                event => event.type !== 'error'
            );
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createFixtureEventStream(successEvents),
            });

            const results = await collectStream(generateResponseStream('hello'));

            expect(useStore.getState().currentRunId).toBe('run-fixture-123');
            expect(results.at(-1)).toMatchObject({
                chatResponse: '已更新右侧产出物。',
                newArtifact: expect.stringContaining('# 价值定位分析'),
                action: 'NEXT_STAGE',
                hasArtifactUpdate: true,
            });
        });

        it('应解析共享 typed Agent Runtime SSE fixture 中的错误事件', async () => {
            const errorEvent = agentRuntimeEventFixtures.events.find(
                event => event.type === 'error'
            );
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createFixtureEventStream([errorEvent]),
            });

            await expect(collectStream(generateResponseStream('hello')))
                .rejects
                .toThrow('CONTRACT_VALIDATION_FAILED: missing required heading');
        });

        it('run_started 带 context_truncated warning 时应显示可见上下文截断提示', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"run_started","runId":"run-123","warnings":["context_truncated"]}',
                    createAgentTurnEvent({
                        chat: '你好',
                        artifact_update: { type: 'none' },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(generateResponseStream('hello'));

            expect(results[0]).toMatchObject({
                chatResponse: expect.stringContaining('上下文'),
                hasArtifactUpdate: false,
            });
            expect(results[0].chatResponse).toContain('截断');
        });

        it('已有 currentRunId 时应在请求体中携带 runId', async () => {
            useStore.getState().setCurrentRunId('run-123');
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream('你好'),
            });

            await collectStream(generateResponseStream('hello'));

            const [, options] = mockFetch.mock.calls[0];
            expect(JSON.parse(options.body)).toMatchObject({
                runId: 'run-123',
            });
        });

        it('应将单个长 agent_delta.chat 拆分为多帧聊天更新', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentDeltaEvent({
                        chat: '第一句分析已经完成。第二句继续补充关键风险。第三句说明下一步需要澄清。',
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('帮我分析登录功能')
            );

            expect(results.length).toBeGreaterThan(1);
            expect(results[0]).toMatchObject({
                chatResponse: '第一句分析已经完成。',
                hasArtifactUpdate: false,
            });
            expect(results.at(-1)).toMatchObject({
                chatResponse: '第一句分析已经完成。第二句继续补充关键风险。第三句说明下一步需要澄清。',
                hasArtifactUpdate: false,
            });
        });

        it('多个 artifact delta 携带相同长 chat 时不应让左侧聊天回退变短', async () => {
            const chat = '好的，我们开始梳理手机号验证码登录功能。\n\n我已在右侧生成需求分析文档初稿，请重点确认阻断问题。';
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentDeltaEvent({
                        chat,
                        artifact_update: {
                            type: 'replace',
                            markdown: '# 需求分析文档\n\n第一段',
                        },
                    }),
                    createAgentDeltaEvent({
                        chat,
                        artifact_update: {
                            type: 'replace',
                            markdown: '# 需求分析文档\n\n第一段\n\n第二段',
                        },
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('帮我设计登录功能测试用例')
            );

            const chatLengths = results.map(result => result.chatResponse.length);
            expect(chatLengths).toEqual([...chatLengths].sort((a, b) => a - b));
            expect(results.at(-1)).toMatchObject({
                chatResponse: chat,
                newArtifact: '# 需求分析文档\n\n第一段\n\n第二段',
                hasArtifactUpdate: true,
            });
        });

        it('TEST_DESIGN/CLARIFY typed artifact 包含坏 Mermaid 时应拒绝更新', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 0,
                artifactContent: '# 需求分析文档\n\n初始内容',
                stageArtifacts: { CLARIFY: '# 需求分析文档\n\n初始内容' },
            });
            mockMermaidParse.mockRejectedValueOnce(new Error('Syntax Error'));
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"已更新需求分析文档。","artifact_update":{"type":"replace","markdown":"# 需求分析文档\\n\\n```mermaid\\nsequenceDiagram\\n    A->>\\n```"},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('登录功能需要测试'))
            ).rejects.toThrow('Artifact Mermaid parse failed');
            expect(mockMermaidParse).toHaveBeenCalledWith(
                'sequenceDiagram\n    A->>',
                { suppressErrors: false }
            );
        });

        it('TEST_DESIGN/STRATEGY typed artifact 应先修正常见 Mermaid 变体再预校验', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 1,
                artifactContent: '# 测试策略蓝图\n\n初始内容',
                stageArtifacts: { STRATEGY: '# 测试策略蓝图\n\n初始内容' },
            });
            const artifact = [
                '# 测试策略蓝图',
                '',
                '```mermaid',
                'block-beta',
                '    columns 1 block["测试分层"] {',
                '        e2e["端到端验证"]',
                '    }',
                '```',
            ].join('\n');
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    `data: ${JSON.stringify({
                        type: 'agent_turn',
                        output: {
                            chat: '已更新测试策略蓝图。',
                            artifact_update: {
                                type: 'replace',
                                markdown: artifact,
                            },
                            stage_action: null,
                            warnings: [],
                        },
                    })}`,
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('制定测试策略')
            );

            expect(mockMermaidParse).toHaveBeenCalledWith(
                [
                    'block-beta',
                    '    columns 1',
                    '    block_1["测试分层"]',
                    '        e2e["端到端验证"]',
                ].join('\n'),
                { suppressErrors: false }
            );
            expect(results.at(-1)).toMatchObject({
                chatResponse: '已更新测试策略蓝图。',
                newArtifact: artifact,
                hasArtifactUpdate: true,
            });
        });

        it('TEST_DESIGN/STRATEGY typed artifact 应先清洗 quadrantChart 变体再校验', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 1,
                artifactContent: '# 测试策略蓝图\n\n初始内容',
                stageArtifacts: { STRATEGY: '# 测试策略蓝图\n\n初始内容' },
            });
            mockMermaidParse.mockImplementationOnce(async (code: string) => {
                if (code.includes('title 登录功能风险矩阵 x-axis')) {
                    throw new Error('raw quadrant syntax should be sanitized first');
                }
                return {};
            });
            const artifact = [
                '# 测试策略蓝图',
                '',
                '```mermaid',
                'quadrantChart',
                'title 登录功能风险矩阵 x-axis 低发生概率 --> 高发生概率',
                'y-axis 低严重度 --> 高严重度',
                'quadrant-1 高优先级',
                '登录失败锁定: [0.7, 0.8]',
                '```',
            ].join('\n');
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    `data: ${JSON.stringify({
                        type: 'agent_turn',
                        output: {
                            chat: '已更新测试策略蓝图。',
                            artifact_update: {
                                type: 'replace',
                                markdown: artifact,
                            },
                            stage_action: null,
                            warnings: [],
                        },
                    })}`,
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(generateResponseStream('继续'));

            expect(results.at(-1)).toMatchObject({
                newArtifact: artifact,
                hasArtifactUpdate: true,
            });
            expect(mockMermaidParse).toHaveBeenCalledWith(
                expect.stringContaining('title 登录功能风险矩阵\n    x-axis "低发生概率" --> "高发生概率"'),
                { suppressErrors: false }
            );
        });

        it('TEST_DESIGN/CLARIFY typed artifact 不应把 mermaid-js 代码块当作 Mermaid 校验', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 0,
                artifactContent: '# 需求分析文档\n\n初始内容',
                stageArtifacts: { CLARIFY: '# 需求分析文档\n\n初始内容' },
            });
            mockMermaidParse.mockRejectedValueOnce(new Error('should not parse mermaid-js'));
            const artifact = [
                '# 需求分析文档',
                '',
                '```mermaid-js',
                'const chart = "not a mermaid diagram";',
                '```',
            ].join('\n');
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    `data: ${JSON.stringify({
                        type: 'agent_turn',
                        output: {
                            chat: '已更新需求分析文档。',
                            artifact_update: {
                                type: 'replace',
                                markdown: artifact,
                            },
                            stage_action: null,
                            warnings: [],
                        },
                    })}`,
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('登录功能需要测试')
            );

            expect(mockMermaidParse).not.toHaveBeenCalled();
            expect(results.at(-1)).toEqual({
                chatResponse: '已更新需求分析文档。',
                newArtifact: artifact,
                action: '',
                hasArtifactUpdate: true,
            });
        });

        it('agent_turn 已建议确认进入下一阶段但缺少 stage_action 时应同轮显示确认控件', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 0,
                artifactContent: '# 需求分析文档\n\n初始内容',
                stageArtifacts: { CLARIFY: '# 需求分析文档\n\n初始内容' },
            });
            const artifact = '# 需求分析文档\n\n## 1. 被测系统与边界\n登录功能';
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentTurnEvent({
                        chat: '已根据默认场景更新《需求分析文档》。请查看右侧文档，确认无误后回复“确认”进入下一阶段（策略制定）。',
                        artifact_update: {
                            type: 'replace',
                            markdown: artifact,
                        },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('我想要测试一下当前的工作流，帮我假定一个场景')
            );

            expect(results.at(-1)).toEqual({
                chatResponse: '已根据默认场景更新《需求分析文档》。请查看右侧文档，确认无误后回复“确认”进入下一阶段（策略制定）。',
                newArtifact: artifact,
                action: 'NEXT_STAGE',
                hasArtifactUpdate: true,
            });
        });

        it('agent_turn 仍要求补充阻断信息时不应推断下一阶段确认控件', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 0,
                artifactContent: '# 需求分析文档\n\n初始内容',
                stageArtifacts: { CLARIFY: '# 需求分析文档\n\n初始内容' },
            });
            const artifact = '# 需求分析文档\n\n## 3. 待澄清与阻断性问题\n- 验证码有效期待确认';
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentTurnEvent({
                        chat: '我已生成需求澄清初稿。请重点确认待澄清问题，需要你确认或补充信息后才能进入下一阶段。',
                        artifact_update: {
                            type: 'replace',
                            markdown: artifact,
                        },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('请为手机号验证码登录功能生成需求澄清初稿')
            );

            expect(results.at(-1)).toEqual({
                chatResponse: '我已生成需求澄清初稿。请重点确认待澄清问题，需要你确认或补充信息后才能进入下一阶段。',
                newArtifact: artifact,
                action: '',
                hasArtifactUpdate: true,
            });
        });

        it('agent_turn 带截断警告时即使文案建议进入下一阶段也不应显示确认控件', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 0,
                artifactContent: '# 需求分析文档\n\n初始内容',
                stageArtifacts: { CLARIFY: '# 需求分析文档\n\n初始内容' },
            });
            const artifact = '# 需求分析文档\n\n## 1. 被测系统与边界\n登录功能';
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentTurnEvent({
                        chat: '已根据默认场景更新《需求分析文档》。确认无误后回复“确认”进入下一阶段（策略制定）。',
                        artifact_update: {
                            type: 'replace',
                            markdown: artifact,
                        },
                        stage_action: null,
                        warnings: ['artifact_truncated'],
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('我想要测试一下当前的工作流，帮我假定一个场景')
            );

            expect(results.at(-1)).toEqual({
                chatResponse: '已根据默认场景更新《需求分析文档》。确认无误后回复“确认”进入下一阶段（策略制定）。',
                newArtifact: artifact,
                action: '',
                hasArtifactUpdate: true,
                artifactTruncated: true,
            });
        });

        it('TEST_DESIGN/STRATEGY 也应走结构化 Agent Runtime', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 1,
                artifactContent: '# 测试策略蓝图\n\n初始内容',
                stageArtifacts: {
                    CLARIFY: '# 需求分析文档\n\n已确认',
                    STRATEGY: '# 测试策略蓝图\n\n初始内容',
                },
            });
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"已更新测试策略蓝图。","artifact_update":{"type":"replace","markdown":"# 测试策略蓝图\\n\\n## 1. 质量目标\\n稳定可靠"},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('继续制定测试策略')
            );

            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, options] = mockFetch.mock.calls[0];
            expect(url).toBe('/new-agents/api/agent/runs/stream');
            expect(JSON.parse(options.body)).toMatchObject({
                prompt: '继续制定测试策略',
                systemPrompt: 'mocked-system-prompt',
                workflowId: 'TEST_DESIGN',
                stageId: 'STRATEGY',
            });
            expect(results.at(-1)).toMatchObject({
                chatResponse: '已更新测试策略蓝图。',
                newArtifact: '# 测试策略蓝图\n\n## 1. 质量目标\n稳定可靠',
                hasArtifactUpdate: true,
            });
        });

        it('REQ_REVIEW/REVIEW 应走结构化 Agent Runtime', async () => {
            resetStore({
                workflow: 'REQ_REVIEW',
                stageIndex: 0,
                artifactContent: '# 需求评审问题清单\n\n初始内容',
                stageArtifacts: {
                    REVIEW: '# 需求评审问题清单\n\n初始内容',
                },
            });
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"已更新需求评审问题清单。","artifact_update":{"type":"replace","markdown":"# 需求评审问题清单\\n\\n## 评审概要\\n登录需求评审\\n\\n## 问题统计\\n暂无阻塞项"},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('评审这份登录需求')
            );

            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, options] = mockFetch.mock.calls[0];
            expect(url).toBe('/new-agents/api/agent/runs/stream');
            expect(JSON.parse(options.body)).toMatchObject({
                prompt: '评审这份登录需求',
                systemPrompt: 'mocked-system-prompt',
                workflowId: 'REQ_REVIEW',
                stageId: 'REVIEW',
            });
            expect(results.at(-1)).toMatchObject({
                chatResponse: '已更新需求评审问题清单。',
                newArtifact: '# 需求评审问题清单\n\n## 评审概要\n登录需求评审\n\n## 问题统计\n暂无阻塞项',
                hasArtifactUpdate: true,
            });
        });

        it('INCIDENT_REVIEW/TIMELINE 应走结构化 Agent Runtime', async () => {
            resetStore({
                workflow: 'INCIDENT_REVIEW',
                stageIndex: 0,
                artifactContent: '# 故障复盘报告\n\n初始内容',
                stageArtifacts: {
                    TIMELINE: '# 故障复盘报告\n\n初始内容',
                },
            });
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"已更新事件还原。","artifact_update":{"type":"replace","markdown":"# 故障复盘报告\\n\\n## 1. 事件概要\\n支付失败\\n\\n## 2. 事件时间线\\n待补充"},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('昨天支付失败故障需要复盘')
            );

            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, options] = mockFetch.mock.calls[0];
            expect(url).toBe('/new-agents/api/agent/runs/stream');
            expect(JSON.parse(options.body)).toMatchObject({
                prompt: '昨天支付失败故障需要复盘',
                systemPrompt: 'mocked-system-prompt',
                workflowId: 'INCIDENT_REVIEW',
                stageId: 'TIMELINE',
            });
            expect(results.at(-1)).toMatchObject({
                chatResponse: '已更新事件还原。',
                newArtifact: '# 故障复盘报告\n\n## 1. 事件概要\n支付失败\n\n## 2. 事件时间线\n待补充',
                hasArtifactUpdate: true,
            });
        });

        it('IDEA_BRAINSTORM/DEFINE 应走结构化 Agent Runtime', async () => {
            resetStore({
                workflow: 'IDEA_BRAINSTORM',
                stageIndex: 0,
                artifactContent: '# 问题域分析\n\n初始内容',
                stageArtifacts: {
                    DEFINE: '# 问题域分析\n\n初始内容',
                },
            });
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"已更新问题域分析。","artifact_update":{"type":"replace","markdown":"# 问题域分析\\n\\n## 问题假设陈述\\n独立开发者变现困难\\n\\n## 目标用户画像\\n独立开发者"},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('我想做独立开发者变现工具')
            );

            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, options] = mockFetch.mock.calls[0];
            expect(url).toBe('/new-agents/api/agent/runs/stream');
            expect(JSON.parse(options.body)).toMatchObject({
                prompt: '我想做独立开发者变现工具',
                systemPrompt: 'mocked-system-prompt',
                workflowId: 'IDEA_BRAINSTORM',
                stageId: 'DEFINE',
            });
            expect(results.at(-1)).toMatchObject({
                chatResponse: '已更新问题域分析。',
                newArtifact: '# 问题域分析\n\n## 问题假设陈述\n独立开发者变现困难\n\n## 目标用户画像\n独立开发者',
                hasArtifactUpdate: true,
            });
        });

        it('VALUE_DISCOVERY/ELEVATOR 应走结构化 Agent Runtime', async () => {
            resetStore({
                workflow: 'VALUE_DISCOVERY',
                stageIndex: 0,
                artifactContent: '# 价值定位分析\n\n初始内容',
                stageArtifacts: {
                    ELEVATOR: '# 价值定位分析\n\n初始内容',
                },
            });
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"已更新价值定位。","artifact_update":{"type":"replace","markdown":"# 价值定位分析\\n\\n## 产品核心定位\\n开发者变现工具\\n\\n## 目标用户概览\\n独立开发者"},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('我想做一个开发者变现工具')
            );

            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, options] = mockFetch.mock.calls[0];
            expect(url).toBe('/new-agents/api/agent/runs/stream');
            expect(JSON.parse(options.body)).toMatchObject({
                prompt: '我想做一个开发者变现工具',
                systemPrompt: 'mocked-system-prompt',
                workflowId: 'VALUE_DISCOVERY',
                stageId: 'ELEVATOR',
            });
            expect(results.at(-1)).toMatchObject({
                chatResponse: '已更新价值定位。',
                newArtifact: '# 价值定位分析\n\n## 产品核心定位\n开发者变现工具\n\n## 目标用户概览\n独立开发者',
                hasArtifactUpdate: true,
            });
        });

        it('应在后端返回非 200 状态码时抛出错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                json: async () => ({ error: '系统未配置' }),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('系统未配置');
        });

        it('应在后端返回非 200 且无法解析 JSON 时使用默认错误消息', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                json: async () => { throw new Error('not json'); },
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体请求失败');
        });

        it('应在后端非 200 错误字段为对象时提取 message', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: false,
                json: async () => ({
                    error: {
                        code: 'DEFAULT_LLM_MISSING',
                        message: '后端默认 LLM 未配置',
                    },
                }),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('后端默认 LLM 未配置');
        });

        it('应在 200 响应缺少流式 body 时抛出明确错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: null,
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体响应缺少流式内容');
        });

        it('应在 SSE 流中遇到 error 字段时抛出错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"error","code":"LLM_ERROR","message":"OpenAI API unreachable"}',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('OpenAI API unreachable');
        });

        it('应在 SSE error 抛错中保留后端错误分类 code', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"error","code":"CONTRACT_VALIDATION_FAILED","message":"missing heading"}',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('CONTRACT_VALIDATION_FAILED: missing heading');
        });

        it('应在 SSE 遇到 [DONE] 标记时正常结束流', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentTurnEvent({
                        chat: 'chunk1',
                        artifact_update: { type: 'none' },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                    createAgentTurnEvent({
                        chat: '这段不应该被处理',
                        artifact_update: { type: 'none' },
                        stage_action: null,
                        warnings: [],
                    }),
                ]),
            });

            const results = await collectStream(generateResponseStream('hi'));
            // [DONE] 之后的内容不应被处理
            const allText = results.map((r) => r.chatResponse).join('');
            expect(allText).not.toContain('这段不应该被处理');
        });

        it('应忽略非 data: 开头的 SSE 行', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    ': this is a comment',
                    'event: ping',
                    createAgentTurnEvent({
                        chat: 'valid',
                        artifact_update: { type: 'none' },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(generateResponseStream('hi'));
            expect(results.length).toBeGreaterThan(0);
        });

        it('应接受冒号后不带空格的 SSE data 行', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentTurnEvent({
                        chat: '无空格 data 行',
                        artifact_update: { type: 'none' },
                        stage_action: null,
                        warnings: [],
                    }).replace('data: ', 'data:'),
                    'data:[DONE]',
                ]),
            });

            const results = await collectStream(generateResponseStream('hi'));

            expect(results).toEqual([
                {
                    chatResponse: '无空格 data 行',
                    newArtifact: '# Initial',
                    action: '',
                    hasArtifactUpdate: false,
                },
            ]);
        });

        it('SSE 数据格式错误时应直接报错，不静默跳过协议问题', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {broken json',
                    createAgentTurnEvent({
                        chat: 'ok',
                        artifact_update: { type: 'none' },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 数据格式错误');
        });

        it('SSE agent_turn 缺少 output 时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn"}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE error 事件缺少 message 时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"error","code":"LLM_ERROR"}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE error 事件缺少 code 时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"error","message":"failed"}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE agent_turn output 缺少 chat 时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"artifact_update":{"type":"none"},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE agent_turn output chat 为空白时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"   ","artifact_update":{"type":"none"},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE agent_turn output chat 包含旧标签协议时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentTurnEvent({
                        chat: '<CHART>我已经在右侧生成了《需求分析文档》框架。</CHART>',
                        artifact_update: { type: 'none' },
                        stage_action: null,
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE agent_turn output 缺少 artifact_update 时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"ok","stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE agent_turn artifact_update 为 none 但包含 markdown 时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"ok","artifact_update":{"type":"none","markdown":"# 不应出现"},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE agent_turn artifact_update 为 replace 但 markdown 为空时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"ok","artifact_update":{"type":"replace","markdown":"   "},"stage_action":null,"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE agent_turn stage_action 缺少 target_stage_id 时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"ok","artifact_update":{"type":"none"},"stage_action":{"type":"request_next_stage"},"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE agent_turn stage_action 类型非法时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"ok","artifact_update":{"type":"none"},"stage_action":{"type":"jump","target_stage_id":"STRATEGY"},"warnings":[]}}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE agent_turn warnings 不是字符串数组时应抛出明确协议错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"type":"agent_turn","output":{"chat":"ok","artifact_update":{"type":"none"},"stage_action":null,"warnings":"artifact_truncated"}}',
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 事件格式错误');
        });

        it('SSE agent_turn stage_action 目标不是下一阶段时应抛出明确协议错误', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 0,
                artifactContent: '# 需求分析文档\n\n初始内容',
                stageArtifacts: { CLARIFY: '# 需求分析文档\n\n初始内容' },
            });
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    createAgentTurnEvent({
                        chat: 'ok',
                        artifact_update: { type: 'none' },
                        stage_action: {
                            type: 'request_next_stage',
                            target_stage_id: 'CASES',
                        },
                        warnings: [],
                    }),
                    'data: [DONE]',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('结构化智能体 SSE 阶段动作目标错误');
        });

        it('应正确处理分块到达的 SSE 数据', async () => {
            // 模拟网络分片：一个事件被分成多个 chunk
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createChunkedSSEStream(
                    [
                        createAgentTurnEvent({
                            chat: 'Hello',
                            artifact_update: { type: 'none' },
                            stage_action: null,
                            warnings: [],
                        }),
                        'data: [DONE]',
                    ],
                    15 // 每 15 字节一个 chunk
                ),
            });

            const results = await collectStream(generateResponseStream('hi'));
            expect(results.length).toBeGreaterThan(0);
        });

        it('应按标准 SSE 语义聚合同一事件中的多行 data 字段', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createRawSSEStream(
                    [
                        'data: {"type":"agent_turn",',
                        'data: "output":{"chat":"多行事件",',
                        'data: "artifact_update":{"type":"none"},',
                        'data: "stage_action":null,"warnings":[]}}',
                        '',
                        'data: [DONE]',
                        '',
                    ].join('\n')
                ),
            });

            const results = await collectStream(generateResponseStream('hi'));

            expect(results).toEqual([
                {
                    chatResponse: '多行事件',
                    newArtifact: '# Initial',
                    action: '',
                    hasArtifactUpdate: false,
                },
            ]);
        });

        it('应处理流结束时没有尾随换行的最后一个 SSE 事件', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createRawSSEStream(
                    createAgentTurnEvent({
                        chat: '最后一条',
                        artifact_update: { type: 'none' },
                        stage_action: null,
                        warnings: [],
                    })
                ),
            });

            const results = await collectStream(generateResponseStream('hi'));

            expect(results).toEqual([
                {
                    chatResponse: '最后一条',
                    newArtifact: '# Initial',
                    action: '',
                    hasArtifactUpdate: false,
                },
            ]);
        });
    });

    // ================================================================
    // B. 消息构建 — 聊天历史和附件
    // ================================================================
    describe('消息构建', () => {
        it('应将聊天历史正确注入到结构化 runtime prompt 中', async () => {
            resetStore({
                chatHistory: [
                    { id: '1', role: 'user', content: '第一条消息', timestamp: 1 },
                    { id: '2', role: 'assistant', content: '回复', timestamp: 2 },
                ],
            });

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(generateResponseStream('新消息'));

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt).toContain('[用户]\n第一条消息');
            expect(body.prompt).toContain('[助手]\n回复');
            expect(body.prompt).toContain('[用户]\n新消息');
            expect(body).not.toHaveProperty('messages');
        });

        it('已有 currentRunId 时不应把本地聊天历史注入 runtime prompt', async () => {
            resetStore({
                currentRunId: 'run-123',
                chatHistory: [
                    { id: '1', role: 'user', content: '第一条消息', timestamp: 1 },
                    { id: '2', role: 'assistant', content: '回复', timestamp: 2 },
                ],
            });

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(generateResponseStream('新消息'));

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.runId).toBe('run-123');
            expect(body.prompt).toBe('新消息');
            expect(body.prompt).not.toContain('第一条消息');
            expect(body.prompt).not.toContain('回复');
        });

        it('不应将错误或停止控制反馈注入到结构化 runtime prompt 中', async () => {
            resetStore({
                chatHistory: [
                    { id: '1', role: 'user', content: '普通用户消息', timestamp: 1 },
                    { id: '2', role: 'assistant', content: '普通助手回复', timestamp: 2 },
                    { id: '3', role: 'assistant', content: '**Error:** LLM_ERROR\n请求失败', timestamp: 3 },
                    { id: '4', role: 'assistant', content: '*(已停止生成)*', timestamp: 4 },
                    { id: '5', role: 'assistant', content: '正在生成...\n\n**Error:** LLM_ERROR\n流式中途失败', timestamp: 5 },
                    { id: '6', role: 'assistant', content: '正在生成...\n\n*(已停止生成)*', timestamp: 6 },
                    { id: '7', role: 'assistant', content: '正在生成...\n\n⚠️ **模型额度或限流异常**\n请稍后重试。', timestamp: 7 },
                ],
            });

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(generateResponseStream('继续'));

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt).toContain('[用户]\n普通用户消息');
            expect(body.prompt).toContain('[助手]\n普通助手回复');
            expect(body.prompt).toContain('[用户]\n继续');
            expect(body.prompt).not.toContain('**Error:** LLM_ERROR');
            expect(body.prompt).not.toContain('请求失败');
            expect(body.prompt).not.toContain('*(已停止生成)*');
            expect(body.prompt).not.toContain('流式中途失败');
            expect(body.prompt).not.toContain('已停止生成');
            expect(body.prompt).not.toContain('模型额度或限流异常');
        });

        it('应将附件的 base64 内容解码并拼接到消息文本前', async () => {
            // btoa('附件内容') — 需要用 TextEncoder 制作 base64
            const testContent = '附件内容测试';
            const base64Content = btoa(
                String.fromCharCode(
                    ...new TextEncoder().encode(testContent)
                )
            );

            const attachments = [
                { name: 'test.txt', data: base64Content, mimeType: 'text/plain' },
            ];

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(
                generateResponseStream('用户消息', attachments)
            );

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt).toContain('[附件: test.txt]');
            expect(body.prompt).toContain(testContent);
            expect(body.prompt).toContain('用户消息');
        });

        it('不应将图片或 PDF 附件按 UTF-8 文本解码进 prompt', async () => {
            const attachments = [
                {
                    name: 'screen.png',
                    data: btoa('\x89PNG\r\n\x1a\nbinary-image-content'),
                    mimeType: 'image/png',
                },
                {
                    name: 'report.pdf',
                    data: btoa('%PDF-1.7 binary-pdf-content'),
                    mimeType: 'application/pdf',
                },
            ];

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(
                generateResponseStream('请分析附件', attachments)
            );

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt).toContain('[附件: screen.png]');
            expect(body.prompt).toContain('类型: image/png');
            expect(body.prompt).toContain('[附件: report.pdf]');
            expect(body.prompt).toContain('类型: application/pdf');
            expect(body.prompt).toContain('非文本附件未注入原始二进制内容');
            expect(body.prompt).not.toContain('binary-image-content');
            expect(body.prompt).not.toContain('binary-pdf-content');
            expect(body.prompt).toContain('请分析附件');
        });

        it('附件缺少 mimeType 时应按扩展名判断文本类型', async () => {
            const testContent = '历史附件内容';
            const base64Content = btoa(
                String.fromCharCode(
                    ...new TextEncoder().encode(testContent)
                )
            );
            const attachments = [
                { name: 'legacy.md', data: base64Content } as Attachment,
            ];

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(
                generateResponseStream('请读取历史附件', attachments)
            );

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt).toContain('[附件: legacy.md]');
            expect(body.prompt).toContain('类型: unknown');
            expect(body.prompt).toContain(testContent);
            expect(body.prompt).toContain('请读取历史附件');
        });

        it('文本附件 base64 损坏时不应阻断 Agent 请求', async () => {
            const attachments = [
                {
                    name: 'broken.md',
                    data: 'not-valid-base64%',
                    mimeType: 'text/markdown',
                },
            ];

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(
                generateResponseStream('继续分析损坏附件', attachments)
            );

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt).toContain('[附件: broken.md]');
            expect(body.prompt).toContain('类型: text/markdown');
            expect(body.prompt).toContain('文本附件内容无法解码');
            expect(body.prompt).toContain('继续分析损坏附件');
        });

        it('附件缺少文件名时不应阻断 Agent 请求', async () => {
            const attachments = [
                {
                    data: btoa('legacy attachment content'),
                } as Attachment,
            ];

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(
                generateResponseStream('继续分析缺少文件名的附件', attachments)
            );

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt).toContain('[附件: 未命名附件]');
            expect(body.prompt).toContain('类型: unknown');
            expect(body.prompt).toContain('非文本附件未注入原始二进制内容');
            expect(body.prompt).toContain('继续分析缺少文件名的附件');
        });

        it('文本附件缺少 data 时不应阻断 Agent 请求', async () => {
            const attachments = [
                {
                    name: 'missing-data.md',
                    mimeType: 'text/markdown',
                } as Attachment,
            ];

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(
                generateResponseStream('继续分析缺少内容的附件', attachments)
            );

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt).toContain('[附件: missing-data.md]');
            expect(body.prompt).toContain('类型: text/markdown');
            expect(body.prompt).toContain('文本附件内容缺失');
            expect(body.prompt).toContain('继续分析缺少内容的附件');
        });

        it('附件数组包含空记录时不应阻断 Agent 请求', async () => {
            const attachments = [
                null as unknown as Attachment,
            ];

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(
                generateResponseStream('继续分析异常附件记录', attachments)
            );

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt).toContain('[附件: 无效附件记录]');
            expect(body.prompt).toContain('类型: unknown');
            expect(body.prompt).toContain('附件记录无效');
            expect(body.prompt).toContain('继续分析异常附件记录');
        });

        it('历史消息和当前消息都包含空附件记录时仍应去重当前用户消息', async () => {
            const attachments = [
                null as unknown as Attachment,
            ];
            resetStore({
                chatHistory: [
                    {
                        id: 'current-user',
                        role: 'user',
                        content: '继续分析异常附件记录',
                        timestamp: 1,
                        attachments,
                    },
                ],
            });

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(
                generateResponseStream('继续分析异常附件记录', attachments)
            );

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt.match(/继续分析异常附件记录/g)).toHaveLength(1);
            expect(body.prompt).toContain('[附件: 无效附件记录]');
            expect(body.prompt).toContain('附件记录无效');
        });

        it('历史消息和当前消息都包含非数组附件容器时仍应去重当前用户消息', async () => {
            const attachments = {
                name: 'legacy-object-container.md',
            } as unknown as Attachment[];
            resetStore({
                chatHistory: [
                    {
                        id: 'current-user',
                        role: 'user',
                        content: '继续分析异常附件列表',
                        timestamp: 1,
                        attachments,
                    },
                ],
            });

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(
                generateResponseStream('继续分析异常附件列表', attachments)
            );

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt.match(/继续分析异常附件列表/g)).toHaveLength(1);
            expect(body.prompt).toContain('[附件: 无效附件列表]');
            expect(body.prompt).toContain('附件列表格式无效');
        });

        it('无附件时应直接使用原始文本', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(generateResponseStream('纯文本'));

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt).toBe('纯文本');
            expect(body.prompt).not.toContain('[附件:');
        });

        it('空附件数组时应等价于无附件', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream(),
            });

            await collectStream(generateResponseStream('纯文本', []));

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.prompt).toBe('纯文本');
        });
    });

    // C. 中止 (Abort) 处理
    // ================================================================
    describe('中止信号处理', () => {
        it('结构化 Agent Runtime：abort 应传递给 fetch', async () => {
            const controller = new AbortController();

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream('part1'),
            });

            // 先正常完成，验证 signal 被传递
            await collectStream(
                generateResponseStream('test', undefined, controller.signal)
            );

            expect(mockFetch).toHaveBeenCalledWith(
                '/new-agents/api/agent/runs/stream',
                expect.objectContaining({ signal: controller.signal })
            );
        });
    });

    // ================================================================
    // D. 模式选择逻辑
    // ================================================================
    describe('模式自动选择', () => {
        it('始终走结构化 Agent Runtime', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createDefaultAgentTurnStream('x'),
            });

            await collectStream(generateResponseStream('test'));

            expect(mockFetch).toHaveBeenCalled();
            expect(mockFetch.mock.calls[0][0]).toBe('/new-agents/api/agent/runs/stream');
        });

        it('系统代理模式下阶段索引非法时应直接报错，不回退旧文本代理', async () => {
            resetStore({
                workflow: 'TEST_DESIGN',
                stageIndex: 999,
            });

            await expect(
                collectStream(generateResponseStream('test'))
            ).rejects.toThrow('当前工作流阶段不存在');

            expect(mockFetch).not.toHaveBeenCalled();
        });
    });
});
