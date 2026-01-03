import React, { useState } from 'react';
import { Menu, ChevronDown, Mail, Smartphone, Globe, FileText, Github } from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <>
      {/* Navigation - matching Flask template style */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-[1200px] mx-auto px-10">
          <div className="flex items-center justify-between h-16">
            {/* Brand */}
            <a href="/" className="text-base font-semibold text-gray-800 tracking-tight hover:text-gray-600 transition-colors">
              老兵大头的 AI4SE 工具集
            </a>

            {/* Desktop Nav Links */}
            <div className="hidden md:flex items-center gap-10">
              <a href="/" className="text-gray-500 hover:text-gray-800 text-sm font-normal transition-colors py-2">
                首页
              </a>

              {/* 意图测试工具 Dropdown */}
              <div className="relative group">
                <button className="text-gray-500 hover:text-gray-800 text-sm font-normal transition-colors py-2 flex items-center gap-1.5">
                  意图测试工具
                  <ChevronDown size={12} className="transition-transform group-hover:rotate-180" />
                </button>
                <div className="absolute top-full left-0 bg-white border border-gray-200 rounded shadow-lg min-w-[160px] py-2 opacity-0 invisible translate-y-[-10px] group-hover:opacity-100 group-hover:visible group-hover:translate-y-0 transition-all duration-200 z-50">
                  <a href="/intent-tester/testcases" className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-800">测试用例</a>
                  <a href="/intent-tester/execution" className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-800">执行控制台</a>
                  <a href="/intent-tester/local-proxy" className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-800">本地代理</a>
                </div>
              </div>

              {/* AI智能体们 Dropdown */}
              <div className="relative group">
                <button className="text-gray-800 text-sm font-normal transition-colors py-2 flex items-center gap-1.5 relative">
                  AI智能体们
                  <ChevronDown size={12} className="transition-transform group-hover:rotate-180" />
                  {/* Active indicator */}
                  <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-gray-800"></span>
                </button>
                <div className="absolute top-full left-0 bg-white border border-gray-200 rounded shadow-lg min-w-[160px] py-2 opacity-0 invisible translate-y-[-10px] group-hover:opacity-100 group-hover:visible group-hover:translate-y-0 transition-all duration-200 z-50">
                  <a href="/ai-agents/" className="block px-4 py-2 text-sm text-gray-800 bg-gray-100 font-medium">智能助手</a>
                  <a href="/ai-agents/config" className="block px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 hover:text-gray-800">配置管理</a>
                </div>
              </div>

              <a href="/profile" className="text-gray-500 hover:text-gray-800 text-sm font-normal transition-colors py-2">
                个人简介
              </a>
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
              <a href="/" className="block py-2 text-sm text-gray-600 hover:text-gray-800">首页</a>
              <div className="py-2">
                <div className="text-sm text-gray-800 font-medium mb-1">意图测试工具</div>
                <a href="/intent-tester/testcases" className="block py-1.5 pl-4 text-sm text-gray-600 hover:text-gray-800">测试用例</a>
                <a href="/intent-tester/execution" className="block py-1.5 pl-4 text-sm text-gray-600 hover:text-gray-800">执行控制台</a>
                <a href="/intent-tester/local-proxy" className="block py-1.5 pl-4 text-sm text-gray-600 hover:text-gray-800">本地代理</a>
              </div>
              <div className="py-2">
                <div className="text-sm text-gray-800 font-medium mb-1">AI智能体们</div>
                <a href="/ai-agents/" className="block py-1.5 pl-4 text-sm text-gray-800 font-medium">智能助手</a>
                <a href="/ai-agents/config" className="block py-1.5 pl-4 text-sm text-gray-600 hover:text-gray-800">配置管理</a>
              </div>
              <a href="/profile" className="block py-2 text-sm text-gray-600 hover:text-gray-800">个人简介</a>
            </div>
          )}
        </div>
      </nav>

      <main className="flex-grow max-w-[1200px] mx-auto px-10 py-10 w-full">
        {children}
      </main>

      <footer className="bg-gray-50 dark:bg-gray-900 border-t border-border-light dark:border-border-dark mt-auto pt-12 pb-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
            <div>
              <h3 className="flex items-center text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                <span className="text-lg mr-2">👨‍💻</span> 关于作者
              </h3>
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-3">
                <p className="font-medium">由 安辉（老兵大头） 独立开发与维护</p>
                <p>19年研发经验 | AI4SE 实践者 | ThoughtWorks校友</p>
                <p className="leading-relaxed text-xs">
                  作为一名在软件工程领域深耕近 20 年的老兵，致力于将 AI 技术转化为企业级生产力工具。如果这些工具对你有帮助，欢迎反馈和交流！
                </p>
              </div>
            </div>
            <div className="md:pl-10">
              <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                快速链接
              </h3>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li><a href="#" className="hover:text-primary transition-colors">首页</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">意图测试工具</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">AI智能助手</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">个人简介</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">GitHub 仓库</a></li>
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                联系方式
              </h3>
              <ul className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
                <li className="flex items-center">
                  <Mail className="text-gray-400 mr-2 w-4 h-4" />
                  <a href="mailto:pollyan@163.com" className="hover:text-primary transition-colors border-b border-dotted border-gray-400">pollyan@163.com</a>
                </li>
                <li className="flex items-center">
                  <Smartphone className="text-gray-400 mr-2 w-4 h-4" />
                  <span>18910027087</span>
                </li>
                <li className="flex items-center">
                  <Globe className="text-gray-400 mr-2 w-4 h-4" />
                  <a href="#" className="hover:text-primary transition-colors">个人简介</a>
                </li>
                <li className="flex items-center">
                  <FileText className="text-gray-400 mr-2 w-4 h-4" />
                  <a href="#" className="hover:text-primary transition-colors">技术文章</a>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-200 dark:border-gray-800 pt-8 text-center text-xs text-gray-500 dark:text-gray-500 space-y-2">
            <p>© 2024 老兵大头的 AI4SE 工具集 | 基于 MIT 协议开源</p>
            <p>让 AI 驱动的软件工程变得简单而强大</p>
          </div>
        </div>
      </footer>
    </>
  );
};

export default Layout;