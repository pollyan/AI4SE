// Intent Test Framework Bridge - Background Script

console.log('Intent Test Framework Bridge 后台脚本已加载');

// 监听来自content script的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('收到消息:', request);
    
    if (request.action === 'ping') {
        console.log('收到ping请求');
        sendResponse({
            success: true,
            message: 'Intent Test Framework Bridge 扩展正常运行',
            version: '1.0.0'
        });
        return true;
    }
    
    if (request.action === 'executeStep') {
        console.log('收到执行步骤请求:', request.step);
        
        // 模拟步骤执行
        executeTestStep(request.step, request.stepIndex)
            .then(result => {
                sendResponse({
                    success: true,
                    result: result
                });
            })
            .catch(error => {
                sendResponse({
                    success: false,
                    error: error.message
                });
            });
        
        return true; // 保持消息通道开放
    }
    
    if (request.action === 'getStatus') {
        sendResponse({
            success: true,
            status: 'ready',
            capabilities: [
                'navigate',
                'click',
                'type',
                'wait',
                'screenshot'
            ]
        });
        return true;
    }
});

// 模拟测试步骤执行
async function executeTestStep(step, stepIndex) {
    const action = step.action;
    const params = step.params || {};
    
    console.log(`执行步骤 ${stepIndex + 1}: ${action}`, params);
    
    try {
        switch (action) {
            case 'navigate':
                return await simulateNavigate(params.url);
            
            case 'click':
                return await simulateClick(params.locate);
            
            case 'type':
                return await simulateType(params.locate, params.text);
            
            case 'wait':
                return await simulateWait(params.time || 1000);
            
            case 'screenshot':
                return await simulateScreenshot();
            
            default:
                return await simulateGenericAction(action, params);
        }
    } catch (error) {
        console.error(`步骤执行失败:`, error);
        throw error;
    }
}

// 模拟导航
async function simulateNavigate(url) {
    console.log(`模拟导航到: ${url}`);
    
    // 获取当前活动标签页
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (url && url !== tab.url) {
        // 如果URL不同，更新标签页
        await chrome.tabs.update(tab.id, { url: url });
        
        // 等待页面加载
        await new Promise(resolve => {
            const listener = (tabId, changeInfo) => {
                if (tabId === tab.id && changeInfo.status === 'complete') {
                    chrome.tabs.onUpdated.removeListener(listener);
                    resolve();
                }
            };
            chrome.tabs.onUpdated.addListener(listener);
        });
    }
    
    return {
        action: 'navigate',
        url: url,
        timestamp: Date.now(),
        success: true
    };
}

// 模拟点击
async function simulateClick(locate) {
    console.log(`模拟点击: ${locate}`);
    
    // 在当前标签页执行脚本
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    const result = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: (selector) => {
            const element = document.querySelector(selector) || 
                           document.evaluate(selector, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            
            if (element) {
                element.click();
                return {
                    found: true,
                    tagName: element.tagName,
                    text: element.textContent?.substring(0, 50)
                };
            } else {
                return { found: false };
            }
        },
        args: [locate]
    });
    
    return {
        action: 'click',
        locate: locate,
        result: result[0].result,
        timestamp: Date.now(),
        success: result[0].result.found
    };
}

// 模拟输入
async function simulateType(locate, text) {
    console.log(`模拟输入: ${locate} -> ${text}`);
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    const result = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: (selector, inputText) => {
            const element = document.querySelector(selector) || 
                           document.evaluate(selector, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            
            if (element) {
                element.focus();
                element.value = inputText;
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                return {
                    found: true,
                    value: element.value
                };
            } else {
                return { found: false };
            }
        },
        args: [locate, text]
    });
    
    return {
        action: 'type',
        locate: locate,
        text: text,
        result: result[0].result,
        timestamp: Date.now(),
        success: result[0].result.found
    };
}

// 模拟等待
async function simulateWait(time) {
    console.log(`模拟等待: ${time}ms`);
    
    await new Promise(resolve => setTimeout(resolve, time));
    
    return {
        action: 'wait',
        time: time,
        timestamp: Date.now(),
        success: true
    };
}

// 模拟截图
async function simulateScreenshot() {
    console.log('模拟截图');
    
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const dataUrl = await chrome.tabs.captureVisibleTab(tab.windowId, { format: 'png' });
    
    return {
        action: 'screenshot',
        dataUrl: dataUrl,
        timestamp: Date.now(),
        success: true
    };
}

// 模拟通用动作
async function simulateGenericAction(action, params) {
    console.log(`模拟通用动作: ${action}`, params);
    
    // 简单的延迟模拟
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return {
        action: action,
        params: params,
        timestamp: Date.now(),
        success: true,
        message: `动作 ${action} 执行完成`
    };
}

// 扩展安装时的初始化
chrome.runtime.onInstalled.addListener(() => {
    console.log('Intent Test Framework Bridge 扩展已安装');
});
