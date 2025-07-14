#!/usr/bin/env python3
"""
开发环境设置脚本
用于快速设置符合项目规范的开发环境

使用方法:
    python scripts/setup_dev_env.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path


class DevEnvironmentSetup:
    """开发环境设置器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.success_count = 0
        self.total_steps = 0

    def setup_all(self):
        """设置完整的开发环境"""
        print("🚀 开始设置开发环境...")
        print(f"📁 项目根目录: {self.project_root}")

        steps = [
            ("创建必要目录", self.create_directories),
            ("设置Python环境", self.setup_python_env),
            ("安装Python依赖", self.install_python_deps),
            ("设置Node.js环境", self.setup_nodejs_env),
            ("创建配置文件", self.create_config_files),
            ("设置Git配置", self.setup_git_config),
            ("设置编辑器配置", self.setup_editor_config),
            ("设置Git Hooks", self.setup_git_hooks),
            ("验证环境", self.verify_environment),
        ]

        self.total_steps = len(steps)

        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            try:
                if step_func():
                    print(f"✅ {step_name} 完成")
                    self.success_count += 1
                else:
                    print(f"⚠️ {step_name} 跳过或部分完成")
            except Exception as e:
                print(f"❌ {step_name} 失败: {e}")

        self.print_summary()

    def create_directories(self) -> bool:
        """创建必要的目录结构"""
        directories = [
            "web_gui/static/css",
            "web_gui/static/js",
            "web_gui/static/screenshots",
            "logs",
            "tests",
            "docs",
            "scripts",
            "PRD",
            "TASK",
        ]

        for dir_path in directories:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"  📁 创建目录: {dir_path}")

        return True

    def setup_python_env(self) -> bool:
        """设置Python环境"""
        # 检查Python版本
        python_version = sys.version_info
        if python_version < (3, 8):
            print(f"⚠️ Python版本过低: {python_version.major}.{python_version.minor}")
            print("建议使用Python 3.8+")
            return False

        print(
            f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}"
        )

        # 检查虚拟环境
        if hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ):
            print("✅ 已在虚拟环境中")
        else:
            print("⚠️ 建议在虚拟环境中运行")
            print("创建虚拟环境: python -m venv venv")
            print(
                "激活虚拟环境: source venv/bin/activate (Linux/Mac) 或 venv\\Scripts\\activate (Windows)"
            )

        return True

    def install_python_deps(self) -> bool:
        """安装Python依赖"""
        requirements_file = self.project_root / "requirements.txt"

        if not requirements_file.exists():
            print("⚠️ requirements.txt 不存在，创建基础依赖文件")
            basic_requirements = [
                "flask>=2.0.0",
                "flask-socketio>=5.0.0",
                "python-socketio>=5.0.0",
                "requests>=2.25.0",
                "python-dotenv>=0.19.0",
                "black>=22.0.0",
                "flake8>=4.0.0",
                "pytest>=6.0.0",
                "pytest-cov>=3.0.0",
            ]

            with open(requirements_file, "w") as f:
                f.write("\n".join(basic_requirements))
            print("📝 已创建 requirements.txt")

        # 安装依赖
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                cwd=self.project_root,
                check=True,
            )
            print("✅ Python依赖安装完成")
            return True
        except subprocess.CalledProcessError:
            print("❌ Python依赖安装失败")
            return False

    def setup_nodejs_env(self) -> bool:
        """设置Node.js环境"""
        package_json = self.project_root / "package.json"

        if not package_json.exists():
            print("⚠️ package.json 不存在，创建基础配置")
            package_config = {
                "name": "ai-webui-auto",
                "version": "1.0.0",
                "description": "AI Web自动化测试系统",
                "main": "midscene_server.js",
                "scripts": {
                    "start": "node midscene_server.js",
                    "test": 'echo "Error: no test specified" && exit 1',
                },
                "dependencies": {
                    "@midscene/web": "latest",
                    "express": "^4.18.0",
                    "socket.io": "^4.7.0",
                },
                "devDependencies": {"eslint": "^8.0.0", "prettier": "^2.8.0"},
            }

            with open(package_json, "w") as f:
                json.dump(package_config, f, indent=2)
            print("📝 已创建 package.json")

        # 检查npm是否可用
        try:
            subprocess.run(["npm", "--version"], capture_output=True, check=True)
            print("✅ npm 可用")

            # 安装Node.js依赖
            subprocess.run(["npm", "install"], cwd=self.project_root, check=True)
            print("✅ Node.js依赖安装完成")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️ npm 不可用，请安装Node.js")
            return False

    def create_config_files(self) -> bool:
        """创建配置文件"""
        configs = {
            ".env.example": """# AI服务配置
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest
MIDSCENE_USE_QWEN_VL=1

# 应用配置
DEBUG=false
SECRET_KEY=your_secret_key_here

# 数据库配置
DATABASE_URL=sqlite:///app.db

# 文件路径配置
SCREENSHOT_DIR=web_gui/static/screenshots
LOG_DIR=logs""",
            ".flake8": """[flake8]
max-line-length = 88
exclude = node_modules,migrations,venv,.git,__pycache__
ignore = E203,W503""",
            "pyproject.toml": """[tool.black]
line-length = 88
target-version = ['py38']
include = '\\.pyi?$'
exclude = '''
/(
    \\.git
  | \\.hg
  | \\.mypy_cache
  | \\.tox
  | \\.venv
  | _build
  | buck-out
  | build
  | dist
  | node_modules
)/
'''""",
            ".gitignore": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
.env
logs/
web_gui/static/screenshots/*.png
!web_gui/static/screenshots/.gitkeep

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Database
*.db
*.sqlite3""",
        }

        for filename, content in configs.items():
            file_path = self.project_root / filename
            if not file_path.exists():
                with open(file_path, "w") as f:
                    f.write(content)
                print(f"📝 创建配置文件: {filename}")

        # 创建.gitkeep文件
        gitkeep_dirs = ["logs", "web_gui/static/screenshots"]
        for dir_name in gitkeep_dirs:
            gitkeep_path = self.project_root / dir_name / ".gitkeep"
            gitkeep_path.touch()

        return True

    def setup_git_config(self) -> bool:
        """设置Git配置"""
        try:
            # 检查Git是否可用
            subprocess.run(["git", "--version"], capture_output=True, check=True)

            # 设置Git配置
            git_configs = [
                ("core.autocrlf", "input"),
                ("core.safecrlf", "true"),
                ("pull.rebase", "false"),
            ]

            for key, value in git_configs:
                try:
                    subprocess.run(
                        ["git", "config", key, value], cwd=self.project_root, check=True
                    )
                    print(f"  ⚙️ 设置Git配置: {key} = {value}")
                except subprocess.CalledProcessError:
                    pass  # 忽略配置失败

            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️ Git 不可用")
            return False

    def setup_editor_config(self) -> bool:
        """设置编辑器配置"""
        vscode_dir = self.project_root / ".vscode"
        vscode_dir.mkdir(exist_ok=True)

        settings = {
            "python.formatting.provider": "black",
            "python.linting.enabled": True,
            "python.linting.flake8Enabled": True,
            "editor.formatOnSave": True,
            "files.trimTrailingWhitespace": True,
            "files.insertFinalNewline": True,
            "editor.tabSize": 4,
            "editor.insertSpaces": True,
        }

        settings_file = vscode_dir / "settings.json"
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)

        print("📝 创建VSCode配置")
        return True

    def setup_git_hooks(self) -> bool:
        """设置Git Hooks"""
        hooks_script = self.project_root / "scripts" / "setup_git_hooks.sh"
        if hooks_script.exists():
            try:
                subprocess.run(["bash", str(hooks_script)], check=True)
                print("✅ Git Hooks 设置完成")
                return True
            except subprocess.CalledProcessError:
                print("⚠️ Git Hooks 设置失败")
                return False
        else:
            print("⚠️ Git Hooks 脚本不存在")
            return False

    def verify_environment(self) -> bool:
        """验证环境设置"""
        print("🔍 验证开发环境...")

        checks = [
            ("Python", lambda: sys.version_info >= (3, 8)),
            ("Flask", lambda: self._check_import("flask")),
            ("Black", lambda: self._check_command("black")),
            ("Flake8", lambda: self._check_command("flake8")),
            ("Git", lambda: self._check_command("git")),
        ]

        all_passed = True
        for name, check_func in checks:
            try:
                if check_func():
                    print(f"  ✅ {name}")
                else:
                    print(f"  ❌ {name}")
                    all_passed = False
            except Exception:
                print(f"  ❌ {name}")
                all_passed = False

        return all_passed

    def _check_import(self, module_name: str) -> bool:
        """检查Python模块是否可导入"""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False

    def _check_command(self, command: str) -> bool:
        """检查命令是否可用"""
        try:
            subprocess.run([command, "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def print_summary(self):
        """打印设置结果摘要"""
        print("\n" + "=" * 60)
        print("📊 开发环境设置结果")
        print("=" * 60)
        print(f"✅ 完成步骤: {self.success_count}/{self.total_steps}")

        if self.success_count == self.total_steps:
            print("🎉 开发环境设置完成！")
        else:
            print("⚠️ 部分步骤未完成，请检查上述输出")

        print("\n📋 下一步:")
        print("1. 复制 .env.example 为 .env 并填入正确的配置")
        print("2. 运行 python scripts/quality_check.py 检查代码质量")
        print("3. 运行 python web_gui/run_enhanced.py 启动应用")
        print("4. 访问 http://localhost:5001 查看Web界面")


def main():
    setup = DevEnvironmentSetup()
    setup.setup_all()


if __name__ == "__main__":
    main()
