import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactElement } from 'react';
import { act, cleanup, render, renderHook, waitFor } from '@testing-library/react';
import { ArtifactPane } from '../ArtifactPane';
import { useChatService } from '../../services/chatService';
import { useStore, type WorkflowType } from '../../store';

vi.mock('../../services/runSnapshotService', async (importOriginal) => {
    const actual = await importOriginal<typeof import('../../services/runSnapshotService')>();
    return {
        ...actual,
        updateRunArtifact: vi.fn(),
        updateRunArtifactCollaboration: vi.fn(),
    };
});

vi.mock('../../services/storyHandoffPacketService', () => ({
    fetchStoryHandoffCandidates: vi.fn().mockResolvedValue([]),
    fetchStoryHandoffPackets: vi.fn().mockResolvedValue([]),
    createStoryHandoffPacket: vi.fn(),
}));

vi.mock('../Mermaid', () => ({
    Mermaid: ({ chart }: { chart: string }) => <div data-testid="mermaid">{chart}</div>,
}));

vi.mock('../../services/mermaidRetryService', () => ({
    retryMermaidGeneration: vi.fn(),
}));

vi.mock('lucide-react', () => {
    const icons = [
        'Download',
        'Code',
        'Eye',
        'History',
        'X',
        'AlertTriangle',
        'GitCompare',
        'Edit3',
        'Save',
        'MessageSquare',
        'Trash2',
        'Lock',
        'Unlock',
        'MoreHorizontal',
        'RefreshCw',
    ];
    const mod: Record<string, () => ReactElement> = {};
    icons.forEach((name) => {
        mod[name] = () => <span>{name}</span>;
    });
    return mod;
});

type WorkflowProbe = {
    workflow: WorkflowType;
    title: string;
    firstSection: string;
    secondSection: string;
    thirdSection: string;
};

const WORKFLOW_PROBES: WorkflowProbe[] = [
    { workflow: 'TEST_DESIGN', title: '需求分析文档', firstSection: '需求事实', secondSection: '系统边界', thirdSection: '业务规则' },
    { workflow: 'REQ_REVIEW', title: '需求评审问题清单', firstSection: '评审范围', secondSection: '质量总览', thirdSection: '问题统计' },
    { workflow: 'INCIDENT_REVIEW', title: '故障复盘报告', firstSection: '事件摘要', secondSection: '影响指标', thirdSection: '事实来源' },
    { workflow: 'IDEA_BRAINSTORM', title: '问题域分析', firstSection: '问题陈述', secondSection: '目标用户', thirdSection: '问题全景' },
    { workflow: 'VALUE_DISCOVERY', title: '价值定位分析', firstSection: '定位摘要', secondSection: '目标场景', thirdSection: '痛点证据' },
    { workflow: 'STORY_BREAKDOWN', title: '用户故事拆解包', firstSection: '输入分析', secondSection: 'Epic Map', thirdSection: '故事待办' },
    { workflow: 'PRD_REVIEW', title: 'PRD 输入盘点', firstSection: '目标与范围', secondSection: '输入事实', thirdSection: '已有验收标准' },
];

const sseEvent = (event: unknown): string => `data: ${JSON.stringify(event)}\n\n`;

const buildArtifact = (
    probe: WorkflowProbe,
    sectionCount: 1 | 2 | 3,
): string => [
    `# ${probe.title}`,
    '',
    `## ${probe.firstSection}`,
    '',
    `${probe.firstSection}正文`,
    ...(sectionCount >= 2 ? [
        '',
        `## ${probe.secondSection}`,
        '',
        `${probe.secondSection}正文`,
    ] : []),
    ...(sectionCount >= 3 ? [
        '',
        `## ${probe.thirdSection}`,
        '',
        `${probe.thirdSection}正文`,
    ] : []),
].join('\n');

