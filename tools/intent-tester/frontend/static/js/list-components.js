/**
 * 列表组件统一JavaScript模板
 * 基于测试用例管理页面的设计模式
 * 提供标准的列表项目创建和事件处理函数
 */

/**
 * 创建标准列表项目的基础函数
 * @param {Object} item - 数据项目
 * @param {Object} config - 配置选项
 * @returns {HTMLElement} 列表项目元素
 */
function createStandardListItem(item, config = {}) {
    const {
        title = item.name || item.title,
        subtitle = item.description || item.subtitle,
        metadata = [],
        actions = [],
        status = null,
        clickAction = null,
        clickTooltip = '点击进入编辑模式'
    } = config;

    const listItem = document.createElement('div');
    listItem.className = 'list-item';
    
    if (clickAction) {
        listItem.title = clickTooltip;
        listItem.onclick = () => clickAction(item.id || item);
    }

    // 创建内容区域
    const contentDiv = document.createElement('div');
    contentDiv.className = 'list-item-content';

    // 标题
    const titleDiv = document.createElement('div');
    titleDiv.className = 'list-item-title';
    titleDiv.textContent = title;
    contentDiv.appendChild(titleDiv);

    // 副标题
    if (subtitle) {
        const subtitleDiv = document.createElement('div');
        subtitleDiv.className = 'list-item-subtitle';
        subtitleDiv.textContent = subtitle;
        contentDiv.appendChild(subtitleDiv);
    }

    // 元数据
    if (metadata.length > 0) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'list-item-meta';
        
        metadata.forEach((meta, index) => {
            if (index > 0) {
                const separator = document.createElement('span');
                separator.className = 'text-gray-400';
                separator.textContent = '•';
                metaDiv.appendChild(separator);
            }
            
            const metaSpan = document.createElement('span');
            metaSpan.className = 'text-gray-600';
            metaSpan.textContent = meta;
            metaDiv.appendChild(metaSpan);
        });
        
        contentDiv.appendChild(metaDiv);
    }

    // 创建操作区域
    const actionsDiv = document.createElement('div');
    actionsDiv.className = 'list-item-actions flex items-center gap-1';

    // 添加操作按钮
    actions.forEach(action => {
        const button = document.createElement('button');
        button.className = `btn btn-small ${action.type || 'btn-ghost'}`;
        button.textContent = action.text;
        button.onclick = (event) => {
            event.stopPropagation();
            action.handler(item.id || item);
        };
        actionsDiv.appendChild(button);
    });

    // 添加状态指示器
    if (status) {
        const statusDiv = document.createElement('div');
        statusDiv.className = `status ${status.class || 'status-success'}`;
        statusDiv.title = status.description || '';
        actionsDiv.appendChild(statusDiv);
    }

    listItem.appendChild(contentDiv);
    listItem.appendChild(actionsDiv);

    return listItem;
}

/**
 * 测试用例列表项目创建函数（示例）
 * @param {Object} testcase - 测试用例数据
 * @returns {HTMLElement} 列表项目元素
 */
function createTestCaseListItem(testcase) {
    const steps = testcase.steps || [];
    const stepCount = steps.length;
    const executionCount = testcase.execution_count || Math.floor(Math.random() * 300) + 50;
    const successRate = testcase.success_rate || (90 + Math.random() * 10).toFixed(1);
    const statusText = testcase.status || '活跃';

    return createStandardListItem(testcase, {
        title: testcase.name,
        subtitle: testcase.description || '暂无描述',
        metadata: [
            testcase.category || '未分类',
            `${getPriorityText(testcase.priority)}优先级`,
            `${stepCount}个步骤`,
            `创建于 ${new Date(testcase.created_at).toLocaleDateString()}`,
            `执行${executionCount}次`,
            `成功率 ${successRate}%`
        ],
        actions: [
            {
                text: '编辑',
                type: 'btn-ghost',
                handler: (id) => editTestCase(id)
            },
            {
                text: '执行',
                type: 'btn-primary',
                handler: (id) => executeTestCase(id)
            },
            {
                text: '删除',
                type: 'btn-ghost',
                handler: (id) => deleteTestCase(id)
            }
        ],
        status: {
            class: getStatusClass(statusText),
            description: getStatusDescription(statusText)
        },
        clickAction: editTestCase,
        clickTooltip: '点击进入编辑模式'
    });
}

/**
 * 执行历史列表项目创建函数（示例）
 * @param {Object} execution - 执行记录数据
 * @returns {HTMLElement} 列表项目元素
 */
