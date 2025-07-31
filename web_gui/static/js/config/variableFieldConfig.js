/**
 * 变量字段配置
 * 实现STORY-012 AC-3: 参数字段智能识别
 * 
 * 定义哪些Action类型的哪些参数字段支持变量引用
 */

/**
 * 支持变量引用的字段配置
 * 格式: { action: ['field1', 'field2', ...] }
 */
const VARIABLE_SUPPORTED_FIELDS = {
    // 页面导航操作
    'goto': ['url'],
    'refresh': [],
    'back': [],
    'evaluateJavaScript': ['script'],
    
    // 智能交互操作
    'ai': ['prompt'],
    'aiTap': ['locate'],
    'aiInput': ['text', 'locate'],
    'aiHover': ['locate'],
    'aiScroll': ['locate'],
    'aiKeyboardPress': ['keys'],
    'aiRightClick': ['locate'],
    
    // 数据提取操作
    'aiQuery': ['query', 'schema'],
    'aiAsk': ['query', 'question'],
    'aiBoolean': ['query', 'question'],
    'aiNumber': ['query', 'question'],
    'aiString': ['query', 'question'],
    'aiLocate': ['locate'],
    
    // 验证等待操作
    'aiAssert': ['condition', 'assertion'],
    'aiWaitFor': ['prompt', 'assertion'],
    
    // 工具操作
    'logScreenshot': ['description'],
    'sleep': [], // duration 通常不需要变量引用
    'runYaml': ['yaml']
};

/**
 * 字段类型配置
 * 定义每个字段的类型、标签、占位符等信息
 */
const FIELD_TYPE_CONFIG = {
    // 通用字段
    'url': {
        type: 'text',
        label: '目标URL',
        placeholder: '输入URL或使用${variable}引用变量',
        required: true,
        variableSupported: true
    },
    'text': {
        type: 'text',
        label: '输入文本',
        placeholder: '输入文本内容或使用${variable}引用变量',
        required: false,
        variableSupported: true
    },
    'locate': {
        type: 'text',
        label: '元素定位',
        placeholder: '描述要定位的元素或使用${variable}引用',
        required: true,
        variableSupported: true
    },
    'prompt': {
        type: 'textarea',
        label: '操作提示',
        placeholder: '描述要执行的操作或使用${variable}引用',
        required: false,
        variableSupported: true
    },
    'query': {
        type: 'textarea',
        label: '查询内容',
        placeholder: '输入查询描述或使用${variable}引用',
        required: false,
        variableSupported: true
    },
    'question': {
        type: 'textarea',
        label: '问题内容',
        placeholder: '输入问题或使用${variable}引用',
        required: false,
        variableSupported: true
    },
    'condition': {
        type: 'text',
        label: '验证条件',
        placeholder: '描述验证条件或使用${variable}引用',
        required: true,
        variableSupported: true
    },
    'assertion': {
        type: 'text',
        label: '断言条件',
        placeholder: '描述断言条件或使用${variable}引用',
        required: true,
        variableSupported: true
    },
    'keys': {
        type: 'text',
        label: '按键',
        placeholder: '输入按键名称或组合，如Enter、Ctrl+A',
        required: true,
        variableSupported: true
    },
    'script': {
        type: 'textarea',
        label: 'JavaScript代码',
        placeholder: '输入JavaScript代码或使用${variable}引用',
        required: true,
        variableSupported: true
    },
    'yaml': {
        type: 'textarea',
        label: 'YAML脚本',
        placeholder: '输入YAML格式的脚本或使用${variable}引用',
        required: true,
        variableSupported: true
    },
    'description': {
        type: 'text',
        label: '描述',
        placeholder: '输入描述信息或使用${variable}引用',
        required: false,
        variableSupported: true
    },
    'duration': {
        type: 'number',
        label: '持续时间(ms)',
        placeholder: '输入毫秒数',
        required: false,
        variableSupported: false
    },
    'timeout': {
        type: 'number',
        label: '超时时间(ms)',
        placeholder: '输入超时毫秒数',
        required: false,
        variableSupported: false
    },
    'schema': {
        type: 'textarea',
        label: '数据结构',
        placeholder: '输入JSON格式的数据结构定义',
        required: false,
        variableSupported: false,
        isJsonField: true
    }
};

