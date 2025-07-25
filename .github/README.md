# GitHub Actions 配置说明

## 自动化测试工作流

本项目配置了两个独立的自动化测试工作流，会在以下情况自动运行：

1. **推送到主分支**：当代码推送到 `master` 或 `main` 分支时
2. **Pull Request**：当创建或更新 Pull Request 时

## 工作流程

### 1. Python Tests (python-tests.yml)
测试Python Web GUI层的功能

**触发条件**:
- 推送到主分支
- Pull Request
- 影响Python代码的文件变更

**测试矩阵**:
- **操作系统**: Ubuntu Latest
- **Python版本**: 3.11

**测试内容**:
- 单元测试 (tests/unit/)
- API测试 (tests/api/)
- 数据库模型测试
- Web界面功能测试

**生成报告**:
- HTML测试报告
- 覆盖率报告 (XML和HTML格式)
- Codecov集成

### 2. Proxy Server Tests (proxy-server-tests.yml) 🆕
测试本地代理服务器的核心功能

**触发条件**:
- 推送到主分支时以下文件发生变更：
  - `midscene_server.js`
  - `tests/proxy/**`
  - `package.json`
  - `jest.config.js`
- Pull Request包含上述文件变更
- 手动触发 (workflow_dispatch)

**测试矩阵**:
- **操作系统**: Ubuntu Latest
- **Node.js版本**: 18.x, 20.x

**测试内容**:
- HTTP API端点测试
- WebSocket通信测试
- AI功能模拟测试
- 资源管理测试
- 错误处理测试
- 性能基准测试

**生成报告**:
- Jest测试报告 (JUnit XML格式)
- 代码覆盖率报告 (LCOV格式)
- 独立的Codecov上传

## 并行执行优势

### 智能触发机制
两个工作流使用不同的路径过滤器，只在相关文件变更时触发：

- **Python工作流**: 默认触发，测试Web GUI层
- **代理服务器工作流**: 仅在代理相关文件变更时触发

### 性能优化
- **并行执行**: 两个工作流可以同时运行，显著提高CI效率
- **缓存策略**: 
  - Python: pip缓存
  - Node.js: npm缓存
- **矩阵策略**: 多版本并行测试

### 资源隔离
- **独立环境**: 每个工作流使用独立的运行环境
- **专用端口**: 代理服务器测试使用端口3002避免冲突
- **分离报告**: 测试结果和覆盖率分别上传

## 测试报告

### 查看测试结果
1. 进入仓库的 **Actions** 标签页
2. 选择对应的工作流运行
3. 查看测试结果和日志
4. 下载测试报告工件

### 工件说明

**Python Tests**:
- `test-results-3.11`: 包含单元测试和API测试报告
- 覆盖率报告: `htmlcov/` 目录

**Proxy Server Tests**:
- `proxy-test-results-node-18.x`: Node.js 18.x测试结果
- `proxy-test-results-node-20.x`: Node.js 20.x测试结果
- 覆盖率报告: `coverage/proxy/` 目录

### 覆盖率集成
- **Python**: 上传到Codecov，标签为 `unittests`
- **代理服务器**: 上传到Codecov，标签为 `proxy-server`
- **徽章**: README中的徽章会显示综合覆盖率

## 徽章说明

README 中的徽章会实时显示：

- **Python Tests**: 显示Python测试运行状态
- **Proxy Server Tests**: 显示代理服务器测试状态
- **代码覆盖率**: 显示综合测试覆盖率
- **Node.js版本**: 支持的Node.js版本
- **Python版本**: 支持的Python版本

## 本地测试

### Python测试
```bash
# 运行所有Python测试
python -m pytest

# 运行单元测试
python -m pytest tests/unit/ -v

# 运行API测试
python -m pytest tests/api/ -v

# 生成覆盖率报告
python -m pytest --cov=web_gui --cov-report=html
```

### 代理服务器测试
```bash
# 安装Node.js依赖
npm install

# 运行代理服务器测试
npm run test:proxy

# 运行测试并生成覆盖率
npm run test:proxy:coverage

# 监听模式
npm run test:proxy:watch
```

## 本地预览 GitHub Actions

使用 [act](https://github.com/nektos/act) 在本地测试 GitHub Actions：

```bash
# 安装 act
brew install act  # macOS

# 运行Python测试工作流
act push -W .github/workflows/python-tests.yml

# 运行代理服务器测试工作流
act push -W .github/workflows/proxy-server-tests.yml

# 运行特定作业
act push -j proxy-tests
```

## 故障排除

### Python测试失败
1. 检查Python版本兼容性
2. 验证数据库迁移
3. 确保依赖正确安装
4. 检查环境变量配置

### 代理服务器测试失败
1. 检查Node.js版本兼容性
2. 验证Jest配置正确性
3. 确保端口3002未被占用
4. 检查Mock配置
5. 验证WebSocket连接

### 性能问题
1. 检查缓存是否正常工作
2. 监控工作流运行时间
3. 优化测试并行度
4. 检查依赖安装时间

### 覆盖率问题
1. 确保测试覆盖关键代码路径
2. 检查覆盖率配置
3. 验证Codecov token配置
4. 查看覆盖率报告详情

## 最佳实践

### 提交代码
1. 提交前运行本地测试
2. 确保测试覆盖率符合要求
3. 检查代码质量
4. 添加适当的测试用例

### 工作流优化
1. 合理使用路径过滤器
2. 避免不必要的工作流触发
3. 优化缓存策略
4. 监控运行时间和资源使用

### 测试维护
1. 定期更新测试依赖
2. 清理过时的测试用例
3. 保持Mock数据的准确性
4. 监控测试稳定性

---

**注意**: 代理服务器测试是新增功能，提供了对本地代理服务器核心功能的全面测试覆盖，与现有Python测试完全独立并行运行。