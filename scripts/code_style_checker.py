"""
代码风格检查和自动修复工具
检查Python代码的风格规范，包括类型提示、格式化、命名规范等
"""
import os
import re
import ast
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class CodeStyleChecker:
    """代码风格检查器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.issues = []
        self.stats = {
            'files_checked': 0,
            'functions_without_types': 0,
            'missing_docstrings': 0,
            'naming_issues': 0,
            'import_issues': 0
        }
    
    def check_project(self, directories: List[str] = None) -> Dict[str, Any]:
        """检查整个项目的代码风格"""
        if directories is None:
            directories = ['web_gui']
        
        logger.info(f"开始检查项目代码风格...")
        
        for directory in directories:
            dir_path = self.project_root / directory
            if dir_path.exists():
                self._check_directory(dir_path)
        
        return self._generate_report()
    
    def _check_directory(self, directory: Path):
        """检查目录中的Python文件"""
        for py_file in directory.glob('**/*.py'):
            if self._should_skip_file(py_file):
                continue
                
            logger.info(f"检查文件: {py_file.relative_to(self.project_root)}")
            self._check_file(py_file)
            self.stats['files_checked'] += 1
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否跳过文件"""
        skip_patterns = [
            '*/migrations/*',
            '*/__pycache__/*',
            '*/.*',  # 隐藏文件
            'tests/*',  # 暂时跳过测试文件
        ]
        
        file_str = str(file_path)
        for pattern in skip_patterns:
            if file_str.find(pattern.replace('*', '')) != -1:
                return True
        
        return False
    
    def _check_file(self, file_path: Path):
        """检查单个文件"""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content, filename=str(file_path))
            
            # 检查各个方面
            self._check_imports(tree, file_path, content)
            self._check_functions(tree, file_path)
            self._check_classes(tree, file_path)
            self._check_constants(tree, file_path)
            self._check_docstrings(tree, file_path)
            
        except SyntaxError as e:
            self.issues.append({
                'file': str(file_path.relative_to(self.project_root)),
                'type': 'syntax_error',
                'line': e.lineno,
                'message': f'语法错误: {e.msg}',
                'severity': 'error'
            })
        except Exception as e:
            logger.error(f"检查文件 {file_path} 时出错: {e}")
    
    def _check_imports(self, tree: ast.AST, file_path: Path, content: str):
        """检查导入语句"""
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                # 检查是否有未使用的导入
                for alias in node.names:
                    if not self._is_import_used(content, alias.name):
                        self.issues.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'type': 'unused_import',
                            'line': node.lineno,
                            'message': f'未使用的导入: {alias.name}',
                            'severity': 'warning'
                        })
            
            elif isinstance(node, ast.ImportFrom):
                # 检查from imports
                if node.module and len(node.names) > 10:
                    self.issues.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'type': 'too_many_imports',
                        'line': node.lineno,
                        'message': f'单个from语句导入项目过多 ({len(node.names)})',
                        'severity': 'info'
                    })
        
        # 检查typing导入
        typing_imports = ['typing', 'Dict', 'List', 'Optional', 'Union', 'Any', 'Tuple']
        has_typing = any(imp in content for imp in typing_imports)
        
        if not has_typing:
            # 检查是否有函数定义
            has_functions = any(isinstance(node, ast.FunctionDef) for node in ast.walk(tree))
            if has_functions:
                self.issues.append({
                    'file': str(file_path.relative_to(self.project_root)),
                    'type': 'missing_typing',
                    'line': 1,
                    'message': '文件包含函数但缺少typing导入',
                    'severity': 'info'
                })
                self.stats['import_issues'] += 1
    
    def _check_functions(self, tree: ast.AST, file_path: Path):
        """检查函数定义"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检查函数名称规范
                if not re.match(r'^[a-z_][a-z0-9_]*$', node.name) and not node.name.startswith('_'):
                    self.issues.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'type': 'naming_convention',
                        'line': node.lineno,
                        'message': f'函数名不符合snake_case规范: {node.name}',
                        'severity': 'warning'
                    })
                    self.stats['naming_issues'] += 1
                
                # 检查返回类型注解
                if not node.returns and not node.name.startswith('_'):
                    self.issues.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'type': 'missing_return_type',
                        'line': node.lineno,
                        'message': f'函数缺少返回类型注解: {node.name}',
                        'severity': 'info'
                    })
                    self.stats['functions_without_types'] += 1
                
                # 检查参数类型注解
                missing_param_types = []
                for arg in node.args.args:
                    if not arg.annotation and arg.arg != 'self':
                        missing_param_types.append(arg.arg)
                
                if missing_param_types:
                    self.issues.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'type': 'missing_param_types',
                        'line': node.lineno,
                        'message': f'函数 {node.name} 的参数缺少类型注解: {", ".join(missing_param_types)}',
                        'severity': 'info'
                    })
    
    def _check_classes(self, tree: ast.AST, file_path: Path):
        """检查类定义"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 检查类名规范
                if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                    self.issues.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'type': 'naming_convention',
                        'line': node.lineno,
                        'message': f'类名不符合PascalCase规范: {node.name}',
                        'severity': 'warning'
                    })
                    self.stats['naming_issues'] += 1
    
    def _check_constants(self, tree: ast.AST, file_path: Path):
        """检查常量定义"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id
                        # 检查模块级别的常量
                        if (isinstance(node.value, (ast.Str, ast.Num, ast.Constant)) and 
                            name.isupper() and len(name) > 1):
                            # 这是一个常量，检查命名规范
                            if not re.match(r'^[A-Z_][A-Z0-9_]*$', name):
                                self.issues.append({
                                    'file': str(file_path.relative_to(self.project_root)),
                                    'type': 'naming_convention',
                                    'line': node.lineno,
                                    'message': f'常量名不符合UPPER_CASE规范: {name}',
                                    'severity': 'warning'
                                })
                                self.stats['naming_issues'] += 1
    
    def _check_docstrings(self, tree: ast.AST, file_path: Path):
        """检查文档字符串"""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not self._has_docstring(node):
                    if not node.name.startswith('_'):  # 跳过私有方法
                        self.issues.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'type': 'missing_docstring',
                            'line': node.lineno,
                            'message': f'缺少文档字符串: {node.name}',
                            'severity': 'info'
                        })
                        self.stats['missing_docstrings'] += 1
    
    def _has_docstring(self, node) -> bool:
        """检查节点是否有文档字符串"""
        if (node.body and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, (ast.Str, ast.Constant))):
            return True
        return False
    
    def _is_import_used(self, content: str, import_name: str) -> bool:
        """检查导入是否被使用（简化版本）"""
        # 简单检查，可以改进
        return import_name in content.replace(f'import {import_name}', '')
    
    def _generate_report(self) -> Dict[str, Any]:
        """生成检查报告"""
        # 按严重程度分组
        issues_by_severity = {'error': [], 'warning': [], 'info': []}
        for issue in self.issues:
            issues_by_severity[issue['severity']].append(issue)
        
        # 按文件分组
        issues_by_file = {}
        for issue in self.issues:
            file_path = issue['file']
            if file_path not in issues_by_file:
                issues_by_file[file_path] = []
            issues_by_file[file_path].append(issue)
        
        return {
            'summary': {
                'total_issues': len(self.issues),
                'files_checked': self.stats['files_checked'],
                'errors': len(issues_by_severity['error']),
                'warnings': len(issues_by_severity['warning']),
                'info': len(issues_by_severity['info']),
                'stats': self.stats
            },
            'issues_by_severity': issues_by_severity,
            'issues_by_file': issues_by_file,
            'issues': self.issues
        }
    
    def print_report(self, report: Dict[str, Any]):
        """打印检查报告"""
        summary = report['summary']
        
        print("\n" + "="*60)
        print("代码风格检查报告")
        print("="*60)
        print(f"检查文件数: {summary['files_checked']}")
        print(f"总问题数: {summary['total_issues']}")
        print(f"  - 错误: {summary['errors']}")
        print(f"  - 警告: {summary['warnings']}")
        print(f"  - 信息: {summary['info']}")
        print()
        print("详细统计:")
        print(f"  - 缺少类型注解的函数: {summary['stats']['functions_without_types']}")
        print(f"  - 缺少文档字符串: {summary['stats']['missing_docstrings']}")
        print(f"  - 命名规范问题: {summary['stats']['naming_issues']}")
        print(f"  - 导入问题: {summary['stats']['import_issues']}")
        
        if summary['total_issues'] > 0:
            print("\n按文件分组的问题:")
            print("-" * 40)
            
            for file_path, issues in report['issues_by_file'].items():
                print(f"\n📁 {file_path} ({len(issues)} 个问题)")
                
                # 按类型分组显示
                issues_by_type = {}
                for issue in issues:
                    issue_type = issue['type']
                    if issue_type not in issues_by_type:
                        issues_by_type[issue_type] = []
                    issues_by_type[issue_type].append(issue)
                
                for issue_type, type_issues in issues_by_type.items():
                    print(f"  {issue_type}: {len(type_issues)} 个")
                    for issue in type_issues[:3]:  # 只显示前3个
                        severity_icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}
                        print(f"    {severity_icon.get(issue['severity'], '•')} L{issue['line']}: {issue['message']}")
                    
                    if len(type_issues) > 3:
                        print(f"    ... 还有 {len(type_issues) - 3} 个")
        else:
            print("\n🎉 恭喜！没有发现代码风格问题。")


def main():
    """主函数"""
    # 获取项目根目录
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    
    print(f"Intent Test Framework 代码风格检查工具")
    print(f"项目根目录: {project_root}")
    
    # 创建检查器
    checker = CodeStyleChecker(str(project_root))
    
    # 执行检查
    report = checker.check_project(['web_gui'])
    
    # 打印报告
    checker.print_report(report)
    
    # 生成建议
    print("\n📋 改进建议:")
    print("-" * 30)
    
    if report['summary']['stats']['functions_without_types'] > 0:
        print("1. 为函数添加类型注解可以提高代码可读性和IDE支持")
    
    if report['summary']['stats']['missing_docstrings'] > 0:
        print("2. 添加文档字符串有助于代码维护和团队协作")
    
    if report['summary']['stats']['naming_issues'] > 0:
        print("3. 遵循Python命名规范（PEP 8）提高代码一致性")
    
    print("4. 建议使用 black 和 isort 自动格式化代码")
    print("5. 建议使用 mypy 进行类型检查")
    
    return 0 if report['summary']['total_issues'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())