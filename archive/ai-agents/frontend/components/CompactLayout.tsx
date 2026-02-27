/**
 * CompactLayout - 紧凑型布局组件
 * 无页脚，精简导航栏
 */
import React, { useState } from 'react';
import { Menu, ChevronDown, X } from 'lucide-react';

interface CompactLayoutProps {
    children: React.ReactNode;
}

const CompactLayout: React.FC<CompactLayoutProps> = ({ children }) => {
    console.log('[CompactLayout] Rendering children:', children);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    return (
        <div className="flex flex-col h-screen overflow-hidden bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 transition-colors duration-300">
            {/* 精简导航栏 */}
            <nav className="bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 shrink-0 h-14 z-50">
                <div className="h-full px-4 lg:px-6">
                    <div className="flex items-center justify-between h-full">
                        {/* Brand */}
                        <a
                            href="/"
                            className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent text-lg font-bold tracking-tight hover:opacity-80 transition-opacity"
                        >
                            AI4SE 工具集
                        </a>

                        {/* Desktop Nav */}
                        <div className="hidden md:flex items-center gap-8">
                            <a
                                href="/"
                                className="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                            >
                                首页
                            </a>

                            {/* AI智能体 Dropdown */}
                            <div className="relative group">
                                <button className="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 flex items-center gap-1 transition-colors">
                                    AI智能体
                                    <ChevronDown size={14} className="transition-transform group-hover:rotate-180" />
                                </button>
                                <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl min-w-[160px] p-2 opacity-0 invisible translate-y-2 group-hover:opacity-100 group-hover:visible group-hover:translate-y-0 transition-all duration-200 z-50">
                                    <a
                                        href="/ai-agents/"
                                        className="block px-3 py-2 text-sm text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                    >
                                        智能对话
                                    </a>
                                    <a
                                        href="/ai-agents/config"
                                        className="block px-3 py-2 text-sm text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                                    >
                                        配置管理
                                    </a>
                                </div>
                            </div>

                            <a
                                href="/intent-tester/testcases"
                                className="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                            >
                                意图测试
                            </a>

                            <a
                                href="/profile"
                                className="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                            >
                                个人中心
                            </a>
                        </div>

                        {/* Mobile menu button */}
                        <div className="flex items-center gap-2 md:hidden">
                            <button
                                className="text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 p-2"
                                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            >
                                {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                            </button>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Mobile menu overlay */}
            {mobileMenuOpen && (
                <div className="md:hidden absolute top-14 left-0 right-0 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 z-40 shadow-lg animate-in slide-in-from-top-2">
                    <div className="px-4 py-4 space-y-2">
                        <a href="/" className="block py-2.5 px-3 text-base font-medium rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200">
                            首页
                        </a>
                        <div className="py-2">
                            <div className="px-3 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">AI智能体</div>
                            <a href="/ai-agents/" className="block py-2 px-3 text-base text-slate-600 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 pl-6">
                                智能对话
                            </a>
                            <a href="/ai-agents/config" className="block py-2 px-3 text-base text-slate-600 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 pl-6">
                                配置管理
                            </a>
                        </div>
                        <a href="/intent-tester/testcases" className="block py-2.5 px-3 text-base font-medium rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200">
                            意图测试
                        </a>
                        <a href="/profile" className="block py-2.5 px-3 text-base font-medium rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200">
                            个人中心
                        </a>
                    </div>
                </div>
            )}

            {/* 主内容区 - 占满剩余空间 */}
            <main className="flex-1 overflow-hidden">
                {children}
            </main>
        </div>
    );
};

export default CompactLayout;
