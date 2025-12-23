#!/usr/bin/env python3
"""
Mock服务
提供完整的Mock API用于开发和测试
"""

import asyncio
import random
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MockMidSceneAPI:
    """Mock MidScene API服务"""

    def __init__(self, response_delay: float = 0.1):
        """
        初始化Mock服务

        Args:
            response_delay: 响应延迟时间（秒）
        """
        self.response_delay = response_delay
        self.call_count = 0
        self.method_calls = {}

    async def aiQuery(
        self, query: str, dataDemand: str, options: Dict = None
    ) -> Dict[str, Any]:
        """
        Mock aiQuery方法

        Args:
            query: 查询描述
            dataDemand: 数据需求格式
            options: 可选参数

        Returns:
            模拟的结构化数据
        """
        await self._simulate_delay()
        self._record_call("aiQuery", {"query": query, "dataDemand": dataDemand})

        # 根据dataDemand生成对应的模拟数据
        if "name: string, price: number" in dataDemand:
            return {"name": "测试商品", "price": 99.99}
        elif "title: string, description: string" in dataDemand:
            return {"title": "测试标题", "description": "测试描述内容"}
        elif "user: object" in dataDemand:
            return {
                "user": {"id": 12345, "name": "测试用户", "email": "test@example.com"}
            }
        elif "items: array" in dataDemand:
            return {
                "items": [
                    {"id": 1, "name": "商品1"},
                    {"id": 2, "name": "商品2"},
                    {"id": 3, "name": "商品3"},
                ]
            }
        else:
            # 通用响应
            return {
                "result": "通用查询结果",
                "query": query,
                "timestamp": "2025-01-30T10:00:00Z",
            }

    async def aiString(self, query: str, options: Dict = None) -> str:
        """
        Mock aiString方法

        Args:
            query: 查询描述
            options: 可选参数

        Returns:
            模拟的字符串结果
        """
        await self._simulate_delay()
        self._record_call("aiString", {"query": query})

        # 根据查询内容返回不同的模拟数据
        if "标题" in query or "title" in query.lower():
            return "测试页面标题"
        elif "描述" in query or "description" in query.lower():
            return "这是一个测试描述内容"
        elif "用户名" in query or "username" in query.lower():
            return "testuser123"
        elif "地址" in query or "address" in query.lower():
            return "北京市朝阳区测试大街123号"
        elif "电话" in query or "phone" in query.lower():
            return "13800138000"
        elif "邮箱" in query or "email" in query.lower():
            return "test@example.com"
        else:
            return f"模拟字符串结果: {query}"

    async def aiNumber(self, query: str, options: Dict = None) -> float:
        """
        Mock aiNumber方法

        Args:
            query: 查询描述
            options: 可选参数

        Returns:
            模拟的数字结果
        """
        await self._simulate_delay()
        self._record_call("aiNumber", {"query": query})

        # 根据查询内容返回不同的模拟数据
        if "价格" in query or "price" in query.lower():
            return round(random.uniform(10.0, 999.99), 2)
        elif "数量" in query or "count" in query.lower() or "quantity" in query.lower():
            return random.randint(1, 100)
        elif "评分" in query or "rating" in query.lower() or "score" in query.lower():
            return round(random.uniform(1.0, 5.0), 1)
        elif "百分比" in query or "percent" in query.lower():
            return round(random.uniform(0.0, 100.0), 1)
        elif "年龄" in query or "age" in query.lower():
            return random.randint(18, 80)
        else:
            return round(random.uniform(1.0, 1000.0), 2)

    async def aiBoolean(self, query: str, options: Dict = None) -> bool:
        """
        Mock aiBoolean方法

        Args:
            query: 查询描述
            options: 可选参数

        Returns:
            模拟的布尔结果
        """
        await self._simulate_delay()
        self._record_call("aiBoolean", {"query": query})

        # 根据查询内容返回不同的模拟数据
        if "库存" in query or "stock" in query.lower() or "available" in query.lower():
            return random.choice([True, True, True, False])  # 75%概率为True
        elif "登录" in query or "login" in query.lower() or "logged" in query.lower():
            return random.choice([True, False])
        elif "启用" in query or "enable" in query.lower() or "active" in query.lower():
            return random.choice([True, True, False])  # 67%概率为True
        elif (
            "可见" in query or "visible" in query.lower() or "display" in query.lower()
        ):
            return True  # 默认可见
        elif "错误" in query or "error" in query.lower() or "fail" in query.lower():
            return random.choice([False, False, True])  # 33%概率为True
        else:
            return random.choice([True, False])

    async def aiAsk(self, query: str, options: Dict = None) -> str:
        """
        Mock aiAsk方法

        Args:
            query: 查询描述
            options: 可选参数

        Returns:
            模拟的AI问答结果
        """
        await self._simulate_delay()
        self._record_call("aiAsk", {"query": query})

        # 根据问题类型返回不同的模拟回答
        if "什么是" in query or "what is" in query.lower():
            return f"关于'{query}'的解释：这是一个测试性的回答，用于模拟AI问答功能。"
        elif "如何" in query or "how to" in query.lower():
            return f"要解决'{query}'这个问题，可以按照以下步骤进行：1. 首先... 2. 然后... 3. 最后..."
        elif "为什么" in query or "why" in query.lower():
            return f"关于'{query}'的原因分析：这主要是由于多种因素的综合作用导致的。"
        else:
            return f"针对您的问题'{query}'，这里是一个模拟的AI回答。"

    async def aiLocate(self, query: str, options: Dict = None) -> Dict[str, Any]:
        """
        Mock aiLocate方法

        Args:
            query: 查询描述
            options: 可选参数

        Returns:
            模拟的元素位置信息
        """
        await self._simulate_delay()
        self._record_call("aiLocate", {"query": query})

        # 生成模拟的元素位置信息
        return {
            "rect": {
                "x": random.randint(100, 800),
                "y": random.randint(100, 600),
                "width": random.randint(50, 200),
                "height": random.randint(20, 100),
            },
            "center": {"x": random.randint(150, 850), "y": random.randint(120, 650)},
            "scale": 1.0,
            "element_type": (
                "button" if "按钮" in query or "button" in query.lower() else "element"
            ),
            "confidence": round(random.uniform(0.8, 1.0), 2),
        }

    async def _simulate_delay(self):
        """模拟API调用延迟"""
        if self.response_delay > 0:
            # 添加一些随机性
            actual_delay = self.response_delay + random.uniform(-0.05, 0.05)
            actual_delay = max(0, actual_delay)
            await asyncio.sleep(actual_delay)

    def _record_call(self, method: str, params: Dict):
        """记录方法调用"""
        self.call_count += 1

        if method not in self.method_calls:
            self.method_calls[method] = []

        self.method_calls[method].append(
            {
                "params": params,
                "call_index": self.call_count,
                "timestamp": asyncio.get_event_loop().time(),
            }
        )

        logger.debug(f"Mock调用记录: {method}, 总调用次数: {self.call_count}")

    def get_call_stats(self) -> Dict[str, Any]:
        """获取调用统计"""
        return {
            "total_calls": self.call_count,
            "method_calls": {
                method: len(calls) for method, calls in self.method_calls.items()
            },
            "method_details": self.method_calls,
        }

    def reset_stats(self):
        """重置统计信息"""
        self.call_count = 0
        self.method_calls = {}
        logger.info("Mock服务统计信息已重置")

    def set_response_delay(self, delay: float):
        """设置响应延迟"""
        self.response_delay = max(0, delay)
        logger.info(f"Mock服务响应延迟设置为: {self.response_delay}秒")


