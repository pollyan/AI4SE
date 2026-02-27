import React from 'react';
import { ArrowRight, Bot, Sparkles, Terminal } from 'lucide-react';

const HeroSection: React.FC = () => {
    return (
        <section className="relative overflow-hidden py-20 lg:py-32">
            {/* Background Gradients */}
            <div className="absolute top-0 -left-4 w-72 h-72 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob dark:bg-purple-800/30"></div>
            <div className="absolute top-0 -right-4 w-72 h-72 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000 dark:bg-yellow-800/30"></div>
            <div className="absolute -bottom-8 left-20 w-72 h-72 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000 dark:bg-pink-800/30"></div>

            <div className="container mx-auto px-4 relative z-10">
                <div className="max-w-4xl mx-auto text-center">
                    <div className="inline-flex items-center gap-2 px-3 py-1 mb-6 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300 text-sm font-medium border border-blue-100 dark:border-blue-800/50">
                        <Sparkles size={14} />
                        <span>AI4SE 下一代软件工程</span>
                    </div>

                    <h1 className="text-5xl lg:text-7xl font-bold tracking-tight text-slate-900 dark:text-white mb-6">
                        用 <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-violet-600">AI 智能体</span> <br />
                        重塑软件研发
                    </h1>

                    <p className="text-xl text-slate-600 dark:text-slate-300 mb-10 max-w-2xl mx-auto leading-relaxed">
                        集成意图驱动开发、智能测试生成与 DevOps 自动化的全栈 AI4SE 平台。让 AI 成为你的超级结对编程伙伴。
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <a
                            href="/new-agents/"
                            className="w-full sm:w-auto px-8 py-4 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-xl font-semibold hover:bg-slate-800 dark:hover:bg-slate-100 transition-all transform hover:scale-105 shadow-lg shadow-slate-200/50 dark:shadow-none flex items-center justify-center gap-2"
                        >
                            <Bot size={20} />
                            开始智能对话
                        </a>
                        <a
                            href="/intent-tester/testcases"
                            className="w-full sm:w-auto px-8 py-4 bg-white dark:bg-slate-800/50 text-slate-700 dark:text-white border border-slate-200 dark:border-slate-700 rounded-xl font-semibold hover:bg-slate-50 dark:hover:bg-slate-700 transition-all backdrop-blur-sm flex items-center justify-center gap-2"
                        >
                            <Terminal size={20} />
                            意图测试工具
                        </a>
                    </div>
                </div>

                {/* Feature Preview Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-20">
                    {[
                        {
                            title: "意图理解",
                            desc: "基于 LLM 的精准需求分析与澄清",
                            icon: <Sparkles className="text-yellow-500" />
                        },
                        {
                            title: "测试生成",
                            desc: "自动生成边界条件完备的测试用例",
                            icon: <Terminal className="text-blue-500" />
                        },
                        {
                            title: "流程自动化",
                            desc: "从需求到交付的全链路智能辅助",
                            icon: <ArrowRight className="text-purple-500" />
                        }
                    ].map((feature, idx) => (
                        <div key={idx} className="p-6 bg-white/60 dark:bg-slate-800/40 backdrop-blur-lg border border-white/20 dark:border-slate-700/50 rounded-2xl shadow-sm hover:shadow-md transition-all">
                            <div className="w-12 h-12 bg-white dark:bg-slate-700 rounded-xl flex items-center justify-center shadow-sm mb-4">
                                {feature.icon}
                            </div>
                            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">{feature.title}</h3>
                            <p className="text-slate-600 dark:text-slate-400 text-sm">{feature.desc}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default HeroSection;
