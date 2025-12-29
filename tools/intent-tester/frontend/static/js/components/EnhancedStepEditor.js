/**
 * 增强的步骤编辑器组件
 * 实现STORY-012的核心功能：集成智能变量提示到测试用例编辑器
 * 
 * 功能：
 * - 智能变量输入组件集成 (AC-1)
 * - 上下文感知的变量提示 (AC-2)
 * - 参数字段智能识别 (AC-3)
 * - 实时参数预览 (AC-4)
 * - 增强的表单验证 (AC-5)
 */

class EnhancedStepEditor {
    constructor(stepContainer, stepIndex, testCaseId = null, executionId = null) {
        this.stepContainer = stepContainer;
        this.stepIndex = stepIndex;
        this.testCaseId = testCaseId;
        this.executionId = executionId;
        
        // 初始化服务
        this.contextService = new VariableContextService(testCaseId, executionId);
        
        // 状态管理
        this.parameterValues = {};
        this.validationErrors = {};
        this.previewValues = {};
        this.smartInputInstances = new Map();
        
        // 防抖定时器
        this.validationTimers = new Map();
        this.previewTimers = new Map();
        
        this.init();
    }

    init() {
        console.log('初始化增强步骤编辑器:', {
            stepIndex: this.stepIndex,
            testCaseId: this.testCaseId,
            executionId: this.executionId
        });
    }

    /**
     * 创建增强的参数编辑表单
     * @param {Object} step - 步骤数据
     * @returns {HTMLElement} 表单元素
     */
    createEnhancedParameterForm(step) {
        const formContainer = document.createElement('div');
        formContainer.className = 'enhanced-parameter-form';
        
        const parameterFields = VariableFieldConfig.getParameterFields(step.action);
        
        if (parameterFields.length === 0) {
            formContainer.innerHTML = `
                <div class="no-parameters">
                    <p class="text-gray-600">此操作不需要参数配置</p>
                </div>
            `;
            return formContainer;
        }

        // 创建参数字段
        parameterFields.forEach(({ name, config }) => {
            const fieldElement = this.createParameterField(name, config, step.params?.[name] || '');
            formContainer.appendChild(fieldElement);
        });

        return formContainer;
    }

    /**
     * 创建单个参数字段
     * @param {string} fieldName - 字段名
     * @param {Object} fieldConfig - 字段配置
     * @param {any} currentValue - 当前值
     * @returns {HTMLElement} 字段元素
     */
    createParameterField(fieldName, fieldConfig, currentValue) {
        const fieldContainer = document.createElement('div');
        fieldContainer.className = 'parameter-field';
        fieldContainer.dataset.fieldName = fieldName;

        const isVariableSupported = fieldConfig.variableSupported;
        const fieldId = `field-${this.stepIndex}-${fieldName}`;

        fieldContainer.innerHTML = `
            <div class="field-header">
                <label class="form-label" for="${fieldId}">
                    ${fieldConfig.label}
                    ${fieldConfig.required ? '<span class="required">*</span>' : ''}
                    ${isVariableSupported ? '<span class="variable-support-badge">支持变量</span>' : ''}
                </label>
                <div class="field-hint">
                    ${this.getFieldHint(fieldName, fieldConfig)}
                </div>
            </div>
            
            <div class="field-input-container">
                ${this.createInputElement(fieldId, fieldName, fieldConfig, currentValue)}
            </div>
            
            <div class="field-feedback">
                <div class="validation-error" id="error-${fieldId}" style="display: none;"></div>
                <div class="preview-value" id="preview-${fieldId}" style="display: none;">
                    <span class="preview-label">预览值：</span>
                    <span class="preview-content"></span>
                </div>
                <div class="field-meta" id="meta-${fieldId}">
                    ${VariableFieldConfig.getFieldValueTypeHint(fieldName, currentValue)}
                </div>
            </div>
        `;

        // 绑定事件和初始化智能输入
        this.bindFieldEvents(fieldContainer, fieldName, fieldConfig);

        return fieldContainer;
    }

