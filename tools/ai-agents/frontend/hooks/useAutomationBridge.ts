import { useEffect } from 'react';

interface AutomationAPI {
    setText: (text: string) => void;
    send: () => void;
    getText: () => string;
}

interface UseAutomationBridgeOptions {
    enabled?: boolean;
    api: AutomationAPI;
}

export function useAutomationBridge({ enabled = true, api }: UseAutomationBridgeOptions) {
    useEffect(() => {
        if (!enabled) return;

        window.assistantComposer = api;

        return () => {
            delete window.assistantComposer;
        };
    }, [enabled, api]); // api dependency should be stable
}