describe('all workflow artifact streaming through the headless DOM', () => {
    beforeEach(() => {
        useStore.setState({
            chatHistory: [],
            artifactContent: '',
            artifactChangeIndex: [],
            artifactHistory: [],
            artifactComments: [],
            artifactSectionLocks: [],
            stageArtifacts: {},
            stageIndex: 0,
            workflow: 'TEST_DESIGN',
            currentRunId: null,
            isGenerating: false,
            pendingStageTransition: null,
        });
    });

    afterEach(() => {
        cleanup();
        vi.unstubAllGlobals();
    });

    it.each(WORKFLOW_PROBES)(
        '$workflow commits three typed SSE artifact snapshots and one final version',
        async (probe) => {
            const firstArtifact = buildArtifact(probe, 1);
            const secondArtifact = buildArtifact(probe, 2);
            const finalArtifact = buildArtifact(probe, 3);
            let releaseSecondArtifact: () => void = () => undefined;
            const waitForSecondArtifact = new Promise<void>((resolve) => {
                releaseSecondArtifact = resolve;
            });
            let releaseFinalEvents: () => void = () => undefined;
            const waitForFinalEvents = new Promise<void>((resolve) => {
                releaseFinalEvents = resolve;
            });
            const encoder = new TextEncoder();
            const body = new ReadableStream<Uint8Array>({
                async start(controller) {
                    controller.enqueue(encoder.encode(sseEvent({ type: 'run_started' })));
                    controller.enqueue(encoder.encode(sseEvent({
                        type: 'agent_delta',
                        output: {
                            chat: '我已完成当前阶段分析，正在逐段更新右侧产出物。',
                            artifact_update: { type: 'none' },
                            warnings: [],
                        },
                    })));
                    controller.enqueue(encoder.encode(sseEvent({
                        type: 'agent_delta',
                        output: {
                            artifact_update: {
                                type: 'replace',
                                markdown: firstArtifact,
                            },
                            warnings: [],
                        },
                    })));
                    await waitForSecondArtifact;
                    controller.enqueue(encoder.encode(sseEvent({
                        type: 'agent_delta',
                        output: {
                            artifact_update: {
                                type: 'replace',
                                markdown: secondArtifact,
                            },
                            warnings: [],
                        },
                    })));
                    await waitForFinalEvents;
                    controller.enqueue(encoder.encode(sseEvent({
                        type: 'agent_delta',
                        output: {
                            artifact_update: {
                                type: 'replace',
                                markdown: finalArtifact,
                            },
                            warnings: [],
                        },
                    })));
                    controller.enqueue(encoder.encode(sseEvent({
                        type: 'agent_turn',
                        output: {
                            chat: '当前阶段分析已完成，请查看右侧完整产出物。',
                            artifact_update: {
                                type: 'replace',
                                markdown: finalArtifact,
                            },
                            stage_action: null,
                            warnings: [],
                        },
                    })));
                    controller.enqueue(encoder.encode('data: [DONE]\n\n'));
                    controller.close();
                },
            });
            vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, body }));
            useStore.setState({ workflow: probe.workflow, stageIndex: 0 });

            render(<ArtifactPane />);
            const { result } = renderHook(() => useChatService());
            act(() => result.current.setInput('请生成当前阶段产出物'));
            let sendPromise: Promise<void> | undefined;
            act(() => {
                sendPromise = result.current.handleSend();
            });

            await waitFor(() => {
                const content = document.querySelector('[data-testid="artifact-content"]');
                expect(content?.textContent).toContain(`${probe.firstSection}正文`);
                expect(content?.textContent).not.toContain(`${probe.secondSection}正文`);
                expect(useStore.getState().artifactHistory).toHaveLength(0);
            });

            await act(async () => {
                releaseSecondArtifact();
            });
            await waitFor(() => {
                const content = document.querySelector('[data-testid="artifact-content"]');
                expect(content?.textContent).toContain(`${probe.secondSection}正文`);
                expect(content?.textContent).not.toContain(`${probe.thirdSection}正文`);
                expect(useStore.getState().artifactHistory).toHaveLength(0);
            });

            await act(async () => {
                releaseFinalEvents();
                await sendPromise;
            });

            const content = document.querySelector('[data-testid="artifact-content"]');
            expect(content?.textContent).toContain(`${probe.firstSection}正文`);
            expect(content?.textContent).toContain(`${probe.secondSection}正文`);
            expect(content?.textContent).toContain(`${probe.thirdSection}正文`);
            expect(useStore.getState().artifactContent).toBe(finalArtifact);
            expect(useStore.getState().artifactHistory).toHaveLength(1);
            expect(useStore.getState().artifactHistory[0]?.content).toBe(finalArtifact);
        },
    );
});
