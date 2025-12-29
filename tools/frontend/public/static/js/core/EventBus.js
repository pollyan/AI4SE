/**
 * 事件总线
 * 提供组件间解耦的事件通信机制
 */

class EventBus {
    constructor() {
        this.events = new Map();
        this.onceEvents = new Map();
        this.debugMode = false;
        this.eventHistory = [];
        this.maxHistoryLength = 100;
        
        // 预定义的系统事件
        this.SYSTEM_EVENTS = {
            // 组件生命周期
            COMPONENT_CREATED: 'component:created',
            COMPONENT_DESTROYED: 'component:destroyed',
            
            // UI状态变化
            UI_LOADING_START: 'ui:loading:start',
            UI_LOADING_END: 'ui:loading:end',
            UI_ERROR_OCCURRED: 'ui:error:occurred',
            UI_SUCCESS_MESSAGE: 'ui:success:message',
            
            // 测试用例相关
            TESTCASE_SELECTED: 'testcase:selected',
            TESTCASE_UPDATED: 'testcase:updated',
            TESTCASE_STEP_ADDED: 'testcase:step:added',
            TESTCASE_STEP_REMOVED: 'testcase:step:removed',
            
            // 执行相关
            EXECUTION_STARTED: 'execution:started',
            EXECUTION_FINISHED: 'execution:finished',
            EXECUTION_STEP_COMPLETED: 'execution:step:completed',
            
            // 变量相关
            VARIABLE_SELECTED: 'variable:selected',
            VARIABLE_VALIDATED: 'variable:validated',
            VARIABLE_SUGGESTIONS_LOADED: 'variable:suggestions:loaded',
            
            // 表单验证
            FORM_VALIDATION_STARTED: 'form:validation:started',
            FORM_VALIDATION_COMPLETED: 'form:validation:completed',
            FIELD_VALIDATION_ERROR: 'field:validation:error'
        };
    }

    /**
     * 订阅事件
     */
    on(event, callback, context = null) {
        if (typeof callback !== 'function') {
            throw new Error('事件回调必须是一个函数');
        }

        if (!this.events.has(event)) {
            this.events.set(event, new Set());
        }

        const listener = {
            callback,
            context,
            id: this.generateListenerId()
        };

        this.events.get(event).add(listener);

        if (this.debugMode) {
            console.log(`订阅事件: ${event}`, listener.id);
        }

        // 返回取消订阅函数
        return () => this.off(event, listener.id);
    }

    /**
     * 订阅一次性事件
     */
    once(event, callback, context = null) {
        if (typeof callback !== 'function') {
            throw new Error('事件回调必须是一个函数');
        }

        if (!this.onceEvents.has(event)) {
            this.onceEvents.set(event, new Set());
        }

        const listener = {
            callback,
            context,
            id: this.generateListenerId()
        };

        this.onceEvents.get(event).add(listener);

        if (this.debugMode) {
            console.log(`订阅一次性事件: ${event}`, listener.id);
        }

        // 返回取消订阅函数
        return () => {
            const onceListeners = this.onceEvents.get(event);
            if (onceListeners) {
                onceListeners.delete(listener);
            }
        };
    }

    /**
     * 取消事件订阅
     */
    off(event, listenerId = null) {
        if (listenerId) {
            // 取消特定监听器
            const listeners = this.events.get(event);
            if (listeners) {
                for (const listener of listeners) {
                    if (listener.id === listenerId) {
                        listeners.delete(listener);
                        if (this.debugMode) {
                            console.log(`取消订阅: ${event}`, listenerId);
                        }
                        return true;
                    }
                }
            }
        } else {
            // 取消事件的所有监听器
            const removed = this.events.delete(event);
            this.onceEvents.delete(event);
            
            if (this.debugMode && removed) {
                console.log(`取消所有订阅: ${event}`);
            }
            
            return removed;
        }
        
        return false;
    }

    /**
     * 触发事件
     */
    emit(event, ...args) {
        const timestamp = Date.now();
        
        // 记录事件历史
        this.recordEvent(event, args, timestamp);

        if (this.debugMode) {
            console.log(`触发事件: ${event}`, args);
        }

        let listenerCount = 0;

        // 执行普通监听器
        const listeners = this.events.get(event);
        if (listeners) {
            for (const listener of listeners) {
                try {
                    if (listener.context) {
                        listener.callback.apply(listener.context, args);
                    } else {
                        listener.callback(...args);
                    }
                    listenerCount++;
                } catch (error) {
                    console.error(`事件监听器执行失败 (${event}):`, error);
                }
            }
        }

        // 执行一次性监听器
        const onceListeners = this.onceEvents.get(event);
        if (onceListeners) {
            const listenersToRemove = Array.from(onceListeners);
            onceListeners.clear();

            for (const listener of listenersToRemove) {
                try {
                    if (listener.context) {
                        listener.callback.apply(listener.context, args);
                    } else {
                        listener.callback(...args);
                    }
                    listenerCount++;
                } catch (error) {
                    console.error(`一次性事件监听器执行失败 (${event}):`, error);
                }
            }
        }

        return listenerCount;
    }