/**
 * Action对应的参数字段配置
 * 定义每个Action类型需要哪些参数字段
 */
const ACTION_PARAMETER_FIELDS = {
    // 页面导航操作
    'goto': [
        { name: 'url', config: FIELD_TYPE_CONFIG.url }
    ],
    'refresh': [],
    'back': [],
    'evaluateJavaScript': [
        { name: 'script', config: FIELD_TYPE_CONFIG.script }
    ],
    
    // 智能交互操作
    'ai': [
        { name: 'prompt', config: FIELD_TYPE_CONFIG.prompt }
    ],
    'aiTap': [
        { name: 'locate', config: FIELD_TYPE_CONFIG.locate }
    ],
    'aiInput': [
        { name: 'text', config: FIELD_TYPE_CONFIG.text },
        { name: 'locate', config: FIELD_TYPE_CONFIG.locate }
    ],
    'aiHover': [
        { name: 'locate', config: FIELD_TYPE_CONFIG.locate }
    ],
    'aiScroll': [
        { name: 'locate', config: FIELD_TYPE_CONFIG.locate }
    ],
    'aiKeyboardPress': [
        { name: 'keys', config: FIELD_TYPE_CONFIG.keys }
    ],
    'aiRightClick': [
        { name: 'locate', config: FIELD_TYPE_CONFIG.locate }
    ],
    
    // 数据提取操作
    'aiQuery': [
        { name: 'schema', config: FIELD_TYPE_CONFIG.schema }
    ],
    'aiAsk': [
        { name: 'query', config: FIELD_TYPE_CONFIG.query }
    ],
    'aiBoolean': [
        { name: 'query', config: FIELD_TYPE_CONFIG.query }
    ],
    'aiNumber': [
        { name: 'query', config: FIELD_TYPE_CONFIG.query }
    ],
    'aiString': [
        { name: 'query', config: FIELD_TYPE_CONFIG.query }
    ],
    'aiLocate': [
        { name: 'locate', config: FIELD_TYPE_CONFIG.locate }
    ],
    
    // 验证等待操作
    'aiAssert': [
        { name: 'condition', config: FIELD_TYPE_CONFIG.condition }
    ],
    'aiWaitFor': [
        { name: 'prompt', config: FIELD_TYPE_CONFIG.prompt }
    ],
    
    // 工具操作
    'logScreenshot': [
        { name: 'description', config: FIELD_TYPE_CONFIG.description }
    ],
    'sleep': [
        { name: 'duration', config: FIELD_TYPE_CONFIG.duration }
    ],
    'runYaml': [
        { name: 'yaml', config: FIELD_TYPE_CONFIG.yaml }
    ]
};

/**
 * 检查指定Action的字段是否支持变量引用
 * @param {string} action - Action类型
 * @param {string} fieldName - 字段名
 * @returns {boolean} 是否支持变量引用
 */
function isVariableSupportedField(action, fieldName) {
    const supportedFields = VARIABLE_SUPPORTED_FIELDS[action];
    return supportedFields ? supportedFields.includes(fieldName) : false;
}

/**
 * 获取Action对应的参数字段列表
 * @param {string} action - Action类型
 * @returns {Array} 参数字段配置列表
 */
function getParameterFields(action) {
    return ACTION_PARAMETER_FIELDS[action] || [];
}

/**
 * 获取字段的配置信息
 * @param {string} fieldName - 字段名
 * @returns {Object} 字段配置
 */
function getFieldConfig(fieldName) {
    return FIELD_TYPE_CONFIG[fieldName] || {
        type: 'text',
        label: fieldName,
        placeholder: '请输入内容',
        required: false,
        variableSupported: false
    };
}

