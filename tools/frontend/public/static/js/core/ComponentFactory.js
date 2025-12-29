/**
 * 组件工厂类
 * 统一管理前端组件的创建、销毁和生命周期
 */

class ComponentFactory {
    constructor() {
        this.components = new Map();
        this.componentInstances = new Map();
        this.nextInstanceId = 1;
        
        // 注册内置组件
        this.registerBuiltinComponents();
    }

    /**
     * 注册组件类型
     */
    registerComponent(type, componentClass, defaultOptions = {}) {
        if (typeof componentClass !== 'function') {
            throw new Error(`组件类型 ${type} 必须是一个构造函数`);
        }
        
        this.components.set(type, {
            componentClass,
            defaultOptions: { ...defaultOptions }
        });
        
        console.log(`注册组件类型: ${type}`);
    }

    /**
     * 创建组件实例
     */
    createComponent(type, element, options = {}) {
        const componentDef = this.components.get(type);
        if (!componentDef) {
            throw new Error(`未找到组件类型: ${type}`);
        }

        const instanceId = `${type}_${this.nextInstanceId++}`;
        const mergedOptions = {
            ...componentDef.defaultOptions,
            ...options,
            instanceId
        };

        try {
            const instance = new componentDef.componentClass(element, mergedOptions);
            
            // 添加实例管理方法
            instance._instanceId = instanceId;
            instance._componentType = type;
            instance._element = element;
            instance._isDestroyed = false;
            
            // 包装销毁方法
            const originalDestroy = instance.destroy ? instance.destroy.bind(instance) : () => {};
            instance.destroy = () => {
                if (instance._isDestroyed) return;
                
                originalDestroy();
                this.componentInstances.delete(instanceId);
                instance._isDestroyed = true;
                
                console.log(`销毁组件实例: ${instanceId}`);
            };

            this.componentInstances.set(instanceId, instance);
            console.log(`创建组件实例: ${instanceId}`);
            
            return instance;
            
        } catch (error) {
            console.error(`创建组件失败 ${type}:`, error);
            throw error;
        }
    }

    /**
     * 获取组件实例
     */
    getInstance(instanceId) {
        return this.componentInstances.get(instanceId);
    }

    /**
     * 根据元素获取组件实例
     */
    getInstanceByElement(element) {
        for (const [id, instance] of this.componentInstances) {
            if (instance._element === element) {
                return instance;
            }
        }
        return null;
    }

    /**
     * 获取指定类型的所有实例
     */
    getInstancesByType(type) {
        return Array.from(this.componentInstances.values())
            .filter(instance => instance._componentType === type);
    }

    /**
     * 销毁组件实例
     */
    destroyInstance(instanceId) {
        const instance = this.componentInstances.get(instanceId);
        if (instance) {
            instance.destroy();
            return true;
        }
        return false;
    }

    /**
     * 销毁指定元素的所有组件
     */
    destroyInstancesByElement(element) {
        const instancesToDestroy = [];
        for (const [id, instance] of this.componentInstances) {
            if (instance._element === element || element.contains(instance._element)) {
                instancesToDestroy.push(id);
            }
        }
        
        instancesToDestroy.forEach(id => this.destroyInstance(id));
        return instancesToDestroy.length;
    }

    /**
     * 销毁所有组件实例
     */
    destroyAll() {
        const instanceIds = Array.from(this.componentInstances.keys());
        instanceIds.forEach(id => this.destroyInstance(id));
        console.log(`销毁了 ${instanceIds.length} 个组件实例`);
    }

    /**
     * 批量创建组件
     */
    createBatch(components) {
        const instances = [];
        const errors = [];

        for (const { type, element, options } of components) {
            try {
                const instance = this.createComponent(type, element, options);
                instances.push(instance);
            } catch (error) {
                errors.push({ type, element, error });
            }
        }

        return {
            instances,
            errors,
            success: errors.length === 0
        };
    }

    /**
     * 自动发现并初始化页面组件
     */
    autoDiscoverComponents() {
        const discovered = [];
        
        // 扫描具有data-component属性的元素
        const elements = document.querySelectorAll('[data-component]');
        
        for (const element of elements) {
            const componentType = element.dataset.component;
            const options = this.parseElementOptions(element);
            
            try {
                const instance = this.createComponent(componentType, element, options);
                discovered.push(instance);
            } catch (error) {
                console.error(`自动发现组件失败 ${componentType}:`, error);
            }
        }
        
        console.log(`自动发现并初始化了 ${discovered.length} 个组件`);
        return discovered;
    }

    /**
     * 解析元素的配置选项
     */
    parseElementOptions(element) {
        const options = {};
        
        // 解析data-*属性
        for (const [key, value] of Object.entries(element.dataset)) {
            if (key === 'component') continue;
            
            // 尝试解析JSON
            try {
                options[key] = JSON.parse(value);
            } catch {
                options[key] = value;
            }
        }
        
        return options;
    }

    /**
     * 注册内置组件
     */
    registerBuiltinComponents() {
        // 注册SmartVariableInput
        if (typeof SmartVariableInput !== 'undefined') {
            this.registerComponent('smart-variable-input', SmartVariableInput, {
                debounceMs: 200,
                maxSuggestions: 10
            });
        }

        // 注册EnhancedStepEditor
        if (typeof EnhancedStepEditor !== 'undefined') {
            this.registerComponent('enhanced-step-editor', EnhancedStepEditor);
        }

        // 可以继续注册其他组件...
    }

    /**
     * 获取统计信息
     */
    getStats() {
        const statsByType = {};
        
        for (const instance of this.componentInstances.values()) {
            const type = instance._componentType;
            statsByType[type] = (statsByType[type] || 0) + 1;
        }

        return {
            totalInstances: this.componentInstances.size,
            registeredTypes: this.components.size,
            instancesByType: statsByType
        };
    }
}

// 全局组件工厂实例
const componentFactory = new ComponentFactory();

// 全局导出
if (typeof window !== 'undefined') {
    window.ComponentFactory = ComponentFactory;
    window.componentFactory = componentFactory;
}

// CommonJS导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ComponentFactory, componentFactory };
}