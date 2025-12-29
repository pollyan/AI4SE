/**
 * 应用程序核心
 * 统一管理前端应用的初始化、配置和生命周期
 */

class ApplicationCore {
    constructor() {
        this.version = '1.0.0';
        this.initialized = false;
        this.modules = new Map();
        this.config = {};
        
        // 核心服务实例
        this.stateManager = null;
        this.eventBus = null;
        this.componentFactory = null;
        
        // 应用状态
        this.status = 'idle'; // idle, initializing, ready, error
        this.errors = [];
        this.startTime = null;
    }

    /**
     * 初始化应用程序
     */
    async initialize(config = {}) {
        if (this.initialized) {
            console.warn('应用程序已经初始化');
            return this;
        }

        this.startTime = Date.now();
        this.status = 'initializing';
        this.config = { ...this.getDefaultConfig(), ...config };

        console.log(`初始化Intent Test Framework v${this.version}...`);

        try {
            // 初始化核心服务
            await this.initializeCoreServices();
            
            // 加载和初始化模块
            await this.initializeModules();
            
            // 自动发现并初始化组件
            await this.autoDiscoverComponents();
            
            // 绑定全局事件
            this.bindGlobalEvents();
            
            // 设置错误处理
            this.setupErrorHandling();

            this.initialized = true;
            this.status = 'ready';
            
            const initTime = Date.now() - this.startTime;
            console.log(`应用程序初始化完成 (${initTime}ms)`);
            
            // 触发初始化完成事件
            this.eventBus?.emit('app:initialized', { 
                initTime, 
                modules: Array.from(this.modules.keys())
            });

        } catch (error) {
            this.status = 'error';
            this.errors.push(error);
            console.error('应用程序初始化失败:', error);
            throw error;
        }

        return this;
    }

    /**
     * 初始化核心服务
     */
    async initializeCoreServices() {
        // 初始化状态管理器
        if (typeof StateManager !== 'undefined') {
            this.stateManager = window.stateManager || new StateManager();
            console.log('状态管理器已初始化');
        }

        // 初始化事件总线
        if (typeof EventBus !== 'undefined') {
            this.eventBus = window.eventBus || new EventBus();
            if (this.config.debug) {
                this.eventBus.setDebugMode(true);
            }
            console.log('事件总线已初始化');
        }

        // 初始化组件工厂
        if (typeof ComponentFactory !== 'undefined') {
            this.componentFactory = window.componentFactory || new ComponentFactory();
            console.log('组件工厂已初始化');
        }
    }

    /**
     * 初始化模块
     */
    async initializeModules() {
        const modulePromises = [];

        // 根据配置加载模块
        for (const [moduleName, moduleConfig] of Object.entries(this.config.modules)) {
            if (moduleConfig.enabled !== false) {
                modulePromises.push(this.loadModule(moduleName, moduleConfig));
            }
        }

        const results = await Promise.allSettled(modulePromises);
        
        // 检查模块加载结果
        results.forEach((result, index) => {
            const moduleName = Object.keys(this.config.modules)[index];
            if (result.status === 'rejected') {
                console.error(`模块加载失败: ${moduleName}`, result.reason);
                this.errors.push(result.reason);
            }
        });
    }

    /**
     * 加载单个模块
     */
    async loadModule(name, config) {
        try {
            // 尝试从全局作用域获取模块
            const moduleClass = window[config.className || name];
            
            if (!moduleClass) {
                throw new Error(`未找到模块类: ${config.className || name}`);
            }

            const instance = new moduleClass(config.options || {});
            
            // 如果模块有初始化方法，调用它
            if (typeof instance.initialize === 'function') {
                await instance.initialize();
            }

            this.modules.set(name, instance);
            console.log(`模块加载成功: ${name}`);
            
            return instance;
            
        } catch (error) {
            console.error(`加载模块失败 ${name}:`, error);
            throw error;
        }
    }

    /**
     * 自动发现组件
     */
    async autoDiscoverComponents() {
        if (this.componentFactory && this.config.autoDiscoverComponents) {
            try {
                const discoveredComponents = this.componentFactory.autoDiscoverComponents();
                console.log(`自动发现了 ${discoveredComponents.length} 个组件`);
                
                // 更新状态
                if (this.stateManager) {
                    this.stateManager.setState('components.activeInstances', 
                        new Set(discoveredComponents.map(c => c._instanceId)));
                }
                
            } catch (error) {
                console.error('自动发现组件失败:', error);
                this.errors.push(error);
            }
        }
    }

