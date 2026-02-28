import { useState, useRef, useCallback } from 'react';
import { useStore, Attachment, WORKFLOWS } from '../store';
import { generateResponseStream } from '../llm';

export function useChatService() {
    const [input, setInput] = useState('');
    const [pendingAttachments, setPendingAttachments] = useState<Attachment[]>([]);
    const abortControllerRef = useRef<AbortController | null>(null);

    const { chatHistory, addMessage, updateLastMessage, removeLastMessage, isGenerating, setIsGenerating } = useStore();

    const handleStop = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
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
                        mimeType: file.type || 'text/plain'
                    }
                ]);
            };
            reader.readAsDataURL(file);
        });
    }, []);

    const removeAttachment = useCallback((index: number) => {
        setPendingAttachments(prev => prev.filter((_, i) => i !== index));
    }, []);

    const handleSend = useCallback(async () => {
        if ((!input.trim() && pendingAttachments.length === 0) || isGenerating) return;

        const userMsg = input.trim();
        const currentAttachments = [...pendingAttachments];

        setInput('');
        setPendingAttachments([]);

        addMessage({
            id: Date.now().toString(),
            role: 'user',
            content: userMsg,
            timestamp: Date.now(),
            attachments: currentAttachments.length > 0 ? currentAttachments : undefined,
        });

        setIsGenerating(true);

        const initialArtifact = useStore.getState().artifactContent;
        const initialStage = useStore.getState().stageIndex;

        abortControllerRef.current = new AbortController();
        let isFirstChunk = true;

        try {
            const stream = generateResponseStream(userMsg, currentAttachments, abortControllerRef.current.signal);

            let hasTransitioned = false;

            for await (const { chatResponse, newArtifact, action, hasArtifactUpdate } of stream) {
                if (isFirstChunk) {
                    addMessage({
                        id: (Date.now() + 1).toString(),
                        role: 'assistant',
                        content: chatResponse,
                        timestamp: Date.now(),
                    });
                    isFirstChunk = false;
                } else {
                    updateLastMessage(chatResponse);
                }

                if (action === 'NEXT_STAGE' && !hasTransitioned) {
                    const state = useStore.getState();
                    const wf = WORKFLOWS[state.workflow];
                    if (state.stageIndex < wf.stages.length - 1) {
                        state.transitionToNextStage(initialStage, initialArtifact);
                        hasTransitioned = true;
                    }
                }

                if (hasArtifactUpdate) {
                    useStore.getState().setArtifactContent(newArtifact);
                }
            }
        } catch (error: any) {
            const history = useStore.getState().chatHistory;
            const lastMsgRole = history.length > 0 ? history[history.length - 1].role : null;
            const isMidstream = lastMsgRole === 'assistant' && !isFirstChunk;

            if (error.message === 'Aborted by user') {
                if (isMidstream) {
                    updateLastMessage((history[history.length - 1]?.content || '') + '\n\n*(已停止生成)*');
                }
            } else {
                let errorContent = `**Error:** ${error.message || 'Something went wrong.'}`;

                // Add friendly explanation for 429 Quota Exceeded errors
                if (error.message && (error.message.includes('429') || error.message.toLowerCase().includes('quota'))) {
                    errorContent = `⚠️ **免费额度已用尽**\n\n抱歉，系统内置的公共大模型 API 免费调用额度（Google Gemini Free Tier）已经耗尽。\n\n**解决方案：**\n您可以点击左侧菜单栏底部的 **"设置" (Settings)** 按钮，配置您专属的 API Key（支持 OpenAI、DeepSeek 或 Gemini 等兼容格式）。\n\n*🛡️ **安全提示**：系统绝对不会上传或存储您的 API Key。您的 Key 仅安全地保存在您当前浏览器的本地缓存 (Local Storage) 中供发起请求使用，请放心配置。*\n\n---\n*原始错误附录：*\n\`\`\`text\n${error.message}\n\`\`\``;
                }

                if (isMidstream) {
                    updateLastMessage((history[history.length - 1]?.content || '') + '\n\n' + errorContent);
                } else {
                    addMessage({
                        id: (Date.now() + 1).toString(),
                        role: 'assistant',
                        content: errorContent,
                        timestamp: Date.now(),
                    });
                }
            }
        } finally {
            abortControllerRef.current = null;
            setIsGenerating(false);
            const finalArtifact = useStore.getState().artifactContent;
            if (finalArtifact && finalArtifact !== '# 欢迎使用 Lisa 测试专家\n\n请在左侧输入您的需求，我将为您生成测试文档。') {
                const history = useStore.getState().artifactHistory;
                if (history.length === 0 || history[history.length - 1].content !== finalArtifact) {
                    useStore.getState().addArtifactVersion({
                        id: Date.now().toString(),
                        timestamp: Date.now(),
                        content: finalArtifact
                    });
                }
            }
        }
    }, [input, pendingAttachments, isGenerating, addMessage, updateLastMessage, setIsGenerating]);

    const handleRetry = useCallback(() => {
        if (isGenerating || chatHistory.length === 0) return;

        const history = useStore.getState().chatHistory;
        let lastUserMsgIndex = -1;
        for (let i = history.length - 1; i >= 0; i--) {
            if (history[i].role === 'user') {
                lastUserMsgIndex = i;
                break;
            }
        }

        if (lastUserMsgIndex === -1) return;

        const lastUserMsg = history[lastUserMsgIndex];

        // Remove all messages after the last user message
        const msgsToRemove = history.length - 1 - lastUserMsgIndex;
        for (let i = 0; i < msgsToRemove; i++) {
            useStore.getState().removeLastMessage();
        }

        // Remove the user message itself so we can re-send it
        useStore.getState().removeLastMessage();

        // Set input and attachments so they can be sent again
        setInput(lastUserMsg.content);
        setPendingAttachments(lastUserMsg.attachments || []);

    }, [isGenerating, chatHistory]);

    return {
        input,
        setInput,
        pendingAttachments,
        setPendingAttachments,
        handleSend,
        handleRetry,
        handleStop,
        handleFileChange,
        removeAttachment
    };
}
