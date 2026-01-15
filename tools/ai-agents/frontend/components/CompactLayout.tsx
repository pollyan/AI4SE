/**
 * CompactLayout - 紧凑型布局组件
 * 无页脚，精简导航栏 (48px/40px)
 */
import React, { useState } from 'react';
import { Menu, ChevronDown, X } from 'lucide-react';

interface CompactLayoutProps {
    children: React.ReactNode;
}

const CompactLayout: React.FC<CompactLayoutProps> = ({ children }) => {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    return (
        <div className="flex flex-col h-screen overflow-hidden bg-background-light dark:bg-background-dark">
            {/* 精简导航栏 - 48px (小屏 40px) */}
            <nav className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shrink-0 h-12 sm:h-12">
                <div className="h-full px-3 sm:px-4 lg:px-6">
                    <div className="flex items-center justify-between h-full">
                        {/* Brand */}
                        <a
                            href="/"
                            className="text-sm font-semibold text-gray-800 dark:text-white tracking-tight hover:text-primary transition-colors"
                        >
                            AI4SE 工具集
                        </a>

                        {/* Desktop Nav */}
                        <div className="hidden md:flex items-center gap-6">
                            <a
                                href="/"
                                className="text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-white text-xs font-medium transition-colors"
                            >
                                首页
                            </a>

                            {/* AI智能体 Dropdown */}
                            <div className="relative group">
                                <button className="text-primary text-xs font-medium flex items-center gap-1">
                                    AI智能体
                                    <ChevronDown size={12} className="transition-transform group-hover:rotate-180" />
                                </button>
                                <div className="absolute top-full right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg min-w-[140px] py-1 opacity-0 invisible translate-y-[-4px] group-hover:opacity-100 group-hover:visible group-hover:translate-y-0 transition-all duration-200 z-50">
                                    <a
                                        href="/ai-agents/"
                                        className="block px-3 py-1.5 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                                    >
                                        标准模式
                                    </a>
                                    <a
                                        href="/ai-agents/compact"
                                        className="block px-3 py-1.5 text-xs text-primary font-medium bg-primary/5"
                                    >
                                        紧凑模式
                                    </a>
                                    <a
                                        href="/ai-agents/config"
                                        className="block px-3 py-1.5 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                                    >
                                        配置管理
                                    </a>
                                </div>
                            </div>

                            <a
                                href="/intent-tester/testcases"
                                className="text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-white text-xs font-medium transition-colors"
                            >
                                意图测试
                            </a>
                        </div>

                        {/* Mobile menu button */}
                        <button
                            className="md:hidden text-gray-500 hover:text-gray-800 dark:hover:text-white p-1.5"
                            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                        >
                            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
                        </button>
                    </div>
                </div>
            </nav>

            {/* Mobile menu overlay */}
            {mobileMenuOpen && (
                <div className="md:hidden absolute top-12 left-0 right-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 z-40 shadow-lg">
                    <div className="px-4 py-3 space-y-2">
                        <a href="/" className="block py-2 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-800">
                            首页
                        </a>
                        <div className="py-2">
                            <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">AI智能体</div>
                            <a href="/ai-agents/" className="block py-1.5 pl-3 text-sm text-gray-600 dark:text-gray-300">
                                标准模式
                            </a>
                            <a href="/ai-agents/compact" className="block py-1.5 pl-3 text-sm text-primary font-medium">
                                紧凑模式
                            </a>
                            <a href="/ai-agents/config" className="block py-1.5 pl-3 text-sm text-gray-600 dark:text-gray-300">
                                配置管理
                            </a>
                        </div>
                        <a href="/intent-tester/testcases" className="block py-2 text-sm text-gray-600 dark:text-gray-300">
                            意图测试
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
