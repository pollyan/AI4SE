# HTTP接口调用功能特性文档

## 📋 文档概述

本文件夹包含Intent Test Framework中HTTP接口调用功能的完整需求和设计文档。该功能允许在测试用例中调用RESTful API，实现UI测试与API测试的无缝集成。

## 📁 文档结构

### 核心文档
1. **[PRD-HTTP接口调用功能.md](./PRD-HTTP接口调用功能.md)**
   - 产品需求文档，定义功能范围和业务价值
   - 包含功能需求、非功能需求、验收标准
   - 实现路线图和成功指标

2. **[技术设计文档-HTTP接口调用.md](./技术设计文档-HTTP接口调用.md)**
   - 详细的技术架构设计
   - 模块设计、数据结构、接口定义
   - 实现细节和部署方案

3. **[用户故事-HTTP接口调用.md](./用户故事-HTTP接口调用.md)**
   - 以用户为中心的功能描述
   - 详细的验收标准和用户体验流程
   - 覆盖所有主要使用场景

4. **[API规格-HTTP步骤配置.md](./API规格-HTTP步骤配置.md)**
   - HTTP步骤的配置格式规范
   - REST API接口定义
   - 配置示例和错误码定义

## 🎯 功能概述

### 核心价值
- **端到端测试**: 支持UI操作与API验证的完整测试流程
- **数据驱动**: 通过API动态准备和验证测试数据
- **无缝集成**: 与现有AI测试步骤完美协作
- **变量共享**: 统一的变量系统，支持数据在步骤间传递

### 主要功能
- ✅ 支持全部HTTP方法 (GET/POST/PUT/DELETE/PATCH)
- ✅ 多种认证方式 (Bearer Token, API Key, Basic Auth)
- ✅ 响应验证和断言 (状态码、内容、时间)
- ✅ 变量提取和存储 (JSONPath支持)
- ✅ 错误处理和重试机制
- ✅ 调试和日志功能

## 🏗️ 技术架构

### 技术选型
- **HTTP执行**: Playwright fetch API (浏览器上下文)
- **变量提取**: jsonpath-ng (Python)
- **UI集成**: 现有步骤编辑器扩展
- **数据存储**: 现有变量管理系统

### 架构优势
- 统一执行环境，与AI步骤共享浏览器状态
- 自动Cookie和Session管理
- 简化的变量作用域和生命周期
- 一致的错误处理和日志记录

## 🚀 实现计划

### 阶段1: 核心功能 (2-3周)
- HTTP请求执行器
- 基础变量集成
- 简单配置界面
- 基础错误处理

### 阶段2: 增强功能 (1-2周)
- 认证机制完善
- 响应验证和断言
- 错误处理和重试
- 更多HTTP方法支持

### 阶段3: 用户体验 (1周)
- 配置界面优化
- 调试工具完善
- 文档和帮助信息
- 完整集成测试

## 📝 使用示例

### 典型测试流程
```yaml
步骤1: AI操作 - 获取页面基础信息
  输出变量: baseUrl, authToken

步骤2: HTTP请求 - 创建测试数据  
  方法: POST ${baseUrl}/api/users
  认证: Bearer ${authToken}
  输出变量: userId, userEmail

步骤3: AI操作 - 使用测试数据执行业务流程
  使用变量: userId, userEmail

步骤4: HTTP请求 - 验证后端状态
  方法: GET ${baseUrl}/api/users/${userId}
  断言: 用户状态正确
```

### 配置示例
```json
{
  "action": "http_request",
  "description": "创建用户账号",
  "params": {
    "method": "POST",
    "url": "${baseUrl}/api/users",
    "headers": {
      "Content-Type": "application/json",
      "Authorization": "Bearer ${authToken}"
    },
    "body": {
      "username": "${userName}",
      "email": "${userEmail}"
    },
    "assertions": [
      {"type": "status_code", "expected": 201},
      {"type": "json_path", "path": "$.id", "condition": "exists"}
    ],
    "extract_variables": {
      "userId": "$.id",
      "createdAt": "$.created_at"
    }
  }
}
```

## ✅ 验收标准

### 功能完整性
- [ ] 所有HTTP方法正常工作
- [ ] 认证机制功能正确
- [ ] 响应断言准确可靠
- [ ] 变量提取和使用正常
- [ ] 错误处理和重试正确

### 集成性
- [ ] 步骤编辑器完美集成
- [ ] 与AI步骤协作正常
- [ ] 执行报告完整准确
- [ ] 实时更新功能正常

### 用户体验
- [ ] 配置界面简洁易用
- [ ] 错误信息清晰明确
- [ ] 调试信息丰富详细
- [ ] 操作响应迅速流畅

## 🔗 相关资源

### 项目文档
- [Intent Test Framework架构文档](../../architecture/)
- [现有变量系统文档](../../tools/数据流功能/)
- [MidSceneJS集成指南](../../../midscene_framework/)

### 外部资源
- [JSONPath语法参考](https://jsonpath.com/)
- [HTTP状态码参考](https://httpstatuses.com/)
- [REST API设计指南](https://restfulapi.net/)

## 📞 联系方式

### 开发团队
- **需求分析**: Mary (Business Analyst)
- **技术架构**: Development Team
- **测试验证**: QA Team

### 文档维护
本文档由业务分析师Mary创建和维护，将根据开发进展和用户反馈持续更新。

---

**文档版本**: v1.0  
**最后更新**: 2025-08-16  
**状态**: 需求分析完成，等待开发实现

*这是一个活文档，将随着功能开发过程持续演进和完善*