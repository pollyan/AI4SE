# PostgreSQL 数据库配置指南

本系统**仅支持PostgreSQL数据库**，不再支持SQLite。请按照以下步骤配置PostgreSQL数据库。

## 📋 前提条件

1. **安装PostgreSQL驱动**
   ```bash
   pip install psycopg2-binary
   # 或者
   pip install psycopg2
   ```

2. **准备PostgreSQL数据库**
   - 本地PostgreSQL服务器
   - 或者云数据库服务（如Supabase、AWS RDS等）

## 🛠️ 本地开发环境配置

### 1. 安装PostgreSQL
```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql postgresql-server
```

### 2. 创建数据库和用户
```sql
-- 连接到PostgreSQL
psql -U postgres

-- 创建数据库
CREATE DATABASE intent_test;

-- 创建用户 (可选)
CREATE USER intent_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE intent_test TO intent_user;
```

### 3. 配置环境变量
```bash
# 复制环境变量示例文件
cp env.example .env

# 编辑.env文件，设置数据库连接
DATABASE_URL=postgresql://postgres:password@localhost:5432/intent_test
```

## ☁️ 云数据库配置 (Supabase)

### 1. 创建Supabase项目
1. 访问 [Supabase官网](https://supabase.com)
2. 创建新项目
3. 等待项目初始化完成

### 2. 获取数据库连接字符串
1. 进入项目设置 -> Database
2. 在"Connection string"部分找到PostgreSQL连接字符串
3. 复制连接字符串，格式类似：
   ```
   postgresql://postgres:[password]@[host]:5432/[database]
   ```

### 3. 配置环境变量
```bash
# 使用Supabase数据库
DATABASE_URL=postgresql://postgres:[password]@[host]:5432/[database]

# 或者使用Supabase专用配置
SUPABASE_DATABASE_URL=postgresql://postgres:[password]@[host]:5432/[database]
```

## 🚀 启动应用

```bash
# 确保环境变量已配置
export DATABASE_URL=postgresql://postgres:password@localhost:5432/intent_test

# 启动应用
python3 web_gui/app_enhanced.py
```

## 📊 验证配置

应用启动时会显示数据库配置信息：
```
🗄️  数据库配置信息:
   类型: PostgreSQL
   环境: 开发环境
   主机: localhost
   端口: 5432
   数据库: intent_test
```

## 🔧 故障排除

### 常见错误及解决方法

1. **PostgreSQL驱动未安装**
   ```
   ❌ PostgreSQL驱动未安装！
   请安装PostgreSQL驱动：pip install psycopg2-binary
   ```
   **解决方法**：安装PostgreSQL驱动
   ```bash
   pip install psycopg2-binary
   ```

2. **数据库连接配置缺失**
   ```
   ❌ 未找到PostgreSQL数据库配置！
   请设置DATABASE_URL环境变量
   ```
   **解决方法**：设置环境变量
   ```bash
   export DATABASE_URL=postgresql://postgres:password@localhost:5432/intent_test
   ```

3. **数据库连接失败**
   ```
   ❌ PostgreSQL数据库连接失败: connection refused
   ```
   **解决方法**：
   - 确保PostgreSQL服务运行中
   - 检查连接字符串中的主机、端口、用户名、密码
   - 确保数据库存在

## 📚 更多信息

- [PostgreSQL官方文档](https://www.postgresql.org/docs/)
- [Supabase数据库文档](https://supabase.com/docs/guides/database)
- [psycopg2文档](https://www.psycopg.org/docs/)

## 🆘 获取帮助

如果遇到问题，请检查：
1. PostgreSQL服务是否正在运行
2. 环境变量是否正确设置
3. 数据库连接字符串是否有效
4. 防火墙是否阻止了数据库连接

测试数据库连接：
```bash
python3 web_gui/database_config.py
```