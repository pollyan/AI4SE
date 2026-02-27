import { renderHook } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
// @ts-expect-error - Hook not created yet
import { useAutomationBridge } from '../hooks/useAutomationBridge';

describe('useAutomationBridge', () => {
    it('exposes api on window.assistantComposer', () => {
        const api = { setText: vi.fn(), send: vi.fn(), getText: vi.fn() };
        renderHook(() => useAutomationBridge({ api }));
        
        expect(window.assistantComposer).toBeDefined();
        expect(window.assistantComposer?.setText).toBe(api.setText);
    });

    it('cleans up on unmount', () => {
        const api = { setText: vi.fn(), send: vi.fn(), getText: vi.fn() };
        const { unmount } = renderHook(() => useAutomationBridge({ api }));
        
        unmount();
        expect(window.assistantComposer).toBeUndefined();
    });
});
