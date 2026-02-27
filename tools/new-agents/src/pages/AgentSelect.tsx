import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, Code2, Sparkles, Navigation, ArrowRight, ShieldCheck, Zap, ArrowLeft, LucideIcon } from 'lucide-react';
import { getAgents } from '../config/agents';
import { clsx } from 'clsx';

export function AgentSelect() {
    const navigate = useNavigate();
    const agents = getAgents();

    // Map string names to Lucide icon components
    const ICONS: Record<string, LucideIcon> = {
        Bot: Bot,
        Code2: Code2
    };

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
                    {agents.map((agent) => {
                        const IconComponent = ICONS[agent.id === 'lisa' ? 'Bot' : 'Code2'];
                        const isOnline = agent.status === 'online';

                        return (
                            <div
                                key={agent.id}
                                onClick={() => isOnline ? navigate(`/workflows/${agent.id}`) : undefined}
                                className={clsx(
                                    "group relative rounded-2xl border p-8 overflow-hidden transition-all duration-300",
                                    isOnline
                                        ? "bg-[#131d31] border-slate-700/50 hover:border-blue-500/50 cursor-pointer hover:shadow-2xl hover:shadow-blue-500/10 hover:-translate-y-1"
                                        : "bg-[#0d1624] border-slate-800 opacity-75"
                                )}
                            >
                                {isOnline ? (
                                    <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
                                ) : (
                                    <div className="absolute inset-0 bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,rgba(255,255,255,0.02)_10px,rgba(255,255,255,0.02)_20px)] pointer-events-none" />
                                )}

                                <div className="flex items-start justify-between mb-8 relative z-10">
                                    <div className={clsx(
                                        "w-14 h-14 flex items-center justify-center rounded-xl",
                                        isOnline
                                            ? "bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-500/20"
                                            : "bg-slate-800 text-slate-500 border border-slate-700"
                                    )}>
                                        {IconComponent && <IconComponent className="w-7 h-7" />}
                                    </div>
                                    <div className={clsx(
                                        "flex px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider",
                                        isOnline
                                            ? "bg-green-500/10 border border-green-500/20 text-green-400"
                                            : "bg-slate-800 border border-slate-700 text-slate-400"
                                    )}>
                                        {isOnline ? 'Online' : 'Coming Soon'}
                                    </div>
                                </div>

                                <div className={clsx("relative z-10", !isOnline && "grayscale-[50%]")}>
                                    <h2 className={clsx("text-2xl font-bold mb-2 flex items-center gap-2", isOnline ? "text-white" : "text-slate-300")}>
                                        {agent.name} <span className={clsx("text-sm font-normal", isOnline ? "text-slate-400" : "text-slate-500")}>{agent.role}</span>
                                    </h2>
                                    <p className={clsx("mb-6 min-h-[48px]", isOnline ? "text-slate-400" : "text-slate-500")}>
                                        {agent.description}
                                    </p>

                                    <ul className={clsx("space-y-3 mb-8", !isOnline && "opacity-60")}>
                                        {agent.features.map((feature, i) => (
                                            <li key={i} className={clsx("flex items-center gap-3 text-sm", isOnline ? "text-slate-300" : "text-slate-500")}>
                                                {isOnline ? (
                                                    i === 0 ? <ShieldCheck className="w-4 h-4 text-blue-400 shrink-0" /> :
                                                        i === 1 ? <Zap className="w-4 h-4 text-blue-400 shrink-0" /> :
                                                            <Navigation className="w-4 h-4 text-blue-400 shrink-0" />
                                                ) : (
                                                    <div className="w-1.5 h-1.5 rounded-full bg-slate-600 shrink-0" />
                                                )}
                                                <span>{feature}</span>
                                            </li>
                                        ))}
                                    </ul>

                                    <div className={clsx(
                                        "flex items-center font-medium",
                                        isOnline
                                            ? "text-blue-400 group-hover:text-blue-300 transition-colors"
                                            : "text-slate-600 cursor-not-allowed"
                                    )}>
                                        {isOnline ? (
                                            <>进入工作室 <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" /></>
                                        ) : (
                                            '功能研发中，敬请期待...'
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
