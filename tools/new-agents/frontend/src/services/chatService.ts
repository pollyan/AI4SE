import { useState, useRef, useCallback, useEffect } from 'react';
import { useStore, Attachment, getWelcomeMessage, WORKFLOWS } from '../store';
import { generateResponseStream } from '../core/llm';
import {
    planArtifactVersionUpdate,
    planRetryFromHistory,
    reduceAgentStreamChunk,
} from '../core/agentCore';

const STAGE_CONTINUATION_PROMPT = '请继续生成当前阶段产出物';
let messageIdSequence = 0;

type SendOptions = {
    appendUserMessage?: boolean;
    useDraftAttachments?: boolean;
    attachmentsOverride?: Attachment[];
};

type ArtifactRollbackSnapshot = {
    artifactContent: string;
    artifactHistory: ReturnType<typeof useStore.getState>['artifactHistory'];
    stageArtifacts: ReturnType<typeof useStore.getState>['stageArtifacts'];
};

type MarkdownSection = {
    heading: string;
    startLine: number;
    endLine: number;
};

function createMessageId(): string {
    messageIdSequence += 1;
    return `${Date.now()}-${messageIdSequence}`;
}

function parseMarkdownSections(markdown: string): MarkdownSection[] {
    const lines = markdown.split(/\r?\n/);
    const headingIndexes = lines.flatMap((line, index) => (
        /^#{1,3}\s+/.test(line)
            ? [{ heading: line.trim(), startLine: index }]
            : []
    ));

    return headingIndexes.map((section, index) => ({
        ...section,
        endLine: headingIndexes[index + 1]?.startLine ?? lines.length,
    }));
}

function replaceSectionContent(
    markdown: string,
    section: MarkdownSection,
    replacementContent: string
): string {
    const lines = markdown.split(/\r?\n/);
    const replacementLines = replacementContent.split(/\r?\n/);
    return [
        ...lines.slice(0, section.startLine),
        ...replacementLines,
        ...lines.slice(section.endLine),
    ].join('\n');
}

function preserveLockedSections(
    nextArtifact: string,
    locks: ReturnType<typeof useStore.getState>['artifactSectionLocks']
): string {
    if (locks.length === 0) return nextArtifact;

    let protectedArtifact = nextArtifact;
    locks.forEach((lock) => {
        const sections = parseMarkdownSections(protectedArtifact);
        const section = sections.find(candidate => candidate.heading === lock.heading);
        if (!section) {
            protectedArtifact = protectedArtifact.endsWith('\n')
                ? `${protectedArtifact}${lock.content}`
                : `${protectedArtifact}\n\n${lock.content}`;
            return;
        }
        protectedArtifact = replaceSectionContent(
            protectedArtifact,
            section,
            lock.content,
        );
    });
    return protectedArtifact;
}

function getErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : 'Something went wrong.';
}

type ProviderErrorDiagnostic = {
    reason: string;
    action: string;
};

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

function formatProviderErrorContent(errorMessage: string, diagnostic: ProviderErrorDiagnostic): string {
    return [
        '⚠️ **模型配置或供应商异常**',
        '',
        `**可能原因**：${diagnostic.reason}`,
        '',
        `**建议处理**：${diagnostic.action}`,
        '',
        '右侧产出物已保持不变。处理配置或供应商问题后，可以直接重试本阶段生成。',
        '',
        '---',
        '*原始错误附录：*',
        '```text',
        errorMessage,
        '```',
    ].join('\n');
}

function formatAssistantErrorContent(errorMessage: string): string {
    if (
        errorMessage.includes('SCHEMA_VALIDATION_FAILED')
        || errorMessage.includes('Exceeded maximum output retries')
        || errorMessage.includes('Artifact Mermaid parse failed')
        || errorMessage.includes('Artifact validation failed')
        || errorMessage.includes('Mermaid parse failed')
    ) {
        return [
            '⚠️ **结构化输出生成失败**',
            '',
            '模型本轮没有生成符合工作流契约的结果，右侧产出物已保持不变。可以直接重试；如果连续失败，请补充更明确的需求或阶段确认信息。',
        ].join('\n');
    }

    const providerDiagnostic = diagnoseProviderError(errorMessage);
    if (providerDiagnostic) {
        return formatProviderErrorContent(errorMessage, providerDiagnostic);
    }

    return `**Error:** ${errorMessage}`;
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
            const stream = generateResponseStream(userMsg, currentAttachments, runAbortController.signal);

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

                if (decision.pendingStageTransition) {
                    useStore.getState().setPendingStageTransition(
                        decision.pendingStageTransition
                    );
                }

                if (decision.artifactUpdate) {
                    const latestState = useStore.getState();
                    const currentStageLocks = latestState.artifactSectionLocks.filter(
                        lock => lock.stageId === decision.artifactUpdate?.stageId
                    );
                    const protectedArtifactContent = preserveLockedSections(
                        decision.artifactUpdate.content,
                        currentStageLocks,
                    );
                    latestState.setStageArtifact(
                        decision.artifactUpdate.stageId,
                        protectedArtifactContent
                    );
                    latestState.setArtifactContent(
                        protectedArtifactContent
                    );
                    if (!decision.artifactTruncated) {
                        latestState.setArtifactTruncated(false);
                    }
                    didUpdateArtifact = true;
                    latestRunArtifactContent = protectedArtifactContent;
                }

                if (decision.shouldStopStream) {
                    runAbortController.abort();
                    break;
                }
            }
        } catch (error) {
            const errorMessage = getErrorMessage(error);
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
                const errorContent = formatAssistantErrorContent(errorMessage);

                if (isMidstream) {
                    updateLastMessage((history[history.length - 1]?.content || '') + '\n\n' + errorContent);
                } else {
                    addMessage({
                        id: createMessageId(),
                        role: 'assistant',
                        content: errorContent,
                        timestamp: Date.now(),
                        retryable: assistantRetryable,
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

    const handleConfirmStageTransition = useCallback(async () => {
        const state = useStore.getState();
        if (!state.pendingStageTransition || state.isGenerating) return;

        const targetStageIndex = state.pendingStageTransition.toStageIndex;
        state.confirmStageTransition();
        if (useStore.getState().stageIndex !== targetStageIndex) return;

        await handleSend(STAGE_CONTINUATION_PROMPT, {
            appendUserMessage: false,
            useDraftAttachments: false,
        });
    }, [handleSend]);

    const handleRetry = useCallback(() => {
        const currentState = useStore.getState();
        if (currentState.isGenerating || currentState.chatHistory.length === 0) return;

        const history = currentState.chatHistory;
        const retryPlan = planRetryFromHistory(history);
        if (!retryPlan) return;
        const removedMessages = history.slice(
            history.length - retryPlan.messagesToRemove
        );
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
        handleConfirmStageTransition,
        handleRetry,
        handleRetryCurrentStageGeneration,
        handleStop,
        handleFileChange,
        removeAttachment
    };
}
