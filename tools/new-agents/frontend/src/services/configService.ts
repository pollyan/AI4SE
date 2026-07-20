export type ConfigCheckResult = {
    ok: boolean;
    message: string;
};

const readString = (value: unknown): string | null => (
    typeof value === 'string' && value.trim() ? value.trim() : null
);

export const checkDefaultLlmConfig = async (): Promise<ConfigCheckResult> => {
    try {
        const response = await fetch('/new-agents/api/config/default/check', { method: 'POST' });
        let data: { ok?: unknown; message?: unknown; error?: unknown } = {};
        try {
            data = await response.json();
        } catch {
            data = {};
        }

        const ok = response.ok && data.ok !== false;
        return {
            ok,
            message: readString(data.message)
                || readString(data.error)
                || (ok ? '模型配置可用' : '模型连接检测失败'),
        };
    } catch {
        return { ok: false, message: '模型连接检测失败' };
    }
};
