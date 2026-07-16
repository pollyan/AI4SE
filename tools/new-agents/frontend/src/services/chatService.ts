import { useState, useRef, useCallback, useEffect } from 'react';
import { useStore, Attachment, getWelcomeMessage, WORKFLOWS } from '../store';
import {
    createTurnRequestId,
    generateResponseStream,
    type AgentRunRequestIdentity,
} from '../core/llm';
import {
    planArtifactVersionUpdate,
    planRetryFromHistory,
    reduceAgentStreamChunk,
} from '../core/agentCore';
import {
    buildArtifactSectionChangeIndex,
    findArtifactSection,
    findArtifactSectionLock,
    mergeRegeneratedArtifactSection,
    parseArtifactMarkdownSections,
    preserveLockedArtifactSections,
} from '../core/artifactSections';
import type { ArtifactSectionTarget } from '../core/artifactSections';

const STAGE_CONTINUATION_PROMPT = '请继续生成当前阶段产出物';
let messageIdSequence = 0;

type SendOptions = {
    appendUserMessage?: boolean;
    useDraftAttachments?: boolean;
    attachmentsOverride?: Attachment[];
    sectionRegeneration?: {
        target: ArtifactSectionTarget;
        originalArtifact: string;
    };
};

type ArtifactRollbackSnapshot = {
    artifactContent: string;
    artifactHistory: ReturnType<typeof useStore.getState>['artifactHistory'];
    stageArtifacts: ReturnType<typeof useStore.getState>['stageArtifacts'];
};

function createMessageId(): string {
    messageIdSequence += 1;
    return `${Date.now()}-${messageIdSequence}`;
}

function buildArtifactSectionRegenerationPrompt({
    workflowId,
    stageId,
    target,
    targetContent,
    artifactContent,
    lockedSections,
}: {
    workflowId: string;
    stageId: string;
    target: ArtifactSectionTarget;
    targetContent: string;
    artifactContent: string;
    lockedSections: ReturnType<typeof useStore.getState>['artifactSectionLocks'];
}): string {
    const lockedSectionBlocks = lockedSections.length === 0
        ? '无'
        : lockedSections.map((lock, index) => [
            `### 锁定章节 ${index + 1}`,
            `heading: ${lock.heading}`,
            `anchor: ${lock.sectionAnchor ?? '未记录'}`,
            '````markdown',
            lock.content,
            '````',
        ].join('\n')).join('\n\n');

    return [
        'Artifact 定向修订请求',
        '',
        `Workflow: ${workflowId}`,
        `Stage: ${stageId}`,
        `目标章节: ${target.displayTitle ?? target.heading.replace(/^#{1,3}\s+/, '')}`,
        `目标 heading: ${target.heading}`,
        `目标 anchor: ${target.sectionAnchor ?? '未记录'}`,
        '',
        '请基于当前完整 artifact 重生成目标章节，并返回符合当前阶段契约的完整 artifact。',
        '硬性约束:',
        '- 只改写目标章节的内容。',
        '- 不要改写、删除或重排非目标章节。',
        '- 锁定章节必须逐字保留。',
        '- 返回仍必须是完整 artifact，而不是只返回目标章节。',
        '',
        '当前目标章节内容:',
        '````markdown',
        targetContent,
        '````',
        '',
        '锁定章节:',
        lockedSectionBlocks,
        '',
        '当前完整 artifact:',
        '````markdown',
        artifactContent,
        '````',
    ].join('\n');
}

function getErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : 'Something went wrong.';
}

type ProviderErrorDiagnostic = {
    reason: string;
    action: string;
};

type ErrorDiagnosticPayload = {
    phase?: unknown;
    workflowId?: unknown;
    stageId?: unknown;
    fieldPath?: unknown;
    validator?: unknown;
    retryable?: unknown;
    publicReason?: unknown;
};

type AssistantErrorFeedback = {
    content: string;
    diagnostic: NonNullable<ReturnType<typeof useStore.getState>['chatHistory'][number]['errorDiagnostic']>;
};

const isErrorRecord = (error: unknown): error is Record<string, unknown> => (
    typeof error === 'object' && error !== null
);

