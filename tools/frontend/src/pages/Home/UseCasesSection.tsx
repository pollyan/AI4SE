import React from 'react';
import { Terminal, Bot, CheckCircle, Users, Repeat, Globe, FileText, TestTube, Layers, GraduationCap } from 'lucide-react';

const UseCasesSection: React.FC = () => {
    const intentTestCases = [
        { icon: <Repeat size={16} />, title: "Web应用回归测试", desc: "频繁发布的Web应用需要快速验证核心功能" },
        { icon: <CheckCircle size={16} />, title: "用户流程验证", desc: "电商购买、用户注册等关键业务流程测试" },
        { icon: <Globe size={16} />, title: "跨浏览器兼容性", desc: "需要在多种浏览器环境下验证功能" },
        { icon: <Users size={16} />, title: "敏捷开发团队", desc: "需要快速创建和维护自动化测试的团队" },
    ];

    const aiAssistantCases = [
        { icon: <FileText size={16} />, title: "需求分析师Alex", desc: "澄清业务需求，生成PRD文档" },
        { icon: <TestTube size={16} />, title: "测试分析师Song", desc: "设计测试策略，生成测试用例" },
        { icon: <Layers size={16} />, title: "团队协作", desc: "标准化分析流程和文档模板" },
        { icon: <GraduationCap size={16} />, title: "知识传承", desc: "新人培训和方法论学习" },
    ];

    return (
        <section className="py-16 bg-white dark:bg-slate-900">
            <div className="container mx-auto px-4">
                <div className="text-center mb-12">
                    <h2 className="text-2xl lg:text-3xl font-bold text-slate-900 dark:text-white mb-3">典型使用场景</h2>
                    <p className="text-slate-600 dark:text-slate-400">了解如何在项目中最大化这些工具的价值</p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl mx-auto">
                    {/* 意图驱动测试场景 */}
                    <div className="bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-slate-800 dark:to-slate-800 rounded-2xl p-6 border border-blue-100 dark:border-slate-700">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-2.5 bg-blue-600 text-white rounded-xl shadow-lg shadow-blue-200 dark:shadow-none">
                                <Terminal size={20} />
                            </div>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">意图驱动测试适用场景</h3>
                        </div>

                        <div className="space-y-4">
                            {intentTestCases.map((item, idx) => (
                                <div key={idx} className="flex items-start gap-3 group">
                                    <div className="mt-0.5 p-1.5 bg-white dark:bg-slate-700 rounded-lg text-blue-600 dark:text-blue-400 shadow-sm group-hover:shadow transition-shadow">
                                        {item.icon}
                                    </div>
                                    <div>
                                        <div className="font-semibold text-slate-800 dark:text-slate-200 text-sm">{item.title}</div>
                                        <div className="text-slate-600 dark:text-slate-400 text-sm">{item.desc}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* AI智能助手场景 */}
                    <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-slate-800 dark:to-slate-800 rounded-2xl p-6 border border-purple-100 dark:border-slate-700">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="p-2.5 bg-purple-600 text-white rounded-xl shadow-lg shadow-purple-200 dark:shadow-none">
                                <Bot size={20} />
                            </div>
                            <h3 className="text-lg font-bold text-slate-900 dark:text-white">AI智能助手适用场景</h3>
                        </div>

                        <div className="space-y-4">
                            {aiAssistantCases.map((item, idx) => (
                                <div key={idx} className="flex items-start gap-3 group">
                                    <div className="mt-0.5 p-1.5 bg-white dark:bg-slate-700 rounded-lg text-purple-600 dark:text-purple-400 shadow-sm group-hover:shadow transition-shadow">
                                        {item.icon}
                                    </div>
                                    <div>
                                        <div className="font-semibold text-slate-800 dark:text-slate-200 text-sm">{item.title}</div>
                                        <div className="text-slate-600 dark:text-slate-400 text-sm">{item.desc}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default UseCasesSection;
