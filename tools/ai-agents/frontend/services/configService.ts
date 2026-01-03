/**
 * Config API Service
 * API calls for AI model configuration management
 */

const API_BASE = '/ai-agents/api/ai-configs';

export interface AIConfig {
    id: number;
    config_name: string;
    api_key_masked: string;
    base_url: string;
    model_name: string;
    is_default: boolean;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface ConfigStats {
    total_configs: number;
    selected_configs: number;
    current_config_name: string;
}

export interface TestResult {
    test_success: boolean;
    config_name: string;
    model_name: string;
    duration_ms: number;
    ai_response?: string;
    message?: string;
}

// List all configurations
export async function listConfigs(): Promise<AIConfig[]> {
    const response = await fetch(API_BASE);
    if (!response.ok) throw new Error('Failed to load configs');
    const result = await response.json();
    return result.data || [];
}

// Get config stats
export async function getConfigStats(): Promise<ConfigStats> {
    const response = await fetch(`${API_BASE}/stats`);
    if (!response.ok) throw new Error('Failed to load stats');
    const result = await response.json();
    return result.data;
}

// Create new config
export async function createConfig(data: {
    config_name: string;
    api_key: string;
    base_url: string;
    model_name: string;
}): Promise<AIConfig> {
    const response = await fetch(API_BASE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    const result = await response.json();
    if (!response.ok || result.code !== 200) {
        throw new Error(result.message || 'Failed to create config');
    }
    return result.data;
}

// Update config
export async function updateConfig(id: number, data: {
    config_name?: string;
    api_key?: string;
    base_url?: string;
    model_name?: string;
}): Promise<AIConfig> {
    const response = await fetch(`${API_BASE}/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    const result = await response.json();
    if (!response.ok || result.code !== 200) {
        throw new Error(result.message || 'Failed to update config');
    }
    return result.data;
}

// Delete config
export async function deleteConfig(id: number): Promise<void> {
    const response = await fetch(`${API_BASE}/${id}`, {
        method: 'DELETE',
    });
    const result = await response.json();
    if (!response.ok || result.code !== 200) {
        throw new Error(result.message || 'Failed to delete config');
    }
}

// Set config as default
export async function setDefaultConfig(id: number): Promise<void> {
    const response = await fetch(`${API_BASE}/${id}/set-default`, {
        method: 'POST',
    });
    const result = await response.json();
    if (!response.ok || result.code !== 200) {
        throw new Error(result.message || 'Failed to set default config');
    }
}

// Test single config
export async function testConfig(id: number): Promise<TestResult> {
    const response = await fetch(`${API_BASE}/${id}/test`, {
        method: 'POST',
    });
    const result = await response.json();
    return {
        test_success: result.code === 200 && result.data?.test_success,
        ...result.data,
        message: result.message,
    };
}

// Test new config (before saving)
export async function testNewConfig(data: {
    api_key: string;
    base_url: string;
    model_name: string;
}): Promise<TestResult> {
    const response = await fetch(`${API_BASE}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    const result = await response.json();
    return {
        test_success: result.code === 200 && result.data?.test_success,
        ...result.data,
        message: result.message,
    };
}
