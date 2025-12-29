/**
 * 变量上下文管理服务
 * 实现STORY-012的上下文感知变量提示功能
 * 
 * 功能：
 * - 根据步骤索引提供上下文感知的变量建议
 * - 支持实际执行和预测模式
 * - 变量数据缓存管理
 * - 智能的变量过滤和排序
 */

class VariableContextService {
    constructor(testCaseId = null, executionId = null) {
        this.testCaseId = testCaseId;
        this.executionId = executionId;
        this.cachedVariables = new Map();
        this.cachedProperties = new Map();
        this.cacheTimeout = 60000; // 1分钟缓存过期
        this.lastCacheTime = new Map();
        
        console.log('VariableContextService初始化:', { testCaseId, executionId });
    }

    /**
     * 获取指定步骤索引的可用变量
     * @param {number} stepIndex 当前步骤索引
     * @param {boolean} includeProperties 是否包含属性信息
     * @param {number} limit 限制返回数量
     * @returns {Promise<VariableData[]>} 变量数据列表
     */
    async getAvailableVariables(stepIndex, includeProperties = true, limit = null) {
        try {
            const cacheKey = `variables:${stepIndex}:${includeProperties}:${limit}`;
            
            // 检查缓存
            if (this.isCacheValid(cacheKey)) {
                const cached = this.cachedVariables.get(cacheKey);
                console.log('从缓存返回变量数据:', cacheKey, cached.length, '个变量');
                return cached;
            }

            let variables = [];

            if (this.executionId && this.executionId !== 'temp-execution-id') {
                // 基于实际执行数据
                variables = await this.fetchExecutionVariables(stepIndex, includeProperties, limit);
            } else if (this.testCaseId) {
                // 基于历史执行数据的预测
                variables = await this.predictVariables(stepIndex, includeProperties, limit);
            } else {
                // 使用演示数据
                variables = this.getDemoVariables(stepIndex, includeProperties, limit);
            }

            // 缓存结果
            this.cachedVariables.set(cacheKey, variables);
            this.lastCacheTime.set(cacheKey, Date.now());
            
            console.log('获取变量数据成功:', stepIndex, variables.length, '个变量');
            return variables;
            
        } catch (error) {
            console.error('获取变量数据失败:', error);
            // 返回演示数据作为后备
            return this.getDemoVariables(stepIndex, includeProperties, limit);
        }
    }

