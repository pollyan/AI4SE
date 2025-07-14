# Supabase设置指南

本指南将帮您将Intent Test Framework从SQLite迁移到Supabase PostgreSQL数据库。

## 🚀 快速开始

### 步骤1: 创建Supabase项目

1. **访问Supabase**: https://supabase.com
2. **注册/登录账户**
3. **创建新项目**:
   - 项目名称: `intent-test-framework`
   - 数据库密码: 设置一个强密码并记住
   - 区域: 选择离您最近的区域

### 步骤2: 获取数据库连接信息

1. **进入项目仪表板**
2. **点击左侧菜单 "Settings" -> "Database"**
3. **复制连接字符串**:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@[HOST]:5432/postgres
   ```

### 步骤3: 配置环境变量

1. **复制环境变量模板**:
   ```bash
   cp env.example .env
   ```

2. **编辑.env文件**，添加Supabase配置:
   ```bash
   # Supabase数据库配置
   DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@[HOST]:5432/postgres
   
   # 或者使用专用变量
   SUPABASE_DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@[HOST]:5432/postgres
   
   # Supabase项目配置 (可选)
   SUPABASE_URL=https://[project-id].supabase.co
   SUPABASE_ANON_KEY=your_anon_key_here
   ```

### 步骤4: 安装依赖

```bash
# 安装Python依赖 (包含PostgreSQL支持)
pip install -r requirements.txt

# 安装Node.js依赖
npm install
```

### 步骤5: 数据迁移

#### 方法1: 自动迁移 (推荐)

```bash
# 自动检测配置并迁移
python scripts/migrate_to_supabase.py --auto
```

#### 方法2: 手动指定数据库

```bash
# 手动指定源和目标数据库
python scripts/migrate_to_supabase.py \
  --source "sqlite:///web_gui/instance/gui_test_cases.db" \
  --target "postgresql://postgres:[password]@[host]:5432/postgres"
```

### 步骤6: 验证迁移

1. **启动应用**:
   ```bash
   python web_gui/run_enhanced.py
   ```

2. **检查日志输出**:
   ```
   🗄️  数据库配置信息:
      类型: PostgreSQL
      环境: 生产环境
      主机: [your-supabase-host]
      数据库: postgres
   ✅ 数据库初始化成功
   ```

3. **访问应用**: http://localhost:5001

## 🔧 高级配置

### Supabase仪表板功能

1. **表编辑器**: 直接在Web界面查看和编辑数据
2. **SQL编辑器**: 执行自定义SQL查询
3. **API文档**: 自动生成的RESTful API
4. **实时功能**: WebSocket支持
5. **认证系统**: 用户管理和权限控制

### 性能优化

1. **连接池配置**:
   ```python
   # 在database_config.py中已配置
   'pool_size': 10,
   'pool_timeout': 30,
   'pool_recycle': 3600,
   'max_overflow': 20,
   ```

2. **索引优化**:
   ```sql
   -- 迁移脚本会自动创建这些索引
   CREATE INDEX idx_test_cases_name ON test_cases(name);
   CREATE INDEX idx_execution_history_status ON execution_history(status);
   ```

### 备份和恢复

1. **自动备份**: Supabase提供自动备份功能
2. **手动备份**:
   ```bash
   pg_dump [connection-string] > backup.sql
   ```
3. **恢复数据**:
   ```bash
   psql [connection-string] < backup.sql
   ```

## 🚀 部署到Vercel

### 步骤1: 连接GitHub仓库

1. **访问Vercel**: https://vercel.com
2. **导入GitHub仓库**: `pollyan/intent-test-framework`

### 步骤2: 配置环境变量

在Vercel项目设置中添加环境变量:

```bash
# 必需的环境变量
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/postgres
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest
SECRET_KEY=your_secret_key
VERCEL=1

# 可选的环境变量
SUPABASE_URL=https://[project-id].supabase.co
SUPABASE_ANON_KEY=your_anon_key
DEBUG=false
```

### 步骤3: 部署

1. **推送代码到GitHub**
2. **Vercel自动部署**
3. **访问部署的应用**

## 🔍 故障排除

### 常见问题

1. **连接失败**:
   ```
   ❌ 数据库连接失败: connection to server failed
   ```
   - 检查DATABASE_URL是否正确
   - 确认Supabase项目状态正常
   - 验证网络连接

2. **迁移失败**:
   ```
   ❌ 迁移表 test_cases 失败
   ```
   - 检查源数据库文件是否存在
   - 确认目标数据库权限
   - 查看详细错误日志

3. **依赖问题**:
   ```
   ImportError: No module named 'psycopg2'
   ```
   - 安装PostgreSQL依赖: `pip install psycopg2-binary`

### 调试命令

```bash
# 测试数据库配置
python -c "from web_gui.database_config import print_database_info, validate_database_connection; print_database_info(); print(validate_database_connection())"

# 检查迁移日志
cat migration_log_*.txt

# 验证表结构
python -c "from web_gui.app_enhanced import app, db; app.app_context().push(); print([table.name for table in db.metadata.tables.values()])"
```

## 📊 监控和维护

### Supabase监控

1. **仪表板指标**: CPU、内存、连接数
2. **查询性能**: 慢查询分析
3. **存储使用**: 数据库大小监控

### 应用监控

1. **日志记录**: 应用运行日志
2. **错误追踪**: 异常监控
3. **性能指标**: 响应时间统计

## 🎉 完成

恭喜！您已经成功将Intent Test Framework迁移到Supabase PostgreSQL数据库。

现在您可以享受：
- ✅ **云端数据库**: 无需管理本地数据库文件
- ✅ **高可用性**: Supabase提供99.9%可用性保证
- ✅ **自动备份**: 数据安全有保障
- ✅ **实时功能**: 支持WebSocket实时更新
- ✅ **可扩展性**: 随着应用增长自动扩容

如有问题，请查看[故障排除](#故障排除)部分或创建GitHub Issue。
