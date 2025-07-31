/**
 * SmartVariableInput 组件测试套件
 * 基于STORY-010验收标准
 */

// 模拟 fetch API
global.fetch = jest.fn();

// 模拟 DOM 环境
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.document = dom.window.document;
global.window = dom.window;

// 导入组件
const { SmartVariableInput, createSmartVariableInput } = require('./smart-variable-input');

describe('SmartVariableInput', () => {
    let inputElement, component;

    beforeEach(() => {
        // 创建测试输入框
        inputElement = document.createElement('input');
        inputElement.type = 'text';
        document.body.appendChild(inputElement);
        
        // 清理 fetch mock
        fetch.mockClear();
        
        // 创建组件实例
        component = new SmartVariableInput(inputElement, {
            executionId: 'test-execution-id',
            currentStepIndex: 1
        });
    });

    afterEach(() => {
        // 清理
        if (component) {
            component.destroy();
        }
        document.body.innerHTML = '';
    });

    describe('组件初始化', () => {
        test('应该正确初始化组件', () => {
            expect(component.input).toBe(inputElement);
            expect(component.options.executionId).toBe('test-execution-id');
            expect(component.options.currentStepIndex).toBe(1);
        });

        test('应该创建容器结构', () => {
            expect(inputElement.parentElement.classList.contains('smart-variable-input')).toBe(true);
            expect(inputElement.classList.contains('smart-input')).toBe(true);
        });

        test('应该绑定事件监听器', () => {
            const spy = jest.spyOn(component, 'handleInput');
            inputElement.dispatchEvent(new Event('input'));
            expect(spy).toHaveBeenCalled();
        });
    });

    describe('AC-1: 自动触发智能提示', () => {
        test('输入${ 应该触发智能提示', async () => {
            const mockResponse = {
                variables: [
                    { name: 'test_var', data_type: 'string', preview: 'test', source_step_index: 1 }
                ]
            };
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            });

            // 模拟输入
            inputElement.value = '${';
            inputElement.selectionStart = 2;
            inputElement.dispatchEvent(new Event('input'));

            // 等待异步操作
            await new Promise(resolve => setTimeout(resolve, 250));

            expect(component.showSuggestions).toBe(true);
            expect(component.dropdown).not.toBeNull();
        });

        test('光标不在${ 后时不应该显示提示', () => {
            inputElement.value = 'test ${var}';
            inputElement.selectionStart = 4;
            inputElement.dispatchEvent(new Event('input'));

            expect(component.showSuggestions).toBe(false);
        });
    });

    describe('AC-2: 显示可用变量列表', () => {
        test('应该加载并显示变量列表', async () => {
            const mockResponse = {
                variables: [
                    { 
                        name: 'product_info', 
                        data_type: 'object', 
                        preview: '{name: "iPhone", price: 999}',
                        source_step_index: 2 
                    },
                    { 
                        name: 'user_name', 
                        data_type: 'string', 
                        preview: '"张三"',
                        source_step_index: 1 
                    }
                ]
            };
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            });

            component.currentContext = { type: 'variable', prefix: '', startPos: 2 };
            await component.loadSuggestions();

            expect(component.suggestions).toHaveLength(2);
            expect(component.suggestions[0].name).toBe('product_info');
            expect(component.suggestions[1].name).toBe('user_name');
        });

        test('应该正确显示变量元数据', async () => {
            const mockResponse = {
                variables: [
                    { 
                        name: 'test_var', 
                        data_type: 'string', 
                        preview: '"test"',
                        source_step_index: 3 
                    }
                ]
            };
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            });

            component.currentContext = { type: 'variable', prefix: '', startPos: 2 };
            await component.loadSuggestions();
            component.renderSuggestions();

            const suggestionItem = component.dropdown.querySelector('.suggestion-item');
            expect(suggestionItem.textContent).toContain('test_var');
            expect(suggestionItem.textContent).toContain('步骤 3');
            expect(suggestionItem.textContent).toContain('[string]');
            expect(suggestionItem.textContent).toContain('预览: "test"');
        });
    });

    describe('AC-3: 实时搜索和过滤', () => {
        beforeEach(async () => {
            const mockResponse = {
                variables: [
                    { name: 'product_info', data_type: 'object', preview: '{}', source_step_index: 1 },
                    { name: 'product_name', data_type: 'string', preview: '"test"', source_step_index: 2 },
                    { name: 'user_data', data_type: 'object', preview: '{}', source_step_index: 3 }
                ]
            };
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            });

            component.currentContext = { type: 'variable', prefix: '', startPos: 2 };
            await component.loadSuggestions();
        });

        test('应该根据输入过滤变量', () => {
            component.filterText = 'prod';
            component.filterSuggestions();

            expect(component.filteredSuggestions).toHaveLength(2);
            expect(component.filteredSuggestions[0].name).toBe('product_info');
            expect(component.filteredSuggestions[1].name).toBe('product_name');
        });

        test('应该支持大小写不敏感搜索', () => {
            component.filterText = 'PROD';
            component.filterSuggestions();

            expect(component.filteredSuggestions).toHaveLength(2);
        });

        test('应该高亮匹配的字符', () => {
            const highlighted = component.highlightMatch('product_info', 'prod');
            expect(highlighted).toContain('<mark>prod</mark>');
        });
    });

    describe('AC-4: 嵌套属性智能提示', () => {
        test('应该检测对象属性访问', () => {
            inputElement.value = '${product_info.';
            inputElement.selectionStart = 15;

            const context = component.getVariableContext(inputElement.value, inputElement.selectionStart);
            
            expect(context.type).toBe('property');
            expect(context.variableName).toBe('product_info');
            expect(context.propertyPrefix).toBe('');
        });

        test('应该加载对象属性建议', async () => {
            const mockResponse = {
                properties: [
                    { name: 'name', type: 'string', value: '"iPhone 15"' },
                    { name: 'price', type: 'number', value: 999 },
                    { name: 'category', type: 'string', value: '"电子产品"' }
                ]
            };
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            });

            component.currentContext = { 
                type: 'property', 
                variableName: 'product_info', 
                propertyPrefix: '', 
                startPos: 2 
            };
            await component.loadSuggestions();

            expect(fetch).toHaveBeenCalledWith('/api/executions/test-execution-id/variables/product_info/properties');
            expect(component.suggestions).toHaveLength(3);
            expect(component.suggestions[0].name).toBe('name');
        });

        test('应该正确显示属性建议项', async () => {
            const mockResponse = {
                properties: [
                    { name: 'name', type: 'string', value: '"iPhone 15"' }
                ]
            };
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            });

            component.currentContext = { 
                type: 'property', 
                variableName: 'product_info', 
                propertyPrefix: '', 
                startPos: 2 
            };
            await component.loadSuggestions();
            component.renderSuggestions();

            const suggestionItem = component.dropdown.querySelector('.suggestion-item');
            expect(suggestionItem.textContent).toContain('name');
            expect(suggestionItem.textContent).toContain('属性');
            expect(suggestionItem.textContent).toContain('[string]');
        });
    });

    describe('AC-5: 键盘导航支持', () => {
        beforeEach(async () => {
            const mockResponse = {
                variables: [
                    { name: 'var1', data_type: 'string', preview: '"test1"', source_step_index: 1 },
                    { name: 'var2', data_type: 'string', preview: '"test2"', source_step_index: 1 }
                ]
            };
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            });

            component.currentContext = { type: 'variable', prefix: '', startPos: 2 };
            await component.loadSuggestions();
            component.renderSuggestions();
        });

        test('箭头键应该选择不同的变量', () => {
            expect(component.selectedIndex).toBe(0);

            // 向下箭头
            const downEvent = new KeyboardEvent('keydown', { key: 'ArrowDown' });
            inputElement.dispatchEvent(downEvent);
            expect(component.selectedIndex).toBe(1);

            // 向上箭头
            const upEvent = new KeyboardEvent('keydown', { key: 'ArrowUp' });
            inputElement.dispatchEvent(upEvent);
            expect(component.selectedIndex).toBe(0);
        });

        test('ESC键应该关闭提示菜单', () => {
            const escEvent = new KeyboardEvent('keydown', { key: 'Escape' });
            inputElement.dispatchEvent(escEvent);
            expect(component.showSuggestions).toBe(false);
        });

        test('Ctrl+Space应该强制打开提示菜单', () => {
            component.hideSuggestions();
            
            const ctrlSpaceEvent = new KeyboardEvent('keydown', { 
                key: ' ', 
                code: 'Space',
                ctrlKey: true 
            });
            inputElement.dispatchEvent(ctrlSpaceEvent);
            
            expect(component.currentContext).not.toBeNull();
        });
    });

    describe('AC-6: 自动补全和格式化', () => {
        test('应该正确插入变量引用', async () => {
            const mockResponse = {
                variables: [
                    { name: 'test_var', data_type: 'string', preview: '"test"', source_step_index: 1 }
                ]
            };
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            });

            inputElement.value = '${';
            inputElement.selectionStart = 2;
            component.currentContext = { type: 'variable', prefix: '', startPos: 2 };
            await component.loadSuggestions();

            component.selectedIndex = 0;
            component.insertSelectedVariable();

            expect(inputElement.value).toBe('${test_var}');
            expect(inputElement.selectionStart).toBe(11); // 光标在}之后
        });

        test('应该正确插入属性引用', async () => {
            const mockResponse = {
                properties: [
                    { name: 'name', type: 'string', value: '"iPhone"' }
                ]
            };
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            });

            inputElement.value = '${product_info.';
            inputElement.selectionStart = 15;
            component.currentContext = { 
                type: 'property', 
                variableName: 'product_info', 
                propertyPrefix: '', 
                startPos: 2 
            };
            await component.loadSuggestions();

            component.selectedIndex = 0;
            component.insertSelectedVariable();

            expect(inputElement.value).toBe('${product_info.name}');
            expect(inputElement.selectionStart).toBe(19); // 光标在}之后
        });

        test('应该触发onChange回调', async () => {
            const onChange = jest.fn();
            component.options.onChange = onChange;

            const mockResponse = {
                variables: [
                    { name: 'test_var', data_type: 'string', preview: '"test"', source_step_index: 1 }
                ]
            };
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve(mockResponse)
            });

            inputElement.value = '${';
            component.currentContext = { type: 'variable', prefix: '', startPos: 2 };
            await component.loadSuggestions();

            component.selectedIndex = 0;
            component.insertSelectedVariable();

            expect(onChange).toHaveBeenCalledWith('${test_var}');
        });
    });

    describe('错误处理', () => {
        test('应该处理API错误', async () => {
            fetch.mockRejectedValueOnce(new Error('Network error'));

            component.currentContext = { type: 'variable', prefix: '', startPos: 2 };
            await component.loadSuggestions();

            expect(component.dropdown.textContent).toContain('加载失败，请重试');
        });

        test('应该处理空响应', async () => {
            fetch.mockResolvedValueOnce({
                ok: true,
                json: () => Promise.resolve({ variables: [] })
            });

            component.currentContext = { type: 'variable', prefix: '', startPos: 2 };
            await component.loadSuggestions();
            component.renderSuggestions();

            expect(component.dropdown.textContent).toContain('暂无可用变量');
        });

        test('应该处理没有executionId的情况', async () => {
            const consoleWarn = jest.spyOn(console, 'warn').mockImplementation(() => {});
            
            component.options.executionId = null;
            await component.loadSuggestions();

            expect(consoleWarn).toHaveBeenCalledWith('SmartVariableInput: executionId 未设置，无法加载变量建议');
            
            consoleWarn.mockRestore();
        });
    });

    describe('组件生命周期', () => {
        test('应该正确销毁组件', () => {
            const removeEventListenerSpy = jest.spyOn(inputElement, 'removeEventListener');
            
            component.destroy();

            expect(removeEventListenerSpy).toHaveBeenCalledWith('input', component.handleInput);
            expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', component.handleKeyDown);
            expect(inputElement.className).not.toContain('smart-input');
        });

        test('应该正确更新配置', () => {
            component.updateOptions({ executionId: 'new-id', placeholder: '新占位符' });

            expect(component.options.executionId).toBe('new-id');
            expect(component.options.placeholder).toBe('新占位符');
            expect(inputElement.placeholder).toBe('新占位符');
        });
    });

    describe('工厂函数', () => {
        test('createSmartVariableInput应该创建组件实例', () => {
            const testInput = document.createElement('input');
            document.body.appendChild(testInput);

            const instance = createSmartVariableInput(testInput, { executionId: 'test' });

            expect(instance).toBeInstanceOf(SmartVariableInput);
            expect(instance.options.executionId).toBe('test');

            instance.destroy();
        });

        test('应该处理无效元素', () => {
            const consoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
            
            const instance = createSmartVariableInput('#non-existent', {});
            
            expect(instance).toBeNull();
            expect(consoleError).toHaveBeenCalledWith('SmartVariableInput: 未找到目标元素');
            
            consoleError.mockRestore();
        });
    });
});

describe('性能测试', () => {
    test('防抖功能应该正常工作', (done) => {
        const inputElement = document.createElement('input');
        document.body.appendChild(inputElement);
        
        const component = new SmartVariableInput(inputElement, {
            executionId: 'test',
            debounceMs: 100
        });

        const loadSuggestionsSpy = jest.spyOn(component, 'loadSuggestions');

        // 快速触发多次
        component.debouncedLoadSuggestions();
        component.debouncedLoadSuggestions();
        component.debouncedLoadSuggestions();

        // 100ms后检查只调用了一次
        setTimeout(() => {
            expect(loadSuggestionsSpy).toHaveBeenCalledTimes(1);
            component.destroy();
            done();
        }, 150);
    });

    test('应该限制建议数量', () => {
        const inputElement = document.createElement('input');
        document.body.appendChild(inputElement);
        
        const component = new SmartVariableInput(inputElement, {
            executionId: 'test',
            maxSuggestions: 3
        });

        component.suggestions = new Array(10).fill(0).map((_, i) => ({
            name: `var${i}`,
            data_type: 'string',
            preview: '"test"',
            source_step_index: 1
        }));

        component.filterSuggestions();

        expect(component.filteredSuggestions).toHaveLength(3);
        
        component.destroy();
    });
});