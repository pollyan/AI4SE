import React, { useState, useEffect } from 'react';
import Layout from './components/Layout';
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

type TestStatus = 'unknown' | 'pending' | 'success' | 'error';

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
    const [testStatuses, setTestStatuses] = useState<Record<number, TestStatus>>({});

    // UI state
    const [loading, setLoading] = useState(true);
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
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingId) {
                await updateConfig(editingId, formData);
                showMessage('配置更新成功', 'success');
            } else {
                await createConfig(formData);
                showMessage('配置创建成功', 'success');
            }
            clearForm();
            await loadData();
        } catch (error) {
            showMessage((error as Error).message, 'error');
        }
    };

    const handleEdit = (config: AIConfig) => {
        setFormData({
            config_name: config.config_name,
            api_key: '', // Don't pre-fill password
            base_url: config.base_url,
            model_name: config.model_name,
        });
        setEditingId(config.id);
        showMessage('已加载配置到编辑表单，修改后点击保存', 'info');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    const handleDelete = async (id: number) => {
        if (!confirm('确定要删除这个配置吗？删除后无法恢复。')) return;
        try {
            await deleteConfig(id);
            showMessage('配置删除成功', 'success');
            await loadData();
        } catch (error) {
            showMessage('删除失败: ' + (error as Error).message, 'error');
        }
    };

    const handleSetDefault = async (id: number) => {
        try {
            await setDefaultConfig(id);
            showMessage('配置选用成功', 'success');
            await loadData();
        } catch (error) {
            showMessage('选用失败: ' + (error as Error).message, 'error');
        }
    };

    const handleTest = async (id: number) => {
        setTestStatuses(prev => ({ ...prev, [id]: 'pending' }));
        try {
            const result = await testConfig(id);
            setTestStatuses(prev => ({ ...prev, [id]: result.test_success ? 'success' : 'error' }));
            if (result.test_success) {
                showMessage(`✅ 测试成功！响应时间: ${result.duration_ms}ms`, 'success');
            } else {
                showMessage(`❌ 测试失败: ${result.message}`, 'error');
            }
        } catch (error) {
            setTestStatuses(prev => ({ ...prev, [id]: 'error' }));
            showMessage('测试失败: ' + (error as Error).message, 'error');
        }
    };

    const handleTestNew = async () => {
        if (!formData.api_key || !formData.base_url || !formData.model_name) {
            showMessage('请填写API密钥、基础URL和模型名称后再测试', 'error');
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

    const formatDate = (dateStr: string) => {
        if (!dateStr) return '未知';
        try {
            return new Date(dateStr).toLocaleString('zh-CN', {
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit'
            });
        } catch {
            return '未知';
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
        <Layout>
            <h1 className="text-3xl font-light text-gray-800 mb-2">AI配置管理</h1>
            <p className="text-gray-500 mb-8">管理你的AI助手连接配置</p>

            {/* Message Toast */}
            {message && (
                <div className={`fixed top-20 right-4 z-50 px-4 py-3 rounded shadow-lg max-w-md whitespace-pre-wrap text-sm ${message.type === 'success' ? 'bg-green-100 text-green-800 border border-green-200' :
                        message.type === 'error' ? 'bg-red-100 text-red-800 border border-red-200' :
                            'bg-blue-100 text-blue-800 border border-blue-200'
                    }`}>
                    {message.text}
                </div>
            )}

            <div className="space-y-6">
                {/* Config Form Card */}
                <div className="bg-white border border-gray-200 rounded p-5">
                    <h2 className="text-base font-medium text-gray-800 mb-1">AI服务配置</h2>
                    <p className="text-sm text-gray-500 mb-5">配置你的AI助手连接设置</p>

                    <form onSubmit={handleSubmit}>
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-1.5">配置名称</label>
                            <input
                                type="text"
                                name="config_name"
                                value={formData.config_name}
                                onChange={handleInputChange}
                                placeholder="给你的AI配置起个名字，如：我的OpenAI配置"
                                className="w-full px-3 py-2.5 border border-gray-200 rounded text-sm focus:outline-none focus:border-gray-800"
                                required
                            />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1.5">API密钥</label>
                                <input
                                    type="password"
                                    name="api_key"
                                    value={formData.api_key}
                                    onChange={handleInputChange}
                                    placeholder="输入你的API密钥"
                                    className="w-full px-3 py-2.5 border border-gray-200 rounded text-sm focus:outline-none focus:border-gray-800"
                                    required={!editingId}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1.5">模型名称</label>
                                <input
                                    type="text"
                                    name="model_name"
                                    value={formData.model_name}
                                    onChange={handleInputChange}
                                    placeholder="如: gpt-4o, qwen-vl-max-latest"
                                    className="w-full px-3 py-2.5 border border-gray-200 rounded text-sm focus:outline-none focus:border-gray-800"
                                    required
                                />
                            </div>
                        </div>

                        <div className="mb-5">
                            <label className="block text-sm font-medium text-gray-700 mb-1.5">API基础URL</label>
                            <input
                                type="url"
                                name="base_url"
                                value={formData.base_url}
                                onChange={handleInputChange}
                                placeholder="如: https://api.openai.com/v1"
                                className="w-full px-3 py-2.5 border border-gray-200 rounded text-sm focus:outline-none focus:border-gray-800"
                                required
                            />
                        </div>

                        <div className="flex justify-end gap-3">
                            <button type="button" onClick={clearForm} className="px-4 py-2.5 border border-gray-200 rounded text-sm text-gray-600 hover:bg-gray-50">
                                清空
                            </button>
                            <button type="button" onClick={handleTestNew} className="px-4 py-2.5 border border-gray-200 rounded text-sm text-gray-600 hover:bg-gray-50">
                                测试连接
                            </button>
                            <button type="submit" className="px-4 py-2.5 bg-gray-800 text-white rounded text-sm hover:bg-gray-700">
                                {editingId ? '更新配置' : '保存配置'}
                            </button>
                        </div>
                    </form>
                </div>

                {/* Config Management Section */}
                <div className="border-t border-gray-200 pt-6">
                    <h3 className="text-base font-medium text-gray-800 mb-4 flex items-center gap-2">
                        <span>⚙️</span> 配置管理
                    </h3>

                    {/* Stats */}
                    <div className="flex gap-4 mb-5 flex-wrap">
                        <div className="bg-gray-50 border border-gray-200 rounded px-3 py-2 text-sm text-gray-600">
                            总配置: <span className="font-medium text-gray-800">{stats.total_configs}</span>
                        </div>
                        <div className="bg-gray-50 border border-gray-200 rounded px-3 py-2 text-sm text-gray-600">
                            已选用: <span className="font-medium text-gray-800">{stats.selected_configs}</span>
                        </div>
                        <div className="bg-gray-50 border border-gray-200 rounded px-3 py-2 text-sm text-gray-600">
                            当前使用: <span className="font-medium text-gray-800">{stats.current_config_name}</span>
                        </div>
                    </div>

                    {/* Config List */}
                    <div className="border border-gray-200 rounded bg-white max-h-[500px] overflow-y-auto">
                        {loading ? (
                            <div className="text-center py-10 text-gray-500">加载中...</div>
                        ) : configs.length === 0 ? (
                            <div className="text-center py-10">
                                <div className="text-4xl text-gray-300 mb-4">⚙️</div>
                                <div className="text-base font-medium text-gray-700 mb-2">暂无AI配置</div>
                                <div className="text-sm text-gray-500">创建你的第一个AI配置来开始使用智能功能</div>
                            </div>
                        ) : (
                            configs.map(config => (
                                <div
                                    key={config.id}
                                    className={`p-4 border-b border-gray-100 last:border-b-0 flex items-center justify-between hover:bg-gray-50 transition-colors ${config.is_default ? 'bg-blue-50 border-l-2 border-l-gray-800' : ''
                                        }`}
                                >
                                    <div className="flex-1">
                                        <div className="text-sm font-medium text-gray-800 mb-1 flex items-center gap-2">
                                            {config.config_name}
                                            {config.is_default && (
                                                <span className="inline-block px-1.5 py-0.5 rounded-full text-[11px] font-medium bg-blue-100 text-blue-700">
                                                    使用中
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-xs text-gray-500 leading-relaxed">
                                            模型: <span className="text-gray-700 font-medium">{config.model_name}</span>
                                            {' • '}API: {getHostname(config.base_url)}
                                            {' • '}创建时间: {formatDate(config.created_at)}
                                        </div>
                                        <div className={`flex items-center gap-1 text-[11px] mt-1 ${testStatuses[config.id] === 'success' ? 'text-green-600' :
                                                testStatuses[config.id] === 'error' ? 'text-red-600' :
                                                    testStatuses[config.id] === 'pending' ? 'text-yellow-600' :
                                                        'text-gray-400'
                                            }`}>
                                            <span className={`w-1.5 h-1.5 rounded-full ${testStatuses[config.id] === 'success' ? 'bg-green-500' :
                                                    testStatuses[config.id] === 'error' ? 'bg-red-500' :
                                                        testStatuses[config.id] === 'pending' ? 'bg-yellow-500' :
                                                            'bg-gray-400'
                                                }`}></span>
                                            {testStatuses[config.id] === 'success' ? '连接正常' :
                                                testStatuses[config.id] === 'error' ? '连接失败' :
                                                    testStatuses[config.id] === 'pending' ? '测试中...' :
                                                        '连接状态未知'}
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <button onClick={() => handleEdit(config)} className="px-3 py-1.5 border border-gray-200 rounded text-xs text-gray-600 hover:bg-gray-100">
                                            编辑
                                        </button>
                                        <button onClick={() => handleTest(config.id)} className="px-3 py-1.5 border border-gray-200 rounded text-xs text-gray-600 hover:bg-gray-100">
                                            测试
                                        </button>
                                        {config.is_default ? (
                                            <span className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded text-xs font-medium">使用中</span>
                                        ) : (
                                            <button onClick={() => handleSetDefault(config.id)} className="px-3 py-1.5 bg-gray-800 text-white rounded text-xs hover:bg-gray-700">
                                                选用
                                            </button>
                                        )}
                                        <button onClick={() => handleDelete(config.id)} className="px-3 py-1.5 border border-red-300 text-red-600 rounded text-xs hover:bg-red-50">
                                            删除
                                        </button>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>
        </Layout>
    );
};

export default ConfigPage;