function diagnoseProviderError(errorMessage: string): ProviderErrorDiagnostic | null {
    const normalized = errorMessage.toLowerCase();

    if (
        errorMessage.includes('系统未配置默认 LLM')
        || normalized.includes('default llm')
        || normalized.includes('default_llm_missing')
        || normalized.includes('llm config')
    ) {
        return {
            reason: '模型配置缺失',
            action: '请先到设置中维护后端默认 LLM 配置，至少包含 API Key、Base URL 和模型名称。',
        };
    }

    if (
        normalized.includes('401')
        || normalized.includes('403')
        || normalized.includes('api key')
        || normalized.includes('authentication')
        || normalized.includes('unauthorized')
        || normalized.includes('forbidden')
        || normalized.includes('permission')
    ) {
        return {
            reason: '密钥或权限异常',
            action: '请检查 API Key、Base URL、模型名称和供应商权限，确认密钥仍有效且具备调用当前模型的权限。',
        };
    }

    if (
        errorMessage.includes('429')
        || normalized.includes('quota')
        || normalized.includes('rate limit')
        || normalized.includes('ratelimit')
        || normalized.includes('too many requests')
    ) {
        return {
            reason: '模型额度或限流异常',
            action: '请检查供应商额度、并发限制和账户状态；如果是临时限流，可以稍后重试本阶段生成。',
        };
    }

    if (
        normalized.includes('timeout')
        || normalized.includes('timed out')
        || normalized.includes('network')
        || normalized.includes('unreachable')
        || normalized.includes('connection')
        || normalized.includes('connect')
    ) {
        return {
            reason: '供应商连接异常',
            action: '请检查 Base URL、网络连通性或供应商服务状态；如果服务恢复，可以重试本阶段生成。',
        };
    }

    return null;
}

function formatProviderErrorContent(diagnostic: ProviderErrorDiagnostic): string {
    return [
        '⚠️ **模型调用未完成**',
        '',
        `**可能原因**：${diagnostic.reason}`,
        '',
        '右侧产出物已保持不变。处理配置或供应商问题后，可以直接重试本阶段生成。',
    ].join('\n');
}

function getErrorCode(error: unknown): string | undefined {
    if (!isErrorRecord(error)) return undefined;
    return typeof error.code === 'string' ? error.code : undefined;
}

function getErrorDiagnosticPayload(error: unknown): ErrorDiagnosticPayload | null {
    if (!isErrorRecord(error)) return null;
    return isErrorRecord(error.diagnostic)
        ? error.diagnostic
        : null;
}

function isStructuredOutputError(error: unknown, errorMessage: string): boolean {
    const errorCode = getErrorCode(error);
    return (
        errorCode === 'SCHEMA_VALIDATION_FAILED'
        || errorCode === 'VISUAL_VALIDATION_FAILED'
        || errorMessage.includes('SCHEMA_VALIDATION_FAILED')
        || errorMessage.includes('VISUAL_VALIDATION_FAILED')
        || errorMessage.includes('Exceeded maximum output retries')
        || errorMessage.includes('Artifact Mermaid parse failed')
        || errorMessage.includes('Artifact validation failed')
        || errorMessage.includes('Artifact structured visual validation failed')
        || errorMessage.includes('Mermaid parse failed')
    );
}