    /**
     * 从实际执行获取变量数据
     * @private
     */
    async fetchExecutionVariables(stepIndex, includeProperties, limit) {
        const url = `/api/v1/executions/${this.executionId}/variable-suggestions`;
        const params = new URLSearchParams();
        
        if (stepIndex !== null && stepIndex !== undefined) {
            params.append('step_index', stepIndex.toString());
        }
        if (includeProperties !== undefined) {
            params.append('include_properties', includeProperties.toString());
        }
        if (limit) {
            params.append('limit', limit.toString());
        }

        const response = await fetch(`${url}?${params}`);
        
        if (!response.ok) {
            throw new Error(`获取执行变量失败: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        return data.variables || [];
    }

    /**
     * 基于测试用例预测变量数据
     * @private
     */
    async predictVariables(stepIndex, includeProperties, limit) {
        try {
            const url = `/api/v1/testcases/${this.testCaseId}/predicted-variables`;
            const params = new URLSearchParams();
            
            if (stepIndex !== null && stepIndex !== undefined) {
                params.append('step_index', stepIndex.toString());
            }
            if (includeProperties !== undefined) {
                params.append('include_properties', includeProperties.toString());
            }
            if (limit) {
                params.append('limit', limit.toString());
            }

            const response = await fetch(`${url}?${params}`);
            
            if (!response.ok) {
                console.warn('预测变量API不可用，使用演示数据');
                return this.getDemoVariables(stepIndex, includeProperties, limit);
            }
            
            const data = await response.json();
            return data.predicted_variables || [];
            
        } catch (error) {
            console.warn('预测变量失败，使用演示数据:', error);
            return this.getDemoVariables(stepIndex, includeProperties, limit);
        }
    }

    /**
     * 获取演示变量数据
     * @private
     */
    getDemoVariables(stepIndex, includeProperties, limit) {
        const demoVariables = [
            {
                name: 'user_name',
                data_type: 'string',
                source_step_index: 0,
                source_api_method: 'aiString',
                created_at: new Date().toISOString(),
                preview_value: '"张三"',
                properties: []
            },
            {
                name: 'product_info',
                data_type: 'object',
                source_step_index: 1,
                source_api_method: 'aiQuery',
                created_at: new Date().toISOString(),
                preview_value: '{"name": "iPhone 15", "price": 999, "stock": 10}',
                properties: includeProperties ? [
                    { name: 'name', type: 'string', value: 'iPhone 15', path: 'product_info.name' },
                    { name: 'price', type: 'number', value: 999, path: 'product_info.price' },
                    { name: 'stock', type: 'number', value: 10, path: 'product_info.stock' }
                ] : []
            },
            {
                name: 'order_total',
                data_type: 'number',
                source_step_index: 2,
                source_api_method: 'aiNumber',
                created_at: new Date().toISOString(),
                preview_value: '999.00',
                properties: []
            },
            {
                name: 'login_status',
                data_type: 'boolean',
                source_step_index: 1,
                source_api_method: 'aiBoolean',
                created_at: new Date().toISOString(),
                preview_value: 'true',
                properties: []
            },
            {
                name: 'product_list',
                data_type: 'array',
                source_step_index: 2,
                source_api_method: 'aiQuery',
                created_at: new Date().toISOString(),
                preview_value: '[3 items]',
                properties: includeProperties ? [
                    { name: '0', type: 'object', value: {name: 'Product 1'}, path: 'product_list.0' },
                    { name: '1', type: 'object', value: {name: 'Product 2'}, path: 'product_list.1' },
                    { name: '2', type: 'object', value: {name: 'Product 3'}, path: 'product_list.2' }
                ] : []
            }
        ];

        // 过滤步骤索引
        let filteredVariables = demoVariables;
        if (stepIndex !== null && stepIndex !== undefined) {
            filteredVariables = demoVariables.filter(v => 
                v.source_step_index < stepIndex
            );
        }

        // 限制数量
        if (limit && filteredVariables.length > limit) {
            filteredVariables = filteredVariables.slice(0, limit);
        }

        return filteredVariables;
    }

    /**
     * 获取变量的详细属性信息
     * @param {string} variableName 变量名
     * @param {number} maxDepth 最大深度
     * @returns {Promise<Object>} 属性信息
     */
    async getVariableProperties(variableName, maxDepth = 3) {
        try {
            const cacheKey = `properties:${variableName}:${maxDepth}`;
            
            // 检查缓存
            if (this.isCacheValid(cacheKey)) {
                const cached = this.cachedProperties.get(cacheKey);
                console.log('从缓存返回属性数据:', cacheKey);
                return cached;
            }

            if (this.executionId && this.executionId !== 'temp-execution-id') {
                const url = `/api/v1/executions/${this.executionId}/variables/${variableName}/properties`;
                const params = new URLSearchParams();
                params.append('max_depth', maxDepth.toString());

                const response = await fetch(`${url}?${params}`);
                
                if (!response.ok) {
                    throw new Error(`获取变量属性失败: ${response.status}`);
                }
                
                const data = await response.json();
                
                // 缓存结果
                this.cachedProperties.set(cacheKey, data);
                this.lastCacheTime.set(cacheKey, Date.now());
                
                return data;
            } else {
                // 返回演示数据
                const demoProperties = this.getDemoProperties(variableName);
                this.cachedProperties.set(cacheKey, demoProperties);
                this.lastCacheTime.set(cacheKey, Date.now());
                return demoProperties;
            }
            
        } catch (error) {
            console.error('获取变量属性失败:', error);
            return this.getDemoProperties(variableName);
        }
    }

    /**
     * 获取演示属性数据
     * @private
     */
    getDemoProperties(variableName) {
        const demoPropertiesMap = {
            'product_info': {
                variable_name: 'product_info',
                data_type: 'object',
                properties: [
                    { name: 'name', type: 'string', value: 'iPhone 15', path: 'product_info.name' },
                    { name: 'price', type: 'number', value: 999, path: 'product_info.price' },
                    { name: 'stock', type: 'number', value: 10, path: 'product_info.stock' },
                    { name: 'category', type: 'string', value: 'Electronics', path: 'product_info.category' },
                    { name: 'specs', type: 'object', value: {color: 'blue', storage: '128GB'}, path: 'product_info.specs',
                        properties: [
                            { name: 'color', type: 'string', value: 'blue', path: 'product_info.specs.color' },
                            { name: 'storage', type: 'string', value: '128GB', path: 'product_info.specs.storage' }
                        ]
                    }
                ]
            },
            'product_list': {
                variable_name: 'product_list',
                data_type: 'array',
                properties: [
                    { name: '0', type: 'object', value: {name: 'Product 1'}, path: 'product_list.0' },
                    { name: '1', type: 'object', value: {name: 'Product 2'}, path: 'product_list.1' },
                    { name: '2', type: 'object', value: {name: 'Product 3'}, path: 'product_list.2' }
                ]
            }
        };

        return demoPropertiesMap[variableName] || {
            variable_name: variableName,
            data_type: 'string',
            properties: []
        };
    }

    /**
     * 搜索变量
     * @param {string} query 搜索查询
     * @param {number} stepIndex 当前步骤索引
     * @param {number} limit 结果限制
     * @returns {Promise<Object>} 搜索结果
     */
    async searchVariables(query, stepIndex = null, limit = 10) {
        try {
            if (this.executionId && this.executionId !== 'temp-execution-id') {
                const url = `/api/v1/executions/${this.executionId}/variable-suggestions/search`;
                const params = new URLSearchParams();
                params.append('q', query);
                if (stepIndex !== null) {
                    params.append('step_index', stepIndex.toString());
                }
                if (limit) {
                    params.append('limit', limit.toString());
                }

                const response = await fetch(`${url}?${params}`);
                
                if (!response.ok) {
                    throw new Error(`搜索变量失败: ${response.status}`);
                }
                
                return await response.json();
            } else {
                // 使用本地搜索逻辑
                return this.localSearchVariables(query, stepIndex, limit);
            }
            
        } catch (error) {
            console.error('搜索变量失败:', error);
            return this.localSearchVariables(query, stepIndex, limit);
        }
    }

    /**
     * 本地变量搜索
     * @private
     */
    async localSearchVariables(query, stepIndex, limit) {
        const variables = await this.getAvailableVariables(stepIndex, false, null);
        const queryLower = query.toLowerCase();
        
        const matches = variables.filter(variable => {
            const nameLower = variable.name.toLowerCase();
            return nameLower.includes(queryLower);
        }).map(variable => ({
            name: variable.name,
            match_score: this.calculateMatchScore(variable.name, query),
            highlighted_name: this.highlightMatch(variable.name, query),
            data_type: variable.data_type,
            source_step_index: variable.source_step_index,
            preview_value: variable.preview_value
        }));

        // 按匹配分数排序
        matches.sort((a, b) => b.match_score - a.match_score);

        // 限制结果数量
        const limitedMatches = limit ? matches.slice(0, limit) : matches;

        return {
            query: query,
            matches: limitedMatches,
            count: limitedMatches.length
        };
    }

    /**
     * 计算匹配分数
     * @private
     */
    calculateMatchScore(name, query) {
        const nameLower = name.toLowerCase();
        const queryLower = query.toLowerCase();
        
        if (nameLower === queryLower) return 1.0;
        if (nameLower.startsWith(queryLower)) return 0.8;
        if (nameLower.includes(queryLower)) return 0.6;
        
        // 计算编辑距离相似度
        const similarity = this.calculateSimilarity(nameLower, queryLower);
        return similarity * 0.4;
    }

    /**
     * 计算相似度
     * @private
     */
    calculateSimilarity(str1, str2) {
        const matrix = [];
        const len1 = str1.length;
        const len2 = str2.length;

        if (len1 === 0) return len2 === 0 ? 1 : 0;
        if (len2 === 0) return 0;

        for (let i = 0; i <= len2; i++) {
            matrix[i] = [i];
        }

        for (let j = 0; j <= len1; j++) {
            matrix[0][j] = j;
        }

        for (let i = 1; i <= len2; i++) {
            for (let j = 1; j <= len1; j++) {
                if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
                    matrix[i][j] = matrix[i - 1][j - 1];
                } else {
                    matrix[i][j] = Math.min(
                        matrix[i - 1][j - 1] + 1,
                        Math.min(matrix[i][j - 1] + 1, matrix[i - 1][j] + 1)
                    );
                }
            }
        }

        const maxLen = Math.max(len1, len2);
        return 1 - matrix[len2][len1] / maxLen;
    }

    /**
     * 高亮匹配文本
     * @private
     */
    highlightMatch(text, query) {
        if (!query) return text;
        
        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    /**
     * 检查缓存是否有效
     * @private
     */
    isCacheValid(key) {
        if (!this.cachedVariables.has(key) && !this.cachedProperties.has(key)) {
            return false;
        }
        
        const cacheTime = this.lastCacheTime.get(key);
        if (!cacheTime) return false;
        
        return Date.now() - cacheTime < this.cacheTimeout;
    }

    /**
     * 清理缓存
     */
    clearCache() {
        this.cachedVariables.clear();
        this.cachedProperties.clear();
        this.lastCacheTime.clear();
        console.log('变量上下文缓存已清理');
    }

    /**
     * 更新上下文（当testCaseId或executionId改变时）
     */
    updateContext(testCaseId = null, executionId = null) {
        if (this.testCaseId !== testCaseId || this.executionId !== executionId) {
            this.testCaseId = testCaseId;
            this.executionId = executionId;
            this.clearCache();
            console.log('变量上下文已更新:', { testCaseId, executionId });
        }
    }

    /**
     * 获取当前上下文信息
     */
    getContextInfo() {
        return {
            testCaseId: this.testCaseId,
            executionId: this.executionId,
            cacheSize: this.cachedVariables.size + this.cachedProperties.size,
            isExecutionMode: !!(this.executionId && this.executionId !== 'temp-execution-id'),
            isPredictionMode: !!(this.testCaseId && (!this.executionId || this.executionId === 'temp-execution-id'))
        };
    }
}

// 导出到全局作用域
window.VariableContextService = VariableContextService;