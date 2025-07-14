// Intent Test Framework Bridge - Injected Script
// 这个脚本直接注入到页面上下文中，可以访问页面的全局对象

(function() {
    'use strict';
    
    console.log('Intent Test Framework Bridge injected script 已加载');
    
    // 创建全局扩展对象
    window.midsceneExtension = {
        version: '1.0.0',
        name: 'Intent Test Framework Bridge',
        ready: true,
        
        // 执行测试步骤
        async executeStep(step) {
            console.log('通过全局对象执行步骤:', step);
            
            return new Promise((resolve, reject) => {
                const messageId = `global_${Date.now()}_${Math.random()}`;
                
                // 监听响应
                const responseHandler = (event) => {
                    if (event.data && 
                        event.data.type === 'midscene_response' && 
                        event.data.messageId === messageId) {
                        
                        window.removeEventListener('message', responseHandler);
                        
                        if (event.data.success) {
                            resolve(event.data.result);
                        } else {
                            reject(new Error(event.data.error || '执行失败'));
                        }
                    }
                };
                
                window.addEventListener('message', responseHandler);
                
                // 发送执行请求
                window.postMessage({
                    type: 'midscene_execute',
                    messageId: messageId,
                    step: step,
                    stepIndex: 0
                }, '*');
                
                // 设置超时
                setTimeout(() => {
                    window.removeEventListener('message', responseHandler);
                    reject(new Error('执行超时'));
                }, 30000);
            });
        },
        
        // 获取扩展状态
        getStatus() {
            return {
                ready: true,
                version: this.version,
                capabilities: [
                    'navigate',
                    'click',
                    'type',
                    'wait',
                    'screenshot'
                ]
            };
        },
        
        // 检查扩展是否可用
        isAvailable() {
            return true;
        }
    };
    
    // 触发扩展就绪事件
    const readyEvent = new CustomEvent('midsceneExtensionReady', {
        detail: {
            extension: window.midsceneExtension
        }
    });
    
    document.dispatchEvent(readyEvent);
    
    console.log('Intent Test Framework Bridge 全局对象已创建');
    
})();
