#!/usr/bin/env python3
"""
代码质量检查脚本
用于检查项目代码是否符合PROJECT_RULES.md中定义的规范

使用方法:
    python scripts/quality_check.py
    python scripts/quality_check.py --fix  # 自动修复可修复的问题
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import ast
import re


class QualityChecker:
    """代码质量检查器"""

    def __init__(self, project_root: str, auto_fix: bool = False):
        self.project_root = Path(project_root)
        self.auto_fix = auto_fix
        self.issues = []

    def check_all(self) -> bool:
        """执行所有质量检查"""
        print("🔍 开始代码质量检查...")

        checks = [
            ("文件结构检查", self.check_file_structure),
            ("Python代码规范检查", self.check_python_style),
            ("JavaScript代码规范检查", self.check_javascript_style),
            ("文档注释检查", self.check_documentation),
            ("配置文件检查", self.check_configuration),
            ("安全性检查", self.check_security),
            ("依赖检查", self.check_dependencies),
        ]

        all_passed = True
        for check_name, check_func in checks:
            print(f"\n📋 {check_name}...")
            try:
                passed = check_func()
                if passed:
                    print(f"✅ {check_name} 通过")
                else:
                    print(f"❌ {check_name} 失败")
                    all_passed = False
            except Exception as e:
                print(f"⚠️ {check_name} 检查出错: {e}")
                all_passed = False

        self.print_summary()
        return all_passed

    def check_file_structure(self) -> bool:
        """检查文件结构是否符合规范"""
        required_dirs = [
            "web_gui",
            "web_gui/templates",
            "web_gui/static",
            "web_gui/static/css",
            "web_gui/static/js",
            "web_gui/static/screenshots",
            "PRD",
            "TASK",
            "tests",
            "logs",
        ]

        missing_dirs = []
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
                if self.auto_fix:
                    full_path.mkdir(parents=True, exist_ok=True)
                    print(f"🔧 自动创建目录: {dir_path}")

        if missing_dirs and not self.auto_fix:
            self.issues.append(f"缺少必要目录: {', '.join(missing_dirs)}")
            return False

        return True

    def check_python_style(self) -> bool:
        """检查Python代码风格"""
        python_files = list(self.project_root.glob("**/*.py"))
        if not python_files:
            return True

        # 检查是否安装了必要工具
        tools = ["flake8", "black"]
        for tool in tools:
            if not self._command_exists(tool):
                self.issues.append(f"缺少代码检查工具: {tool}")
                return False

        # 运行flake8检查
        try:
            result = subprocess.run(
                [
                    "flake8",
                    "--max-line-length=88",
                    "--exclude=node_modules,migrations,.venv,venv,.git,__pycache__",
                    ".",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                self.issues.append(f"Flake8检查失败:\n{result.stdout}")
                if self.auto_fix:
                    # 运行black自动格式化
                    subprocess.run(["black", "."], cwd=self.project_root)
                    print("🔧 已运行black自动格式化")
                return False
        except FileNotFoundError:
            self.issues.append("flake8未安装，请运行: pip install flake8")
            return False

        return True

    def check_javascript_style(self) -> bool:
        """检查JavaScript代码风格"""
        js_files = list(self.project_root.glob("**/*.js"))
        if not js_files:
            return True

        # 检查基本的JavaScript代码规范
        issues_found = False
        for js_file in js_files:
            if any(
                exclude in str(js_file)
                for exclude in ["node_modules", ".venv", "venv", ".git"]
            ):
                continue

            with open(js_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 检查基本规范
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                # 检查缩进（应该使用4个空格）
                if line.startswith("\t"):
                    self.issues.append(f"{js_file}:{i} 使用了Tab缩进，应使用4个空格")
                    issues_found = True

                # 检查行尾分号
                stripped = line.strip()
                if (
                    stripped
                    and not stripped.endswith((";", "{", "}", ")", ","))
                    and not stripped.startswith(
                        ("*", "//", "/*", "if", "for", "while", "function", "class")
                    )
                    and not stripped.endswith("*/")
                    and "=" in stripped
                ):
                    self.issues.append(f"{js_file}:{i} 可能缺少行尾分号")

        return not issues_found

    def check_documentation(self) -> bool:
        """检查文档注释完整性"""
        python_files = [
            f
            for f in self.project_root.glob("**/*.py")
            if not any(
                exclude in str(f)
                for exclude in ["node_modules", "__pycache__", ".venv", "venv", ".git"]
            )
        ]

        issues_found = False
        for py_file in python_files:
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)

                # 检查模块级文档字符串
                if not ast.get_docstring(tree):
                    self.issues.append(f"{py_file} 缺少模块级文档字符串")
                    issues_found = True

                # 检查类和函数的文档字符串
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        if not ast.get_docstring(node):
                            self.issues.append(f"{py_file} {node.name} 缺少文档字符串")
                            issues_found = True

                        # 检查公共方法（不以_开头）
                        if isinstance(
                            node, ast.FunctionDef
                        ) and not node.name.startswith("_"):
                            docstring = ast.get_docstring(node)
                            if docstring:
                                # 检查是否包含Args和Returns说明
                                if node.args.args and "Args:" not in docstring:
                                    self.issues.append(
                                        f"{py_file} {node.name} 文档字符串缺少Args说明"
                                    )
                                    issues_found = True

                                if (
                                    hasattr(node, "returns")
                                    and node.returns
                                    and "Returns:" not in docstring
                                ):
                                    self.issues.append(
                                        f"{py_file} {node.name} 文档字符串缺少Returns说明"
                                    )
                                    issues_found = True

            except Exception as e:
                self.issues.append(f"解析文件 {py_file} 时出错: {e}")
                issues_found = True

        return not issues_found

    def check_configuration(self) -> bool:
        """检查配置文件"""
        required_files = [
            "PROJECT_RULES.md",
            ".gitignore",
            "requirements.txt",
            "package.json",
        ]

        missing_files = []
        for file_name in required_files:
            file_path = self.project_root / file_name
            if not file_path.exists():
                missing_files.append(file_name)

        if missing_files:
            self.issues.append(f"缺少配置文件: {', '.join(missing_files)}")
            return False

        # 检查.gitignore内容
        gitignore_path = self.project_root / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                gitignore_content = f.read()

            required_ignores = [
                "__pycache__",
                "*.pyc",
                ".env",
                "node_modules",
                "logs/",
                ".DS_Store",
            ]

            missing_ignores = [
                ignore for ignore in required_ignores if ignore not in gitignore_content
            ]

            if missing_ignores:
                self.issues.append(f".gitignore缺少规则: {', '.join(missing_ignores)}")
                if self.auto_fix:
                    with open(gitignore_path, "a") as f:
                        f.write("\n# Auto-added by quality check\n")
                        for ignore in missing_ignores:
                            f.write(f"{ignore}\n")
                    print("🔧 已自动更新.gitignore")
                return False

        return True

    def check_security(self) -> bool:
        """检查安全性问题"""
        python_files = [
            f
            for f in self.project_root.glob("**/*.py")
            if not any(
                exclude in str(f)
                for exclude in ["node_modules", "__pycache__", ".venv", "venv", ".git"]
            )
        ]

        security_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "硬编码密码"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "硬编码API密钥"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "硬编码密钥"),
            (r"eval\s*\(", "使用了危险的eval函数"),
            (r"exec\s*\(", "使用了危险的exec函数"),
        ]

        issues_found = False
        for py_file in python_files:

            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern, message in security_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    self.issues.append(f"{py_file}:{line_num} {message}")
                    issues_found = True

        return not issues_found

    def check_dependencies(self) -> bool:
        """检查依赖管理"""
        requirements_file = self.project_root / "requirements.txt"
        package_json = self.project_root / "package.json"

        issues_found = False

        # 检查Python依赖
        if requirements_file.exists():
            with open(requirements_file, "r") as f:
                requirements = f.read()

            # 检查是否有版本固定
            lines = [line.strip() for line in requirements.split("\n") if line.strip()]
            for line in lines:
                if (
                    "==" not in line
                    and ">=" not in line
                    and line
                    and not line.startswith("#")
                ):
                    self.issues.append(f"requirements.txt中 {line} 没有指定版本")
                    issues_found = True

        # 检查Node.js依赖
        if package_json.exists():
            try:
                import json

                with open(package_json, "r") as f:
                    package_data = json.load(f)

                if (
                    "dependencies" not in package_data
                    and "devDependencies" not in package_data
                ):
                    self.issues.append("package.json中没有定义依赖")
                    issues_found = True
            except json.JSONDecodeError:
                self.issues.append("package.json格式错误")
                issues_found = True

        return not issues_found

    def _command_exists(self, command: str) -> bool:
        """检查命令是否存在"""
        try:
            subprocess.run([command, "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def print_summary(self):
        """打印检查结果摘要"""
        print("\n" + "=" * 60)
        print("📊 代码质量检查结果摘要")
        print("=" * 60)

        if not self.issues:
            print("🎉 恭喜！所有检查都通过了！")
        else:
            print(f"❌ 发现 {len(self.issues)} 个问题:")
            for i, issue in enumerate(self.issues, 1):
                print(f"{i}. {issue}")

        print("\n💡 建议:")
        print("- 定期运行此脚本检查代码质量")
        print("- 使用 --fix 参数自动修复可修复的问题")
        print("- 在提交代码前运行检查")


def main():
    parser = argparse.ArgumentParser(description="代码质量检查工具")
    parser.add_argument("--fix", action="store_true", help="自动修复可修复的问题")
    parser.add_argument("--root", default=".", help="项目根目录路径")

    args = parser.parse_args()

    checker = QualityChecker(args.root, args.fix)
    success = checker.check_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
