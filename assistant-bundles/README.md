# 助手提示词目录（assistant-bundles）

此目录用于存放运行时读取的助手提示词（persona/bundle）文件：

- intelligent-requirements-analyst-bundle.txt
- testmaster-song-bundle.txt

说明：
- 该目录为运行时唯一的读取来源，后端通过 web_gui/services/requirements_ai_service.py 的 BUNDLE_DIR 指向此目录。
- 请直接在此目录维护提示词文件；不再依赖 intelligent-requirements-analyzer 下的内容。

