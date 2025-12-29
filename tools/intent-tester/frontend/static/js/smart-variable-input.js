/**
 * SmartVariableInput智能变量输入组件
 * 基于STORY-010实现的智能提示功能
 * 支持${variable}语法自动补全
 */

class SmartVariableInput {
    constructor(inputElement, options = {}) {
        this.input = inputElement;
        this.options = {
            executionId: options.executionId || null,
            currentStepIndex: options.currentStepIndex || null,
            placeholder: options.placeholder || '输入参数值',
            disabled: options.disabled || false,
            debounceMs: options.debounceMs || 200,
            maxSuggestions: options.maxSuggestions || 10,
            ...options
        };

        // 状态管理
        this.suggestions = [];
        this.filteredSuggestions = [];
        this.showSuggestions = false;
        this.selectedIndex = 0;
        this.filterText = '';
        this.isLoading = false;
        this.currentContext = null;
        
        // DOM元素
        this.dropdown = null;
        this.container = null;
        
        // 防抖定时器
        this.debounceTimer = null;
        
        // 初始化组件
        this.init();
    }

    /**
     * 初始化组件
     */
    init() {
        this.setupContainer();
        this.setupInput();
        this.bindEvents();
    }

    /**
     * 设置容器结构
     */
    setupContainer() {
        // 如果input已经被包装，跳过
        if (this.input.parentElement.classList.contains('smart-variable-input')) {
            this.container = this.input.parentElement;
            return;
        }

        // 创建容器
        this.container = document.createElement('div');
        this.container.className = 'smart-variable-input';
        
        // 包装原有input
        this.input.parentNode.insertBefore(this.container, this.input);
        this.container.appendChild(this.input);
    }

    /**
     * 设置输入框属性
     */
    setupInput() {
        this.input.placeholder = this.options.placeholder;
        this.input.disabled = this.options.disabled;
        this.input.className += ' smart-input';
        this.input.autocomplete = 'off';
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 输入事件
        this.input.addEventListener('input', this.handleInput.bind(this));
        this.input.addEventListener('keydown', this.handleKeyDown.bind(this));
        this.input.addEventListener('focus', this.handleFocus.bind(this));
        this.input.addEventListener('blur', this.handleBlur.bind(this));
        
        // 点击外部关闭提示
        document.addEventListener('click', this.handleDocumentClick.bind(this));
    }

    /**
     * 处理输入事件
     */
    handleInput(event) {
        const value = event.target.value;
        const cursorPosition = event.target.selectionStart;
        
        // 检测是否应该显示提示
        if (this.shouldShowSuggestions(value, cursorPosition)) {
            this.currentContext = this.getVariableContext(value, cursorPosition);
            this.filterText = this.extractFilterText(value, cursorPosition);
            this.debouncedLoadSuggestions();
        } else {
            this.hideSuggestions();
        }

        // 触发onChange回调
        if (this.options.onChange) {
            this.options.onChange(value);
        }
    }

