import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SettingsModal } from '../SettingsModal';
import { useStore } from '../../store';

describe('SettingsModal Component', () => {
    beforeEach(() => {
        // Reset the store to default state
        useStore.setState({ 
            isSettingsOpen: true,
            apiKey: '',
            model: 'gemini-3-flash-preview',
            baseUrl: '',
            isUserConfigured: false,
            chatHistory: [] // required for clearHistory
        });
    });

    it('renders correctly when open', () => {
        render(<SettingsModal />);
        expect(screen.getByText('设置')).toBeDefined();
        expect(screen.getByText('API Key')).toBeDefined();
        expect(screen.getByText('Base URL')).toBeDefined();
        expect(screen.getByText('模型名称')).toBeDefined();
    });

    it('does not render when isSettingsOpen is false', () => {
        useStore.setState({ isSettingsOpen: false });
        render(<SettingsModal />);
        expect(screen.queryByText('设置')).toBeNull();
    });

    it('updates API key when input changes', () => {
        render(<SettingsModal />);
        
        const apiKeyInput = screen.getByPlaceholderText('不填则使用系统默认内置 API Key') as HTMLInputElement;
        fireEvent.change(apiKeyInput, { target: { value: 'new-api-key' } });
        
        expect(useStore.getState().apiKey).toBe('new-api-key');
    });

    it('updates Base URL when input changes', () => {
        render(<SettingsModal />);
        
        const baseUrlInput = screen.getByPlaceholderText('例如: https://api.deepseek.com/v1') as HTMLInputElement;
        fireEvent.change(baseUrlInput, { target: { value: 'https://new-base.url/v1' } });
        
        expect(useStore.getState().baseUrl).toBe('https://new-base.url/v1');
    });

    it('updates Model Name when input changes', () => {
        render(<SettingsModal />);
        
        const modelInput = screen.getByPlaceholderText('例如: gemini-3-flash-preview, deepseek-chat, gpt-4o') as HTMLInputElement;
        fireEvent.change(modelInput, { target: { value: 'new-model' } });
        
        expect(useStore.getState().model).toBe('new-model');
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
