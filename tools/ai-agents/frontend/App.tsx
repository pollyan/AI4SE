import React, { useState, useRef, useCallback } from 'react';
import Layout from './components/Layout';
import AssistantPanel from './components/AssistantPanel';
import AnalysisResultPanel from './components/AnalysisResultPanel';
import { ASSISTANTS } from './constants';
import { AssistantId, ChatMessage } from './types';
import { createSession, sendMessageStream } from './services/backendService';

const App: React.FC = () => {
  const [selectedAssistantId, setSelectedAssistantId] = useState<AssistantId | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [analysisResult, setAnalysisResult] = useState<string>('');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  // Store the backend session ID instead of a ChatSession object
  const sessionIdRef = useRef<string | null>(null);

  const handleSelectAssistant = async (id: AssistantId) => {
    // If clicking the same assistant, do nothing
    // If id is empty (back button), clear selection
    if (!id) {
      setSelectedAssistantId(null);
      sessionIdRef.current = null;
      return;
    }

    if (id === selectedAssistantId) return;

    const assistant = ASSISTANTS.find(a => a.id === id);
    if (!assistant) return;

    setSelectedAssistantId(id);
    setAnalysisResult('');

    // Show thinking indicator while waiting for AI welcome message
    const welcomeMsgTimestamp = Date.now();
    setMessages([{
      role: 'model',
      text: '',
      timestamp: welcomeMsgTimestamp,
      isThinking: true
    }]);
    setIsProcessing(true);

    // Create a new session with the backend
    try {
      const session = await createSession('AI4SE Project', id);
      sessionIdRef.current = session.sessionId;

      // Send hidden welcome request to get AI-generated welcome message
      await sendMessageStream(
        session.sessionId,
        '请显示欢迎语',  // Hidden command, not shown to user
        (fullText) => {
          // Update the welcome message with AI response
          setMessages([{
            role: 'model',
            text: fullText,
            timestamp: welcomeMsgTimestamp,
            isThinking: false
          }]);
        }
      );
    } catch (error) {
      console.error('Failed to create session or get welcome:', error);
      setMessages([{
        role: 'model',
        text: '抱歉，无法连接到后端服务。请确保服务已启动。',
        timestamp: welcomeMsgTimestamp,
        isThinking: false
      }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSubmit = useCallback(async (inputText: string) => {
    if (!sessionIdRef.current) {
      console.error('No session ID available');
      return;
    }

    // Add user message
    const userMsg: ChatMessage = { role: 'user', text: inputText, timestamp: Date.now() };
    setMessages(prev => [...prev, userMsg]);

    setIsProcessing(true);

    // Add placeholder for bot message
    const botMsgTimestamp = Date.now();
    setMessages(prev => [...prev, { role: 'model', text: '', timestamp: botMsgTimestamp, isThinking: true }]);

    try {
      await sendMessageStream(
        sessionIdRef.current,
        inputText,
        (fullText) => {
          // Parsing logic for Artifacts
          // Format: :::artifact \n content \n :::
          // We want to extract content for the right panel, and remove the whole block from the left panel

          const artifactRegex = /:::artifact\s*([\s\S]*?)(\s*:::|$)/;
          const match = fullText.match(artifactRegex);

          let displayMessage = fullText;

          if (match) {
            const artifactContent = match[1];
            setAnalysisResult(artifactContent);

            // Remove the artifact block from the chat display
            displayMessage = fullText.replace(artifactRegex, '\n*(已更新右侧分析成果)*\n');
          }

          setMessages(prev => {
            const newMessages = [...prev];
            const lastMsg = newMessages[newMessages.length - 1];
            if (lastMsg.role === 'model' && lastMsg.timestamp === botMsgTimestamp) {
              lastMsg.text = displayMessage;
              lastMsg.isThinking = false;
            }
            return newMessages;
          });
        }
      );
    } catch (error) {
      console.error('Message send failed:', error);
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMsg = newMessages[newMessages.length - 1];
        if (lastMsg.role === 'model' && lastMsg.timestamp === botMsgTimestamp) {
          lastMsg.text = "抱歉，由于网络或服务原因，我无法完成回复。请稍后再试。";
          lastMsg.isThinking = false;
        }
        return newMessages;
      });
    } finally {
      setIsProcessing(false);
    }
  }, []);

  return (
    <Layout>
      <h1 className="text-3xl font-light text-gray-800 dark:text-gray-100 mb-8 border-l-4 border-primary pl-4 hidden md:block">
        智能助手
      </h1>

      <div className="flex flex-col lg:flex-row gap-6 h-[calc(100vh-140px)] md:h-[calc(100vh-220px)] min-h-[600px]">
        <AssistantPanel
          assistants={ASSISTANTS}
          selectedAssistantId={selectedAssistantId}
          onSelectAssistant={handleSelectAssistant}
          messages={messages}
          onSubmit={handleSubmit}
          isProcessing={isProcessing}
        />

        <AnalysisResultPanel
          result={analysisResult}
          isProcessing={isProcessing}
          hasStarted={!!analysisResult}
        />
      </div>
    </Layout>
  );
};

export default App;