    /**
     * 创建输入元素
     * @private
     */
    createInputElement(fieldId, fieldName, fieldConfig, currentValue) {
        const commonAttributes = `
            id="${fieldId}"
            name="${fieldName}"
            placeholder="${fieldConfig.placeholder}"
            class="form-input ${fieldConfig.variableSupported ? 'variable-supported' : ''}"
        `;

        switch (fieldConfig.type) {
            case 'textarea':
                return `<textarea ${commonAttributes} rows="3">${this.escapeHtml(currentValue)}</textarea>`;
            
            case 'number':
                return `<input type="number" ${commonAttributes} value="${this.escapeHtml(currentValue)}">`;
            
            default:
                return `<input type="text" ${commonAttributes} value="${this.escapeHtml(currentValue)}">`;
        }
    }

    /**
     * 获取字段提示信息
     * @private
     */
    getFieldHint(fieldName, fieldConfig) {
        const hints = {
            'url': '支持HTTP/HTTPS协议的完整URL地址',
            'locate': '描述要定位的页面元素，如"登录按钮"、"用户名输入框"',
            'text': '要输入的文本内容',
            'prompt': '描述要执行的操作或任务',
            'query': '描述要查询或提取的信息',
            'question': '要询问的具体问题',
            'condition': '描述要验证的条件，如"页面显示成功信息"',
            'assertion': '描述要断言的条件',
            'keys': '按键名称，如Enter、Ctrl+A、Alt+Tab',
            'script': 'JavaScript代码，支持返回值',
            'yaml': 'YAML格式的步骤配置',
            'description': '操作的描述信息',
            'duration': '等待时间，单位毫秒',
            'schema': 'JSON格式的数据结构定义'
        };

        let hint = hints[fieldName] || '请输入相应的参数值';
        
        if (fieldConfig.variableSupported) {
            hint += '，支持使用${变量名}引用变量';
        }

        return hint;
    }

