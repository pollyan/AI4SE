import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, ChevronDown } from 'lucide-react';

interface NavDropdownItem {
    label: string;
    href: string;
}

const Navbar: React.FC = () => {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const location = useLocation();

    // 辅助函数：判断路径是否激活
    const isActive = (path: string) => {
        if (path === '/') return location.pathname === '/';
        return location.pathname.startsWith(path);
    };

    const intentTesterItems: NavDropdownItem[] = [
        { label: '测试用例', href: '/intent-tester/testcases' },
        { label: '执行控制台', href: '/intent-tester/execution' },
        { label: '本地代理', href: '/intent-tester/local-proxy' },
    ];

    const aiAgentsItems: NavDropdownItem[] = [
        { label: '智能助手', href: '/new-agents/' },
        { label: '配置管理', href: '/new-agents/' },
    ];

    return (
        <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
            <div className="max-w-[1200px] mx-auto px-10">
                <div className="flex items-center justify-between h-16">
                    {/* Brand */}
                    <Link to="/" className="text-base font-semibold text-gray-800 tracking-tight hover:text-gray-600 transition-colors">
                        老兵大头的 AI4SE 工具集
                    </Link>

                    {/* Desktop Nav Links */}
                    <div className="hidden md:flex items-center gap-10">
                        <Link
                            to="/"
                            className={`${isActive('/') ? 'text-gray-800 font-medium' : 'text-gray-500 font-normal'} hover:text-gray-800 text-sm transition-colors py-2`}
                        >
                            首页
                        </Link>

                        {/* 意图测试工具 Dropdown */}
                        <div className="relative group">
                            <button className="text-gray-500 hover:text-gray-800 text-sm font-normal transition-colors py-2 flex items-center gap-1.5">
                                意图测试工具
                                <ChevronDown size={12} className="transition-transform group-hover:rotate-180" />
                            </button>
                            <div className="absolute top-full left-0 bg-white border border-gray-200 rounded shadow-lg min-w-[160px] py-2 opacity-0 invisible translate-y-[-10px] group-hover:opacity-100 group-hover:visible group-hover:translate-y-0 transition-all duration-200 z-50">
                                {intentTesterItems.map((item) => (
                                    <a
                                        key={item.href}
                                        href={item.href}
                                        className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-800"
                                    >
                                        {item.label}
                                    </a>
                                ))}
                            </div>
                        </div>

                        {/* AI智能体们 Dropdown */}
                        <div className="relative group">
                            <button className="text-gray-500 hover:text-gray-800 text-sm font-normal transition-colors py-2 flex items-center gap-1.5">
                                AI智能体们
                                <ChevronDown size={12} className="transition-transform group-hover:rotate-180" />
                            </button>
                            <div className="absolute top-full left-0 bg-white border border-gray-200 rounded shadow-lg min-w-[160px] py-2 opacity-0 invisible translate-y-[-10px] group-hover:opacity-100 group-hover:visible group-hover:translate-y-0 transition-all duration-200 z-50">
                                {aiAgentsItems.map((item) => (
                                    <a
                                        key={item.href}
                                        href={item.href}
                                        className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-800"
                                    >
                                        {item.label}
                                    </a>
                                ))}
                            </div>
                        </div>

                        <Link
                            to="/profile"
                            className={`${isActive('/profile') ? 'text-gray-800 font-medium' : 'text-gray-500 font-normal'} hover:text-gray-800 text-sm transition-colors py-2`}
                        >
                            个人简介
                        </Link>
                    </div>

                    {/* Mobile menu button */}
                    <button
                        className="md:hidden text-gray-500 hover:text-gray-800 p-2"
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    >
                        <Menu size={24} />
                    </button>
                </div>

                {/* Mobile menu */}
                {mobileMenuOpen && (
                    <div className="md:hidden py-4 border-t border-gray-200">
                        <Link to="/" className="block py-2 text-sm text-gray-600 hover:text-gray-800">首页</Link>
                        <div className="py-2">
                            <div className="text-sm text-gray-800 font-medium mb-1">意图测试工具</div>
                            {intentTesterItems.map((item) => (
                                <a
                                    key={item.href}
                                    href={item.href}
                                    className="block py-1.5 pl-4 text-sm text-gray-600 hover:text-gray-800"
                                >
                                    {item.label}
                                </a>
                            ))}
                        </div>
                        <div className="py-2">
                            <div className="text-sm text-gray-800 font-medium mb-1">AI智能体们</div>
                            {aiAgentsItems.map((item) => (
                                <a
                                    key={item.href}
                                    href={item.href}
                                    className="block py-1.5 pl-4 text-sm text-gray-600 hover:text-gray-800"
                                >
                                    {item.label}
                                </a>
                            ))}
                        </div>
                        <Link to="/profile" className="block py-2 text-sm text-gray-600 hover:text-gray-800">个人简介</Link>
                    </div>
                )}
            </div>
        </nav>
    );
};

export default Navbar;
