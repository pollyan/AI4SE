import { sanitizeMermaidCode } from '../core/utils/mermaidSanitizer';

type MermaidRepairResponse = {
    repairedCode: string;
};

type MermaidRepairArtifactContext = {
    workflowId: string;
    stageId: string;
    currentArtifact: string;
};

type MermaidRepairRequestPayload = {
    brokenCode: string;
    errorMessage: string;
    blockIndex?: number;
    workflowId?: string;
    stageId?: string;
    currentArtifact?: string;
};

function isMermaidRepairResponse(value: unknown): value is MermaidRepairResponse {
    return (
        typeof value === 'object'
        && value !== null
        && 'repairedCode' in value
        && typeof value.repairedCode === 'string'
    );
}

async function validateRepairedMermaidCode(code: string): Promise<string | null> {
    const sanitized = sanitizeMermaidCode(code.trim());
    if (!sanitized.trim()) return null;

    const { default: mermaid } = await import('mermaid');
    const parseResult = await mermaid.parse(
        sanitized,
        { suppressErrors: false },
    );
    if ((parseResult as unknown) === false) return null;
    return sanitized;
}

/**
 * 修正因解析失败而出错的 Mermaid 图表代码
 *
 * @param brokenCode 出错的 Mermaid 代码
 * @param errorMessage Mermaid 抛出的错误信息
 * @param blockIndex 当前图表在所有图表中的索引顺序（用于上下文反馈，可选）
 * @returns {Promise<string | null>} 返回修正后的纯 Mermaid 代码，若网络请求失败等则返回 null
 */
export async function retryMermaidGeneration(
    brokenCode: string,
    errorMessage: string,
    blockIndex?: number,
    artifactContext?: MermaidRepairArtifactContext
): Promise<string | null> {
    try {
        const requestBody: MermaidRepairRequestPayload = {
            brokenCode,
            errorMessage,
            blockIndex,
        };
        if (artifactContext) {
            requestBody.workflowId = artifactContext.workflowId;
            requestBody.stageId = artifactContext.stageId;
            requestBody.currentArtifact = artifactContext.currentArtifact;
        }

        const response = await fetch('/new-agents/api/utils/mermaid/repair', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
            const payload = await response.json().catch(() => ({}));
            const message = (
                typeof payload === 'object'
                && payload !== null
                && 'error' in payload
                && typeof payload.error === 'string'
            )
                ? payload.error
                : 'Mermaid repair request failed';
            throw new Error(message);
        }

        const payload: unknown = await response.json();
        if (!isMermaidRepairResponse(payload)) {
            throw new Error('Invalid Mermaid repair response');
        }

        return await validateRepairedMermaidCode(payload.repairedCode);
    } catch {
        return null;
    }
}
