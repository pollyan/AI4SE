import { useEffect, useMemo, useState } from 'react';
import type {
    StoryHandoffCandidate,
    StoryHandoffPacket,
    StoryHandoffPacketListItem,
} from '../core/types';
import {
    createStoryHandoffPacket,
    fetchStoryHandoffCandidates,
    fetchStoryHandoffPackets,
} from '../services/storyHandoffPacketService';

type StoryHandoffPacketPanelProps = {
    runId: string;
    stageId: string;
};

export const StoryHandoffPacketPanel = ({
    runId,
    stageId,
}: StoryHandoffPacketPanelProps) => {
    const [candidates, setCandidates] = useState<StoryHandoffCandidate[]>([]);
    const [packets, setPackets] = useState<StoryHandoffPacketListItem[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [creatingStoryId, setCreatingStoryId] = useState<string | null>(null);
    const [copiedStoryId, setCopiedStoryId] = useState<string | null>(null);
    const packetByStoryId = useMemo(
        () => new Map(packets.map(packet => [packet.storyId, packet])),
        [packets],
    );

    useEffect(() => {
        let cancelled = false;
        setIsLoading(true);
        setError(null);
        Promise.all([
            fetchStoryHandoffCandidates(runId, stageId),
            fetchStoryHandoffPackets(runId, stageId),
        ])
            .then(([candidateResponse, packetResponse]) => {
                if (cancelled) return;
                setCandidates(candidateResponse.candidates);
                setPackets(packetResponse.packets);
            })
            .catch((loadError: unknown) => {
                if (cancelled) return;
                const message = loadError instanceof Error ? loadError.message : '未知错误';
                setCandidates([]);
                setPackets([]);
                setError(`单故事需求包加载失败：${message}`);
            })
            .finally(() => {
                if (!cancelled) setIsLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, [runId, stageId]);

    const refreshPackets = async () => {
        const response = await fetchStoryHandoffPackets(runId, stageId);
        setPackets(response.packets);
    };

    const handleCreate = async (storyId: string) => {
        setCreatingStoryId(storyId);
        setError(null);
        try {
            await createStoryHandoffPacket(runId, stageId, storyId);
            await refreshPackets();
        } catch (createError) {
            const message = createError instanceof Error ? createError.message : '未知错误';
            setError(`单故事需求包生成失败：${message}`);
        } finally {
            setCreatingStoryId(null);
        }
    };

    const handleCopy = async (storyId: string, packet: StoryHandoffPacket) => {
        setError(null);
        if (!navigator.clipboard?.writeText) {
            setError('当前浏览器不支持复制单故事需求包。');
            return;
        }
        try {
            await navigator.clipboard.writeText(JSON.stringify(packet, null, 2));
            setCopiedStoryId(storyId);
        } catch (copyError) {
            const message = copyError instanceof Error ? copyError.message : '未知错误';
            setError(`单故事需求包复制失败：${message}`);
        }
    };

    return (
        <section
            className="mx-auto mb-5 max-w-4xl rounded-lg border border-[#1e293b] bg-[#0f172a] p-4 shadow-xl"
            aria-label="单故事需求包"
        >
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h3 className="text-sm font-semibold text-slate-100">单故事需求包</h3>
                    <p className="mt-1 text-xs leading-relaxed text-slate-500">
                        从当前 ready story 生成可复制的 AI Coding 需求输入。
                    </p>
                </div>
                {isLoading && (
                    <span className="rounded-md border border-sky-400/20 bg-sky-400/10 px-2 py-1 text-[11px] font-semibold text-sky-100">
                        加载中
                    </span>
                )}
            </div>
            {error && (
                <div className="mt-3 rounded-md border border-red-400/20 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-100">
                    {error}
                </div>
            )}
            {!isLoading && !error && candidates.length === 0 && (
                <p className="mt-3 text-xs text-slate-500">
                    当前阶段还没有可生成需求包的 ready story。
                </p>
            )}
            {candidates.length > 0 && (
                <div className="mt-3 space-y-2">
                    {candidates.map((candidate) => {
                        const packet = packetByStoryId.get(candidate.storyId);
                        const isCreating = creatingStoryId === candidate.storyId;
                        return (
                            <div
                                key={candidate.storyId}
                                className="rounded-md border border-[#1e293b] bg-[#020617] px-3 py-3"
                            >
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                    <div className="min-w-0 flex-1">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className="text-xs font-bold text-blue-200">{candidate.storyId}</span>
                                            {packet && (
                                                <span className="rounded-md border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-100">
                                                    {candidate.storyId} · v{packet.packet.sourceArtifactVersion}
                                                </span>
                                            )}
                                            <span className="text-sm font-semibold text-slate-100">{candidate.title}</span>
                                        </div>
                                        <p className="mt-1 text-xs leading-relaxed text-slate-400">
                                            {candidate.userValue}
                                        </p>
                                        <p className="mt-1 text-[11px] text-slate-500">
                                            {candidate.readyReason}
                                        </p>
                                        {packet?.isStale && (
                                            <p className="mt-2 text-[11px] font-medium text-amber-200">
                                                该需求包可能基于旧版需求，请重新生成后再交给 AI Coding。
                                            </p>
                                        )}
                                        {copiedStoryId === candidate.storyId && (
                                            <p className="mt-2 text-[11px] font-semibold text-emerald-200">
                                                已复制 {candidate.storyId}
                                            </p>
                                        )}
                                    </div>
                                    <div className="flex shrink-0 items-center gap-2">
                                        {packet ? (
                                            <button
                                                type="button"
                                                onClick={() => handleCopy(candidate.storyId, packet.packet)}
                                                className="rounded-md border border-emerald-400/20 px-3 py-1.5 text-xs font-semibold text-emerald-100 transition-colors hover:bg-emerald-400/10"
                                            >
                                                复制 {candidate.storyId} 需求包
                                            </button>
                                        ) : (
                                            <button
                                                type="button"
                                                onClick={() => handleCreate(candidate.storyId)}
                                                disabled={isCreating}
                                                className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-bold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                                            >
                                                {isCreating ? `生成 ${candidate.storyId} 中` : `生成 ${candidate.storyId} 需求包`}
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </section>
    );
};
