/**
 * 按钮防重复点击保护机制
 * 增强版：支持更多选项和更好的用户体验
 */

// 存储正在处理的按钮状态
const processingButtons = new WeakMap();

// 防重复点击的通用函数
function preventDoubleClick(button, callback, delay = 2000) {
    // 如果按钮已经在处理中，显示提示
    if (processingButtons.get(button)) {
        // 如果有全局消息函数，显示提示
        if (window.showMessage) {
            window.showMessage('正在处理中，请稍候...', 'warning');
        }
        return;
    }
    
    // 标记按钮为处理中
    processingButtons.set(button, true);
    
    // 禁用按钮
    button.disabled = true;
    const originalText = button.textContent;
    const originalClasses = button.className;
    
    // 添加处理中的样式
    button.classList.add('processing', 'disabled');
    
    // 如果按钮有 data-loading-text 属性，显示加载文本
    const loadingText = button.getAttribute('data-loading-text') || 
                       (originalText.includes('保存') ? '保存中...' :
                        originalText.includes('创建') ? '创建中...' :
                        originalText.includes('添加') ? '添加中...' :
                        originalText.includes('删除') ? '删除中...' :
                        '处理中...');
    
    button.textContent = loadingText;
    
    // 执行回调函数
    try {
        const result = callback();
        
        // 处理 Promise 返回值
        if (result && typeof result.then === 'function') {
            result
                .then(() => {
                    // 成功后恢复按钮
                    setTimeout(() => {
                        resetButton();
                    }, delay);
                })
                .catch((error) => {
                    // 错误时立即恢复按钮
                    resetButton();
                    console.error('操作失败:', error);
                });
        } else {
            // 非异步操作，延迟恢复按钮
            setTimeout(() => {
                resetButton();
            }, delay);
        }
    } catch (error) {
        // 同步错误时立即恢复按钮
        resetButton();
        console.error('操作失败:', error);
        throw error;
    }
    
    // 恢复按钮状态的函数
    function resetButton() {
        button.disabled = false;
        button.textContent = originalText;
        button.className = originalClasses;
        processingButtons.delete(button);
    }
}

// 为按钮添加防重复点击保护的装饰器
function protectButton(button, handler, options = {}) {
    const {
        delay = 2000,
        loadingText = null,
        confirmMessage = null
    } = options;
    
    if (loadingText) {
        button.setAttribute('data-loading-text', loadingText);
    }
    
    button.addEventListener('click', function(event) {
        // 如果需要确认
        if (confirmMessage && !confirm(confirmMessage)) {
            return;
        }
        
        preventDoubleClick(button, () => handler.call(this, event), delay);
    });
}

// 自动为带有特定类的按钮添加保护
document.addEventListener('DOMContentLoaded', function() {
    // 为所有带有 protect-click 类的按钮添加保护
    document.querySelectorAll('.protect-click').forEach(button => {
        const originalOnclick = button.onclick;
        if (originalOnclick) {
            button.onclick = function(event) {
                preventDoubleClick(button, () => originalOnclick.call(this, event));
            };
        }
    });
});

// 添加CSS样式
if (!document.getElementById('button-protection-styles')) {
    const style = document.createElement('style');
    style.id = 'button-protection-styles';
    style.textContent = `
        .btn.processing {
            opacity: 0.7;
            cursor: not-allowed;
            position: relative;
        }
        
        .btn.processing:hover {
            opacity: 0.7;
        }
        
        .btn.processing::after {
            content: '';
            position: absolute;
            width: 16px;
            height: 16px;
            margin: auto;
            border: 2px solid transparent;
            border-top-color: currentColor;
            border-radius: 50%;
            animation: button-spin 1s linear infinite;
            top: 0;
            bottom: 0;
            left: 8px;
        }
        
        @keyframes button-spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}

// 导出给其他模块使用
window.ButtonProtection = {
    preventDoubleClick,
    protectButton
};