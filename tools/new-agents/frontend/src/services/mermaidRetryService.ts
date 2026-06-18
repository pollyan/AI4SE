type MermaidRepairResponse = {
    repairedCode: string;
};

function isMermaidRepairResponse(value: unknown): value is MermaidRepairResponse {
    return (
        typeof value === 'object'
        && value !== null
        && 'repairedCode' in value
        && typeof value.repairedCode === 'string'
    );
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
    blockIndex?: number
): Promise<string | null> {
    try {
        const response = await fetch('/new-agents/api/utils/mermaid/repair', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                brokenCode,
                errorMessage,
                blockIndex,
            }),
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

        return payload.repairedCode.trim();
    } catch {
        return null;
    }
}