/**
 * 获取Action的显示名称
 * @param {string} action - Action类型
 * @returns {string} 显示名称
 */
function getActionDisplayName(action) {
    const displayNames = {
        // 页面导航操作
        'goto': '导航到页面',
        'refresh': '刷新页面',
        'back': '返回上一页',
        'evaluateJavaScript': '执行JavaScript',
        
        // 智能交互操作
        'ai': '智能操作',
        'aiTap': 'AI点击',
        'aiInput': 'AI输入',
        'aiHover': 'AI悬停',
        'aiScroll': 'AI滚动',
        'aiKeyboardPress': 'AI按键',
        'aiRightClick': 'AI右键',
        
        // 数据提取操作
        'aiQuery': 'AI提取数据',
        'aiAsk': 'AI询问',
        'aiBoolean': 'AI布尔值',
        'aiNumber': 'AI数值',
        'aiString': 'AI字符串',
        'aiLocate': 'AI定位',
        
        // 验证等待操作
        'aiAssert': 'AI断言',
        'aiWaitFor': 'AI等待',
        
        // 工具操作
        'logScreenshot': '截图',
        'sleep': '等待',
        'runYaml': '执行YAML'
    };
    
    return displayNames[action] || action;
}

/**
 * 获取所有支持变量引用的Action列表
 * @returns {string[]} Action列表
 */
function getVariableSupportedActions() {
    return Object.keys(VARIABLE_SUPPORTED_FIELDS).filter(action => 
        VARIABLE_SUPPORTED_FIELDS[action].length > 0
    );
}

/**
 * 获取字段值的类型提示
 * @param {string} fieldName - 字段名
 * @param {any} value - 字段值
 * @returns {string} 类型提示
 */
function getFieldValueTypeHint(fieldName, value) {
    const config = getFieldConfig(fieldName);
    
    if (config.isJsonField) {
        try {
            JSON.parse(value);
            return 'Valid JSON';
        } catch {
            return 'Invalid JSON';
        }
    }
    
    if (config.type === 'number') {
        const num = Number(value);
        if (isNaN(num)) {
            return 'Invalid number';
        }
        return `Number: ${num}`;
    }
    
    if (typeof value === 'string' && value.includes('${')) {
        const varCount = (value.match(/\$\{[^}]*\}/g) || []).length;
        return `Contains ${varCount} variable reference${varCount > 1 ? 's' : ''}`;
    }
    
    return `Text: ${String(value).length} chars`;
}

/**
 * 验证字段值格式
 * @param {string} fieldName - 字段名
 * @param {any} value - 字段值
 * @returns {Object} 验证结果
 */
function validateFieldValue(fieldName, value) {
    const config = getFieldConfig(fieldName);
    
    // 检查必填字段
    if (config.required && (!value || String(value).trim() === '')) {
        return {
            isValid: false,
            error: `${config.label}是必填字段`
        };
    }
    
    // JSON字段特殊验证
    if (config.isJsonField && value && String(value).trim() !== '') {
        try {
            JSON.parse(value);
        } catch (error) {
            return {
                isValid: false,
                error: `${config.label}必须是有效的JSON格式`
            };
        }
    }
    
    // 数字字段验证
    if (config.type === 'number' && value && String(value).trim() !== '') {
        const num = Number(value);
        if (isNaN(num)) {
            return {
                isValid: false,
                error: `${config.label}必须是有效的数字`
            };
        }
    }
    
    return {
        isValid: true
    };
}

// 导出到全局作用域
window.VariableFieldConfig = {
    VARIABLE_SUPPORTED_FIELDS,
    FIELD_TYPE_CONFIG,
    ACTION_PARAMETER_FIELDS,
    isVariableSupportedField,
    getParameterFields,
    getFieldConfig,
    getActionDisplayName,
    getVariableSupportedActions,
    getFieldValueTypeHint,
    validateFieldValue
};