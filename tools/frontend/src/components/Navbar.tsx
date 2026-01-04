import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu } from 'lucide-react';

interface NavDropdownItem {
    label: string;
    href: string;
}


const Navbar: React.FC = () => {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const location = useLocation();

    const isActive = (path: string) => location.pathname === path;

    const intentTesterItems: NavDropdownItem[] = [
        { label: '测试用例', href: '/intent-tester/testcases' },
        { label: '执行控制台', href: '/intent-tester/execution' },
        { label: '本地代理', href: '/intent-tester/local-proxy' },
    ];

    const aiAgentsItems: NavDropdownItem[] = [
        { label: '智能助手', href: '/ai-agents/' },
        { label: '配置管理', href: '/ai-agents/config' },
    ];

    return (
        <nav className="top-nav">
            <div className="nav-container">
                <Link to="/" className="nav-brand">
                    老兵大头的 AI4SE 工具集
                </Link>

                <div className="nav-links">
                    <Link to="/" className={`nav-link ${isActive('/') ? 'active' : ''}`}>
                        首页
                    </Link>

                    {/* 意图测试工具 Dropdown */}
                    <div className="nav-dropdown">
                        <span className="nav-link nav-dropdown-trigger">
                            意图测试工具
                            <span className="dropdown-arrow">▼</span>
                        </span>
                        <div className="nav-dropdown-menu">
                            {intentTesterItems.map((item) => (
                                <a
                                    key={item.href}
                                    href={item.href}
                                    className="nav-dropdown-item"
                                >
                                    {item.label}
                                </a>
                            ))}
                        </div>
                    </div>

                    {/* AI智能体们 Dropdown */}
                    <div className="nav-dropdown">
                        <span className="nav-link nav-dropdown-trigger">
                            AI智能体们
                            <span className="dropdown-arrow">▼</span>
                        </span>
                        <div className="nav-dropdown-menu">
                            {aiAgentsItems.map((item) => (
                                <a
                                    key={item.href}
                                    href={item.href}
                                    className="nav-dropdown-item"
                                >
                                    {item.label}
                                </a>
                            ))}
                        </div>
                    </div>

                    <Link to="/profile" className={`nav-link ${isActive('/profile') ? 'active' : ''}`}>
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
                <div className="md:hidden py-4 border-t border-gray-200 px-4">
                    <Link to="/" className="block py-2 text-sm text-gray-600 hover:text-gray-800">
                        首页
                    </Link>
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
                    <Link to="/profile" className="block py-2 text-sm text-gray-600 hover:text-gray-800">
                        个人简介
                    </Link>
                </div>
            )}
        </nav>
    );
};

export default Navbar;
