import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
// @ts-expect-error - Component not created yet
import { RuntimeErrorDisplay } from '../components/chat/RuntimeErrorDisplay';
import * as AssistantUI from '@assistant-ui/react';

// Mock assistant-ui
vi.mock('@assistant-ui/react', () => ({
    useAssistantRuntime: vi.fn()
}));

describe('RuntimeErrorDisplay', () => {
    it('returns null when no error', () => {
        vi.mocked(AssistantUI.useAssistantRuntime).mockReturnValue({
            thread: { error: null }
        } as any);

        const { container } = render(<RuntimeErrorDisplay />);
        expect(container.firstChild).toBeNull();
    });

    it('displays error message', () => {
        vi.mocked(AssistantUI.useAssistantRuntime).mockReturnValue({
            thread: { error: new Error('Test Error') }
        } as any);

        render(<RuntimeErrorDisplay />);
        expect(screen.getByText('出错了: Test Error')).toBeInTheDocument();
    });

    it('calls reload on retry button click', () => {
        const reloadMock = vi.fn();
        vi.mocked(AssistantUI.useAssistantRuntime).mockReturnValue({
            thread: { 
                error: new Error('Test Error'),
                reload: reloadMock
            }
        } as any);

        render(<RuntimeErrorDisplay />);
        fireEvent.click(screen.getByText('重试'));
        expect(reloadMock).toHaveBeenCalled();
    });
});
