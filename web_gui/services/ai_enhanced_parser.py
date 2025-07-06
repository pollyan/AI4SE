"""
AI增强的自然语言解析器
使用AI模型来更智能地解析用户的自然语言测试描述
"""
import re
import json
from typing import List, Dict, Any, Optional
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from midscene_python import MidSceneAI

class AITestCaseParser:
    """AI增强的测试用例解析器"""
    
    def __init__(self):
        self.ai = None
        self.step_patterns = {
            'input': [
                r'输入|填写|填入|键入',
                r'在.*?[框|栏|字段].*?输入',
                r'搜索.*?关键词'
            ],
            'click': [
                r'点击|按|选择|单击',
                r'点击.*?[按钮|链接|选项]',
                r'提交|确认|登录'
            ],
            'wait': [
                r'等待|等候',
                r'加载|完成|出现',
                r'直到.*?显示'
            ],
            'assert': [
                r'验证|检查|确认|断言',
                r'应该|必须|需要',
                r'页面.*?显示|包含.*?内容'
            ],
            'query': [
                r'提取|获取|查询|收集',
                r'获取.*?信息|提取.*?数据',
                r'统计|计算|分析'
            ],
            'scroll': [
                r'滚动|翻页|下拉|上拉',
                r'向.*?滚动',
                r'滚动到.*?位置'
            ]
        }
    
    def get_ai_instance(self) -> Optional[MidSceneAI]:
        """获取AI实例"""
        if self.ai is None:
            try:
                self.ai = MidSceneAI()
            except Exception as e:
                print(f"AI初始化失败: {e}")
                return None
        return self.ai
    
    def parse_with_ai(self, natural_input: str, target_url: str = None) -> List[Dict[str, Any]]:
        """
        使用AI模型解析自然语言描述
        这是更高级的解析方法，可以理解复杂的测试场景
        """
        ai = self.get_ai_instance()
        if not ai:
            # 如果AI不可用，回退到规则解析
            return self.parse_with_rules(natural_input, target_url)
        
        try:
            # 构造AI提示词
            prompt = f"""
请将以下自然语言测试描述转换为结构化的测试步骤。

测试描述：
{natural_input}

目标网址：{target_url or '未指定'}

请返回JSON格式的测试步骤数组，每个步骤包含以下字段：
- type: 操作类型 (goto, ai_input, ai_tap, ai_wait_for, ai_assert, ai_query, ai_scroll, ai_action)
- description: 步骤描述
- params: 参数对象

支持的操作类型说明：
- goto: 导航到网页，params: {{"url": "网址"}}
- ai_input: AI输入文本，params: {{"text": "输入内容", "locate_prompt": "输入框描述"}}
- ai_tap: AI点击元素，params: {{"prompt": "元素描述"}}
- ai_wait_for: AI等待条件，params: {{"prompt": "等待条件描述"}}
- ai_assert: AI验证断言，params: {{"prompt": "验证条件描述"}}
- ai_query: AI查询数据，params: {{"prompt": "查询描述"}}
- ai_scroll: AI滚动页面，params: {{"direction": "方向", "scroll_type": "类型"}}
- ai_action: AI通用操作，params: {{"prompt": "操作描述"}}

示例输出：
[
  {{
    "type": "goto",
    "description": "访问百度首页",
    "params": {{"url": "https://www.baidu.com"}}
  }},
  {{
    "type": "ai_input",
    "description": "在搜索框输入关键词",
    "params": {{"text": "人工智能", "locate_prompt": "搜索框"}}
  }},
  {{
    "type": "ai_tap",
    "description": "点击搜索按钮",
    "params": {{"prompt": "百度一下按钮"}}
  }}
]

请只返回JSON数组，不要包含其他文字说明。
"""
            
            # 注意：这里我们不能直接调用AI，因为当前的MidSceneAI需要浏览器环境
            # 在实际实现中，可能需要单独的AI服务来处理这种文本解析
            # 目前先使用规则解析作为备选方案
            return self.parse_with_rules(natural_input, target_url)
            
        except Exception as e:
            print(f"AI解析失败，使用规则解析: {e}")
            return self.parse_with_rules(natural_input, target_url)
    
    def parse_with_rules(self, natural_input: str, target_url: str = None) -> List[Dict[str, Any]]:
        """
        使用规则解析自然语言描述
        这是基础的解析方法，使用预定义的模式匹配
        """
        steps = []
        
        # 添加导航步骤
        if target_url:
            steps.append({
                "type": "goto",
                "description": f"访问网站: {target_url}",
                "params": {"url": target_url}
            })
        
        # 按行解析
        lines = natural_input.strip().split('\n')
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):  # 跳过空行和注释
                continue
            
            # 移除行号前缀（如 "1. ", "2) ", "步骤1："等）
            line = re.sub(r'^\d+[.)、：]\s*', '', line)
            line = re.sub(r'^步骤\d+[：:]\s*', '', line, flags=re.IGNORECASE)
            
            step = self._parse_single_line(line, line_num)
            if step:
                steps.append(step)
        
        return steps
    
    def _parse_single_line(self, line: str, line_num: int) -> Optional[Dict[str, Any]]:
        """解析单行描述"""
        line_lower = line.lower()
        
        # 输入操作
        if self._matches_patterns(line_lower, self.step_patterns['input']):
            return self._parse_input_step(line, line_num)
        
        # 点击操作
        elif self._matches_patterns(line_lower, self.step_patterns['click']):
            return self._parse_click_step(line, line_num)
        
        # 等待操作
        elif self._matches_patterns(line_lower, self.step_patterns['wait']):
            return self._parse_wait_step(line, line_num)
        
        # 验证操作
        elif self._matches_patterns(line_lower, self.step_patterns['assert']):
            return self._parse_assert_step(line, line_num)
        
        # 查询操作
        elif self._matches_patterns(line_lower, self.step_patterns['query']):
            return self._parse_query_step(line, line_num)
        
        # 滚动操作
        elif self._matches_patterns(line_lower, self.step_patterns['scroll']):
            return self._parse_scroll_step(line, line_num)
        
        # 默认为通用AI操作
        else:
            return {
                "type": "ai_action",
                "description": f"AI操作: {line}",
                "params": {"prompt": line}
            }
    
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """检查文本是否匹配任一模式"""
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _parse_input_step(self, line: str, line_num: int) -> Dict[str, Any]:
        """解析输入步骤"""
        # 尝试提取输入内容和目标元素
        
        # 模式1: 在[元素]中输入[内容]
        match = re.search(r'在(.+?)[中里]输入[\'"]?(.+?)[\'"]?', line)
        if match:
            locate_prompt = match.group(1).strip()
            text = match.group(2).strip()
            return {
                "type": "ai_input",
                "description": f"在{locate_prompt}中输入'{text}'",
                "params": {"text": text, "locate_prompt": locate_prompt}
            }
        
        # 模式2: 输入[内容]到[元素]
        match = re.search(r'输入[\'"]?(.+?)[\'"]?到(.+)', line)
        if match:
            text = match.group(1).strip()
            locate_prompt = match.group(2).strip()
            return {
                "type": "ai_input",
                "description": f"输入'{text}'到{locate_prompt}",
                "params": {"text": text, "locate_prompt": locate_prompt}
            }
        
        # 模式3: 搜索[内容]
        match = re.search(r'搜索[\'"]?(.+?)[\'"]?', line)
        if match:
            text = match.group(1).strip()
            return {
                "type": "ai_input",
                "description": f"搜索'{text}'",
                "params": {"text": text, "locate_prompt": "搜索框"}
            }
        
        # 默认处理
        return {
            "type": "ai_input",
            "description": f"AI输入: {line}",
            "params": {"text": "待提取", "locate_prompt": "输入框"}
        }
    
    def _parse_click_step(self, line: str, line_num: int) -> Dict[str, Any]:
        """解析点击步骤"""
        # 移除"点击"等动词，保留目标元素
        cleaned_line = re.sub(r'^(点击|按|选择|单击)\s*', '', line)
        
        return {
            "type": "ai_tap",
            "description": f"点击: {cleaned_line}",
            "params": {"prompt": cleaned_line}
        }
    
    def _parse_wait_step(self, line: str, line_num: int) -> Dict[str, Any]:
        """解析等待步骤"""
        return {
            "type": "ai_wait_for",
            "description": f"等待: {line}",
            "params": {"prompt": line}
        }
    
    def _parse_assert_step(self, line: str, line_num: int) -> Dict[str, Any]:
        """解析验证步骤"""
        return {
            "type": "ai_assert",
            "description": f"验证: {line}",
            "params": {"prompt": line}
        }
    
    def _parse_query_step(self, line: str, line_num: int) -> Dict[str, Any]:
        """解析查询步骤"""
        return {
            "type": "ai_query",
            "description": f"查询: {line}",
            "params": {"prompt": line}
        }
    
    def _parse_scroll_step(self, line: str, line_num: int) -> Dict[str, Any]:
        """解析滚动步骤"""
        direction = "down"  # 默认向下
        scroll_type = "once"  # 默认滚动一次
        
        if "向上" in line or "上拉" in line:
            direction = "up"
        elif "向下" in line or "下拉" in line:
            direction = "down"
        elif "向左" in line:
            direction = "left"
        elif "向右" in line:
            direction = "right"
        
        if "到底" in line or "底部" in line:
            scroll_type = "untilBottom"
        elif "到顶" in line or "顶部" in line:
            scroll_type = "untilTop"
        
        return {
            "type": "ai_scroll",
            "description": f"滚动: {line}",
            "params": {
                "direction": direction,
                "scroll_type": scroll_type
            }
        }
    
    def enhance_steps_with_context(self, steps: List[Dict[str, Any]], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        根据上下文增强测试步骤
        例如：自动添加等待步骤、优化元素定位描述等
        """
        enhanced_steps = []
        
        for i, step in enumerate(steps):
            enhanced_steps.append(step)
            
            # 在某些操作后自动添加等待
            if step["type"] in ["ai_tap", "ai_input"] and i < len(steps) - 1:
                next_step = steps[i + 1]
                # 如果下一步不是等待，且是验证或查询，则添加等待
                if next_step["type"] in ["ai_assert", "ai_query"] and next_step["type"] != "ai_wait_for":
                    enhanced_steps.append({
                        "type": "ai_wait_for",
                        "description": "等待页面响应",
                        "params": {"prompt": "页面加载完成"}
                    })
        
        return enhanced_steps
    
    def validate_steps(self, steps: List[Dict[str, Any]]) -> List[str]:
        """
        验证生成的测试步骤
        返回验证错误列表，空列表表示验证通过
        """
        errors = []
        
        for i, step in enumerate(steps):
            step_num = i + 1
            
            # 检查必需字段
            if "type" not in step:
                errors.append(f"步骤 {step_num}: 缺少 'type' 字段")
                continue
            
            if "params" not in step:
                errors.append(f"步骤 {step_num}: 缺少 'params' 字段")
                continue
            
            # 根据类型验证参数
            step_type = step["type"]
            params = step["params"]
            
            if step_type == "goto":
                if "url" not in params:
                    errors.append(f"步骤 {step_num}: goto 操作缺少 'url' 参数")
            
            elif step_type == "ai_input":
                if "text" not in params or "locate_prompt" not in params:
                    errors.append(f"步骤 {step_num}: ai_input 操作缺少 'text' 或 'locate_prompt' 参数")
            
            elif step_type in ["ai_tap", "ai_wait_for", "ai_assert", "ai_query", "ai_action"]:
                if "prompt" not in params:
                    errors.append(f"步骤 {step_num}: {step_type} 操作缺少 'prompt' 参数")
        
        return errors

# 全局解析器实例
parser = AITestCaseParser()

def parse_natural_language(natural_input: str, target_url: str = None, use_ai: bool = True) -> List[Dict[str, Any]]:
    """
    解析自然语言测试描述的便捷函数
    
    Args:
        natural_input: 自然语言描述
        target_url: 目标网址
        use_ai: 是否使用AI解析（如果可用）
    
    Returns:
        测试步骤列表
    """
    if use_ai:
        steps = parser.parse_with_ai(natural_input, target_url)
    else:
        steps = parser.parse_with_rules(natural_input, target_url)
    
    # 增强步骤
    steps = parser.enhance_steps_with_context(steps)
    
    # 验证步骤
    errors = parser.validate_steps(steps)
    if errors:
        print("⚠️ 步骤验证发现问题:")
        for error in errors:
            print(f"  - {error}")
    
    return steps