function formatAssistantErrorFeedback(error: unknown): AssistantErrorFeedback {
    const errorMessage = getErrorMessage(error);
    const errorCode = getErrorCode(error);
    const runtimeDiagnostic = getErrorDiagnosticPayload(error);

    if (
        isStructuredOutputError(error, errorMessage)
    ) {
        const publicReason = typeof runtimeDiagnostic?.publicReason === 'string'
            ? runtimeDiagnostic.publicReason
            : '模型本轮没有生成符合工作流契约的结果，右侧产出物已保持不变。可以直接重试；如果连续失败，请补充更明确的需求或阶段确认信息。';
        return {
            content: [
            '⚠️ **结构化输出生成失败**',
            '',
                publicReason,
            ].join('\n'),
            diagnostic: {
                kind: 'structured',
                summary: '结构化输出生成失败',
                rawMessage: errorMessage,
                ...(errorCode ? { code: errorCode } : {}),
                ...(typeof runtimeDiagnostic?.phase === 'string' ? { phase: runtimeDiagnostic.phase } : {}),
                ...(typeof runtimeDiagnostic?.workflowId === 'string' ? { workflowId: runtimeDiagnostic.workflowId } : {}),
                ...(typeof runtimeDiagnostic?.stageId === 'string' ? { stageId: runtimeDiagnostic.stageId } : {}),
                ...(typeof runtimeDiagnostic?.fieldPath === 'string' ? { fieldPath: runtimeDiagnostic.fieldPath } : {}),
                ...(typeof runtimeDiagnostic?.validator === 'string' ? { validator: runtimeDiagnostic.validator } : {}),
                ...(typeof runtimeDiagnostic?.retryable === 'boolean' ? { retryable: runtimeDiagnostic.retryable } : {}),
            },
        };
    }

    if (isErrorRecord(error) && error.name === 'ArtifactSectionRegenerationError') {
        return {
            content: [
                '⚠️ **本轮生成失败**',
                '',
                errorMessage,
            ].join('\n'),
            diagnostic: {
                kind: 'generic',
                summary: '本轮生成失败',
                rawMessage: errorMessage,
            },
        };
    }

    const providerDiagnostic = diagnoseProviderError(errorMessage);
    if (providerDiagnostic) {
        return {
            content: formatProviderErrorContent(providerDiagnostic),
            diagnostic: {
                kind: 'provider',
                summary: '模型调用未完成',
                rawMessage: errorMessage,
                reason: providerDiagnostic.reason,
                action: providerDiagnostic.action,
            },
        };
    }

    return {
        content: [
            '⚠️ **本轮生成失败**',
            '',
            '模型本轮调用没有完成，右侧产出物已保持不变。可以直接重试；如果连续失败，请补充更明确的上下文后再试。',
        ].join('\n'),
        diagnostic: {
            kind: 'generic',
            summary: '本轮生成失败',
            rawMessage: errorMessage,
        },
    };
}

function isAbortError(error: unknown): boolean {
    return (
        error instanceof DOMException && error.name === 'AbortError'
    ) || (
        error instanceof Error && (
            error.name === 'AbortError'
            || error.message === 'Aborted by user'
        )
    );
}

function createPersistedArtifactRollbackSnapshot(
    state: ReturnType<typeof useStore.getState>
): ArtifactRollbackSnapshot | null {
    if (state.artifactHistory.length < 1) return null;

    const currentStage = WORKFLOWS[state.workflow].stages[state.stageIndex];
    const currentStageId = currentStage.id;
    const latestVersion = state.artifactHistory[state.artifactHistory.length - 1];
    if (latestVersion.stageId !== currentStageId) return null;
    if (latestVersion.content !== state.artifactContent) return null;

    const artifactHistory = state.artifactHistory.slice(0, -1);
    const restoredVersion = artifactHistory[artifactHistory.length - 1];
    const currentStageBaseline = state.stageIndex === 0
        ? getWelcomeMessage(state.workflow)
        : currentStage.template;
    if (!restoredVersion) {
        return {
            artifactContent: currentStageBaseline,
            artifactHistory,
            stageArtifacts: {
                ...state.stageArtifacts,
                [currentStageId]: currentStageBaseline,
            },
        };
    }

    const restoredContent = restoredVersion.stageId === currentStageId
        ? restoredVersion.content
        : currentStageBaseline;

    return {
        artifactContent: restoredContent,
        artifactHistory,
        stageArtifacts: {
            ...state.stageArtifacts,
            [currentStageId]: restoredContent,
        },
    };
}

