# intelligent-requirements-analyzer 目录结构与使用说明

本目录用于存放不同 AI 助手（需求分析/测试分析）的运行时指令集（persona/bundle）。

关键事实
- 运行时仅使用 dist/ 目录内的打包结果：
  - intelligent-requirements-analyst-bundle.txt
  - testmaster-song-bundle.txt
- 其他 core/, templates/, workflows/ 等文件目前作为资料来源与未来扩展参考，不在运行路径上被直接读取。
- 服务端 IntelligentAssistantService 已固定从 dist/ 目录加载 bundle（见 web_gui/services/requirements_ai_service.py 中的 BUNDLE_DIR）。

建议与约定
- 如需更新 persona，请只修改 dist/ 下对应 txt，并在 PR 中说明来源（可以引用 core/ 或外部文档）。
- 如要引入动态生成/构建流程，建议在 scripts/ 下新增构建脚本，将 core/ → dist/ 的生成步骤自动化，但运行时仍只读取 dist/。

前后端协作
- 后端在无法读取 dist 文件时会降级到内置 fallback persona（极简提示），但建议确保 dist 文件存在，避免体验退化。
- 前端通过 /api/requirements/assistants/<assistant_type>/bundle 获取完整 bundle 内容。

维护建议
- 若确认 core/ 等目录暂时不再需要，可在后续重构中迁移到 docs/ 或 tools/，将运行时目录保持精简：仅 dist/ 与 README。

