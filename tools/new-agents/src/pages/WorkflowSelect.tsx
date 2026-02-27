import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FileCode2, TestTube2, ActivitySquare, ArrowLeft, ArrowRight, Bot, Code2, LucideIcon } from 'lucide-react';
import { clsx } from 'clsx';
import { getAgentWorkflows } from '../config/agentWorkflows';
import { getAgentById } from '../config/agents';

export function WorkflowSelect() {
    const navigate = useNavigate();
    const { agentId } = useParams();

    const agent = agentId ? getAgentById(agentId) : undefined;
    const workflows = agentId ? getAgentWorkflows(agentId) : [];

    // If agent is not found or unsupported workflow list
    if (!agent || workflows.length === 0) {
        return (
            <div className="min-h-screen bg-[#0B1120] text-slate-200 flex flex-col items-center justify-center p-6">
                <h1 className="text-2xl font-bold mb-4">该智能体暂不支持工作流配置</h1>
                <button
                    onClick={() => navigate('/')}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors flex items-center gap-2"
                >
                    <ArrowLeft className="w-4 h-4" /> 返回
                </button>
            </div>
        );
    }

    const ICONS: Record<string, LucideIcon> = {
        Bot: Bot,
        Code2: Code2,
        TestTube2: TestTube2,
        ActivitySquare: ActivitySquare,
        FileCode2: FileCode2
    };

    const AgentIcon = ICONS[agent.id === 'lisa' ? 'Bot' : 'Code2'] || Bot;

    return (
        <div className="min-h-screen bg-[#0B1120] text-slate-200 font-sans selection:bg-blue-500/30 selection:text-white relative overflow-hidden flex flex-col items-center pt-24 pb-12 px-6">

            {/* Background decorations */}
            <div className="absolute top-[-20%] left-[20%] w-[60%] h-[60%] bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />

            {/* Nav */}
            <div className="absolute top-6 left-6 z-20">
                <button
                    onClick={() => navigate('/')}
                    className="group px-4 py-2 bg-slate-800/50 hover:bg-slate-700/80 backdrop-blur-sm rounded-xl transition-colors flex items-center gap-2 border border-slate-700/50 hover:border-blue-500/30 text-slate-300 hover:text-white"
                >
                    <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" /> 返回智能体列表
                </button>
            </div>

            <div className="w-full max-w-5xl z-10 flex flex-col items-center">
                <div className="mb-16 text-center">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/20 mb-6 border border-blue-400/20">
                        <AgentIcon className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-4xl font-extrabold text-white tracking-tight mb-4">
                        部署 {agent.name} 工作流
                    </h1>
                    <p className="text-lg text-slate-400 max-w-xl mx-auto">
                        选择相应的端到端研发测试能力矩阵，开启智能化意图测试之旅。
                    </p>
                </div>

                <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-6">
                    {workflows.map((workflow) => {
                        const IconComponent = ICONS[workflow.icon] || FileCode2;
                        const isOnline = workflow.status === 'online';

                        return (
                            <div
                                key={workflow.id}
                                onClick={() => isOnline && workflow.link ? navigate(workflow.link) : undefined}
                                className={clsx(
                                    "group relative rounded-2xl border p-6 sm:p-8 flex flex-col h-full overflow-hidden transition-all duration-300",
                                    isOnline
                                        ? "bg-[#131d31] border-blue-500/30 hover:border-blue-500/70 cursor-pointer hover:shadow-xl hover:shadow-blue-500/20 hover:-translate-y-1"
                                        : "bg-[#0d1624]/60 border-slate-800 opacity-80"
                                )}
                            >
                                {isOnline && (
                                    <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-bl-full blur-2xl pointer-events-none" />
                                )}

                                {!isOnline && workflow.statusLabel && (
                                    <div className="absolute top-4 right-4 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-slate-800 text-slate-500 uppercase">
                                        {workflow.statusLabel}
                                    </div>
                                )}

                                <div className={clsx(
                                    "w-12 h-12 flex items-center justify-center rounded-xl mb-6",
                                    isOnline
                                        ? "bg-blue-500/20 text-blue-400 border border-blue-500/30 group-hover:bg-blue-500 group-hover:text-white transition-colors"
                                        : "bg-slate-800 text-slate-500"
                                )}>
                                    <IconComponent className="w-6 h-6" />
                                </div>

                                <h2 className={clsx("text-xl font-bold mb-3", isOnline ? "text-white" : "text-slate-300 grayscale")}>
                                    {workflow.name}
                                </h2>
                                <p className={clsx("text-sm mb-6 flex-1 min-h-[40px]", isOnline ? "text-slate-400" : "text-slate-500")}>
                                    {workflow.description}
                                </p>

                                <div className={clsx(
                                    "flex items-center text-sm font-medium mt-auto",
                                    isOnline
                                        ? "text-blue-400 group-hover:text-blue-300"
                                        : "text-slate-600 cursor-not-allowed"
                                )}>
                                    {isOnline ? (
                                        <>立即采用该工作流 <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" /></>
                                    ) : (
                                        workflow.status === 'dev' ? '功能孵化中' : '下一期规划'
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
