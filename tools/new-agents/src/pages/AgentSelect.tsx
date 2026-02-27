import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, Code2, Sparkles, Navigation, ArrowRight, ShieldCheck, Zap, ArrowLeft } from 'lucide-react';
import { clsx } from 'clsx';

export function AgentSelect() {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen bg-[#0B1120] text-slate-200 font-sans selection:bg-blue-500/30 selection:text-white flex flex-col items-center justify-center p-6 relative overflow-hidden">

            {/* Background decorations */}
            <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-600/10 rounded-full blur-[120px] pointer-events-none" />

            {/* Nav */}
            <div className="absolute top-6 left-6 z-20">
                <a
                    href="/"
                    className="group px-4 py-2 bg-slate-800/50 hover:bg-slate-700/80 backdrop-blur-sm rounded-xl transition-colors flex items-center gap-2 border border-slate-700/50 hover:border-blue-500/30 text-slate-300 hover:text-white"
                >
                    <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" /> 返回平台首页
                </a>
            </div>

            <div className="w-full max-w-4xl z-10">
                <div className="text-center mb-16">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-medium mb-6">
                        <Sparkles className="w-4 h-4" />
                        AI4SE 智能引擎
                    </div>
                    <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight mb-4">
                        选择智能研发专家
                    </h1>
                    <p className="text-lg text-slate-400 max-w-2xl mx-auto">
                        为您配置专属领域大模型智能体，无缝融入各项研发与协作流程。
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

                    {/* Lisa Card - Active */}
                    <div
                        onClick={() => navigate('/workflows/lisa')}
                        className="group relative bg-[#131d31] rounded-2xl border border-slate-700/50 hover:border-blue-500/50 p-8 cursor-pointer overflow-hidden transition-all duration-300 hover:shadow-2xl hover:shadow-blue-500/10 hover:-translate-y-1"
                    >
                        <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />

                        <div className="flex items-start justify-between mb-8 relative z-10">
                            <div className="w-14 h-14 flex items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-500/20">
                                <Bot className="w-7 h-7" />
                            </div>
                            <div className="flex px-3 py-1 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-semibold uppercase tracking-wider">
                                Online
                            </div>
                        </div>

                        <div className="relative z-10">
                            <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                                Lisa <span className="text-sm font-normal text-slate-400">测试专家</span>
                            </h2>
                            <p className="text-slate-400 mb-6 min-h-[48px]">
                                专注于意图测试设计、用例自动生成和自动化测试脚本编写的智能体。
                            </p>

                            <ul className="space-y-3 mb-8">
                                <li className="flex items-center gap-3 text-sm text-slate-300">
                                    <ShieldCheck className="w-4 h-4 text-blue-400 shrink-0" />
                                    <span>自动化端到端测试设计</span>
                                </li>
                                <li className="flex items-center gap-3 text-sm text-slate-300">
                                    <Zap className="w-4 h-4 text-blue-400 shrink-0" />
                                    <span>UI / API 自动化用例生成</span>
                                </li>
                                <li className="flex items-center gap-3 text-sm text-slate-300">
                                    <Navigation className="w-4 h-4 text-blue-400 shrink-0" />
                                    <span>意图驱动执行支持</span>
                                </li>
                            </ul>

                            <div className="flex items-center text-blue-400 font-medium group-hover:text-blue-300 transition-colors">
                                进入工作室 <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                            </div>
                        </div>
                    </div>

                    {/* Alex Card - Disabled */}
                    <div className="relative bg-[#0d1624] rounded-2xl border border-slate-800 p-8 overflow-hidden opacity-75">
                        <div className="absolute inset-0 bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,rgba(255,255,255,0.02)_10px,rgba(255,255,255,0.02)_20px)] pointer-events-none" />

                        <div className="flex items-start justify-between mb-8 relative z-10">
                            <div className="w-14 h-14 flex items-center justify-center rounded-xl bg-slate-800 text-slate-500 border border-slate-700">
                                <Code2 className="w-7 h-7" />
                            </div>
                            <div className="flex px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-slate-400 text-xs font-semibold uppercase tracking-wider">
                                Coming Soon
                            </div>
                        </div>

                        <div className="relative z-10 grayscale-[50%]">
                            <h2 className="text-2xl font-bold text-slate-300 mb-2 flex items-center gap-2">
                                Alex <span className="text-sm font-normal text-slate-500">前端框架专家</span>
                            </h2>
                            <p className="text-slate-500 mb-6 min-h-[48px]">
                                擅长解析 UI 设计稿，自动化编写 React/Vue 组件与框架层代码，提升产研效能。
                            </p>

                            <ul className="space-y-3 mb-8 opacity-60">
                                <li className="flex items-center gap-3 text-sm text-slate-500">
                                    <div className="w-1.5 h-1.5 rounded-full bg-slate-600 shrink-0" />
                                    <span>UI 视觉稿精准切图与识别</span>
                                </li>
                                <li className="flex items-center gap-3 text-sm text-slate-500">
                                    <div className="w-1.5 h-1.5 rounded-full bg-slate-600 shrink-0" />
                                    <span>页面骨架与交互逻辑生成</span>
                                </li>
                                <li className="flex items-center gap-3 text-sm text-slate-500">
                                    <div className="w-1.5 h-1.5 rounded-full bg-slate-600 shrink-0" />
                                    <span>样式系统无缝接入 (Tailwind)</span>
                                </li>
                            </ul>

                            <div className="flex items-center text-slate-600 font-medium cursor-not-allowed">
                                功能研发中，敬请期待...
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}
