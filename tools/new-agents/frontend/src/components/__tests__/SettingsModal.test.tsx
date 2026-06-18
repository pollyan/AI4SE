import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SettingsModal } from '../SettingsModal';
import { useStore } from '../../store';

describe('SettingsModal Component', () => {
    beforeEach(() => {
        // Reset the store to default state
        useStore.setState({ 
            isSettingsOpen: true,
            chatHistory: [] // required for clearHistory
        });
    });

    it('renders correctly when open', () => {
        render(<SettingsModal />);
        expect(screen.getByText('设置')).toBeDefined();
        expect(screen.getByText('LLM 由后端系统配置统一管理')).toBeDefined();
        expect(screen.queryByText('API Key')).toBeNull();
        expect(screen.queryByText('Base URL')).toBeNull();
        expect(screen.queryByText('模型名称')).toBeNull();
    });

    it('does not render when isSettingsOpen is false', () => {
        useStore.setState({ isSettingsOpen: false });
        render(<SettingsModal />);
        expect(screen.queryByText('设置')).toBeNull();
    });

    it('closes modal when X button is clicked', () => {
        render(<SettingsModal />);

        // By looking at the DOM, the first button is the close button in the header
        const clearButton = screen.getAllByRole('button')[0];
        fireEvent.click(clearButton);
        
        expect(useStore.getState().isSettingsOpen).toBe(false);
    });

    it('closes modal when save/done button is clicked', () => {
        render(<SettingsModal />);
        
        const submitButton = screen.getByText('完成');
        fireEvent.click(submitButton);
        
        expect(useStore.getState().isSettingsOpen).toBe(false);
    });

    it('calls clearHistory when trash button is clicked and confirmed', () => {
        // Mock window.confirm
        const confirmSpy = vi.spyOn(window, 'confirm').mockImplementation(() => true);
        useStore.setState({ chatHistory: [{ id: '1', role: 'user', content: 'test', timestamp: 123 }] });
        
        render(<SettingsModal />);
        
        const clearButton = screen.getByText('清空数据');
        fireEvent.click(clearButton);
        
        expect(confirmSpy).toHaveBeenCalled();
        expect(useStore.getState().isSettingsOpen).toBe(false); // Should close after clear
        expect(useStore.getState().chatHistory.length).toBe(0); // Should be cleared
        
        confirmSpy.mockRestore();
    });

    it('does not call clearHistory when trash button is clicked and not confirmed', () => {
        // Mock window.confirm
        const confirmSpy = vi.spyOn(window, 'confirm').mockImplementation(() => false);
        useStore.setState({ chatHistory: [{ id: '1', role: 'user', content: 'test', timestamp: 123 }] });
        
        render(<SettingsModal />);
        
        const clearButton = screen.getByText('清空数据');
        fireEvent.click(clearButton);
        
        expect(confirmSpy).toHaveBeenCalled();
        expect(useStore.getState().isSettingsOpen).toBe(true); // Should NOT close
        expect(useStore.getState().chatHistory.length).toBe(1); // Should NOT be cleared
        
        confirmSpy.mockRestore();
    });
});
