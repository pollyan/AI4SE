# Intent Test Framework 部署指南

本指南将帮您将Intent Test Framework部署到Vercel + Supabase的免费云平台组合。

## 🎯 部署架构

```
GitHub Repository (代码托管)
    ↓
Vercel (应用部署)
    ↓
Supabase (数据库服务)
```

## 🚀 快速部署 (5分钟上线)

### 前置条件

- GitHub账户
- Vercel账户 (免费)
- Supabase账户 (免费)

### 步骤1: 准备Supabase数据库

1. **创建Supabase项目**:
   - 访问 https://supabase.com
   - 点击 "New Project"
   - 项目名称: `intent-test-framework`
   - 设置数据库密码并记住

2. **获取数据库连接字符串**:
   - 进入项目 → Settings → Database
   - 复制 "Connection string" 中的 URI:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@[HOST]:5432/postgres
   ```

### 步骤2: 部署到Vercel

1. **Fork GitHub仓库**:
   - 访问 https://github.com/pollyan/intent-test-framework
   - 点击右上角 "Fork" 按钮

2. **连接Vercel**:
   - 访问 https://vercel.com
   - 点击 "New Project"
   - 选择您fork的仓库
   - 点击 "Import"

3. **配置环境变量**:
   在Vercel部署页面的 "Environment Variables" 部分添加：

   ```bash
   # 必需配置
   DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@[HOST]:5432/postgres
   OPENAI_API_KEY=your_api_key_here
   OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
   MIDSCENE_MODEL_NAME=qwen-vl-max-latest
   SECRET_KEY=your_random_secret_key_here
   VERCEL=1
   
   # 可选配置
   DEBUG=false
   MIDSCENE_USE_QWEN_VL=1
   ```

4. **部署**:
   - 点击 "Deploy"
   - 等待部署完成 (约2-3分钟)

### 步骤3: 初始化数据库

部署完成后，数据库表会自动创建。如果需要迁移现有数据：

```bash
# 本地运行迁移脚本
python scripts/migrate_to_supabase.py --auto
```

### 步骤4: 验证部署

1. **访问应用**: 点击Vercel提供的部署URL
2. **检查功能**: 
   - 测试用例管理
   - 执行控制台
   - 测试报告

## 🔧 详细配置

### Supabase高级设置

#### 1. 数据库优化

在Supabase SQL编辑器中执行：

```sql
-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_test_cases_name ON test_cases(name);
CREATE INDEX IF NOT EXISTS idx_test_cases_category ON test_cases(category);
CREATE INDEX IF NOT EXISTS idx_execution_history_status ON execution_history(status);
CREATE INDEX IF NOT EXISTS idx_execution_history_start_time ON execution_history(start_time);

-- 设置行级安全策略 (可选)
ALTER TABLE test_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE execution_history ENABLE ROW LEVEL SECURITY;
```

#### 2. 实时功能配置

```sql
-- 启用实时更新 (可选)
ALTER PUBLICATION supabase_realtime ADD TABLE test_cases;
ALTER PUBLICATION supabase_realtime ADD TABLE execution_history;
```

### Vercel高级配置

#### 1. 自定义域名

1. 在Vercel项目设置中点击 "Domains"
2. 添加您的自定义域名
3. 配置DNS记录

#### 2. 性能优化

```json
// vercel.json 已包含优化配置
{
  "functions": {
    "web_gui/app_enhanced.py": {
      "maxDuration": 30
    }
  },
  "regions": ["hkg1"]
}
```

## 📊 监控和维护

### 应用监控

1. **Vercel Analytics**:
   - 访问量统计
   - 性能指标
   - 错误监控

2. **Supabase监控**:
   - 数据库性能
   - 连接数监控
   - 存储使用情况

### 日志查看

```bash
# Vercel函数日志
vercel logs [deployment-url]

# 本地调试
python web_gui/run_enhanced.py
```

## 🔒 安全配置

### 环境变量安全

1. **敏感信息保护**:
   - 所有API密钥通过环境变量配置
   - 不在代码中硬编码敏感信息

2. **数据库安全**:
   - 使用连接池限制并发连接
   - 启用SSL连接
   - 定期更新密码

### CORS配置

```python
# 已在app_enhanced.py中配置
CORS(app, origins="*")  # 生产环境建议限制域名
```

## 💰 成本分析

### 免费额度

**Vercel免费计划**:
- ✅ 100GB带宽/月
- ✅ 无限静态部署
- ✅ Serverless函数
- ✅ 自定义域名

**Supabase免费计划**:
- ✅ 500MB数据库存储
- ✅ 50MB文件存储
- ✅ 50,000次API请求/月
- ✅ 实时功能

**总成本**: 完全免费 (适合中小型项目)

### 扩容方案

当超出免费额度时：
- **Vercel Pro**: $20/月
- **Supabase Pro**: $25/月

## 🚨 故障排除

### 常见问题

1. **部署失败**:
   ```
   Error: Build failed
   ```
   - 检查requirements.txt依赖
   - 确认Python版本兼容性
   - 查看Vercel构建日志

2. **数据库连接失败**:
   ```
   ❌ 数据库连接失败
   ```
   - 验证DATABASE_URL格式
   - 检查Supabase项目状态
   - 确认网络连接

3. **函数超时**:
   ```
   Function execution timed out
   ```
   - 优化代码性能
   - 增加maxDuration配置
   - 使用异步处理

### 调试命令

```bash
# 本地测试数据库连接
python -c "from web_gui.database_config import validate_database_connection; print(validate_database_connection())"

# 检查环境变量
python -c "import os; print('DATABASE_URL:', os.getenv('DATABASE_URL', 'Not set'))"

# 测试应用启动
python web_gui/run_enhanced.py
```

## 🔄 CI/CD流程

### 自动部署

1. **推送到GitHub** → **Vercel自动部署**
2. **支持分支部署** → **预览环境**
3. **主分支部署** → **生产环境**

### 部署钩子

```bash
# 部署前钩子 (可选)
npm run build

# 部署后钩子 (可选)
python scripts/post_deploy.py
```

## 🎉 部署完成

恭喜！您的Intent Test Framework现在已经成功部署到云端。

### 下一步

1. **配置自定义域名** (可选)
2. **设置监控告警** (推荐)
3. **优化性能** (根据使用情况)
4. **备份数据** (定期)

### 获得的能力

- ✅ **全球访问**: CDN加速，全球快速访问
- ✅ **自动扩容**: 根据流量自动调整资源
- ✅ **高可用性**: 99.9%服务可用性保证
- ✅ **零运维**: 无需管理服务器和数据库
- ✅ **实时协作**: 多人同时使用测试平台

如有问题，请查看[故障排除](#故障排除)部分或在GitHub创建Issue。
