// Intent Test Framework Bridge - Popup Script

document.addEventListener('DOMContentLoaded', async () => {
    console.log('Popup 已加载');
    
    // 更新当前标签信息
    await updateCurrentTab();
    
    // 绑定事件
    document.getElementById('testBtn').addEventListener('click', testConnection);
    document.getElementById('settingsBtn').addEventListener('click', openSettings);
});

async function updateCurrentTab() {
    try {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        const tabElement = document.getElementById('currentTab');
        
        if (tab) {
            const url = new URL(tab.url);
            tabElement.textContent = url.hostname;
            tabElement.className = 'status-value success';
        } else {
            tabElement.textContent = '无法获取';
            tabElement.className = 'status-value error';
        }
    } catch (error) {
        console.error('获取当前标签失败:', error);
        document.getElementById('currentTab').textContent = '错误';
        document.getElementById('currentTab').className = 'status-value error';
    }
}

async function testConnection() {
    const testBtn = document.getElementById('testBtn');
    const statusElement = document.getElementById('status');
    
    testBtn.textContent = '测试中...';
    testBtn.disabled = true;
    
    try {
        // 测试与background script的通信
        const response = await new Promise((resolve) => {
            chrome.runtime.sendMessage({ action: 'ping' }, resolve);
        });
        
        if (response && response.success) {
            statusElement.textContent = '连接正常';
            statusElement.className = 'status-value success';
            
            // 测试与content script的通信
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            
            if (tab) {
                const tabResponse = await chrome.tabs.sendMessage(tab.id, { action: 'pageInfo' });
                console.log('页面信息:', tabResponse);
            }
            
        } else {
            statusElement.textContent = '连接失败';
            statusElement.className = 'status-value error';
        }
        
    } catch (error) {
        console.error('测试连接失败:', error);
        statusElement.textContent = '连接错误';
        statusElement.className = 'status-value error';
    }
    
    testBtn.textContent = '测试连接';
    testBtn.disabled = false;
}

function openSettings() {
    // 打开设置页面
    chrome.tabs.create({
        url: 'https://intent-test-framework.vercel.app/execution'
    });
}
