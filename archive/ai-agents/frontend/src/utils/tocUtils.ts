/**
 * TOC 工具函数
 *
 * 提取自 CompactApp.tsx，提供可独立测试的纯函数。
 */
import type { ArtifactProgress, SubNavItem } from '../../components/ArtifactPanel';

export interface GetActiveArtifactContentParams {
    artifacts: Record<string, string>;
    artifactProgress: ArtifactProgress | null;
    selectedStageId: string | null;
    currentStageId: string | undefined;
    streamingArtifactContent: string | null;
    streamingArtifactKey: string | null;
}

/**
 * 根据当前活动阶段，选取对应的 artifact 内容用于生成 TOC。
 * 
 * 逻辑与 ArtifactPanel 保持一致：
 * - 优先使用 selectedStageId，否则使用 currentStageId
 * - 根据 displayStageId 查找 template 中对应的 artifactKey
 * - 流式内容优先于已存储内容
 */
export function getActiveArtifactContent({
    artifacts,
    artifactProgress,
    selectedStageId,
    currentStageId,
    streamingArtifactContent,
    streamingArtifactKey,
}: GetActiveArtifactContentParams): string {
    if (streamingArtifactContent) {
        return streamingArtifactContent;
    }

    const displayStageId = selectedStageId || currentStageId;
    const template = artifactProgress?.template?.find(
        (t) => t.stageId === displayStageId
    );
    const contentKey = template?.artifactKey || streamingArtifactKey;

    if (contentKey && artifacts[contentKey]) {
        return artifacts[contentKey];
    }

    return '';
}

/**
 * 从 Markdown 内容中解析 TOC（标题列表）。
 * 只保留带数字标号的 h2/h3 标题（如 "1. 风险分析"）。
 */
export function parseTocFromMarkdown(content: string): SubNavItem[] {
    if (!content) return [];

    const headingRegex = /^(#{1,4})\s+(.+)$/gm;
    const items: SubNavItem[] = [];
    let match;

    while ((match = headingRegex.exec(content)) !== null) {
        const level = match[1].length;
        const title = match[2].trim();

        // 只保留带一级标号的标题（如 "1. "）
        const isTopLevelNumbered = /^\d+\.\s/.test(title);
        if (!isTopLevelNumbered) {
            continue;
        }

        const id = title
            .toString()
            .toLowerCase()
            .trim()
            .replace(/\s+/g, '-')
            .replace(/[^\w\u4e00-\u9fa5\-.+]/g, '');

        if (level >= 2 && level <= 3) {
            items.push({
                id,
                title,
                status: 'pending',
            });
        }
    }

    return items;
}
