import React, { useState } from 'react';

export function DebugChat() {
    const [input, setInput] = useState('');
    const [logs, setLogs] = useState<string[]>([]);
    const [messages, setMessages] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    const log = (msg: string) => setLogs(prev => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMsg = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);
        log(`Starting request with message: ${input}`);

        try {
            log('Creating session...');
            const sessionRes = await fetch('/ai-agents/api/requirements/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_name: 'Debug Project', assistant_type: 'alex' })
            });
            const sessionData = await sessionRes.json();
            
            if (!sessionRes.ok) {
                throw new Error(`Session creation failed: ${JSON.stringify(sessionData)}`);
            }
            
            const sid = sessionData.data.id;
            log(`Session created: ${sid}`);

            log('Sending message...');
            const res = await fetch(`/ai-agents/api/requirements/sessions/${sid}/messages/v2/stream`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json' 
                },
                body: JSON.stringify({
                    messages: [userMsg] // Vercel AI SDK format
                })
            });

            log(`Response status: ${res.status}`);
            const headers: Record<string, string> = {};
            res.headers.forEach((v, k) => headers[k] = v);
            log(`Response headers: ${JSON.stringify(headers)}`);

            if (!res.body) throw new Error("No response body");

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            
            let aiContent = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                log(`Received chunk: ${JSON.stringify(chunk)}`);
                
                // Naive Data Stream Protocol Parser
                // WARNING: This doesn't handle chunks split across lines perfectly, but good enough for debug
                const lines = chunk.split('\n');
                for (const line of lines) {
                    if (line.startsWith('0:')) {
                        try {
                            const jsonStr = line.substring(2);
                            // It should be a JSON string, so JSON.parse returns the string content
                            const text = JSON.parse(jsonStr);
                            aiContent += text;
                        } catch (e) {
                            log(`Parse error for line: ${line} - ${e}`);
                        }
                    }
                }
                
                // Update UI with partial content
                setMessages(prev => {
                    const newMsgs = [...prev];
                    const last = newMsgs[newMsgs.length - 1];
                    if (last && last.role === 'assistant') {
                        last.content = aiContent;
                        return [...newMsgs.slice(0, -1), { ...last }];
                    } else {
                        return [...newMsgs, { role: 'assistant', content: aiContent }];
                    }
                });
            }
            log('Stream finished');

        } catch (e) {
            log(`Error: ${e}`);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex h-screen p-4 gap-4 bg-white text-black">
            <div className="flex-1 flex flex-col border rounded p-4">
                <h2 className="font-bold mb-4">Chat Preview</h2>
                <div className="flex-1 overflow-y-auto space-y-4 mb-4 border p-2 bg-gray-50">
                    {messages.map((m, i) => (
                        <div key={i} className={`p-2 rounded ${m.role === 'user' ? 'bg-blue-100 ml-auto max-w-[80%]' : 'bg-white border mr-auto max-w-[80%]'}`}>
                            <strong className="block text-xs text-gray-500 mb-1">{m.role}</strong>
                            <pre className="whitespace-pre-wrap font-sans text-sm">{m.content}</pre>
                        </div>
                    ))}
                </div>
                <form onSubmit={handleSubmit} className="flex gap-2">
                    <input 
                        className="flex-1 border p-2 rounded" 
                        value={input} 
                        onChange={e => setInput(e.target.value)}
                        disabled={isLoading}
                        placeholder="Type a message..."
                    />
                    <button type="submit" className="bg-blue-500 text-white px-4 py-2 rounded disabled:opacity-50" disabled={isLoading}>
                        Send
                    </button>
                </form>
            </div>
            <div className="flex-1 border rounded p-4 bg-gray-900 text-green-400 font-mono text-xs overflow-y-auto">
                <h2 className="font-bold text-white mb-2 sticky top-0 bg-gray-900 pb-2 border-b border-gray-700">Raw Stream Logs</h2>
                {logs.map((l, i) => <div key={i} className="mb-1 border-b border-gray-800 pb-1">{l}</div>)}
            </div>
        </div>
    );
}
