"""
Mock AI Utils - 模拟AI工具函数
从app_enhanced.py中提取的模拟AI相关函数，清理重复代码
"""

import time
import json

def mock_ai_query_result(query: str, data_demand: str = None) -> dict:
    """模拟aiQuery返回结果（旧格式）"""
    
    # 尝试解析dataDemand结构
    if data_demand:
        try:
            # 简单解析dataDemand格式，如 "{name: string, price: number}"
            if 'name' in data_demand and 'price' in data_demand:
                return {
                    'name': f'模拟商品名_{hash(query) % 100}',
                    'price': abs(hash(query) % 1000) + 99.99
                }
            elif 'title' in data_demand:
                return {'title': f'模拟标题_{hash(query) % 100}'}
            elif 'count' in data_demand:
                return {'count': abs(hash(query) % 50) + 1}
        except:
            pass
    
    # 默认返回结构
    return {
        'result': f'模拟查询结果: {query}',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'confidence': 0.85
    }

def mock_ai_query_result_from_schema(schema: dict) -> dict:
    """根据schema格式模拟aiQuery返回结果"""
    result = {}
    
    for field_name, field_desc in schema.items():
        # 根据字段描述生成模拟数据
        field_desc_lower = field_desc.lower()
        
        if 'string' in field_desc_lower or '字符串' in field_desc_lower:
            if 'name' in field_name.lower() or '名称' in field_name or '姓名' in field_name:
                result[field_name] = f'模拟名称_{hash(field_name) % 100}'
            elif 'title' in field_name.lower() or '标题' in field_name:
                result[field_name] = f'模拟标题_{hash(field_name) % 100}'
            elif 'url' in field_name.lower() or '链接' in field_name:
                result[field_name] = f'https://example.com/page_{hash(field_name) % 100}'
            elif 'id' in field_name.lower():
                result[field_name] = f'id_{abs(hash(field_name) % 10000)}'
            else:
                result[field_name] = f'模拟文本_{hash(field_name) % 100}'
                
        elif 'number' in field_desc_lower or '数字' in field_desc_lower or 'int' in field_desc_lower:
            if 'price' in field_name.lower() or '价格' in field_name:
                result[field_name] = abs(hash(field_name) % 1000) + 99.99
            elif 'count' in field_name.lower() or '数量' in field_name:
                result[field_name] = abs(hash(field_name) % 100) + 1
            elif 'age' in field_name.lower() or '年龄' in field_name:
                result[field_name] = abs(hash(field_name) % 50) + 18
            else:
                result[field_name] = abs(hash(field_name) % 1000)
                
        elif 'boolean' in field_desc_lower or '布尔' in field_desc_lower or 'bool' in field_desc_lower:
            result[field_name] = hash(field_name) % 2 == 0
            
        elif 'array' in field_desc_lower or '数组' in field_desc_lower or 'list' in field_desc_lower:
            result[field_name] = [f'项目{i}_{hash(field_name) % 100}' for i in range(3)]
            
        else:
            # 默认返回字符串
            result[field_name] = f'模拟数据_{hash(field_name) % 100}'
    
    return result

def mock_ai_string_result(query: str) -> str:
    """模拟aiString返回结果"""
    # 根据查询内容返回不同的模拟结果
    if '价格' in query or 'price' in query.lower():
        return f'¥{abs(hash(query) % 1000) + 99}'
    elif '标题' in query or 'title' in query.lower():
        return f'模拟页面标题_{hash(query) % 100}'
    elif '时间' in query or 'time' in query.lower():
        return time.strftime('%Y-%m-%d %H:%M:%S')
    else:
        return f'模拟字符串结果: {query}'

def mock_ai_ask_result(query: str) -> str:
    """模拟aiAsk返回结果"""
    # 模拟AI分析结果
    responses = [
        f'根据当前页面内容，{query}的答案是：这是一个模拟的AI分析结果。',
        f'基于页面信息分析，{query}的结论是：模拟的智能回答内容。',
        f'通过AI理解，{query}的回应是：这是模拟生成的智能答案。'
    ]
    return responses[hash(query) % len(responses)]

def mock_javascript_result(script: str):
    """模拟JavaScript执行结果"""
    # 根据脚本内容返回不同的模拟结果
    if 'window.location' in script:
        return {
            'url': 'https://example.com/current-page',
            'title': '模拟页面标题',
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    elif 'document.title' in script:
        return '模拟页面标题'
    elif 'return' in script and '{' in script:
        # 返回对象的脚本
        return {
            'result': '模拟JavaScript执行结果',
            'script': script[:50] + '...' if len(script) > 50 else script,
            'timestamp': time.time()
        }
    else:
        return f'模拟脚本执行结果: {script[:30]}...'
