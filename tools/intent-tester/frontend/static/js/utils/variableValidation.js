/**
 * 变量验证工具函数
 * 实现STORY-012的变量引用验证功能
 * 
 * 功能：
 * - 变量引用语法验证
 * - 变量存在性检查
 * - 属性路径验证
 * - 实时预览和错误提示
 */

/**
 * 验证结果接口
 * @typedef {Object} ValidationResult
 * @property {boolean} is_valid - 是否有效
 * @property {string} [resolved_value] - 解析后的值
 * @property {string} [data_type] - 数据类型
 * @property {string} [error] - 错误信息
 * @property {string} [suggestion] - 修复建议
 */

/**
 * 验证变量引用
 * @param {string} reference - 变量引用字符串
 * @param {string} [executionId] - 执行ID
 * @param {number} [stepIndex] - 步骤索引
 * @returns {Promise<ValidationResult>} 验证结果
 */
async function validateVariableReference(reference, executionId = null, stepIndex = null) {
    try {
        // 首先进行语法验证
        const syntaxResult = validateSyntaxOnly(reference);
        if (!syntaxResult.is_valid) {
            return syntaxResult;
        }

        // 如果没有执行上下文，只返回语法验证结果
        if (!executionId || executionId === 'temp-execution-id') {
            return {
                is_valid: true,
                resolved_value: reference,
                data_type: 'unknown',
                suggestion: '无执行上下文，仅进行语法验证'
            };
        }

        // 调用后端API进行完整验证
        const response = await fetch(`/api/v1/executions/${executionId}/variables/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                references: [reference],
                step_index: stepIndex
            })
        });

        if (!response.ok) {
            throw new Error(`验证请求失败: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        const result = data.validation_results?.[0];
        
        if (!result) {
            throw new Error('验证结果为空');
        }

        return result;
        
    } catch (error) {
        console.warn('变量验证API调用失败:', error);
        // API失败时回退到语法验证
        return validateSyntaxOnly(reference);
    }
}

/**
 * 仅进行语法验证
 * @param {string} reference - 变量引用
 * @returns {ValidationResult} 验证结果
 */
function validateSyntaxOnly(reference) {
    if (!reference || typeof reference !== 'string') {
        return {
            is_valid: false,
            error: '变量引用不能为空',
            suggestion: '请输入变量引用，格式: ${variable_name}'
        };
    }

    // 基础的变量引用格式验证
    const variablePattern = /^\$\{([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*(?:\[\d+\])*)\}$/;
    
    if (variablePattern.test(reference)) {
        const variablePath = reference.match(variablePattern)[1];
        return {
            is_valid: true,
            resolved_value: `[预览: ${variablePath}]`,
            data_type: 'unknown',
            suggestion: '语法正确，需要执行上下文进行完整验证'
        };
    } else {
        return {
            is_valid: false,
            error: '变量引用语法错误',
            suggestion: '使用格式: ${variable_name} 或 ${object.property} 或 ${array[index]}'
        };
    }
}

/**
 * 批量验证变量引用
 * @param {string[]} references - 变量引用列表
 * @param {string} [executionId] - 执行ID
 * @param {number} [stepIndex] - 步骤索引
 * @returns {Promise<ValidationResult[]>} 验证结果列表
 */
async function validateVariableReferences(references, executionId = null, stepIndex = null) {
    if (!Array.isArray(references)) {
        throw new Error('references必须是数组');
    }

    try {
        // 如果有执行上下文，尝试批量验证
        if (executionId && executionId !== 'temp-execution-id') {
            const response = await fetch(`/api/v1/executions/${executionId}/variables/validate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    references: references,
                    step_index: stepIndex
                })
            });

            if (response.ok) {
                const data = await response.json();
                return data.validation_results || [];
            }
        }

        // 回退到逐个语法验证
        return references.map(reference => validateSyntaxOnly(reference));
        
    } catch (error) {
        console.warn('批量验证失败，使用语法验证:', error);
        return references.map(reference => validateSyntaxOnly(reference));
    }
}

/**
 * 提取文本中的所有变量引用
 * @param {string} text - 文本内容
 * @returns {string[]} 变量引用列表
 */
function extractVariableReferences(text) {
    if (!text || typeof text !== 'string') {
        return [];
    }

    const variablePattern = /\$\{[^}]+\}/g;
    const matches = text.match(variablePattern);
    
    return matches ? [...new Set(matches)] : [];
}

/**
 * 验证文本中的所有变量引用
 * @param {string} text - 包含变量引用的文本
 * @param {string} [executionId] - 执行ID
 * @param {number} [stepIndex] - 步骤索引
 * @returns {Promise<Object>} 验证结果
 */
async function validateTextReferences(text, executionId = null, stepIndex = null) {
    const references = extractVariableReferences(text);
    
    if (references.length === 0) {
        return {
            text: text,
            references: [],
            all_valid: true,
            validation_results: []
        };
    }

    const validationResults = await validateVariableReferences(references, executionId, stepIndex);
    const allValid = validationResults.every(result => result.is_valid);

    return {
        text: text,
        references: references,
        all_valid: allValid,
        validation_results: validationResults
    };
}

/**
 * 解析变量引用，返回变量路径
 * @param {string} reference - 变量引用
 * @returns {string|null} 变量路径
 */
function parseVariableReference(reference) {
    if (!reference || typeof reference !== 'string') {
        return null;
    }

    const match = reference.match(/^\$\{([^}]+)\}$/);
    return match ? match[1] : null;
}

/**
 * 构建变量引用字符串
 * @param {string} variablePath - 变量路径
 * @returns {string} 变量引用
 */
function buildVariableReference(variablePath) {
    if (!variablePath || typeof variablePath !== 'string') {
        return '';
    }

    return `\${${variablePath}}`;
}

/**
 * 检查是否为有效的变量名
 * @param {string} name - 变量名
 * @returns {boolean} 是否有效
 */
function isValidVariableName(name) {
    if (!name || typeof name !== 'string') {
        return false;
    }

    const namePattern = /^[a-zA-Z_][a-zA-Z0-9_]*$/;
    return namePattern.test(name);
}

/**
 * 检查是否为有效的属性路径
 * @param {string} path - 属性路径
 * @returns {boolean} 是否有效
 */
function isValidPropertyPath(path) {
    if (!path || typeof path !== 'string') {
        return false;
    }

    const pathPattern = /^[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*|\[\d+\])*$/;
    return pathPattern.test(path);
}

/**
 * 解析属性路径为数组
 * @param {string} path - 属性路径（如 'object.property[0].subprop'）
 * @returns {Array} 路径段数组
 */
function parsePropertyPath(path) {
    if (!path || typeof path !== 'string') {
        return [];
    }

    // 处理数组索引和对象属性
    return path.split(/[\.\[\]]/).filter(segment => segment !== '');
}

/**
 * 格式化变量值用于预览
 * @param {any} value - 变量值
 * @param {string} dataType - 数据类型
 * @param {number} maxLength - 最大长度
 * @returns {string} 格式化后的预览文本
 */
function formatPreviewValue(value, dataType = 'unknown', maxLength = 50) {
    try {
        if (value === null || value === undefined) {
            return 'null';
        }

        switch (dataType) {
            case 'string':
                const strValue = String(value);
                if (strValue.length > maxLength) {
                    return `"${strValue.substring(0, maxLength - 3)}..."`;
                }
                return `"${strValue}"`;
                
            case 'number':
                return String(value);
                
            case 'boolean':
                return value ? 'true' : 'false';
                
            case 'object':
                if (typeof value === 'object' && value !== null) {
                    if (Array.isArray(value)) {
                        return `[${value.length} items]`;
                    } else {
                        const keys = Object.keys(value);
                        if (keys.length === 0) {
                            return '{}';
                        } else if (keys.length <= 3) {
                            return `{${keys.join(', ')}}`;
                        } else {
                            return `{${keys.slice(0, 3).join(', ')}, ...}`;
                        }
                    }
                }
                return String(value).substring(0, maxLength);
                
            case 'array':
                if (Array.isArray(value)) {
                    return `[${value.length} items]`;
                }
                return String(value).substring(0, maxLength);
                
            default:
                return String(value).substring(0, maxLength);
        }
    } catch (error) {
        return 'preview error';
    }
}

/**
 * 创建变量引用错误信息
 * @param {string} reference - 变量引用
 * @param {ValidationResult} validationResult - 验证结果
 * @returns {Object} 错误信息对象
 */
function createErrorInfo(reference, validationResult) {
    return {
        reference: reference,
        error: validationResult.error || '未知错误',
        suggestion: validationResult.suggestion || '请检查变量引用格式',
        severity: validationResult.is_valid ? 'info' : 'error'
    };
}

/**
 * 检查变量引用是否可能是嵌套引用
 * @param {string} reference - 变量引用
 * @returns {boolean} 是否为嵌套引用
 */
function isNestedReference(reference) {
    const path = parseVariableReference(reference);
    return path ? path.includes('.') || path.includes('[') : false;
}

/**
 * 获取变量引用的根变量名
 * @param {string} reference - 变量引用
 * @returns {string|null} 根变量名
 */
function getRootVariableName(reference) {
    const path = parseVariableReference(reference);
    if (!path) return null;
    
    const firstDot = path.indexOf('.');
    const firstBracket = path.indexOf('[');
    
    if (firstDot === -1 && firstBracket === -1) {
        return path;
    }
    
    const endIndex = Math.min(
        firstDot === -1 ? Infinity : firstDot,
        firstBracket === -1 ? Infinity : firstBracket
    );
    
    return path.substring(0, endIndex);
}

// 导出函数到全局作用域
window.VariableValidation = {
    validateVariableReference,
    validateSyntaxOnly,
    validateVariableReferences,
    validateTextReferences,
    extractVariableReferences,
    parseVariableReference,
    buildVariableReference,
    isValidVariableName,
    isValidPropertyPath,
    parsePropertyPath,
    formatPreviewValue,
    createErrorInfo,
    isNestedReference,
    getRootVariableName
};