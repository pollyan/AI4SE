import React, { useState, useRef, useEffect } from 'react';
import { useStore, WORKFLOWS, WorkflowType } from '../store';
import { useNavigate, useParams } from 'react-router-dom';
import { ChevronDown, Check, AlertTriangle, Workflow } from 'lucide-react';
import { clsx } from 'clsx';

/** WorkflowType → URL slug 的映射 */
const WORKFLOW_SLUG_MAP: Record<WorkflowType, string> = {
    TEST_DESIGN: 'test-design',
    REQ_REVIEW: 'req-review',
};

export const WorkflowDropdown: React.FC = () => {
    const { workflow, setWorkflow } = useStore();
    const [isOpen, setIsOpen] = useState(false);
    const [showConfirm, setShowConfirm] = useState<WorkflowType | null>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const navigate = useNavigate();
    const { agentId } = useParams();

    const currentWorkflow = WORKFLOWS[workflow];

    // Handle click outside to close
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        } else {
            document.removeEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen]);

    const handleSelect = (wfId: WorkflowType) => {
        if (wfId === workflow) {
            setIsOpen(false);
            return;
        }
        setShowConfirm(wfId);
    };

    const confirmSwitch = () => {
        if (showConfirm) {
            setWorkflow(showConfirm);
            setIsOpen(false);
            setShowConfirm(null);
            // 同步导航到新工作流的 URL，确保 URL 与 store 状态一致
            const slug = WORKFLOW_SLUG_MAP[showConfirm];
            navigate(`/workspace/${agentId}/${slug}`, { replace: true });
        }
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={clsx(
                    "flex flex-col text-left group rounded-md -mx-2 px-2 py-1 transition-colors",
                    isOpen ? "bg-slate-800/60" : "hover:bg-slate-800/40"
                )}
            >
                <span className="text-[11px] font-medium text-slate-500 uppercase tracking-widest leading-none">Lisa AI 专家</span>
                <div className="flex items-center gap-1.5 mt-1">
                    <span className="text-[15px] font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors">
                        {currentWorkflow?.name || '选择工作流'}
                    </span>
                    <div className="bg-slate-800 group-hover:bg-indigo-500/20 rounded p-0.5 transition-colors">
                        <ChevronDown className={clsx(
                            "w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-400 transition-transform duration-200",
                            isOpen && "rotate-180"
                        )} />
                    </div>
                </div>
            </button>

            {/* Dropdown Menu */}
            <div className={clsx(
                "absolute left-0 top-full mt-2 w-72 bg-[#161923] border border-slate-700/80 rounded-xl shadow-2xl overflow-hidden transform transition-all duration-200 z-50",
                isOpen ? "opacity-100 translate-y-0 pointer-events-auto" : "opacity-0 -translate-y-2 pointer-events-none"
            )}>
                <div className="p-3 border-b border-slate-700/60 bg-slate-800/30">
                    <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">切换工作流</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">选择不同的测试专家流水线</p>
                </div>

                <div className="p-1.5 space-y-0.5">
                    {Object.values(WORKFLOWS).map((wf) => {
                        const isSelected = wf.id === workflow;
                        return (
                            <button
                                key={wf.id}
                                onClick={() => handleSelect(wf.id as WorkflowType)}
                                className={clsx(
                                    "w-full text-left px-3 py-2.5 rounded-lg flex items-start gap-3 transition-colors group relative overflow-hidden",
                                    isSelected
                                        ? "bg-indigo-500/15 border border-indigo-500/30 text-white"
                                        : "hover:bg-slate-800/80 text-slate-300"
                                )}
                            >
                                {isSelected && (
                                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-indigo-500 rounded-l-lg"></div>
                                )}

                                <div className={clsx(
                                    "mt-0.5 p-1.5 rounded-md transition-colors",
                                    isSelected
                                        ? "bg-indigo-500/20 text-indigo-400"
                                        : "bg-slate-800 text-slate-400 group-hover:text-white group-hover:bg-slate-700 ring-1 ring-slate-700/50"
                                )}>
                                    <Workflow className="w-4 h-4" />
                                </div>
                                <div className="flex-1">
                                    <div className={clsx(
                                        "font-medium text-[13px] flex justify-between items-center transition-colors",
                                        isSelected ? "text-indigo-100" : "group-hover:text-white"
                                    )}>
                                        {wf.name}
                                        {isSelected && <Check className="w-3.5 h-3.5 text-indigo-400" />}
                                    </div>
                                    <div className={clsx(
                                        "text-[11px] mt-0.5 leading-snug",
                                        isSelected ? "text-indigo-300/70" : "text-slate-500 group-hover:text-slate-400"
                                    )}>
                                        {wf.id === 'TEST_DESIGN'
                                            ? '对传入需求进行逻辑拆解与边界梳理'
                                            : '分析需求完整性并评估测试风险'}
                                    </div>
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Confirm Switch Modal */}
            {showConfirm && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
                    <div className="flex w-full max-w-sm flex-col overflow-hidden rounded-xl bg-[#151f2b] shadow-2xl ring-1 ring-white/10 p-6">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-yellow-500/10 text-yellow-500">
                                <AlertTriangle className="w-6 h-6" />
                            </div>
                            <h3 className="text-lg font-bold text-white">切换工作流</h3>
                        </div>
                        <p className="text-sm text-slate-300 mb-6">
                            切换工作流将清空当前的对话历史和产出物文档，确定要继续吗？
                        </p>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => setShowConfirm(null)}
                                className="rounded-lg px-4 py-2 text-sm font-medium text-slate-300 hover:bg-white/5 transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={confirmSwitch}
                                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-500 transition-colors shadow-md shadow-indigo-500/20"
                            >
                                确定切换
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