    /**
     * 绑定字段事件
     * @private
     */
    bindFieldEvents(fieldContainer, fieldName, fieldConfig) {
        const input = fieldContainer.querySelector(`#field-${this.stepIndex}-${fieldName}`);
        if (!input) return;

        // 初始化智能变量输入
        if (fieldConfig.variableSupported) {
            this.initializeSmartInput(input, fieldName);
        }

        // 输入事件
        input.addEventListener('input', (e) => {
            this.handleFieldInput(fieldName, e.target.value, fieldConfig);
        });

        // 失焦验证
        input.addEventListener('blur', () => {
            this.validateField(fieldName, input.value, fieldConfig);
        });

        // 焦点事件
        input.addEventListener('focus', () => {
            this.hideFieldError(fieldName);
        });

        // 为支持变量的字段添加快捷键
        if (fieldConfig.variableSupported) {
            input.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.code === 'Space') {
                    e.preventDefault();
                    this.showVariableHelper(input, fieldName);
                }
            });
        }
    }

    /**
     * 初始化智能变量输入
     * @private
     */
    initializeSmartInput(input, fieldName) {
        try {
            const instance = new SmartVariableInput(input, {
                executionId: this.executionId,
                currentStepIndex: this.stepIndex,
                contextService: this.contextService,
                onChange: (value) => {
                    this.handleFieldInput(fieldName, value, VariableFieldConfig.getFieldConfig(fieldName));
                },
                onVariableSelect: (variable) => {
                    console.log('选择变量:', variable);
                },
                placeholder: input.placeholder,
                debounceMs: 300,
                maxSuggestions: 10
            });

            this.smartInputInstances.set(fieldName, instance);
            console.log('智能变量输入初始化成功:', fieldName);
            
        } catch (error) {
            console.error('智能变量输入初始化失败:', fieldName, error);
        }
    }

    /**
     * 处理字段输入
     * @private
     */
    handleFieldInput(fieldName, value, fieldConfig) {
        // 更新参数值
        this.parameterValues[fieldName] = value;

        // 更新字段元信息
        this.updateFieldMeta(fieldName, value);

        // 防抖验证
        this.debounceValidation(fieldName, value, fieldConfig);

        // 防抖预览
        if (fieldConfig.variableSupported && this.containsVariableReference(value)) {
            this.debouncePreview(fieldName, value);
        } else {
            this.hideFieldPreview(fieldName);
        }

        // 触发变更事件
        this.onParameterChange?.(fieldName, value);
    }

    /**
     * 防抖验证
     * @private
     */
    debounceValidation(fieldName, value, fieldConfig, delay = 500) {
        // 清除现有定时器
        if (this.validationTimers.has(fieldName)) {
            clearTimeout(this.validationTimers.get(fieldName));
        }

        // 设置新定时器
        const timer = setTimeout(() => {
            this.validateField(fieldName, value, fieldConfig);
        }, delay);

        this.validationTimers.set(fieldName, timer);
    }

    /**
     * 防抖预览
     * @private
     */
    debouncePreview(fieldName, value, delay = 300) {
        // 清除现有定时器
        if (this.previewTimers.has(fieldName)) {
            clearTimeout(this.previewTimers.get(fieldName));
        }

        // 设置新定时器
        const timer = setTimeout(() => {
            this.updateFieldPreview(fieldName, value);
        }, delay);

        this.previewTimers.set(fieldName, timer);
    }

    /**
     * 验证字段
     * @private
     */
    async validateField(fieldName, value, fieldConfig) {
        try {
            // 基础格式验证
            const basicValidation = VariableFieldConfig.validateFieldValue(fieldName, value);
            if (!basicValidation.isValid) {
                this.showFieldError(fieldName, basicValidation.error);
                return false;
            }

            // 变量引用验证
            if (fieldConfig.variableSupported && this.containsVariableReference(value)) {
                const variableValidation = await VariableValidation.validateTextReferences(
                    value, 
                    this.executionId, 
                    this.stepIndex
                );

                if (!variableValidation.all_valid) {
                    const errors = variableValidation.validation_results
                        .filter(result => !result.is_valid)
                        .map(result => result.error)
                        .join('; ');
                    
                    this.showFieldError(fieldName, `变量引用错误: ${errors}`);
                    return false;
                }
            }

            // 验证通过
            this.hideFieldError(fieldName);
            this.validationErrors[fieldName] = null;
            return true;
            
        } catch (error) {
            console.error('字段验证失败:', fieldName, error);
            this.showFieldError(fieldName, '验证失败，请检查输入内容');
            return false;
        }
    }

    /**
     * 更新字段预览
     * @private
     */
    async updateFieldPreview(fieldName, value) {
        try {
            if (!this.containsVariableReference(value)) {
                this.hideFieldPreview(fieldName);
                return;
            }

            // 获取变量引用
            const references = VariableValidation.extractVariableReferences(value);
            if (references.length === 0) {
                this.hideFieldPreview(fieldName);
                return;
            }

            // 验证并获取解析值
            const validationResults = await VariableValidation.validateVariableReferences(
                references,
                this.executionId,
                this.stepIndex
            );

            // 构建预览值
            let previewValue = value;
            for (let i = 0; i < references.length; i++) {
                const result = validationResults[i];
                if (result?.is_valid && result.resolved_value !== undefined) {
                    const preview = VariableValidation.formatPreviewValue(
                        result.resolved_value,
                        result.data_type
                    );
                    previewValue = previewValue.replace(references[i], preview);
                }
            }

            this.showFieldPreview(fieldName, previewValue);
            
        } catch (error) {
            console.error('更新字段预览失败:', fieldName, error);
            this.hideFieldPreview(fieldName);
        }
    }

    /**
     * 更新字段元信息
     * @private
     */
    updateFieldMeta(fieldName, value) {
        const metaElement = this.stepContainer.querySelector(`#meta-field-${this.stepIndex}-${fieldName}`);
        if (metaElement) {
            metaElement.textContent = VariableFieldConfig.getFieldValueTypeHint(fieldName, value);
        }
    }

    /**
     * 显示字段错误
     * @private
     */
    showFieldError(fieldName, errorMessage) {
        const errorElement = this.stepContainer.querySelector(`#error-field-${this.stepIndex}-${fieldName}`);
        if (errorElement) {
            errorElement.textContent = errorMessage;
            errorElement.style.display = 'block';
        }

        const input = this.stepContainer.querySelector(`#field-${this.stepIndex}-${fieldName}`);
        if (input) {
            input.classList.add('error');
        }

        this.validationErrors[fieldName] = errorMessage;
    }

    /**
     * 隐藏字段错误
     * @private
     */
    hideFieldError(fieldName) {
        const errorElement = this.stepContainer.querySelector(`#error-field-${this.stepIndex}-${fieldName}`);
        if (errorElement) {
            errorElement.style.display = 'none';
        }

        const input = this.stepContainer.querySelector(`#field-${this.stepIndex}-${fieldName}`);
        if (input) {
            input.classList.remove('error');
        }

        this.validationErrors[fieldName] = null;
    }

    /**
     * 显示字段预览
     * @private
     */
    showFieldPreview(fieldName, previewValue) {
        const previewElement = this.stepContainer.querySelector(`#preview-field-${this.stepIndex}-${fieldName}`);
        if (previewElement) {
            const contentElement = previewElement.querySelector('.preview-content');
            if (contentElement) {
                contentElement.textContent = previewValue;
            }
            previewElement.style.display = 'block';
        }

        this.previewValues[fieldName] = previewValue;
    }

    /**
     * 隐藏字段预览
     * @private
     */
    hideFieldPreview(fieldName) {
        const previewElement = this.stepContainer.querySelector(`#preview-field-${this.stepIndex}-${fieldName}`);
        if (previewElement) {
            previewElement.style.display = 'none';
        }

        this.previewValues[fieldName] = null;
    }

    /**
     * 检查值是否包含变量引用
     * @private
     */
    containsVariableReference(value) {
        return typeof value === 'string' && value.includes('${');
    }

    /**
     * 显示变量助手
     * @private
     */
    showVariableHelper(input, fieldName) {
        // 这里可以集成变量选择器或其他辅助工具
        console.log('显示变量助手:', fieldName);
    }

    /**
     * HTML转义
     * @private
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 获取所有参数值
     * @returns {Object} 参数值对象
     */
    getParameterValues() {
        return { ...this.parameterValues };
    }

    /**
     * 获取验证错误
     * @returns {Object} 验证错误对象
     */
    getValidationErrors() {
        return Object.fromEntries(
            Object.entries(this.validationErrors).filter(([_, error]) => error !== null)
        );
    }

    /**
     * 检查表单是否有效
     * @returns {boolean} 是否有效
     */
    isValid() {
        return Object.values(this.validationErrors).every(error => error === null);
    }

    /**
     * 验证所有字段
     * @returns {Promise<boolean>} 是否全部有效
     */
    async validateAllFields() {
        const fields = this.stepContainer.querySelectorAll('.parameter-field');
        const validationPromises = [];

        for (const field of fields) {
            const fieldName = field.dataset.fieldName;
            const input = field.querySelector(`#field-${this.stepIndex}-${fieldName}`);
            const fieldConfig = VariableFieldConfig.getFieldConfig(fieldName);
            
            if (input) {
                validationPromises.push(
                    this.validateField(fieldName, input.value, fieldConfig)
                );
            }
        }

        const results = await Promise.all(validationPromises);
        return results.every(result => result === true);
    }

    /**
     * 更新上下文
     */
    updateContext(testCaseId, executionId) {
        this.testCaseId = testCaseId;
        this.executionId = executionId;
        this.contextService.updateContext(testCaseId, executionId);

        // 更新所有智能输入实例的上下文
        this.smartInputInstances.forEach(instance => {
            if (instance.updateContext) {
                instance.updateContext(executionId, this.stepIndex);
            }
        });
    }

    /**
     * 销毁编辑器
     */
    destroy() {
        // 清理定时器
        this.validationTimers.forEach(timer => clearTimeout(timer));
        this.previewTimers.forEach(timer => clearTimeout(timer));
        this.validationTimers.clear();
        this.previewTimers.clear();

        // 销毁智能输入实例
        this.smartInputInstances.forEach(instance => {
            if (instance.destroy) {
                instance.destroy();
            }
        });
        this.smartInputInstances.clear();

        console.log('增强步骤编辑器已销毁:', this.stepIndex);
    }
}

// 导出到全局作用域
window.EnhancedStepEditor = EnhancedStepEditor;