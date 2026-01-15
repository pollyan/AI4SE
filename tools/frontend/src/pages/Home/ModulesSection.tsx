import React from 'react';
import { Bot, Terminal, CheckCircle2, Zap, LayoutTemplate, MessageSquare, Eye, ShieldCheck } from 'lucide-react';

const ModulesSection: React.FC = () => {
    return (
        <section className="py-20 bg-slate-50 dark:bg-slate-900/50">
            <div className="container mx-auto px-4">
                <div className="text-center mb-16 max-w-3xl mx-auto">
                    <h2 className="text-3xl lg:text-4xl font-bold text-slate-900 dark:text-white mb-4">核心功能模块</h2>
                    <p className="text-lg text-slate-600 dark:text-slate-400">两个强大的 AI 驱动工具，覆盖软件工程的关键环节，从需求分析到自动化测试</p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 max-w-6xl mx-auto">
                    {/* 意图驱动测试模块 */}
                    <div className="group relative bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden flex flex-col">
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-cyan-500"></div>

                        <div className="p-8 flex flex-col flex-1">
                            <div className="flex items-start justify-between mb-6">
                                <div>
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400">
                                            <Terminal size={24} />
                                        </div>
                                        <h3 className="text-2xl font-bold text-slate-900 dark:text-white">意图驱动测试</h3>
                                    </div>
                                    <p className="text-blue-600 dark:text-blue-400 font-medium">AI 自动化 Web 测试平台</p>
                                </div>
                                <span className="px-3 py-1 bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 text-xs font-semibold rounded-full border border-yellow-200 dark:border-yellow-800 shrink-0">
                                    配置难度：中等
                                </span>
                            </div>

                            <p className="text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
                                你见过没有代码的自动化测试吗? 只需用自然语言描述测试意图，AI 将自动识别页面元素并执行测试操作。支持智能断言和自适应执行策略。
                            </p>

                            <div className="mb-6 p-4 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-100 dark:border-slate-700/50">
                                <h4 className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white mb-2">
                                    <Zap size={16} className="text-amber-500" />
                                    核心价值
                                </h4>
                                <p className="text-sm text-slate-600 dark:text-slate-400">
                                    真正具备智能的、可自愈的自动化测试！以前需要数小时编写的测试代码现在只要几分钟的自然语言描述，效率提升 10 倍以上
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-3 mb-6">
                                {[
                                    { icon: <Eye size={16} />, text: "AI 视觉识别元素" },
                                    { icon: <MessageSquare size={16} />, text: "普通话描述步骤" },
                                    { icon: <ShieldCheck size={16} />, text: "页面变化自愈" },
                                    { icon: <Zap size={16} />, text: "智能缓存策略" },
                                ].map((item, idx) => (
                                    <div key={idx} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                                        <span className="text-blue-500">{item.icon}</span>
                                        <span>{item.text}</span>
                                    </div>
                                ))}
                            </div>

                            {/* Spacer to push buttons to bottom */}
                            <div className="flex-1"></div>

                            <div className="flex flex-col sm:flex-row gap-3 pt-6 border-t border-slate-100 dark:border-slate-700">
                                <a href="/intent-tester/testcases" className="flex-1 inline-flex justify-center items-center px-6 py-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl font-medium hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors shadow-lg shadow-slate-200/50 dark:shadow-none cursor-pointer">
                                    开始测试
                                </a>
                                <a href="/intent-tester/execution" className="flex-1 inline-flex justify-center items-center px-6 py-3 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-xl font-medium hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors cursor-pointer">
                                    查看控制台
                                </a>
                            </div>
                        </div>
                    </div>

                    {/* 智能助手模块 */}
                    <div className="group relative bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-xl transition-all duration-300 overflow-hidden flex flex-col">
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-pink-500"></div>

                        <div className="p-8 flex flex-col flex-1">
                            <div className="flex items-start justify-between mb-6">
                                <div>
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg text-purple-600 dark:text-purple-400">
                                            <Bot size={24} />
                                        </div>
                                        <h3 className="text-2xl font-bold text-slate-900 dark:text-white">AI 智能助手</h3>
                                    </div>
                                    <p className="text-purple-600 dark:text-purple-400 font-medium">专业的需求分析师 Alex & 测试分析师 Song</p>
                                </div>
                                <span className="px-3 py-1 bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 text-xs font-semibold rounded-full border border-green-200 dark:border-green-800 shrink-0">
                                    配置难度：简单
                                </span>
                            </div>

                            <p className="text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
                                选择专业的 AI 助手开始对话。Alex 专注需求分析，通过提问引导您澄清业务需求；Song 专注测试分析，协助您设计测试策略和用例。
                            </p>

                            <div className="mb-6 p-4 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-100 dark:border-slate-700/50">
                                <h4 className="flex items-center gap-2 font-semibold text-slate-900 dark:text-white mb-2">
                                    <Zap size={16} className="text-amber-500" />
                                    核心价值
                                </h4>
                                <p className="text-sm text-slate-600 dark:text-slate-400">
                                    专业的 AI 助手团队，基于成熟的方法论，引导您完成需求分析或测试设计，输出标准化的专业文档。
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-3 mb-6">
                                {[
                                    { icon: <MessageSquare size={16} />, text: "AI 引导提问澄清" },
                                    { icon: <Eye size={16} />, text: "盲点识别与发现" },
                                    { icon: <CheckCircle2 size={16} />, text: "最佳实践验证" },
                                    { icon: <LayoutTemplate size={16} />, text: "自动生成 PRD/User Story" },
                                ].map((item, idx) => (
                                    <div key={idx} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                                        <span className="text-purple-500">{item.icon}</span>
                                        <span>{item.text}</span>
                                    </div>
                                ))}
                            </div>

                            {/* Spacer to push buttons to bottom */}
                            <div className="flex-1"></div>

                            <div className="flex flex-col sm:flex-row gap-3 pt-6 border-t border-slate-100 dark:border-slate-700">
                                <a href="/ai-agents/" className="flex-1 inline-flex justify-center items-center px-6 py-3 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl font-medium hover:bg-slate-800 dark:hover:bg-slate-100 transition-colors shadow-lg shadow-slate-200/50 dark:shadow-none cursor-pointer">
                                    开始对话
                                </a>
                                <a href="/ai-agents/config" className="flex-1 inline-flex justify-center items-center px-6 py-3 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-xl font-medium hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors cursor-pointer">
                                    配置管理
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
};

export default ModulesSection;
