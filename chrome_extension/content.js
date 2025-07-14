// Intent Test Framework Bridge - Content Script

console.log('Intent Test Framework Bridge content script 已加载');

// 注入标识，让网页知道扩展已加载
document.documentElement.setAttribute('data-midscene-extension', 'true');

// 创建扩展标识元素
const extensionMarker = document.createElement('div');
extensionMarker.id = 'midscene-bridge';
extensionMarker.style.display = 'none';
extensionMarker.setAttribute('data-web-automation', 'intent-test-framework');
document.documentElement.appendChild(extensionMarker);

// 注入全局对象到页面
const script = document.createElement('script');
script.src = chrome.runtime.getURL('injected.js');
script.onload = function() {
    this.remove();
};
(document.head || document.documentElement).appendChild(script);

// 监听来自页面的消息
window.addEventListener('message', (event) => {
    // 只处理来自同一窗口的消息
    if (event.source !== window) return;
    
    if (event.data && event.data.type === 'midscene_execute') {
        console.log('收到页面执行请求:', event.data);
        
        // 转发到background script
        chrome.runtime.sendMessage({
            action: 'executeStep',
            step: event.data.step,
            stepIndex: event.data.stepIndex
        }, (response) => {
            // 将结果发送回页面
            window.postMessage({
                type: 'midscene_response',
                messageId: event.data.messageId,
                success: response ? response.success : false,
                result: response ? response.result : null,
                error: response ? response.error : 'No response from extension'
            }, '*');
        });
    }
});

// 监听来自background的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'pageInfo') {
        sendResponse({
            url: window.location.href,
            title: document.title,
            ready: document.readyState === 'complete'
        });
        return true;
    }
});

// 页面加载完成后通知
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        console.log('页面DOM加载完成，Intent Test Framework Bridge 准备就绪');
    });
} else {
    console.log('Intent Test Framework Bridge 准备就绪');
}
