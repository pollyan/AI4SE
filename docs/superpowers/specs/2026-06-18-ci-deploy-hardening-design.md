# CI 与部署可信度加固设计

## 背景

本轮目标来自 2026-06-18 的代码库审查。当前仓库已经具备 New Agents 后端契约测试、前端 Vitest、部署脚本和 Docker Compose 配置，但 CI 与部署入口仍有几个信任缺口：New Agents 前端 CI 未执行类型检查，Python critical lint 在 workflow 中被 `|| true` 吞掉，生产 `.env` 写入 secrets 的 shell 片段对特殊字符较脆，本地部署模式指向不存在的 compose 文件，且一个 TypeScript 增量构建元数据文件仍被 Git 追踪。

## 目标

让提交和部署前的工程护栏更可信：

- New Agents 前端 CI 必须执行 `npm run lint` 和 `npm run test`。
- critical Python flake8 失败必须让 CI 失败。
- 生产 `.env` 写入逻辑避免用 `sed` 直接替换 secrets，并收紧 `.env` 权限。
- `scripts/ci/deploy.sh local` 使用仓库实际存在的 `docker-compose.dev.yml`。
- `tools/new-agents/tsconfig.tsbuildinfo` 不再被 Git 追踪。

## 设计

### CI workflow

修改 `.github/workflows/deploy.yml`：

- 在 New Agents frontend job 中，`npm ci` 后先运行 `npm run lint`，再运行 `npm run test`。
- 移除 code-quality job 中 flake8 命令末尾的 `|| true`。
- 把远端 `.env` 写入逻辑改成临时文件重建：先从现有 `.env` 复制除受管 key 之外的行，再用 `printf '%s=%s\n'` 追加受管变量，最后 `mv` 原子替换并 `chmod 600 .env`。

### 部署脚本

修改 `scripts/ci/deploy.sh`：

- local/dev/development 分支使用 `docker-compose.dev.yml`。
- 保持 production 分支和备份逻辑不变。

### 回归测试

新增 `tests/test_ci_deploy_hardening.py`，以文本检查保护这些脚本级不变量：

- workflow 的 New Agents frontend job 包含 `npm run lint` 且顺序早于 `npm run test`。
- workflow 不再包含 `flake8 ... || true`。
- workflow `.env` 管理片段不再用 `sed -i` 写 secrets，包含 `chmod 600 .env`，并有受管 key 过滤逻辑。
- `scripts/ci/deploy.sh` local 分支使用 `docker-compose.dev.yml`。
- Git 索引中没有 `*.tsbuildinfo`。

## 验收

- 聚焦测试 `pytest tests/test_ci_deploy_hardening.py -q` 通过。
- `bash -n scripts/ci/deploy.sh` 通过。
- New Agents frontend `npm run lint` 与 `npm run test` 通过。
- New Agents backend 非 slow 测试通过。
- critical flake8 当前通过。

## 风险与边界

本轮不实际 SSH 部署、不启动 Docker 栈，也不改 New Agents API/运行时契约。生产 secret 的真实值仍由 GitHub Secrets 提供，不写入仓库。
