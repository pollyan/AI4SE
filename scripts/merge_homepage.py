#!/usr/bin/env python3
"""
将 index.html 和 base_layout.html 合并为独立的 HTML 文件
并修正所有链接以适配新架构
"""

import re
import os

def merge_templates(base_path, index_path, output_path):
    """合并模板并生成独立 HTML"""
    
    # 读取文件
    with open(base_path, 'r', encoding='utf-8') as f:
        base_html = f.read()
    
    with open(index_path, 'r', encoding='utf-8') as f:
        index_html = f.read()
    
    # ========== 步骤 1: 提取 index.html 中的各个 block ==========
    
    # 提取 title block
    title_match = re.search(r'{%\s*block\s+title\s*%}(.*?){%\s*endblock\s*%}', index_html, re.DOTALL)
    title_content = title_match.group(1).strip() if title_match else "老兵大头的 AI4SE 工具集 - 智能化软件工程平台"
    
    # 提取 extra_css block  
    extra_css_match = re.search(r'{%\s*block\s+extra_css\s*%}(.*?){%\s*endblock\s*%}', index_html, re.DOTALL)
    extra_css_content = extra_css_match.group(1).strip() if extra_css_match else ""
    
    # 提取 content block
    content_match = re.search(r'{%\s*block\s+content\s*%}(.*?){%\s*endblock\s*%}', index_html, re.DOTALL)
    content_html = content_match.group(1).strip() if content_match else ""
    
    # ========== 步骤 2: 替换 base_layout 中的 blocks ==========
    
    # 替换 title
    base_html = re.sub(
        r'{%\s*block\s+title\s*%}.*?{%\s*endblock\s*%}',
        title_content,
        base_html,
        flags=re.DOTALL
    )
    
    # 替换 extra_css
    base_html = re.sub(
        r'{%\s*block\s+extra_css\s*%}{%\s*endblock\s*%}',
        extra_css_content,
        base_html
    )
    
    # 替换 content
    base_html = re.sub(
        r'{%\s*block\s+content\s*%}{%\s*endblock\s*%}',
        content_html,
        base_html
    )
    
    # 清空 page_title 和 page_subtitle（首页不需要页面标题）
    base_html = re.sub(r'{%\s*block\s+page_title\s*%}.*?{%\s*endblock\s*%}', '', base_html, flags=re.DOTALL)
    base_html = re.sub(r'{%\s*block\s+page_subtitle\s*%}.*?{%\s*endblock\s*%}', '', base_html, flags=re.DOTALL)
    base_html = re.sub(r'{%\s*block\s+container_class\s*%}.*?{%\s*endblock\s*%}', 'main-container', base_html, flags=re.DOTALL)
    
    # ========== 步骤 3: 移除所有 Jinja2 语法 ==========
    
    # 移除 {% if %} 条件块（包括内容）
    base_html = re.sub(r'{%\s*if\s+.*?%}.*?{%\s*endif\s*%}', '', base_html, flags=re.DOTALL)
    
    # 移除其他 {% %} 标签
    base_html = re.sub(r'{%.*?%}', '', base_html)
    
    # 移除 {{ }} 变量
    base_html = re.sub(r'{{.*?}}', '', base_html)
    
    # ========== 步骤 4: 修正链接以适配新架构 ==========
    
    link_mappings = {
        'href="/testcases"': 'href="/intent-tester/testcases"',
        'href="/execution"': 'href="/intent-tester/execution"',
        'href="/local-proxy"': 'href="/intent-tester/local-proxy"',
        'href="/download/local-proxy"': 'href="/intent-tester/download/local-proxy"',
        'href="/requirements-analyzer"': 'href="/ai-agents/"',
        'href="/config-management"': 'href="/ai-agents/config"',
        'href="/profile"': 'href="/intent-tester/profile"',
        'data-page="testcases"': 'href="/intent-tester/testcases"',
        'data-page="execution"': 'href="/intent-tester/execution"',
        'data-page="local-proxy"': 'href="/intent-tester/local-proxy"',
        'data-page="requirements-analyzer"': 'href="/ai-agents/"',
        'data-page="config-management"': 'href="/ai-agents/config"',
        'data-page="profile"': 'href="/intent-tester/profile"',
        'data-page=""': 'href="/"',
    }
    
    for old, new in link_mappings.items():
        base_html = base_html.replace(old, new)
    
    # ========== 步骤 5: 清理输出 ==========
    
    # 清理 "active" 类名残留（来自 Jinja2 条件）
    base_html = re.sub(r'class="([^"]*)\s+active\s*"', r'class="\1"', base_html)
    base_html = re.sub(r'class="active\s+([^"]*)"', r'class="\1"', base_html)
    base_html = re.sub(r'class="active"', 'class=""', base_html)
    
    # 清理空属性
    base_html = base_html.replace('class=""', '')
    
    # 清理多余空行
    base_html = re.sub(r'\n\s*\n\s*\n+', '\n\n', base_html)
    
    # 移除空的 page-header div
    base_html = re.sub(
        r'<div class="page-header">\s*<h1 class="page-title">AI4SE工具集</h1>\s*<p class="page-subtitle"></p>\s*</div>',
        '',
        base_html,
        flags=re.DOTALL
    )
    
    # ========== 额外步骤：注入下拉菜单点击处理脚本 ==========
    dropdown_script = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        // 简单的下拉菜单点击处理（针对移动端或hover失效情况）
        const dropdowns = document.querySelectorAll('.nav-dropdown');
        dropdowns.forEach(dropdown => {
            const trigger = dropdown.querySelector('.nav-dropdown-trigger');
            if (trigger) {
                trigger.addEventListener('click', function(e) {
                    // 如果点击的是链接但没有href，或者屏幕较小，则切换菜单显示
                    if (!this.getAttribute('href') || window.innerWidth < 768) {
                        e.preventDefault();
                        e.stopPropagation();
                        // 切换当前菜单的显示状态
                        const menu = dropdown.querySelector('.nav-dropdown-menu');
                        if (menu) {
                            const isVisible = menu.style.display === 'block' || menu.style.opacity === '1';
                            if (isVisible) {
                                menu.style.opacity = '';
                                menu.style.visibility = '';
                                menu.style.transform = '';
                            } else {
                                menu.style.opacity = '1';
                                menu.style.visibility = 'visible';
                                menu.style.transform = 'translateY(0)';
                            }
                        }
                    }
                });
            }
        });
        
        // 点击页面其他地方关闭菜单
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.nav-dropdown')) {
                document.querySelectorAll('.nav-dropdown-menu').forEach(menu => {
                    menu.style.opacity = '';
                    menu.style.visibility = '';
                    menu.style.transform = '';
                });
            }
        });
    });
    </script>
    """
    
    # 插入脚本到 </body> 之前
    base_html = base_html.replace('</body>', f'{dropdown_script}\n</body>')

    # ========== 步骤 6: 写入输出文件 ==========
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(base_html)
    
    print(f"✅ 成功生成: {output_path}")
    print(f"📄 文件大小: {len(base_html)} 字节")
    
    # 验证关键内容是否存在
    if '开始测试' in base_html:
        print("✅ 验证通过: 找到'开始测试'按钮")
    else:
        print("❌ 警告: 未找到'开始测试'按钮")
    
    if '开始对话' in base_html:
        print("✅ 验证通过: 找到'开始对话'按钮")
    else:
        print("❌ 警告: 未找到'开始对话'按钮")

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    
    base_path = os.path.join(project_root, 'web_gui/templates/base_layout.html')
    index_path = os.path.join(project_root, 'web_gui/templates/index.html')
    output_path = os.path.join(project_root, 'tools/frontend/public/index.html')
    
    merge_templates(base_path, index_path, output_path)