export function useChatService() {
    const [input, setInput] = useState('');
    const [pendingAttachments, setPendingAttachments] = useState<Attachment[]>([]);
    const abortControllerRef = useRef<AbortController | null>(null);
    const artifactRollbackSnapshotsRef = useRef(new Map<string, ArtifactRollbackSnapshot>());
    const requestIdentityByMessageRef = useRef(
        new Map<string, AgentRunRequestIdentity>()
    );
    const pendingRetryIdentityRef = useRef<AgentRunRequestIdentity | null>(null);

    const restoreRetryRequestIdentity = (
        removedMessages: ReturnType<typeof useStore.getState>['chatHistory']
    ) => {
        const retryIdentity = [...removedMessages]
            .reverse()
            .map(message => requestIdentityByMessageRef.current.get(message.id))
            .find((identity): identity is AgentRunRequestIdentity => Boolean(identity));
        if (retryIdentity) {
            pendingRetryIdentityRef.current = retryIdentity;
        }
    };

    const { chatHistory, addMessage, updateLastMessage, removeLastMessage, isGenerating, setIsGenerating } = useStore();

    useEffect(() => {
        return useStore.subscribe((state, previousState) => {
            if (
                previousState.isGenerating
                && !state.isGenerating
                && abortControllerRef.current
            ) {
                abortControllerRef.current.abort();
            }
        });
    }, []);

    const handleStop = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
    }, []);

    const handleFileChange = useCallback((files: FileList | null) => {
        if (!files || files.length === 0) return;

        Array.from(files).forEach(file => {
            const reader = new FileReader();
            reader.onload = (event) => {
                const base64String = (event.target?.result as string).split(',')[1];
                setPendingAttachments(prev => [
                    ...prev,
                    {
                        name: file.name,
                        data: base64String,
                        mimeType: file.type || 'application/octet-stream'
                    }
                ]);
            };
            reader.readAsDataURL(file);
        });
    }, []);

    const removeAttachment = useCallback((index: number) => {
        setPendingAttachments(prev => prev.filter((_, i) => i !== index));
    }, []);

    const handleSend = useCallback(async (overrideInput?: string, options?: SendOptions) => {
        const textToSend = overrideInput !== undefined ? overrideInput : input.trim();
        if (
            (!textToSend && pendingAttachments.length === 0)
            || useStore.getState().isGenerating
        ) return;

        const shouldAppendUserMessage = options?.appendUserMessage !== false;
        const shouldUseDraftAttachments = options?.attachmentsOverride
            ? false
            : options?.useDraftAttachments !== false;
        const assistantRetryable = shouldAppendUserMessage ? undefined : false;
        const userMsg = textToSend;
        const currentAttachments = options?.attachmentsOverride
            ? [...options.attachmentsOverride]
            : shouldUseDraftAttachments
            ? [...pendingAttachments]
            : [];
        const userMessageId = createMessageId();
        const requestIdentity = pendingRetryIdentityRef.current || {
            runId: useStore.getState().currentRunId || createTurnRequestId(),
            requestId: createTurnRequestId(),
        };
        pendingRetryIdentityRef.current = null;
        if (shouldAppendUserMessage) {
            requestIdentityByMessageRef.current.set(
                userMessageId,
                requestIdentity
            );
        }

        if (overrideInput === undefined || shouldAppendUserMessage) {
            setInput('');
        }
        if (shouldUseDraftAttachments) {
            setPendingAttachments([]);
        }

        if (shouldAppendUserMessage) {
            useStore.getState().clearPendingStageTransition();
        }

        if (shouldAppendUserMessage) {
            addMessage({
                id: userMessageId,
                role: 'user',
                content: userMsg,
                timestamp: Date.now(),
                attachments: currentAttachments.length > 0 ? currentAttachments : undefined,
            });
        }

        setIsGenerating(true);

        const runAbortController = new AbortController();
        abortControllerRef.current = runAbortController;
        let isFirstChunk = true;
        let didUpdateArtifact = false;
        let wasRunAborted = false;
        let didRunFail = false;
        let latestRunArtifactContent = '';
        const runState = useStore.getState();
        const runWorkflow = runState.workflow;
        const runStageIndex = runState.stageIndex;
        const runWorkflowDef = WORKFLOWS[runWorkflow];
        const runStageId = runWorkflowDef.stages[runStageIndex].id;
        const artifactRollbackSnapshot: ArtifactRollbackSnapshot = {
            artifactContent: runState.artifactContent,
            artifactHistory: [...runState.artifactHistory],
            stageArtifacts: { ...runState.stageArtifacts },
        };
        let runAssistantMessageId: string | null = null;
        const isRunStillActive = () => {
            const currentState = useStore.getState();
            return (
                currentState.workflow === runWorkflow
                && currentState.stageIndex === runStageIndex
                && (
                    !shouldAppendUserMessage
                    || currentState.chatHistory.some(message => message.id === userMessageId)
                )
            );
        };
        const isRunHistoryStillActive = () => {
            const currentState = useStore.getState();
            if (currentState.workflow !== runWorkflow) return false;
            if (!shouldAppendUserMessage) {
                return Boolean(
                    runAssistantMessageId
                    && currentState.chatHistory.some(
                        message => message.id === runAssistantMessageId
                    )
                );
            }

            return (
                currentState.chatHistory.some(message => message.id === userMessageId)
            );
        };

        try {
            const stream = generateResponseStream(
                userMsg,
                currentAttachments,
                runAbortController.signal,
                requestIdentity
            );

            let hasTransitioned = false;

            for await (const chunk of stream) {
                if (runAbortController.signal.aborted) {
                    wasRunAborted = true;
                    break;
                }

                if (!isRunStillActive()) {
                    runAbortController.abort();
                    break;
                }

                const decision = reduceAgentStreamChunk(chunk, {
                    stageIndex: runStageIndex,
                    stageCount: runWorkflowDef.stages.length,
                    currentStageId: runStageId,
                    hasTransitioned,
                });
                hasTransitioned = decision.hasTransitioned;

                if (isFirstChunk) {
                    const assistantMessageId = createMessageId();
                    runAssistantMessageId = assistantMessageId;
                    requestIdentityByMessageRef.current.set(
                        assistantMessageId,
                        requestIdentity
                    );
                    artifactRollbackSnapshotsRef.current.set(
                        assistantMessageId,
                        artifactRollbackSnapshot
                    );
                    addMessage({
                        id: assistantMessageId,
                        role: 'assistant',
                        content: decision.assistantContent,
                        timestamp: Date.now(),
                        retryable: assistantRetryable,
                    });
                    isFirstChunk = false;
                } else {
                    updateLastMessage(decision.assistantContent);
                }

                if (decision.artifactTruncated) {
                    useStore.getState().setArtifactTruncated(true);
                }

                if (decision.artifactUpdate) {
                    const latestState = useStore.getState();
                    let handledByPatch = false;
                    let fallbackChangeBaseline: string | null = null;
                    if (decision.artifactUpdate.patch) {
                        const artifactBeforePatch = latestState.artifactContent;
                        const patchResult = latestState.applyArtifactSectionPatch(
                            decision.artifactUpdate.patch
                        );
                        if (
                            patchResult.applied
                            && patchResult.content === decision.artifactUpdate.content
                        ) {
                            if (!decision.artifactTruncated) {
                                latestState.setArtifactTruncated(false);
                            }
                            didUpdateArtifact = true;
                            latestRunArtifactContent = patchResult.content;
                            handledByPatch = true;
                        }
                        if (patchResult.applied && !handledByPatch) {
                            fallbackChangeBaseline = artifactBeforePatch;
                        }
                    }

                    if (!handledByPatch) {
                        const currentState = useStore.getState();
                        const currentStageLocks = currentState.artifactSectionLocks.filter(
                            lock => lock.stageId === decision.artifactUpdate?.stageId
                        );
                        const protectedArtifactContent = options?.sectionRegeneration
                            ? mergeRegeneratedArtifactSection({
                                originalArtifact: options.sectionRegeneration.originalArtifact,
                                generatedArtifact: decision.artifactUpdate.content,
                                target: options.sectionRegeneration.target,
                                locks: currentStageLocks,
                            }).content
                            : preserveLockedArtifactSections(
                                decision.artifactUpdate.content,
                                currentStageLocks,
                            );
                        currentState.setStageArtifact(
                            decision.artifactUpdate.stageId,
                            protectedArtifactContent
                        );
                        currentState.setArtifactContent(
                            protectedArtifactContent
                        );
                        if (fallbackChangeBaseline !== null) {
                            useStore.setState({
                                artifactChangeIndex: buildArtifactSectionChangeIndex(
                                    fallbackChangeBaseline,
                                    protectedArtifactContent
                                ),
                            });
                        }
                        if (!decision.artifactTruncated) {
                            currentState.setArtifactTruncated(false);
                        }
                        didUpdateArtifact = true;
                        latestRunArtifactContent = protectedArtifactContent;
                    }
                }

                if (decision.pendingStageTransition) {
                    useStore.getState().setPendingStageTransition(
                        decision.pendingStageTransition
                    );
                }

                if (decision.shouldStopStream) {
                    runAbortController.abort();
                    break;
                }
            }
        } catch (error) {
            const history = useStore.getState().chatHistory;
            const lastMsgRole = history.length > 0 ? history[history.length - 1].role : null;
            const isMidstream = lastMsgRole === 'assistant' && !isFirstChunk;

            if (isAbortError(error)) {
                wasRunAborted = true;
                if (!isRunStillActive()) return;

                if (didUpdateArtifact) {
                    useStore.getState().setArtifactTruncated(true);
                }
                if (isMidstream) {
                    updateLastMessage((history[history.length - 1]?.content || '') + '\n\n*(已停止生成)*');
                } else {
                    addMessage({
                        id: createMessageId(),
                        role: 'assistant',
                        content: '*(已停止生成)*',
                        timestamp: Date.now(),
                        retryable: assistantRetryable,
                    });
                }
            } else {
                didRunFail = true;
                if (!isRunStillActive()) return;

                if (didUpdateArtifact) {
                    useStore.getState().setArtifactTruncated(true);
                }
                const errorFeedback = formatAssistantErrorFeedback(error);

                if (isMidstream) {
                    updateLastMessage(
                        (history[history.length - 1]?.content || '') + '\n\n' + errorFeedback.content,
                        errorFeedback.diagnostic
                    );
                } else {
                    addMessage({
                        id: createMessageId(),
                        role: 'assistant',
                        content: errorFeedback.content,
                        timestamp: Date.now(),
                        retryable: assistantRetryable,
                        errorDiagnostic: errorFeedback.diagnostic,
                    });
                }
            }
        } finally {
            if (abortControllerRef.current === runAbortController) {
                abortControllerRef.current = null;
                setIsGenerating(false);
            }
            if (didUpdateArtifact && !wasRunAborted && !didRunFail && isRunHistoryStillActive()) {
                const state = useStore.getState();
                const artifactVersionPlan = planArtifactVersionUpdate(
                    latestRunArtifactContent,
                    state.artifactHistory
                );
                if (artifactVersionPlan) {
                    useStore.getState().addArtifactVersion({
                        id: createMessageId(),
                        timestamp: Date.now(),
                        content: artifactVersionPlan.content,
                        stageId: runStageId,
                    });
                }
            }
        }
    }, [input, pendingAttachments, isGenerating, addMessage, updateLastMessage, setIsGenerating]);

    const handleRegenerateArtifactSection = useCallback(async (target: ArtifactSectionTarget) => {
        const state = useStore.getState();
        if (state.isGenerating) return;

        const currentStage = WORKFLOWS[state.workflow].stages[state.stageIndex];
        const currentStageLocks = state.artifactSectionLocks.filter(
            lock => lock.stageId === currentStage.id
        );
        const targetTitle = target.displayTitle ?? target.heading.replace(/^#{1,3}\s+/, '');
        const currentSection = findArtifactSection(
            parseArtifactMarkdownSections(state.artifactContent),
            target
        );
        const lockedSection = findArtifactSectionLock(target, currentStageLocks);

        if (lockedSection) {
            addMessage({
                id: createMessageId(),
                role: 'assistant',
                content: `**Error:** 目标章节“${targetTitle}”已锁定，请先解锁后再重生成。`,
                timestamp: Date.now(),
                retryable: false,
            });
            return;
        }

        if (!currentSection) {
            addMessage({
                id: createMessageId(),
                role: 'assistant',
                content: `**Error:** 当前产出物中没有找到目标章节“${targetTitle}”。`,
                timestamp: Date.now(),
                retryable: false,
            });
            return;
        }

        await handleSend(buildArtifactSectionRegenerationPrompt({
            workflowId: state.workflow,
            stageId: currentStage.id,
            target,
            targetContent: currentSection.content,
            artifactContent: state.artifactContent,
            lockedSections: currentStageLocks,
        }), {
            appendUserMessage: false,
            useDraftAttachments: false,
            sectionRegeneration: {
                target,
                originalArtifact: state.artifactContent,
            },
        });
    }, [addMessage, handleSend]);

    const handleConfirmStageTransition = useCallback(async () => {
        const state = useStore.getState();
        if (!state.pendingStageTransition || state.isGenerating) return;

        const targetStageIndex = state.pendingStageTransition.toStageIndex;
        const targetStage = WORKFLOWS[state.workflow].stages[targetStageIndex];
        state.confirmStageTransition();
        if (useStore.getState().stageIndex !== targetStageIndex) return;

        addMessage({
            id: createMessageId(),
            role: 'user',
            content: `已确认进入${targetStage.name}`,
            timestamp: Date.now(),
        });

        await handleSend(STAGE_CONTINUATION_PROMPT, {
            appendUserMessage: false,
            useDraftAttachments: false,
        });
    }, [addMessage, handleSend]);

    const handleRetry = useCallback(() => {
        const currentState = useStore.getState();
        if (currentState.isGenerating || currentState.chatHistory.length === 0) return;

        const history = currentState.chatHistory;
        const retryPlan = planRetryFromHistory(history);
        if (!retryPlan) return;
        const removedMessages = history.slice(
            history.length - retryPlan.messagesToRemove
        );
        restoreRetryRequestIdentity(removedMessages);
        const inMemoryRollbackSnapshot = [...removedMessages]
            .reverse()
            .map(message => artifactRollbackSnapshotsRef.current.get(message.id))
            .find((snapshot): snapshot is ArtifactRollbackSnapshot => Boolean(snapshot));
        const rollbackSnapshot = inMemoryRollbackSnapshot
            || (
                removedMessages.some(message => message.role === 'assistant')
                    ? createPersistedArtifactRollbackSnapshot(currentState)
                    : null
            );

        for (let i = 0; i < retryPlan.messagesToRemove; i += 1) {
            useStore.getState().removeLastMessage();
        }
        removedMessages.forEach(message => {
            artifactRollbackSnapshotsRef.current.delete(message.id);
        });

        if (rollbackSnapshot) {
            useStore.setState({
                artifactContent: rollbackSnapshot.artifactContent,
                artifactHistory: rollbackSnapshot.artifactHistory,
                stageArtifacts: rollbackSnapshot.stageArtifacts,
            });
        }

        useStore.getState().clearPendingStageTransition();
        useStore.getState().setArtifactTruncated(false);
        setInput(retryPlan.retryInput);
        setPendingAttachments(retryPlan.retryAttachments);

    }, []);

    const handleRetryCurrentStageGeneration = useCallback(async () => {
        const currentState = useStore.getState();
        if (currentState.isGenerating || currentState.chatHistory.length === 0) return;

        const history = currentState.chatHistory;
        const retryPlan = planRetryFromHistory(history);
        const latestMessage = history[history.length - 1];
        const messagesToRemove = retryPlan
            ? retryPlan.messagesToRemove
            : latestMessage?.role === 'assistant'
                ? 1
                : 0;
        if (messagesToRemove === 0) return;

        const removedMessages = history.slice(history.length - messagesToRemove);
        restoreRetryRequestIdentity(removedMessages);
        const inMemoryRollbackSnapshot = [...removedMessages]
            .reverse()
            .map(message => artifactRollbackSnapshotsRef.current.get(message.id))
            .find((snapshot): snapshot is ArtifactRollbackSnapshot => Boolean(snapshot));
        const rollbackSnapshot = inMemoryRollbackSnapshot
            || (
                removedMessages.some(message => message.role === 'assistant')
                    ? createPersistedArtifactRollbackSnapshot(currentState)
                    : null
            );

        for (let i = 0; i < messagesToRemove; i += 1) {
            useStore.getState().removeLastMessage();
        }
        removedMessages.forEach(message => {
            artifactRollbackSnapshotsRef.current.delete(message.id);
        });

        if (rollbackSnapshot) {
            useStore.setState({
                artifactContent: rollbackSnapshot.artifactContent,
                artifactHistory: rollbackSnapshot.artifactHistory,
                stageArtifacts: rollbackSnapshot.stageArtifacts,
            });
        }

        useStore.getState().clearPendingStageTransition();
        useStore.getState().setArtifactTruncated(false);

        if (retryPlan) {
            await handleSend(retryPlan.retryInput, {
                attachmentsOverride: retryPlan.retryAttachments,
            });
            return;
        }

        await handleSend(STAGE_CONTINUATION_PROMPT, {
            appendUserMessage: false,
            useDraftAttachments: false,
        });
    }, [handleSend]);

    return {
        input,
        setInput,
        pendingAttachments,
        setPendingAttachments,
        handleSend,
        handleRegenerateArtifactSection,
        handleConfirmStageTransition,
        handleRetry,
        handleRetryCurrentStageGeneration,
        handleStop,
        handleFileChange,
        removeAttachment
    };
}
