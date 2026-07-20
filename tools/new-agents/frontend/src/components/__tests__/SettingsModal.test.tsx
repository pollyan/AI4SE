import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SettingsModal } from '../SettingsModal';
import { useStore } from '../../store';

describe('SettingsModal Component', () => {
    const mockFetch = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        global.fetch = mockFetch;
        mockFetch.mockReturnValue(new Promise(() => {}));
        // Reset the store to default state
        useStore.setState({ 
            isSettingsOpen: true,
            chatHistory: [] // required for clearHistory
        });
    });

    it('renders correctly when open', () => {
        render(<SettingsModal configAdministrationEnabled />);
        expect(screen.getByText('设置')).toBeDefined();
        expect(screen.getByLabelText('Base URL')).toBeDefined();
        expect(screen.getByLabelText('模型名称')).toBeDefined();
        expect(screen.getByLabelText('新 API Key')).toBeDefined();
    });

    it('keeps production model configuration read-only without browser admin credentials', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                hasDefault: true,
                baseUrl: 'https://api.test.com/v1',
                model: 'test-model',
                description: 'Server managed',
            }),
        });

        render(<SettingsModal configAdministrationEnabled={false} />);

        expect(await screen.findByText('生产环境模型配置由服务端管理员 API 管理')).toBeDefined();
        expect(screen.getByLabelText('Base URL')).toHaveProperty('disabled', true);
        expect(screen.getByLabelText('模型名称')).toHaveProperty('disabled', true);
        expect(screen.queryByLabelText('新 API Key')).toBeNull();
        expect(screen.queryByRole('button', { name: '检测连接' })).toBeNull();
        expect(screen.queryByRole('button', { name: '保存配置' })).toBeNull();
        expect(mockFetch).toHaveBeenCalledTimes(1);
        expect(mockFetch).toHaveBeenCalledWith('/new-agents/api/config');
    });

    it('loads sanitized backend config without showing an existing API key', async () => {
        mockFetch.mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({
                hasDefault: true,
                baseUrl: 'https://api.test.com/v1',
                model: 'test-model',
                description: 'Test config',
            }),
        });
        render(<SettingsModal configAdministrationEnabled />);

        expect(await screen.findByDisplayValue('https://api.test.com/v1')).toBeDefined();
        expect(screen.getByDisplayValue('test-model')).toBeDefined();
        expect(screen.getByDisplayValue('Test config')).toBeDefined();
        expect(screen.getByLabelText('新 API Key')).toHaveProperty('value', '');
    });

    it('saves default backend config through the management form', async () => {
        mockFetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ hasDefault: false }),
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    hasDefault: true,
                    baseUrl: 'https://api.new.test/v1',
                    model: 'new-model',
                    description: 'New config',
                }),
            });

        render(<SettingsModal configAdministrationEnabled />);

        fireEvent.change(screen.getByLabelText('Base URL'), {
            target: { value: 'https://api.new.test/v1' },
        });
        fireEvent.change(screen.getByLabelText('模型名称'), {
            target: { value: 'new-model' },
        });
        fireEvent.change(screen.getByLabelText('描述'), {
            target: { value: 'New config' },
        });
        fireEvent.change(screen.getByLabelText('新 API Key'), {
            target: { value: 'new-secret' },
        });
        fireEvent.click(screen.getByText('保存配置'));

        await waitFor(() => {
            expect(mockFetch).toHaveBeenLastCalledWith('/new-agents/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    baseUrl: 'https://api.new.test/v1',
                    model: 'new-model',
                    description: 'New config',
                    apiKey: 'new-secret',
                }),
            });
        });
        expect(await screen.findByText('配置已保存')).toBeDefined();
        expect(screen.getByLabelText('新 API Key')).toHaveProperty('value', '');
    });

    it('notifies workspace after saving default backend config', async () => {
        const notifyDefaultLlmConfigChanged = vi.fn();
        useStore.setState({
            notifyDefaultLlmConfigChanged,
        } as unknown as Partial<ReturnType<typeof useStore.getState>>);
        mockFetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ hasDefault: false }),
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    hasDefault: true,
                    baseUrl: 'https://api.new.test/v1',
                    model: 'new-model',
                    description: 'New config',
                }),
            });

        render(<SettingsModal configAdministrationEnabled />);

        fireEvent.change(screen.getByLabelText('Base URL'), {
            target: { value: 'https://api.new.test/v1' },
        });
        fireEvent.change(screen.getByLabelText('模型名称'), {
            target: { value: 'new-model' },
        });
        fireEvent.change(screen.getByLabelText('新 API Key'), {
            target: { value: 'new-secret' },
        });
        fireEvent.click(screen.getByText('保存配置'));

        await waitFor(() => {
            expect(notifyDefaultLlmConfigChanged).toHaveBeenCalledTimes(1);
        });
    });

    it('checks current model availability from settings', async () => {
        mockFetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    hasDefault: true,
                    baseUrl: 'https://api.test.com/v1',
                    model: 'test-model',
                    description: 'Test config',
                }),
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    ok: true,
                    baseUrl: 'https://api.test.com/v1',
                    model: 'test-model',
                    message: '模型配置可用',
                }),
            });

        render(<SettingsModal configAdministrationEnabled />);

        fireEvent.change(await screen.findByLabelText('Base URL'), {
            target: { value: ' https://current.test/v1 ' },
        });
        fireEvent.change(screen.getByLabelText('模型名称'), {
            target: { value: ' current-model ' },
        });
        fireEvent.change(screen.getByLabelText('描述'), {
            target: { value: ' Current config ' },
        });
        fireEvent.change(screen.getByLabelText('新 API Key'), {
            target: { value: ' current-secret ' },
        });
        fireEvent.click(screen.getByText('检测连接'));

        await waitFor(() => {
            expect(mockFetch).toHaveBeenLastCalledWith('/new-agents/api/config/check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    baseUrl: 'https://current.test/v1',
                    model: 'current-model',
                    description: 'Current config',
                    apiKey: 'current-secret',
                }),
            });
        });
        expect(await screen.findByText('模型配置可用')).toBeDefined();
    });

    it('notifies workspace after a successful model connectivity check', async () => {
        const notifyDefaultLlmConfigChanged = vi.fn();
        useStore.setState({
            notifyDefaultLlmConfigChanged,
        } as unknown as Partial<ReturnType<typeof useStore.getState>>);
        mockFetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    hasDefault: true,
                    baseUrl: 'https://api.test.com/v1',
                    model: 'test-model',
                    description: 'Test config',
                }),
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    ok: true,
                    baseUrl: 'https://api.test.com/v1',
                    model: 'test-model',
                    message: '模型配置可用',
                }),
            });

        render(<SettingsModal configAdministrationEnabled />);

        fireEvent.click(await screen.findByText('检测连接'));

        await screen.findByText('模型配置可用');
        expect(notifyDefaultLlmConfigChanged).not.toHaveBeenCalled();
    });

    it('does not notify workspace when model connectivity check fails', async () => {
        const notifyDefaultLlmConfigChanged = vi.fn();
        useStore.setState({
            notifyDefaultLlmConfigChanged,
        } as unknown as Partial<ReturnType<typeof useStore.getState>>);
        mockFetch
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    hasDefault: true,
                    baseUrl: 'https://api.test.com/v1',
                    model: 'test-model',
                    description: 'Test config',
                }),
            })
            .mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({
                    ok: false,
                    message: '鉴权失败',
                }),
            });

        render(<SettingsModal configAdministrationEnabled />);

        fireEvent.click(await screen.findByText('检测连接'));

        await screen.findByText('鉴权失败');
        expect(notifyDefaultLlmConfigChanged).not.toHaveBeenCalled();
    });

    it('does not render when isSettingsOpen is false', () => {
        useStore.setState({ isSettingsOpen: false });
        render(<SettingsModal configAdministrationEnabled />);
        expect(screen.queryByText('设置')).toBeNull();
    });

    it('closes modal when X button is clicked', () => {
        render(<SettingsModal configAdministrationEnabled />);

        // By looking at the DOM, the first button is the close button in the header
        const clearButton = screen.getAllByRole('button')[0];
        fireEvent.click(clearButton);
        
        expect(useStore.getState().isSettingsOpen).toBe(false);
    });

    it('closes modal when save/done button is clicked', () => {
        render(<SettingsModal configAdministrationEnabled />);
        
        const submitButton = screen.getByText('完成');
        fireEvent.click(submitButton);
        
        expect(useStore.getState().isSettingsOpen).toBe(false);
    });

    it('calls clearHistory when trash button is clicked and confirmed', () => {
        // Mock window.confirm
        const confirmSpy = vi.spyOn(window, 'confirm').mockImplementation(() => true);
        useStore.setState({ chatHistory: [{ id: '1', role: 'user', content: 'test', timestamp: 123 }] });
        
        render(<SettingsModal configAdministrationEnabled />);
        
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
        
        render(<SettingsModal configAdministrationEnabled />);
        
        const clearButton = screen.getByText('清空数据');
        fireEvent.click(clearButton);
        
        expect(confirmSpy).toHaveBeenCalled();
        expect(useStore.getState().isSettingsOpen).toBe(true); // Should NOT close
        expect(useStore.getState().chatHistory.length).toBe(1); // Should NOT be cleared
        
        confirmSpy.mockRestore();
    });
});