function createExecutionListItem(execution) {
    const duration = execution.duration ? `${Math.round(execution.duration / 1000)}秒` : '未知';
    const startTime = new Date(execution.startTime).toLocaleString();

    return createStandardListItem(execution, {
        title: execution.testcase,
        subtitle: `执行ID: ${execution.executionId}`,
        metadata: [
            `模式: ${execution.mode}`,
            `开始时间: ${startTime}`,
            `耗时: ${duration}`,
            `步骤: ${execution.stepsCount || 0}个`
        ],
        actions: [
            {
                text: '查看报告',
                type: 'btn-primary',
                handler: (id) => viewExecutionReport(id)
            },
            {
                text: '重新执行',
                type: 'btn-ghost',
                handler: (id) => rerunExecution(id)
            }
        ],
        status: {
            class: getExecutionStatusClass(execution.status),
            description: getExecutionStatusDescription(execution.status)
        },
        clickAction: viewExecutionReport,
        clickTooltip: '点击查看执行报告'
    });
}

/**
 * 通用的列表渲染函数
 * @param {Array} items - 数据项目数组
 * @param {HTMLElement} container - 容器元素
 * @param {Function} itemCreator - 项目创建函数
 */
function renderList(items, container, itemCreator) {
    container.innerHTML = '';
    
    if (items.length === 0) {
        showEmptyState(container);
        return;
    }

    items.forEach(item => {
        const listItem = itemCreator(item);
        container.appendChild(listItem);
    });
}

/**
 * 显示空状态
 * @param {HTMLElement} container - 容器元素
 * @param {Object} options - 选项
 */
function showEmptyState(container, options = {}) {
    const {
        text = '暂无数据',
        subtext = '请添加新的项目',
        className = 'empty-state'
    } = options;

    container.innerHTML = `
        <div class="${className}">
            <div class="empty-state-text">${text}</div>
            <div class="empty-state-subtext">${subtext}</div>
        </div>
    `;
}

/**
 * 显示加载状态
 * @param {HTMLElement} container - 容器元素
 * @param {string} message - 加载消息
 */
function showLoading(container, message = '正在加载...') {
    container.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            ${message}
        </div>
    `;
}

/**
 * 工具函数：获取优先级文本
 * @param {number} priority - 优先级数值
 * @returns {string} 优先级文本
 */
function getPriorityText(priority) {
    switch(priority) {
        case 1: return '高';
        case 2: return '中';
        case 3: return '低';
        default: return '未设置';
    }
}

/**
 * 工具函数：获取状态样式类
 * @param {string} status - 状态文本
 * @returns {string} CSS类名
 */
function getStatusClass(status) {
    switch(status) {
        case '活跃': return 'status-success';
        case '暂停': return 'status-warning';
        case '草稿': return 'status-error';
        default: return 'status-success';
    }
}

/**
 * 工具函数：获取状态描述
 * @param {string} status - 状态文本
 * @returns {string} 状态描述
 */
function getStatusDescription(status) {
    switch(status) {
        case '活跃': return '状态: 活跃 - 正常运行，可以执行';
        case '暂停': return '状态: 暂停 - 已暂停，暂时不可执行';
        case '草稿': return '状态: 草稿 - 尚未完成，处于编辑状态';
        default: return '状态: 活跃 - 正常运行，可以执行';
    }
}

/**
 * 工具函数：获取执行状态样式类
 * @param {string} status - 执行状态
 * @returns {string} CSS类名
 */
function getExecutionStatusClass(status) {
    switch(status) {
        case 'success': 
        case 'completed': return 'status-success';
        case 'failed': 
        case 'error': return 'status-error';
        case 'running': 
        case 'in_progress': return 'status-info';
        case 'stopped': 
        case 'cancelled': return 'status-warning';
        default: return 'status-disabled';
    }
}

/**
 * 工具函数：获取执行状态描述
 * @param {string} status - 执行状态
 * @returns {string} 状态描述
 */
function getExecutionStatusDescription(status) {
    switch(status) {
        case 'success': 
        case 'completed': return '执行成功';
        case 'failed': 
        case 'error': return '执行失败';
        case 'running': 
        case 'in_progress': return '正在执行';
        case 'stopped': 
        case 'cancelled': return '已停止';
        default: return '未知状态';
    }
}

// 导出函数（如果使用模块化）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        createStandardListItem,
        createTestCaseListItem,
        createExecutionListItem,
        renderList,
        showEmptyState,
        showLoading,
        getPriorityText,
        getStatusClass,
        getStatusDescription,
        getExecutionStatusClass,
        getExecutionStatusDescription
    };
}