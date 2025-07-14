# Intent Test Framework Chrome桥接扩展

## 🎯 功能说明

这是Intent Test Framework的Chrome桥接扩展，用于在客户端直接执行AI自动化测试，实现真正的可视化测试过程。

## 🚀 安装步骤

### 方法1：开发者模式安装（推荐）

1. **打开Chrome扩展管理页面**
   - 在Chrome地址栏输入：`chrome://extensions/`
   - 或者：菜单 → 更多工具 → 扩展程序

2. **启用开发者模式**
   - 点击右上角的"开发者模式"开关

3. **加载扩展**
   - 点击"加载已解压的扩展程序"
   - 选择 `chrome_extension` 文件夹
   - 点击"选择文件夹"

4. **验证安装**
   - 扩展列表中应该出现"Intent Test Framework Bridge"
   - 确保扩展已启用（开关为蓝色）

### 方法2：打包安装

1. **打包扩展**
   ```bash
   # 在项目根目录执行
   cd chrome_extension
   zip -r intent-test-framework-bridge.zip .
   ```

2. **安装打包文件**
   - 在扩展管理页面点击"加载已解压的扩展程序"
   - 选择zip文件进行安装

## 🔧 使用方法

### 1. 基本使用

1. **访问测试页面**
   - 打开：https://intent-test-framework.vercel.app/execution

2. **选择Chrome桥接模式**
   - 在执行类型中选择"🌉 Chrome桥接"
   - 手动确认状态（勾选所有复选框）

3. **执行测试**
   - 选择测试用例
   - 点击"🚀 开始执行"
   - 观察浏览器中的实时执行过程

### 2. 扩展状态检查

点击Chrome工具栏中的扩展图标，可以：
- 查看扩展状态
- 测试连接
- 快速跳转到测试页面

### 3. 调试模式

1. **打开开发者工具**
   - 按F12或右键 → 检查

2. **查看控制台日志**
   - 扩展会输出详细的执行日志
   - 可以看到每个步骤的执行过程

## 🛠️ 技术架构

### 通信流程

```
WebUI → Content Script → Background Script → 页面操作
  ↓           ↓              ↓              ↓
消息发送 → 消息转发 → 步骤执行 → 结果返回
```

### 核心组件

1. **manifest.json** - 扩展配置文件
2. **background.js** - 后台脚本，处理核心逻辑
3. **content.js** - 内容脚本，注入到页面
4. **injected.js** - 注入脚本，创建全局对象
5. **popup.html/js** - 扩展弹窗界面

### 支持的操作

- ✅ **navigate** - 页面导航
- ✅ **click** - 元素点击
- ✅ **type** - 文本输入
- ✅ **wait** - 等待延迟
- ✅ **screenshot** - 页面截图
- ✅ **通用操作** - 其他自定义动作

## 🔍 故障排除

### 常见问题

1. **扩展未检测到**
   ```
   解决方案：
   - 确保扩展已安装并启用
   - 刷新测试页面
   - 检查控制台是否有错误
   ```

2. **执行失败**
   ```
   解决方案：
   - 检查元素定位器是否正确
   - 确保页面已完全加载
   - 查看控制台错误信息
   ```

3. **通信超时**
   ```
   解决方案：
   - 检查网络连接
   - 重新加载扩展
   - 重启Chrome浏览器
   ```

### 调试技巧

1. **查看扩展日志**
   ```
   chrome://extensions/ → 详细信息 → 检查视图：背景页
   ```

2. **查看页面日志**
   ```
   F12 → Console → 查看midscene相关日志
   ```

3. **测试扩展通信**
   ```javascript
   // 在控制台执行
   window.midsceneExtension.getStatus()
   ```

## 📋 开发说明

### 本地开发

1. **修改代码**
   - 编辑 `chrome_extension/` 目录下的文件

2. **重新加载扩展**
   - 在扩展管理页面点击刷新按钮

3. **测试功能**
   - 访问测试页面验证功能

### 发布准备

1. **更新版本号**
   - 修改 `manifest.json` 中的版本号

2. **打包扩展**
   ```bash
   cd chrome_extension
   zip -r ../intent-test-framework-bridge-v1.0.0.zip .
   ```

3. **测试安装**
   - 在新的Chrome配置文件中测试安装

## 🔮 未来计划

- [ ] 支持更多浏览器（Firefox、Edge）
- [ ] 增强元素定位能力
- [ ] 添加录制功能
- [ ] 支持并发执行
- [ ] 集成AI视觉识别

## 📞 支持

如有问题，请：
1. 查看控制台错误信息
2. 检查扩展状态
3. 提交Issue到GitHub仓库

---

**Intent Test Framework Bridge v1.0.0**  
让AI自动化测试真正可视化！🚀
