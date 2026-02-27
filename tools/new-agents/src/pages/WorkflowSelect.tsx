import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FileCode2, TestTube2, ActivitySquare, ArrowLeft, ArrowRight, Bot } from 'lucide-react';
import { clsx } from 'clsx';

export function WorkflowSelect() {
    const navigate = useNavigate();
    const { agentId } = useParams();

    // If agentId is not lisa, redirect back or handle it.
    if (agentId !== 'lisa') {
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
                        <Bot className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-4xl font-extrabold text-white tracking-tight mb-4">
                        部署 Lisa 工作流
                    </h1>
                    <p className="text-lg text-slate-400 max-w-xl mx-auto">
                        选择相应的端到端研发测试能力矩阵，开启智能化意图测试之旅。
                    </p>
                </div>

                <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-6">

                    {/* Active Workflow - 测试设计 */}
                    <div
                        onClick={() => navigate('/workspace/lisa/test-design')}
                        className="group relative bg-[#131d31] rounded-2xl border border-blue-500/30 hover:border-blue-500/70 p-6 sm:p-8 cursor-pointer overflow-hidden transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/20 hover:-translate-y-1 flex flex-col h-full"
                    >
                        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-bl-full blur-2xl pointer-events-none" />

                        <div className="w-12 h-12 flex items-center justify-center rounded-xl bg-blue-500/20 text-blue-400 border border-blue-500/30 mb-6 group-hover:bg-blue-500 group-hover:text-white transition-colors">
                            <TestTube2 className="w-6 h-6" />
                        </div>

                        <h2 className="text-xl font-bold text-white mb-3">自动化测试设计</h2>
                        <p className="text-sm text-slate-400 mb-6 flex-1 min-h-[40px]">
                            输入产品需求，从需求解析到测试步骤生成、UI节点识别，一站式设计意图测试用例。
                        </p>

                        <div className="flex items-center text-sm font-medium text-blue-400 group-hover:text-blue-300 mt-auto">
                            立即采用该工作流 <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                        </div>
                    </div>

                    {/* Disabled Workflow 1 */}
                    <div className="relative bg-[#0d1624]/60 rounded-2xl border border-slate-800 p-6 sm:p-8 overflow-hidden opacity-80 flex flex-col h-full">
                        <div className="absolute top-4 right-4 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-slate-800 text-slate-500 uppercase">
                            Dev
                        </div>
                        <div className="w-12 h-12 flex items-center justify-center rounded-xl bg-slate-800 text-slate-500 mb-6">
                            <ActivitySquare className="w-6 h-6" />
                        </div>

                        <h2 className="text-xl font-bold text-slate-300 mb-3 grayscale">执行日志诊断</h2>
                        <p className="text-sm text-slate-500 mb-6 flex-1 min-h-[40px]">
                            导入 MidScene 录制的运行日志、截图及错误报告，智能定位元素变更和代码故障点。
                        </p>

                        <div className="flex items-center text-sm font-medium text-slate-600 mt-auto cursor-not-allowed">
                            功能孵化中
                        </div>
                    </div>

                    {/* Disabled Workflow 2 */}
                    <div className="relative bg-[#0d1624]/60 rounded-2xl border border-slate-800 p-6 sm:p-8 overflow-hidden opacity-80 flex flex-col h-full">
                        <div className="absolute top-4 right-4 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-slate-800 text-slate-500 uppercase">
                            Plan
                        </div>
                        <div className="w-12 h-12 flex items-center justify-center rounded-xl bg-slate-800 text-slate-500 mb-6">
                            <FileCode2 className="w-6 h-6" />
                        </div>

                        <h2 className="text-xl font-bold text-slate-300 mb-3 grayscale">智能断言生成</h2>
                        <p className="text-sm text-slate-500 mb-6 flex-1 min-h-[40px]">
                            结合上下文语境与页面 DOM 结构，自动预测并生成可执行的 AI 意图校验断言语句。
                        </p>

                        <div className="flex items-center text-sm font-medium text-slate-600 mt-auto cursor-not-allowed">
                            下一期规划
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}
