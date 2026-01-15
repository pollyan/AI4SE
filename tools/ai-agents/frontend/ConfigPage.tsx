import React, { useState, useEffect } from 'react';
import CompactLayout from './components/CompactLayout';
import {
    listConfigs,
    getConfigStats,
    createConfig,
    updateConfig,
    deleteConfig,
    setDefaultConfig,
    testConfig,
    testNewConfig,
    type AIConfig,
    type ConfigStats
} from './services/configService';
import { Plus, Settings, Shield, Server, CheckCircle2, Edit2, Trash2, Gauge, Zap } from 'lucide-react';

const ConfigPage: React.FC = () => {
    // Form state
    const [formData, setFormData] = useState({
        config_name: '',
        api_key: '',
        base_url: '',
        model_name: '',
    });
    const [editingId, setEditingId] = useState<number | null>(null);

    // Data state
    const [configs, setConfigs] = useState<AIConfig[]>([]);
    const [stats, setStats] = useState<ConfigStats>({ total_configs: 0, selected_configs: 0, current_config_name: '无' });
    const [testStatuses, setTestStatuses] = useState<Record<number, 'unknown' | 'pending' | 'success' | 'error'>>({});

    // UI state
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [showForm, setShowForm] = useState(false);
    const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

    // Load data on mount
    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            const [configsData, statsData] = await Promise.all([listConfigs(), getConfigStats()]);
            setConfigs(configsData);
            setStats(statsData);
        } catch (error) {
            showMessage('加载配置失败: ' + (error as Error).message, 'error');
        } finally {
            setLoading(false);
        }
    };

    const showMessage = (text: string, type: 'success' | 'error' | 'info') => {
        setMessage({ text, type });
        setTimeout(() => setMessage(null), 5000);
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const clearForm = () => {
        setFormData({ config_name: '', api_key: '', base_url: '', model_name: '' });
        setEditingId(null);
        setShowForm(false);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            setSaving(true);
            if (editingId) {
                // Update existing config
                const updateData: { config_name?: string; api_key?: string; base_url?: string; model_name?: string } = {
                    config_name: formData.config_name,
                    base_url: formData.base_url,
                    model_name: formData.model_name,
                };
                // Only include api_key if it was provided (not empty)
                if (formData.api_key.trim()) {
                    updateData.api_key = formData.api_key;
                }
                await updateConfig(editingId, updateData);
                showMessage('配置更新成功', 'success');
            } else {
                // Create new config
                await createConfig(formData);
                showMessage('配置创建成功', 'success');
            }
            clearForm();
            await loadData(); // Refresh data
        } catch (error) {
            showMessage('保存失败: ' + (error as Error).message, 'error');
        } finally {
            setSaving(false);
        }
    };

    const handleEdit = (config: AIConfig) => {
        setFormData({
            config_name: config.config_name,
            api_key: '', // Don't pre-fill API key for security
            base_url: config.base_url,
            model_name: config.model_name,
        });
        setEditingId(config.id);
        setShowForm(true);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const handleDelete = async (id: number) => {
        if (!confirm('确定要删除此配置吗？此操作不可恢复。')) return;
        try {
            await deleteConfig(id);
            showMessage('配置已删除', 'success');
            await loadData(); // Refresh data
        } catch (error) {
            showMessage('删除失败: ' + (error as Error).message, 'error');
        }
    };

    const handleSetDefault = async (id: number) => {
        try {
            await setDefaultConfig(id);
            showMessage('已设为默认配置', 'success');
            await loadData(); // Refresh data
        } catch (error) {
            showMessage('设置默认失败: ' + (error as Error).message, 'error');
        }
    };

    const handleTest = async (id: number) => {
        setTestStatuses(prev => ({ ...prev, [id]: 'pending' }));
        try {
            const result = await testConfig(id);
            if (result.test_success) {
                setTestStatuses(prev => ({ ...prev, [id]: 'success' }));
                showMessage(`连接测试成功！响应时间: ${result.duration_ms}ms`, 'success');
            } else {
                setTestStatuses(prev => ({ ...prev, [id]: 'error' }));
                showMessage(`连接测试失败: ${result.message}`, 'error');
            }
        } catch (error) {
            setTestStatuses(prev => ({ ...prev, [id]: 'error' }));
            showMessage('测试失败: ' + (error as Error).message, 'error');
        }
    };

    const handleTestNew = async () => {
        if (!formData.api_key || !formData.base_url || !formData.model_name) {
            showMessage('请先填写 API Key、Base URL 和 Model Name', 'error');
            return;
        }
        showMessage('正在测试连接...', 'info');
        try {
            const result = await testNewConfig({
                api_key: formData.api_key,
                base_url: formData.base_url,
                model_name: formData.model_name,
            });
            if (result.test_success) {
                showMessage(`✅ 连接测试成功！响应时间: ${result.duration_ms}ms`, 'success');
            } else {
                showMessage(`❌ 连接测试失败: ${result.message}`, 'error');
            }
        } catch (error) {
            showMessage('测试失败: ' + (error as Error).message, 'error');
        }
    };

    const getHostname = (url: string) => {
        try {
            return new URL(url).hostname;
        } catch {
            return url;
        }
    };

    return (
        <CompactLayout>
            <div className="h-full bg-slate-50 dark:bg-slate-900 overflow-y-auto">
                <div className="max-w-5xl mx-auto px-4 py-8 lg:py-12">

                    <div className="flex items-center justify-between mb-8">
                        <div>
                            <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">AI 配置管理</h1>
                            <p className="text-slate-500 dark:text-slate-400">管理你的 AI 助手模型连接、API 密钥和环境参数</p>
                        </div>
                        <button
                            onClick={() => { clearForm(); setShowForm(!showForm); }}
                            className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-medium shadow-lg shadow-blue-200/50 dark:shadow-none transition-all flex items-center gap-2"
                        >
                            <Plus size={18} />
                            新建配置
                        </button>
                    </div>

                    {/* Stats Card */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
                        <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl border border-slate-100 dark:border-slate-700/50 shadow-sm flex items-center gap-4">
                            <div className="p-3 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-xl">
                                <Server size={24} />
                            </div>
                            <div>
                                <div className="text-sm text-slate-500 dark:text-slate-400">当前活跃模型</div>
                                <div className="text-lg font-bold text-slate-900 dark:text-white truncate max-w-[150px]" title={stats.current_config_name}>{stats.current_config_name}</div>
                            </div>
                        </div>
                        <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl border border-slate-100 dark:border-slate-700/50 shadow-sm flex items-center gap-4">
                            <div className="p-3 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-xl">
                                <Gauge size={24} />
                            </div>
                            <div>
                                <div className="text-sm text-slate-500 dark:text-slate-400">已保存配置</div>
                                <div className="text-lg font-bold text-slate-900 dark:text-white">{stats.total_configs} 个环境</div>
                            </div>
                        </div>
                        <div className="bg-white dark:bg-slate-800 p-5 rounded-2xl border border-slate-100 dark:border-slate-700/50 shadow-sm flex items-center gap-4">
                            <div className="p-3 bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded-xl">
                                <CheckCircle2 size={24} />
                            </div>
                            <div>
                                <div className="text-sm text-slate-500 dark:text-slate-400">系统状态</div>
                                <div className="text-lg font-bold text-green-600 dark:text-green-400">运行正常</div>
                            </div>
                        </div>
                    </div>

                    {/* Form Section */}
                    <div className={`overflow-hidden transition-all duration-300 ease-in-out ${showForm ? 'max-h-[800px] opacity-100 mb-8' : 'max-h-0 opacity-0'}`}>
                        <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 md:p-8 shadow-lg border border-slate-200 dark:border-slate-700">
                            <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-6 flex items-center gap-2">
                                <Settings className="text-slate-400" size={20} />
                                {editingId ? '编辑配置' : '新建 AI 配置'}
                            </h2>

                            <form onSubmit={handleSubmit}>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                                    <div>
                                        <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">配置名称</label>
                                        <input
                                            type="text"
                                            name="config_name"
                                            value={formData.config_name}
                                            onChange={handleInputChange}
                                            placeholder="如：Production GPT-4"
                                            className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all dark:text-white"
                                            required
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">模型名称 (Model ID)</label>
                                        <input
                                            type="text"
                                            name="model_name"
                                            value={formData.model_name}
                                            onChange={handleInputChange}
                                            placeholder="如: gpt-4o, qwen-vl-max"
                                            className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all dark:text-white"
                                            required
                                        />
                                    </div>
                                </div>

                                <div className="mb-6">
                                    <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">API 基础 URL (Base URL)</label>
                                    <div className="relative">
                                        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                                            <Server size={16} />
                                        </div>
                                        <input
                                            type="url"
                                            name="base_url"
                                            value={formData.base_url}
                                            onChange={handleInputChange}
                                            placeholder="https://api.openai.com/v1"
                                            className="w-full pl-11 pr-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all dark:text-white font-mono"
                                            required
                                        />
                                    </div>
                                </div>

                                <div className="mb-8">
                                    <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
                                        API 密钥 (Key)
                                        {editingId && <span className="text-slate-400 font-normal ml-2">留空则保持原密钥不变</span>}
                                    </label>
                                    <div className="relative">
                                        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
                                            <Shield size={16} />
                                        </div>
                                        <input
                                            type="password"
                                            name="api_key"
                                            value={formData.api_key}
                                            onChange={handleInputChange}
                                            placeholder="sk-..."
                                            className="w-full pl-11 pr-4 py-3 bg-slate-50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all dark:text-white font-mono"
                                            required={!editingId}
                                        />
                                    </div>
                                </div>

                                <div className="flex justify-end gap-3 pt-6 border-t border-slate-100 dark:border-slate-700">
                                    <button
                                        type="button"
                                        onClick={() => setShowForm(false)}
                                        className="px-6 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors text-sm font-medium"
                                    >
                                        取消
                                    </button>
                                    <button
                                        type="button"
                                        onClick={handleTestNew}
                                        className="px-6 py-2.5 rounded-xl bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-colors text-sm font-medium"
                                    >
                                        测试连接
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={saving}
                                        className="px-6 py-2.5 rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors text-sm font-medium shadow-lg shadow-slate-200/50 dark:shadow-none disabled:opacity-50"
                                    >
                                        {saving ? '保存中...' : (editingId ? '更新配置' : '保存配置')}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>

                    {/* Config List */}
                    <div className="space-y-4">
                        {loading ? (
                            <div className="text-center py-20 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700">
                                <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
                                <p className="text-slate-500">加载配置中...</p>
                            </div>
                        ) : configs.length === 0 ? (
                            <div className="text-center py-24 bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700">
                                <div className="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
                                    <Server size={32} className="text-slate-400" />
                                </div>
                                <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">暂无配置</h3>
                                <p className="text-slate-500 mb-6">您还没有添加任何 AI 模型配置。</p>
                                <button onClick={() => setShowForm(true)} className="text-blue-600 font-medium hover:underline">立即创建</button>
                            </div>
                        ) : (
                            configs.map(config => (
                                <div
                                    key={config.id}
                                    className={`group relative bg-white dark:bg-slate-800 p-6 rounded-2xl border transition-all duration-200 hover:shadow-lg ${config.is_default
                                        ? 'border-blue-200 dark:border-blue-900 ring-1 ring-blue-100 dark:ring-blue-900/50'
                                        : 'border-slate-100 dark:border-slate-700/50 hover:border-slate-200 dark:hover:border-slate-600'
                                        }`}
                                >
                                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-3 mb-2">
                                                <h3 className="text-lg font-bold text-slate-900 dark:text-white">{config.config_name}</h3>
                                                {config.is_default && (
                                                    <span className="px-2.5 py-0.5 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 text-xs font-semibold rounded-full flex items-center gap-1">
                                                        <CheckCircle2 size={12} />
                                                        默认
                                                    </span>
                                                )}
                                            </div>

                                            <div className="flex flex-wrap items-center gap-4 text-sm text-slate-500 dark:text-slate-400 mb-3">
                                                <div className="flex items-center gap-1.5 bg-slate-50 dark:bg-slate-900/50 px-2.5 py-1 rounded-md border border-slate-100 dark:border-slate-700">
                                                    <Zap size={14} className="text-amber-500" />
                                                    <span className="font-mono text-slate-700 dark:text-slate-300">{config.model_name}</span>
                                                </div>
                                                <div className="flex items-center gap-1.5">
                                                    <Server size={14} />
                                                    <span className="truncate max-w-[200px]">{getHostname(config.base_url)}</span>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2">
                                                <div className={`flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-md ${testStatuses[config.id] === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400' :
                                                    testStatuses[config.id] === 'error' ? 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                                                        testStatuses[config.id] === 'pending' ? 'bg-yellow-50 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                                            'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                                                    }`}>
                                                    <div className={`w-1.5 h-1.5 rounded-full ${testStatuses[config.id] === 'success' ? 'bg-green-500' :
                                                        testStatuses[config.id] === 'error' ? 'bg-red-500' :
                                                            testStatuses[config.id] === 'pending' ? 'bg-yellow-500 animate-pulse' :
                                                                'bg-slate-400'
                                                        }`}></div>
                                                    {
                                                        testStatuses[config.id] === 'success' ? '连接正常' :
                                                            testStatuses[config.id] === 'error' ? '连接断开' :
                                                                testStatuses[config.id] === 'pending' ? '检测中...' :
                                                                    '未检测'
                                                    }
                                                </div>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-2 border-t pt-4 md:border-t-0 md:pt-0 border-slate-100 dark:border-slate-800">
                                            {/* Action Buttons */}
                                            <button
                                                onClick={() => handleTest(config.id)}
                                                className="p-2 text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                                                title="测试连接"
                                            >
                                                <Gauge size={18} />
                                            </button>
                                            <button
                                                onClick={() => handleEdit(config)}
                                                className="p-2 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
                                                title="编辑"
                                            >
                                                <Edit2 size={18} />
                                            </button>

                                            {!config.is_default && (
                                                <button
                                                    onClick={() => handleSetDefault(config.id)}
                                                    className="p-2 text-slate-500 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors"
                                                    title="设为默认"
                                                >
                                                    <CheckCircle2 size={18} />
                                                </button>
                                            )}

                                            <div className="w-px h-4 bg-slate-200 dark:bg-slate-700 mx-1"></div>

                                            <button
                                                onClick={() => handleDelete(config.id)}
                                                className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                                title="删除"
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Toast Message */}
                {message && (
                    <div className={`fixed bottom-8 left-1/2 -translate-x-1/2 z-50 px-6 py-3 rounded-xl shadow-2xl flex items-center gap-3 animate-in fade-in slide-in-from-bottom-4 ${message.type === 'success' ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' :
                        message.type === 'error' ? 'bg-red-600 text-white' :
                            'bg-blue-600 text-white'
                        }`}>
                        {message.type === 'success' && <CheckCircle2 size={18} />}
                        {message.type === 'error' && <Shield size={18} />}
                        <span className="font-medium">{message.text}</span>
                    </div>
                )}
            </div>
        </CompactLayout>
    );
};

export default ConfigPage;