class MockDataGenerator:
    """Mock数据生成器"""

    @staticmethod
    def generate_user_data() -> Dict[str, Any]:
        """生成用户数据"""
        names = ["张三", "李四", "王五", "赵六", "陈七"]
        domains = ["qq.com", "163.com", "gmail.com", "outlook.com"]

        name = random.choice(names)
        return {
            "id": random.randint(1000, 9999),
            "name": name,
            "email": f"{name.lower()}{random.randint(1, 999)}@{random.choice(domains)}",
            "age": random.randint(18, 65),
            "phone": f"1{random.randint(3, 9)}{random.randint(100000000, 999999999)}",
            "address": f"{random.choice(['北京', '上海', '广州', '深圳'])}市{random.choice(['朝阳', '海淀', '西城', '东城'])}区测试街{random.randint(1, 999)}号",
        }

    @staticmethod
    def generate_product_data() -> Dict[str, Any]:
        """生成商品数据"""
        products = ["手机", "电脑", "平板", "耳机", "音响", "键盘", "鼠标"]
        brands = ["苹果", "华为", "小米", "三星", "联想", "戴尔"]

        product = random.choice(products)
        brand = random.choice(brands)

        return {
            "id": random.randint(1000, 9999),
            "name": f"{brand} {product}",
            "price": round(random.uniform(99.0, 9999.0), 2),
            "stock": random.randint(0, 100),
            "rating": round(random.uniform(3.0, 5.0), 1),
            "category": random.choice(["电子产品", "数码配件", "智能设备"]),
            "available": random.choice([True, True, True, False]),
        }

    @staticmethod
    def generate_list_data(item_type: str = "generic", count: int = 5) -> list:
        """生成列表数据"""
        if item_type == "user":
            return [MockDataGenerator.generate_user_data() for _ in range(count)]
        elif item_type == "product":
            return [MockDataGenerator.generate_product_data() for _ in range(count)]
        else:
            return [
                {"id": i, "name": f"项目{i}", "value": random.randint(1, 100)}
                for i in range(1, count + 1)
            ]
