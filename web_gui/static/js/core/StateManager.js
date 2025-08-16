/**
 * 前端状态管理器
 * 提供全局状态管理和组件间通信能力
 */

class StateManager {
    constructor() {
        this.state = {};
        this.listeners = new Map();
        this.middleware = [];
        this.history = [];
        this.maxHistoryLength = 50;
        
        // 初始化默认状态
        this.initializeDefaultState();
    }

    /**
     * 初始化默认状态
     */
    initializeDefaultState() {
        this.state = {
            // 用户会话信息
            session: {
                userId: null,
                isAuthenticated: false,
                preferences: {}
            },
            
            // 当前测试用例和执行上下文
            currentContext: {
                testCaseId: null,
                executionId: null,
                stepIndex: null
            },
            
            // UI状态
            ui: {
                loading: false,
                error: null,
                success: null,
                modal: {
                    isOpen: false,
                    type: null,
                    data: null
                }
            },
            
            // 变量相关状态
            variables: {
                available: [],
                suggestions: [],
                validationCache: new Map()
            },
            
            // 组件状态
            components: {
                activeInstances: new Set(),
                pendingValidations: new Set()
            }
        };
        
        console.log('状态管理器初始化完成');
    }

    /**
     * 获取状态
     */
    getState(path = null) {
        if (!path) {
            return this.state;
        }
        
        return this.getNestedValue(this.state, path);
    }

    /**
     * 设置状态
     */
    setState(path, value, options = {}) {
        const { silent = false, merge = false } = options;
        const oldState = { ...this.state };
        
        // 记录历史
        if (this.history.length >= this.maxHistoryLength) {
            this.history.shift();
        }
        this.history.push({
            timestamp: Date.now(),
            path,
            oldValue: this.getNestedValue(oldState, path),
            newValue: value
        });

        // 应用中间件
        for (const middleware of this.middleware) {
            const result = middleware(path, value, oldState);
            if (result === false) {
                console.warn('状态更新被中间件阻止:', path);
                return false;
            }
            if (typeof result === 'object' && result !== null) {
                value = result;
            }
        }

        // 更新状态
        if (merge && typeof value === 'object' && value !== null) {
            const existingValue = this.getNestedValue(this.state, path);
            if (typeof existingValue === 'object' && existingValue !== null) {
                value = { ...existingValue, ...value };
            }
        }

        this.setNestedValue(this.state, path, value);

        // 触发监听器
        if (!silent) {
            this.notifyListeners(path, value, oldState);
        }

        return true;
    }

    /**
     * 监听状态变化
     */
    subscribe(path, callback) {
        const listenerId = `${path}_${Date.now()}_${Math.random()}`;
        
        if (!this.listeners.has(path)) {
            this.listeners.set(path, new Map());
        }
        
        this.listeners.get(path).set(listenerId, callback);
        
        // 返回取消订阅函数
        return () => {
            const pathListeners = this.listeners.get(path);
            if (pathListeners) {
                pathListeners.delete(listenerId);
                if (pathListeners.size === 0) {
                    this.listeners.delete(path);
                }
            }
        };
    }

    /**
     * 批量更新状态
     */
    batchUpdate(updates, options = {}) {
        const { silent = false } = options;
        const oldState = { ...this.state };
        
        // 应用所有更新
        const changes = [];
        for (const [path, value] of Object.entries(updates)) {
            const oldValue = this.getNestedValue(this.state, path);
            this.setNestedValue(this.state, path, value);
            changes.push({ path, value, oldValue });
        }

        // 记录历史
        this.history.push({
            timestamp: Date.now(),
            batch: true,
            changes
        });

        // 批量通知监听器
        if (!silent) {
            for (const { path, value } of changes) {
                this.notifyListeners(path, value, oldState);
            }
        }
    }

    /**
     * 添加中间件
     */
    addMiddleware(middleware) {
        if (typeof middleware !== 'function') {
            throw new Error('中间件必须是一个函数');
        }
        
        this.middleware.push(middleware);
    }

    /**
     * 移除中间件
     */
    removeMiddleware(middleware) {
        const index = this.middleware.indexOf(middleware);
        if (index > -1) {
            this.middleware.splice(index, 1);
        }
    }

    /**
     * 重置状态
     */
    reset(path = null) {
        if (path) {
            this.setNestedValue(this.state, path, this.getDefaultValue(path));
        } else {
            this.initializeDefaultState();
        }
        
        console.log('状态已重置:', path || 'all');
    }

    /**
     * 获取状态历史
     */
    getHistory(limit = 10) {
        return this.history.slice(-limit);
    }

    /**
     * 清空历史记录
     */
    clearHistory() {
        this.history = [];
    }

    /**
     * 通知监听器
     */
    notifyListeners(path, value, oldState) {
        // 精确路径匹配
        const exactListeners = this.listeners.get(path);
        if (exactListeners) {
            for (const callback of exactListeners.values()) {
                try {
                    callback(value, this.getNestedValue(oldState, path), path);
                } catch (error) {
                    console.error('状态监听器执行失败:', error);
                }
            }
        }

        // 通配符匹配（如果路径包含父级监听器）
        for (const [listenerPath, listeners] of this.listeners) {
            if (listenerPath !== path && (path.startsWith(listenerPath + '.') || listenerPath === '*')) {
                for (const callback of listeners.values()) {
                    try {
                        callback(value, this.getNestedValue(oldState, path), path);
                    } catch (error) {
                        console.error('状态监听器执行失败:', error);
                    }
                }
            }
        }
    }

    /**
     * 获取嵌套值
     */
    getNestedValue(obj, path) {
        const keys = path.split('.');
        let current = obj;
        
        for (const key of keys) {
            if (current === null || current === undefined) {
                return undefined;
            }
            current = current[key];
        }
        
        return current;
    }

    /**
     * 设置嵌套值
     */
    setNestedValue(obj, path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        let current = obj;
        
        // 创建嵌套对象路径
        for (const key of keys) {
            if (!(key in current) || typeof current[key] !== 'object') {
                current[key] = {};
            }
            current = current[key];
        }
        
        current[lastKey] = value;
    }

    /**
     * 获取默认值
     */
    getDefaultValue(path) {
        // 可以根据路径返回相应的默认值
        const defaults = {
            'ui.loading': false,
            'ui.error': null,
            'ui.success': null,
            'currentContext.testCaseId': null,
            'currentContext.executionId': null,
            'currentContext.stepIndex': null,
            'variables.available': [],
            'variables.suggestions': []
        };
        
        return defaults[path];
    }

    /**
     * 调试信息
     */
    debug() {
        console.group('StateManager Debug Info');
        console.log('Current State:', this.state);
        console.log('Listeners:', this.listeners);
        console.log('History:', this.history);
        console.log('Middleware:', this.middleware);
        console.groupEnd();
    }
}

// 创建全局状态管理器实例
const stateManager = new StateManager();

// 添加一些有用的中间件
stateManager.addMiddleware((path, value, oldState) => {
    // 日志中间件
    if (path.includes('debug')) {
        console.log(`状态更新: ${path}`, value);
    }
    return value;
});

// 全局导出
if (typeof window !== 'undefined') {
    window.StateManager = StateManager;
    window.stateManager = stateManager;
}

// CommonJS导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { StateManager, stateManager };
}