    /**
     * 绑定全局事件
     */
    bindGlobalEvents() {
        if (!this.eventBus) return;

        // 监听未捕获的错误
        window.addEventListener('error', (event) => {
            const error = {
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                error: event.error
            };
            
            this.eventBus.emit('app:error:uncaught', error);
            this.errors.push(error);
        });

        // 监听未处理的Promise拒绝
        window.addEventListener('unhandledrejection', (event) => {
            const error = {
                reason: event.reason,
                promise: event.promise
            };
            
            this.eventBus.emit('app:error:unhandled-promise', error);
            this.errors.push(error);
        });

        // 监听页面卸载
        window.addEventListener('beforeunload', () => {
            this.eventBus.emit('app:before-unload');
        });

        // 监听页面可见性变化
        document.addEventListener('visibilitychange', () => {
            const isVisible = !document.hidden;
            this.eventBus.emit('app:visibility-change', { isVisible });
            
            if (this.stateManager) {
                this.stateManager.setState('ui.isVisible', isVisible);
            }
        });
    }

    /**
     * 设置错误处理
     */
    setupErrorHandling() {
        if (!this.eventBus) return;

        this.eventBus.on('app:error:uncaught', (error) => {
            console.error('未捕获的错误:', error);
            this.handleError(error, 'uncaught');
        });

        this.eventBus.on('app:error:unhandled-promise', (error) => {
            console.error('未处理的Promise拒绝:', error);
            this.handleError(error, 'promise');
        });
    }

    /**
     * 错误处理
     */
    handleError(error, type = 'unknown') {
        // 更新状态
        if (this.stateManager) {
            this.stateManager.setState('ui.error', {
                message: error.message || error.reason || '未知错误',
                type,
                timestamp: Date.now()
            });
        }

        // 如果配置了错误报告，发送到服务器
        if (this.config.errorReporting?.enabled) {
            this.reportError(error, type);
        }
    }

    /**
     * 报告错误到服务器
     */
    async reportError(error, type) {
        try {
            const errorData = {
                message: error.message || error.reason,
                type,
                stack: error.stack,
                url: window.location.href,
                userAgent: navigator.userAgent,
                timestamp: new Date().toISOString(),
                version: this.version
            };

            await fetch('/api/errors', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(errorData)
            });
            
        } catch (reportError) {
            console.error('错误报告发送失败:', reportError);
        }
    }

    /**
     * 获取默认配置
     */
    getDefaultConfig() {
        return {
            debug: false,
            autoDiscoverComponents: true,
            errorReporting: {
                enabled: false,
                endpoint: '/api/errors'
            },
            modules: {
                'VariableContextService': {
                    enabled: true,
                    className: 'VariableContextService'
                },
                'VariableValidation': {
                    enabled: true,
                    className: 'VariableValidation'
                }
            }
        };
    }

    /**
     * 获取模块实例
     */
    getModule(name) {
        return this.modules.get(name);
    }

    /**
     * 获取应用状态
     */
    getStatus() {
        return {
            status: this.status,
            initialized: this.initialized,
            version: this.version,
            uptime: this.startTime ? Date.now() - this.startTime : 0,
            errors: this.errors.length,
            modules: Array.from(this.modules.keys())
        };
    }

    /**
     * 获取统计信息
     */
    getStats() {
        const stats = {
            app: this.getStatus(),
            state: this.stateManager?.getState() || null,
            events: this.eventBus?.getStats() || null,
            components: this.componentFactory?.getStats() || null
        };

        return stats;
    }

    /**
     * 销毁应用程序
     */
    async destroy() {
        console.log('正在销毁应用程序...');

        // 触发销毁事件
        this.eventBus?.emit('app:before-destroy');

        // 销毁所有组件
        if (this.componentFactory) {
            this.componentFactory.destroyAll();
        }

        // 销毁模块
        for (const [name, module] of this.modules) {
            if (typeof module.destroy === 'function') {
                try {
                    await module.destroy();
                    console.log(`模块已销毁: ${name}`);
                } catch (error) {
                    console.error(`销毁模块失败 ${name}:`, error);
                }
            }
        }

        // 清理事件总线
        if (this.eventBus) {
            this.eventBus.removeAllListeners();
        }

        // 重置状态
        this.initialized = false;
        this.status = 'idle';
        this.modules.clear();

        console.log('应用程序已销毁');
    }

    /**
     * 调试信息
     */
    debug() {
        console.group('Application Debug Info');
        console.log('Status:', this.getStatus());
        console.log('Config:', this.config);
        console.log('Modules:', this.modules);
        console.log('Errors:', this.errors);
        
        if (this.stateManager) {
            console.log('State:', this.stateManager.getState());
        }
        
        if (this.eventBus) {
            console.log('Events:', this.eventBus.getStats());
        }
        
        if (this.componentFactory) {
            console.log('Components:', this.componentFactory.getStats());
        }
        
        console.groupEnd();
    }
}

// 创建全局应用实例
const app = new ApplicationCore();

// 全局导出
if (typeof window !== 'undefined') {
    window.ApplicationCore = ApplicationCore;
    window.app = app;
}

// CommonJS导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ApplicationCore, app };
}