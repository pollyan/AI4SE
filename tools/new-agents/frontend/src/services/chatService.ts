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

function getErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : 'Something went wrong.';
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
        const shouldUseDraftAttachments = options?.useDraftAttachments !== false;
        const assistantRetryable = shouldAppendUserMessage ? undefined : false;
        const userMsg = textToSend;
        const currentAttachments = shouldUseDraftAttachments
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
                    latestState.setStageArtifact(
                        decision.artifactUpdate.stageId,
                        decision.artifactUpdate.content
                    );
                    latestState.setArtifactContent(
                        decision.artifactUpdate.content
                    );
                    if (!decision.artifactTruncated) {
                        latestState.setArtifactTruncated(false);
                    }
                    didUpdateArtifact = true;
                    latestRunArtifactContent = decision.artifactUpdate.content;
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
                let errorContent = `**Error:** ${errorMessage}`;

                // Add friendly explanation for 429 Quota Exceeded errors
                if (errorMessage.includes('429') || errorMessage.toLowerCase().includes('quota')) {
                    errorContent = `⚠️ **模型额度或限流异常**\n\n后端默认 LLM 配置当前返回额度或限流错误。主 Agent 调用只通过后端结构化 Agent Runtime 执行，请检查后端默认 LLM 的 API Key、Base URL、模型名称和服务商额度。\n\n---\n*原始错误附录：*\n\`\`\`text\n${errorMessage}\n\`\`\``;
                }

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

    return {
        input,
        setInput,
        pendingAttachments,
        setPendingAttachments,
        handleSend,
        handleConfirmStageTransition,
        handleRetry,
        handleStop,
        handleFileChange,
        removeAttachment
    };
}