    /**
     * 处理键盘事件
     */
    handleKeyDown(event) {
        if (!this.showSuggestions) {
            // Ctrl+Space: 强制打开提示菜单
            if (event.ctrlKey && event.code === 'Space') {
                event.preventDefault();
                this.forceShowSuggestions();
            }
            return;
        }

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                this.selectNext();
                break;
                
            case 'ArrowUp':
                event.preventDefault();
                this.selectPrevious();
                break;
                
            case 'Enter':
                event.preventDefault();
                this.insertSelectedVariable();
                break;
                
            case 'Tab':
                event.preventDefault();
                this.insertSelectedVariable();
                break;
                
            case 'Escape':
                event.preventDefault();
                this.hideSuggestions();
                break;
        }
    }

    /**
     * 处理焦点事件
     */
    handleFocus(event) {
        const value = event.target.value;
        const cursorPosition = event.target.selectionStart;
        
        if (this.shouldShowSuggestions(value, cursorPosition)) {
            this.filterText = this.extractFilterText(value, cursorPosition);
            this.debouncedLoadSuggestions();
        }
    }

    /**
     * 处理失焦事件
     */
    handleBlur(event) {
        // 延迟隐藏，允许点击建议项
        setTimeout(() => {
            if (!this.container.contains(document.activeElement)) {
                this.hideSuggestions();
            }
        }, 200);
    }

    /**
     * 处理文档点击事件
     */
    handleDocumentClick(event) {
        if (!this.container.contains(event.target)) {
            this.hideSuggestions();
        }
    }

    /**
     * 检测是否应该显示建议
     */
    shouldShowSuggestions(value, cursorPosition) {
        const context = this.getVariableContext(value, cursorPosition);
        return context !== null;
    }

    /**
     * 获取变量上下文信息
     */
    getVariableContext(value, cursorPosition) {
        // 向后查找最近的${
        let pos = cursorPosition - 1;
        while (pos >= 1) {
            if (value[pos - 1] === '$' && value[pos] === '{') {
                // 检查是否在变量引用中
                let endPos = value.indexOf('}', pos);
                if (endPos === -1 || cursorPosition <= endPos) {
                    const content = value.substring(pos + 1, cursorPosition);
                    const dotIndex = content.lastIndexOf('.');
                    
                    if (dotIndex !== -1) {
                        // 嵌套属性模式
                        return {
                            type: 'property',
                            variableName: content.substring(0, dotIndex),
                            propertyPrefix: content.substring(dotIndex + 1),
                            startPos: pos + 1
                        };
                    } else {
                        // 变量名模式
                        return {
                            type: 'variable',
                            prefix: content,
                            startPos: pos + 1
                        };
                    }
                }
            }
            pos--;
        }
        return null;
    }

    /**
     * 查找触发位置（兼容性保持）
     */
    findTriggerPosition(value, cursorPosition) {
        const context = this.getVariableContext(value, cursorPosition);
        return context ? context.startPos : null;
    }

    /**
     * 提取过滤文本
     */
    extractFilterText(value, cursorPosition) {
        const context = this.getVariableContext(value, cursorPosition);
        if (!context) return '';
        
        if (context.type === 'property') {
            return context.propertyPrefix;
        } else {
            return context.prefix;
        }
    }

    /**
     * 防抖加载建议
     */
    debouncedLoadSuggestions() {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            this.loadSuggestions();
        }, this.options.debounceMs);
    }

    /**
     * 强制显示建议（Ctrl+Space）
     */
    forceShowSuggestions() {
        const value = this.input.value;
        const cursorPosition = this.input.selectionStart;
        this.currentContext = this.getVariableContext(value, cursorPosition) || { type: 'variable', prefix: '', startPos: cursorPosition };
        this.filterText = '';
        this.loadSuggestions();
    }

    /**
     * 加载变量建议
     */
    async loadSuggestions() {
        if (!this.options.executionId) {
            console.warn('SmartVariableInput: executionId 未设置，无法加载变量建议');
            return;
        }

        this.isLoading = true;
        this.showSuggestionsDropdown();

        try {
            let response, data;
            
            if (this.currentContext && this.currentContext.type === 'property') {
                // 加载对象属性建议
                response = await fetch(`/api/executions/${this.options.executionId}/variables/${this.currentContext.variableName}/properties`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                data = await response.json();
                this.suggestions = data.properties || [];
            } else {
                // 加载变量建议
                response = await fetch(`/api/executions/${this.options.executionId}/variable-suggestions`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                data = await response.json();
                this.suggestions = data.variables || [];
            }
            
            this.filterSuggestions();
            this.renderSuggestions();
            
        } catch (error) {
            console.error('加载变量建议失败:', error);
            this.showErrorState('加载失败，请重试');
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * 过滤建议
     */
    filterSuggestions() {
        if (!this.filterText) {
            this.filteredSuggestions = this.suggestions.slice(0, this.options.maxSuggestions);
            return;
        }

        const filterLower = this.filterText.toLowerCase();
        this.filteredSuggestions = this.suggestions
            .filter(variable => variable.name.toLowerCase().includes(filterLower))
            .slice(0, this.options.maxSuggestions);
    }

    /**
     * 显示建议下拉框
     */
    showSuggestionsDropdown() {
        if (this.dropdown) {
            this.dropdown.remove();
        }

        this.dropdown = document.createElement('div');
        this.dropdown.className = 'variable-suggestion-dropdown';
        this.container.appendChild(this.dropdown);
        
        this.showSuggestions = true;
        this.selectedIndex = 0;
    }

    /**
     * 渲染建议列表
     */
    renderSuggestions() {
        if (!this.dropdown) return;

        if (this.isLoading) {
            this.showLoadingState();
            return;
        }

        if (this.filteredSuggestions.length === 0) {
            this.showEmptyState();
            return;
        }

        const html = this.filteredSuggestions
            .map((variable, index) => this.renderSuggestionItem(variable, index))
            .join('');
            
        this.dropdown.innerHTML = html;
        
        // 绑定点击事件
        this.bindSuggestionEvents();
    }

    /**
     * 渲染建议项
     */
    renderSuggestionItem(item, index) {
        const isSelected = index === this.selectedIndex;
        const selectedClass = isSelected ? 'selected' : '';
        const highlightedName = this.highlightMatch(item.name, this.filterText);
        
        // 区分变量和属性的显示
        if (this.currentContext && this.currentContext.type === 'property') {
            // 属性模式
            return `
                <div class="suggestion-item ${selectedClass}" data-index="${index}">
                    <div class="suggestion-item-header">
                        <span class="suggestion-item-name">${highlightedName}</span>
                        <div class="suggestion-item-meta">
                            <span class="property-indicator">属性</span>
                            <span class="type-info">[${item.type || item.data_type}]</span>
                        </div>
                    </div>
                    <div class="suggestion-item-preview">
                        ${this.formatPreview(item.value || item.preview, item.type || item.data_type)}
                    </div>
                </div>
            `;
        } else {
            // 变量模式
            return `
                <div class="suggestion-item ${selectedClass}" data-index="${index}">
                    <div class="suggestion-item-header">
                        <span class="suggestion-item-name">${highlightedName}</span>
                        <div class="suggestion-item-meta">
                            <span class="step-info">步骤 ${item.source_step_index}</span>
                            <span class="type-info">[${item.data_type}]</span>
                        </div>
                    </div>
                    <div class="suggestion-item-preview">
                        预览: ${this.formatPreview(item.preview, item.data_type)}
                    </div>
                </div>
            `;
        }
    }

    /**
     * 高亮匹配文本
     */
    highlightMatch(text, filter) {
        if (!filter) return text;
        
        const regex = new RegExp(`(${filter})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    /**
     * 格式化预览值
     */
    formatPreview(preview, dataType) {
        if (preview === null || preview === undefined) {
            return 'null';
        }
        
        if (dataType === 'string') {
            return `"${preview}"`;
        }
        
        if (typeof preview === 'object') {
            return JSON.stringify(preview);
        }
        
        return String(preview);
    }

    /**
     * 绑定建议项事件
     */
    bindSuggestionEvents() {
        const items = this.dropdown.querySelectorAll('.suggestion-item');
        items.forEach((item, index) => {
            item.addEventListener('click', () => {
                this.selectedIndex = index;
                this.insertSelectedVariable();
            });
            
            item.addEventListener('mouseenter', () => {
                this.selectedIndex = index;
                this.updateSelection();
            });
        });
    }

    /**
     * 选择下一项
     */
    selectNext() {
        if (this.selectedIndex < this.filteredSuggestions.length - 1) {
            this.selectedIndex++;
        } else {
            this.selectedIndex = 0; // 循环到开头
        }
        this.updateSelection();
    }

    /**
     * 选择上一项
     */
    selectPrevious() {
        if (this.selectedIndex > 0) {
            this.selectedIndex--;
        } else {
            this.selectedIndex = this.filteredSuggestions.length - 1; // 循环到末尾
        }
        this.updateSelection();
    }

    /**
     * 更新选择状态
     */
    updateSelection() {
        const items = this.dropdown.querySelectorAll('.suggestion-item');
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === this.selectedIndex);
        });
        
        // 滚动到选中项
        const selectedItem = items[this.selectedIndex];
        if (selectedItem) {
            selectedItem.scrollIntoView({
                block: 'nearest',
                behavior: 'smooth'
            });
        }
    }

    /**
     * 插入选中的变量
     */
    insertSelectedVariable() {
        if (this.filteredSuggestions.length === 0) return;
        
        const selectedItem = this.filteredSuggestions[this.selectedIndex];
        if (!selectedItem) return;
        
        const value = this.input.value;
        const cursorPosition = this.input.selectionStart;
        
        if (!this.currentContext) return;
        
        let newValue, newCursorPos;
        
        if (this.currentContext.type === 'property') {
            // 属性插入模式
            const beforeContent = value.substring(0, this.currentContext.startPos);
            const afterCursor = value.substring(cursorPosition);
            const fullPropertyPath = this.currentContext.variableName + '.' + selectedItem.name;
            
            newValue = beforeContent + fullPropertyPath + '}' + afterCursor;
            newCursorPos = this.currentContext.startPos + fullPropertyPath.length + 1;
        } else {
            // 变量插入模式
            const beforeContent = value.substring(0, this.currentContext.startPos);
            const afterCursor = value.substring(cursorPosition);
            
            newValue = beforeContent + selectedItem.name + '}' + afterCursor;
            newCursorPos = this.currentContext.startPos + selectedItem.name.length + 1;
        }
        
        // 更新输入框
        this.input.value = newValue;
        
        // 设置光标位置
        this.input.setSelectionRange(newCursorPos, newCursorPos);
        
        // 隐藏建议
        this.hideSuggestions();
        
        // 触发onChange回调
        if (this.options.onChange) {
            this.options.onChange(newValue);
        }
        
        // 触发input事件以便其他监听器响应
        this.input.dispatchEvent(new Event('input', { bubbles: true }));
    }

    /**
     * 隐藏建议
     */
    hideSuggestions() {
        this.showSuggestions = false;
        if (this.dropdown) {
            this.dropdown.remove();
            this.dropdown = null;
        }
    }

    /**
     * 显示加载状态
     */
    showLoadingState() {
        this.dropdown.innerHTML = `
            <div class="suggestion-loading">
                正在加载变量...
            </div>
        `;
    }

    /**
     * 显示空状态
     */
    showEmptyState() {
        const message = this.filterText ? '未找到匹配变量' : '暂无可用变量';
        this.dropdown.innerHTML = `
            <div class="suggestion-empty">
                ${message}
            </div>
        `;
    }

    /**
     * 显示错误状态
     */
    showErrorState(message) {
        this.dropdown.innerHTML = `
            <div class="suggestion-error">
                ${message}
            </div>
        `;
    }

    /**
     * 销毁组件
     */
    destroy() {
        // 移除事件监听器
        this.input.removeEventListener('input', this.handleInput);
        this.input.removeEventListener('keydown', this.handleKeyDown);
        this.input.removeEventListener('focus', this.handleFocus);
        this.input.removeEventListener('blur', this.handleBlur);
        document.removeEventListener('click', this.handleDocumentClick);
        
        // 清理定时器
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // 移除DOM元素
        this.hideSuggestions();
        
        // 重置input
        this.input.className = this.input.className.replace(' smart-input', '');
    }

    /**
     * 更新配置
     */
    updateOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
        this.setupInput();
    }
}

/**
 * 工厂函数：创建SmartVariableInput实例
 */
function createSmartVariableInput(selector, options = {}) {
    const element = typeof selector === 'string' ? document.querySelector(selector) : selector;
    if (!element) {
        console.error('SmartVariableInput: 未找到目标元素');
        return null;
    }
    
    return new SmartVariableInput(element, options);
}

// 全局导出
if (typeof window !== 'undefined') {
    window.SmartVariableInput = SmartVariableInput;
    window.createSmartVariableInput = createSmartVariableInput;
}

// CommonJS导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        SmartVariableInput,
        createSmartVariableInput
    };
}