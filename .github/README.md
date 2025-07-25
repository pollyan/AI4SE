# GitHub Actions 配置说明

## 自动化测试工作流

本项目配置了自动化测试工作流，会在以下情况自动运行：

1. **推送到主分支**：当代码推送到 `master` 或 `main` 分支时
2. **Pull Request**：当创建或更新 Pull Request 时

## 测试矩阵

测试会在以下环境中运行：

- **操作系统**: Ubuntu Latest
- **Python版本**: 3.9, 3.10, 3.11

## 测试报告

每次测试运行会生成以下报告：

1. **HTML测试报告** (`report.html`)
2. **覆盖率报告** (`htmlcov/`)
3. **XML覆盖率报告** (`coverage.xml`)

这些报告会作为工件（artifacts）上传，可以在 GitHub Actions 运行页面下载。

## 查看测试结果

1. 进入仓库的 **Actions** 标签页
2. 选择最新的工作流运行
3. 查看测试结果和日志
4. 下载测试报告工件

## 徽章说明

README 中的徽章会实时显示：

- **测试状态**：显示最新的测试运行状态（通过/失败）
- **代码覆盖率**：显示测试覆盖的代码百分比
- **Python版本**：支持的Python版本
- **许可证**：项目使用的开源许可证

## 本地预览 GitHub Actions

如果想在本地测试 GitHub Actions 配置，可以使用 [act](https://github.com/nektos/act)：

```bash
# 安装 act
brew install act  # macOS
# 或查看 https://github.com/nektos/act 了解其他安装方法

# 运行工作流
act push

# 使用特定的Python版本
act push -P ubuntu-latest=python:3.11
```

## 故障排除

如果测试失败：

1. 检查测试日志中的错误信息
2. 确保所有依赖都已正确安装
3. 验证数据库迁移是否正确
4. 检查环境变量配置