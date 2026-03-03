import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useStore } from '../../store';

// ------------------------------------------------------------------
// Mock 外部依赖
// ------------------------------------------------------------------

// 1. Mock OpenAI SDK
const mockCreate = vi.fn();
let capturedOpenAIArgs: any = null;
vi.mock('openai', () => {
    const MockOpenAI = vi.fn().mockImplementation(function (this: any, args: any) {
        capturedOpenAIArgs = args;
        this.chat = { completions: { create: mockCreate } };
    });
    return { default: MockOpenAI };
});

// 2. Mock systemPrompt
vi.mock('../prompts/systemPrompt', () => ({
    getSystemPrompt: vi.fn(
        (_wf: string, _stage: number, _art: string) => 'mocked-system-prompt'
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
    gen: AsyncGenerator<any, void, unknown>
): Promise<any[]> {
    const results: any[] = [];
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

// ------------------------------------------------------------------
// 公共初始化
// ------------------------------------------------------------------

function resetStore(overrides: Record<string, any> = {}) {
    useStore.setState({
        apiKey: '',
        baseUrl: '',
        model: 'test-model',
        isUserConfigured: false,
        workflow: 'TEST_DESIGN',
        stageIndex: 0,
        chatHistory: [],
        artifactContent: '# Initial',
        artifactHistory: [],
        stageArtifacts: { 0: '# Initial' },
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
        capturedOpenAIArgs = null;
        resetStore();
    });

    // ================================================================
    // A. 后端代理模式 (isUserConfigured = false)
    // ================================================================
    describe('后端代理模式（默认模式，无用户 API Key）', () => {
        it('应正确通过 fetch 调用后端代理并解析 SSE 流', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"content":"<CHAT>你好"}',
                    'data: {"content":"</CHAT><ARTIFACT>NO_UPDATE</ARTIFACT>"}',
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(
                generateResponseStream('hello')
            );

            // 验证 fetch 被正确调用
            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, options] = mockFetch.mock.calls[0];
            expect(url).toBe('/new-agents/api/chat/stream');
            expect(options.method).toBe('POST');
            expect(JSON.parse(options.body)).toMatchObject({
                messages: expect.arrayContaining([
                    { role: 'system', content: 'mocked-system-prompt' },
                    { role: 'user', content: 'hello' },
                ]),
                temperature: 0.7,
            });

            // 验证解析结果
            expect(results.length).toBeGreaterThan(0);
            const lastResult = results[results.length - 1];
            expect(lastResult.chatResponse).toContain('你好');
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
            ).rejects.toThrow('后端代理请求失败');
        });

        it('应在 SSE 流中遇到 error 字段时抛出错误', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"error":"OpenAI API unreachable"}',
                ]),
            });

            await expect(
                collectStream(generateResponseStream('hi'))
            ).rejects.toThrow('OpenAI API unreachable');
        });

        it('应在 SSE 遇到 [DONE] 标记时正常结束流', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"content":"chunk1"}',
                    'data: [DONE]',
                    'data: {"content":"这段不应该被处理"}',
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
                    'data: {"content":"valid"}',
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(generateResponseStream('hi'));
            expect(results.length).toBeGreaterThan(0);
        });

        it('应妥善处理格式错误的 JSON 数据（静默忽略）', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {broken json',
                    'data: {"content":"ok"}',
                    'data: [DONE]',
                ]),
            });

            // 不应抛出异常，而是跳过无效 JSON 继续处理
            const results = await collectStream(generateResponseStream('hi'));
            expect(results.length).toBeGreaterThan(0);
        });

        it('应正确处理分块到达的 SSE 数据', async () => {
            // 模拟网络分片：一个事件被分成多个 chunk
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createChunkedSSEStream(
                    [
                        'data: {"content":"<CHAT>Hello</CHAT>"}',
                        'data: {"content":"<ARTIFACT>NO_UPDATE</ARTIFACT>"}',
                        'data: [DONE]',
                    ],
                    15 // 每 15 字节一个 chunk
                ),
            });

            const results = await collectStream(generateResponseStream('hi'));
            expect(results.length).toBeGreaterThan(0);
        });
    });

    // ================================================================
    // B. 前端直连模式 (isUserConfigured = true, apiKey 存在)
    // ================================================================
    describe('前端直连模式（用户配置了 API Key）', () => {
        beforeEach(() => {
            resetStore({
                isUserConfigured: true,
                apiKey: 'sk-test-key-123',
                baseUrl: 'https://api.test.com/v1',
                model: 'gpt-4-test',
            });
        });

        it('应使用 OpenAI SDK 创建客户端并流式获取响应', async () => {
            // Mock OpenAI stream 返回
            const mockStream = (async function* () {
                yield { choices: [{ delta: { content: '<CHAT>Hi' } }] };
                yield { choices: [{ delta: { content: '</CHAT>' } }] };
                yield { choices: [{ delta: { content: '<ARTIFACT>NO_UPDATE</ARTIFACT>' } }] };
            })();
            mockCreate.mockResolvedValueOnce(mockStream);

            const results = await collectStream(generateResponseStream('test'));

            // 验证 OpenAI 构造参数
            expect(capturedOpenAIArgs).toEqual({
                apiKey: 'sk-test-key-123',
                baseURL: 'https://api.test.com/v1',
                dangerouslyAllowBrowser: true,
            });

            // 验证 create 调用参数
            expect(mockCreate).toHaveBeenCalledWith({
                model: 'gpt-4-test',
                messages: expect.arrayContaining([
                    { role: 'system', content: 'mocked-system-prompt' },
                ]),
                temperature: 0.7,
                stream: true,
            });

            // 验证结果
            expect(results.length).toBeGreaterThan(0);
            const lastResult = results[results.length - 1];
            expect(lastResult.chatResponse).toContain('Hi');
            // 不应该调用 fetch（代理模式）
            expect(mockFetch).not.toHaveBeenCalled();
        });

        it('应在 baseUrl 为空时传递 undefined 给 OpenAI', async () => {
            resetStore({
                isUserConfigured: true,
                apiKey: 'sk-test',
                baseUrl: '',
                model: 'gpt-4',
            });

            const mockStream = (async function* () {
                yield { choices: [{ delta: { content: 'x' } }] };
            })();
            mockCreate.mockResolvedValueOnce(mockStream);

            await collectStream(generateResponseStream('test'));

            expect(capturedOpenAIArgs).toMatchObject({ baseURL: undefined });
        });

        it('应跳过空的 delta.content', async () => {
            const mockStream = (async function* () {
                yield { choices: [{ delta: { content: '' } }] };
                yield { choices: [{ delta: { content: null } }] };
                yield { choices: [{ delta: { content: 'real' } }] };
                yield { choices: [] }; // choices 为空数组
            })();
            mockCreate.mockResolvedValueOnce(mockStream);

            const results = await collectStream(generateResponseStream('test'));
            // 只有 "real" 应该产生一次 yield
            expect(results.length).toBe(1);
        });
    });

    // ================================================================
    // C. 消息构建 — 聊天历史和附件
    // ================================================================
    describe('消息构建', () => {
        it('应将聊天历史正确注入到 messages 数组中', async () => {
            resetStore({
                chatHistory: [
                    { id: '1', role: 'user', content: '第一条消息', timestamp: 1 },
                    { id: '2', role: 'assistant', content: '回复', timestamp: 2 },
                ],
            });

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream(['data: {"content":"ok"}', 'data: [DONE]']),
            });

            await collectStream(generateResponseStream('新消息'));

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            expect(body.messages).toHaveLength(4); // system + 2 history + 1 new
            expect(body.messages[0].role).toBe('system');
            expect(body.messages[1]).toEqual({ role: 'user', content: '第一条消息' });
            expect(body.messages[2]).toEqual({ role: 'assistant', content: '回复' });
            expect(body.messages[3]).toEqual({ role: 'user', content: '新消息' });
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
                body: createSSEStream(['data: {"content":"ok"}', 'data: [DONE]']),
            });

            await collectStream(
                generateResponseStream('用户消息', attachments)
            );

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            const userMsg = body.messages[body.messages.length - 1];
            expect(userMsg.content).toContain('[附件: test.txt]');
            expect(userMsg.content).toContain(testContent);
            expect(userMsg.content).toContain('用户消息');
        });

        it('无附件时应直接使用原始文本', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream(['data: {"content":"ok"}', 'data: [DONE]']),
            });

            await collectStream(generateResponseStream('纯文本'));

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            const userMsg = body.messages[body.messages.length - 1];
            expect(userMsg.content).toBe('纯文本');
            expect(userMsg.content).not.toContain('[附件:');
        });

        it('空附件数组时应等价于无附件', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream(['data: {"content":"ok"}', 'data: [DONE]']),
            });

            await collectStream(generateResponseStream('纯文本', []));

            const body = JSON.parse(mockFetch.mock.calls[0][1].body);
            const userMsg = body.messages[body.messages.length - 1];
            expect(userMsg.content).toBe('纯文本');
        });
    });

    // ================================================================
    // D. 流式解析 — parseLlmStreamChunk 集成
    // ================================================================
    describe('流式解析集成', () => {
        it('应逐步解析 CHAT/ARTIFACT/ACTION 标签并 yield 结构化结果', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"content":"<CHAT>你好"}',
                    'data: {"content":"</CHAT>"}',
                    'data: {"content":"<ACTION>NEXT_STAGE</ACTION>"}',
                    'data: {"content":"<ARTIFACT># 新文档</ARTIFACT>"}',
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(generateResponseStream('hi'));
            const lastResult = results[results.length - 1];

            expect(lastResult.chatResponse).toBe('你好');
            expect(lastResult.action).toBe('NEXT_STAGE');
            expect(lastResult.newArtifact).toBe('# 新文档');
            expect(lastResult.hasArtifactUpdate).toBe(true);
        });

        it('应在 ARTIFACT 为 NO_UPDATE 时保留原始 artifactContent', async () => {
            resetStore({ artifactContent: '# 原始内容' });

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"content":"<CHAT>ok</CHAT><ARTIFACT>NO_UPDATE</ARTIFACT>"}',
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(generateResponseStream('hi'));
            const lastResult = results[results.length - 1];

            expect(lastResult.newArtifact).toBe('# 原始内容');
            expect(lastResult.hasArtifactUpdate).toBe(false);
        });

        it('fullText 应随每次 chunk 累加（渐进式解析）', async () => {
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"content":"<CHA"}',
                    'data: {"content":"T>进行中"}',
                    'data: {"content":"</CHAT>"}',
                    'data: {"content":"<ARTIFACT>NO_UPDATE</ARTIFACT>"}',
                    'data: [DONE]',
                ]),
            });

            const results = await collectStream(generateResponseStream('hi'));

            // 前几个 yield 可能只有部分解析
            expect(results.length).toBeGreaterThanOrEqual(2);
            // 最后一个 yield 应该有完整解析
            const lastResult = results[results.length - 1];
            expect(lastResult.chatResponse).toContain('进行中');
        });
    });

    // ================================================================
    // E. 中止 (Abort) 处理
    // ================================================================
    describe('中止信号处理', () => {
        it('前端直连模式：abort 应在下一个 chunk 处抛出错误', async () => {
            resetStore({
                isUserConfigured: true,
                apiKey: 'sk-test',
                model: 'gpt-4',
            });

            const controller = new AbortController();

            const mockStream = (async function* () {
                yield { choices: [{ delta: { content: 'part1' } }] };
                // 在读取第一个 chunk 后模拟中止
                controller.abort();
                yield { choices: [{ delta: { content: 'part2' } }] };
            })();
            mockCreate.mockResolvedValueOnce(mockStream);

            await expect(
                collectStream(generateResponseStream('test', undefined, controller.signal))
            ).rejects.toThrow('Aborted by user');
        });

        it('后端代理模式：abort 应传递给 fetch', async () => {
            const controller = new AbortController();

            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream([
                    'data: {"content":"part1"}',
                    'data: [DONE]',
                ]),
            });

            // 先正常完成，验证 signal 被传递
            await collectStream(
                generateResponseStream('test', undefined, controller.signal)
            );

            expect(mockFetch).toHaveBeenCalledWith(
                '/new-agents/api/chat/stream',
                expect.objectContaining({ signal: controller.signal })
            );
        });
    });

    // ================================================================
    // F. 模式选择逻辑
    // ================================================================
    describe('模式自动选择', () => {
        it('isUserConfigured=true 且 apiKey 非空时走前端直连', async () => {
            resetStore({ isUserConfigured: true, apiKey: 'sk-key' });
            const mockStream = (async function* () {
                yield { choices: [{ delta: { content: 'x' } }] };
            })();
            mockCreate.mockResolvedValueOnce(mockStream);

            await collectStream(generateResponseStream('test'));

            expect(mockCreate).toHaveBeenCalled();
            expect(mockFetch).not.toHaveBeenCalled();
        });

        it('isUserConfigured=true 但 apiKey 为空时走代理模式', async () => {
            resetStore({ isUserConfigured: true, apiKey: '' });
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream(['data: {"content":"x"}', 'data: [DONE]']),
            });

            await collectStream(generateResponseStream('test'));

            expect(mockFetch).toHaveBeenCalled();
            expect(mockCreate).not.toHaveBeenCalled();
        });

        it('isUserConfigured=false 时走代理模式', async () => {
            resetStore({ isUserConfigured: false, apiKey: 'whatever' });
            mockFetch.mockResolvedValueOnce({
                ok: true,
                body: createSSEStream(['data: {"content":"x"}', 'data: [DONE]']),
            });

            await collectStream(generateResponseStream('test'));

            expect(mockFetch).toHaveBeenCalled();
            expect(mockCreate).not.toHaveBeenCalled();
        });
    });
});