    /**
     * 批量触发事件
     */
    emitBatch(events) {
        const results = [];
        
        for (const { event, args = [] } of events) {
            const listenerCount = this.emit(event, ...args);
            results.push({ event, listenerCount });
        }
        
        return results;
    }

    /**
     * 延迟触发事件
     */
    emitAsync(event, delay = 0, ...args) {
        return new Promise((resolve) => {
            setTimeout(() => {
                const listenerCount = this.emit(event, ...args);
                resolve(listenerCount);
            }, delay);
        });
    }

    /**
     * 等待事件触发
     */
    waitFor(event, timeout = 5000) {
        return new Promise((resolve, reject) => {
            let timeoutId = null;
            
            const unsubscribe = this.once(event, (...args) => {
                if (timeoutId) {
                    clearTimeout(timeoutId);
                }
                resolve(args);
            });

            if (timeout > 0) {
                timeoutId = setTimeout(() => {
                    unsubscribe();
                    reject(new Error(`等待事件超时: ${event}`));
                }, timeout);
            }
        });
    }

    /**
     * 创建事件命名空间
     */
    namespace(prefix) {
        return {
            on: (event, callback, context) => this.on(`${prefix}:${event}`, callback, context),
            once: (event, callback, context) => this.once(`${prefix}:${event}`, callback, context),
            emit: (event, ...args) => this.emit(`${prefix}:${event}`, ...args),
            off: (event, listenerId) => this.off(`${prefix}:${event}`, listenerId)
        };
    }

    /**
     * 获取事件统计信息
     */
    getStats() {
        const totalListeners = Array.from(this.events.values())
            .reduce((sum, listeners) => sum + listeners.size, 0);
        
        const totalOnceListeners = Array.from(this.onceEvents.values())
            .reduce((sum, listeners) => sum + listeners.size, 0);

        const eventCounts = {};
        for (const [event, listeners] of this.events) {
            eventCounts[event] = listeners.size;
        }

        return {
            totalEvents: this.events.size,
            totalListeners,
            totalOnceListeners,
            eventCounts,
            historyLength: this.eventHistory.length
        };
    }

    /**
     * 获取事件历史
     */
    getEventHistory(limit = 20) {
        return this.eventHistory.slice(-limit);
    }

    /**
     * 清空事件历史
     */
    clearEventHistory() {
        this.eventHistory = [];
    }

    /**
     * 开启/关闭调试模式
     */
    setDebugMode(enabled) {
        this.debugMode = enabled;
        console.log(`事件总线调试模式: ${enabled ? '开启' : '关闭'}`);
    }

    /**
     * 移除所有监听器
     */
    removeAllListeners() {
        this.events.clear();
        this.onceEvents.clear();
        console.log('已清除所有事件监听器');
    }

    /**
     * 记录事件历史
     */
    recordEvent(event, args, timestamp) {
        if (this.eventHistory.length >= this.maxHistoryLength) {
            this.eventHistory.shift();
        }

        this.eventHistory.push({
            event,
            args: args.map(arg => {
                // 简化复杂对象以避免内存问题
                if (typeof arg === 'object' && arg !== null) {
                    return '[Object]';
                }
                return arg;
            }),
            timestamp,
            date: new Date(timestamp).toISOString()
        });
    }

    /**
     * 生成监听器ID
     */
    generateListenerId() {
        return `listener_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * 调试信息
     */
    debug() {
        console.group('EventBus Debug Info');
        console.log('Events:', this.events);
        console.log('Once Events:', this.onceEvents);
        console.log('Stats:', this.getStats());
        console.log('Recent History:', this.getEventHistory(10));
        console.groupEnd();
    }
}

// 创建全局事件总线实例
const eventBus = new EventBus();

// 全局导出
if (typeof window !== 'undefined') {
    window.EventBus = EventBus;
    window.eventBus = eventBus;
    
    // 为了方便使用，也导出系统事件常量
    window.SYSTEM_EVENTS = eventBus.SYSTEM_EVENTS;
}

// CommonJS导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EventBus, eventBus };
}