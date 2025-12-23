#!/usr/bin/env python3
"""
数据验证器
提供各种AI方法返回值的验证功能
"""

import json
import math
import re
from typing import Any, Dict, Optional


class DataValidator:
    """数据验证器"""

    @staticmethod
    def validate_query_data(data: Any, rules: Optional[Dict] = None) -> dict:
        """
        验证aiQuery返回的对象数据

        Args:
            data: 要验证的数据
            rules: 验证规则

        Returns:
            验证后的数据

        Raises:
            ValueError: 数据验证失败
        """
        if not isinstance(data, dict):
            raise ValueError("aiQuery必须返回对象类型")

        if not data:
            raise ValueError("aiQuery不能返回空对象")

        if rules:
            # 检查必需字段
            if "required_fields" in rules:
                for field in rules["required_fields"]:
                    if field not in data:
                        raise ValueError(f"缺少必需字段: {field}")

            # 检查字段类型
            if "field_types" in rules:
                for field, expected_type in rules["field_types"].items():
                    if field in data:
                        actual_value = data[field]
                        if not DataValidator._check_field_type(
                            actual_value, expected_type
                        ):
                            raise ValueError(
                                f"字段 {field} 类型不匹配: 期望 {expected_type}, 实际 {type(actual_value).__name__}"
                            )

            # 检查数据范围
            if "value_ranges" in rules:
                for field, range_config in rules["value_ranges"].items():
                    if field in data:
                        DataValidator._validate_value_range(
                            data[field], range_config, field
                        )

        return data

    @staticmethod
    def validate_string_data(data: Any) -> str:
        """
        验证aiString返回的字符串数据

        Args:
            data: 要验证的数据

        Returns:
            验证后的字符串

        Raises:
            ValueError: 数据验证失败
        """
        if not isinstance(data, str):
            raise ValueError("aiString必须返回字符串类型")

        if len(data.strip()) == 0:
            raise ValueError("aiString不能返回空字符串")

        # 检查是否包含可疑内容
        if DataValidator._contains_suspicious_content(data):
            raise ValueError("字符串包含可疑内容")

        return data

    @staticmethod
    def validate_number_data(data: Any) -> float:
        """
        验证aiNumber返回的数字数据

        Args:
            data: 要验证的数据

        Returns:
            验证后的数字

        Raises:
            ValueError: 数据验证失败
        """
        if not isinstance(data, (int, float)):
            # 尝试转换字符串为数字
            if isinstance(data, str):
                try:
                    data = float(data)
                except ValueError:
                    raise ValueError("aiNumber必须返回数字类型或可转换为数字的字符串")
            else:
                raise ValueError("aiNumber必须返回数字类型")

        if math.isnan(data):
            raise ValueError("aiNumber不能返回NaN")

        if math.isinf(data):
            raise ValueError("aiNumber不能返回无穷大")

        return float(data)

    @staticmethod
    def validate_boolean_data(data: Any) -> bool:
        """
        验证aiBoolean返回的布尔数据

        Args:
            data: 要验证的数据

        Returns:
            验证后的布尔值

        Raises:
            ValueError: 数据验证失败
        """
        if isinstance(data, bool):
            return data

        # 尝试转换字符串为布尔值
        if isinstance(data, str):
            data_lower = data.lower().strip()
            if data_lower in ("true", "1", "yes", "on"):
                return True
            elif data_lower in ("false", "0", "no", "off"):
                return False
            else:
                raise ValueError(f"无法将字符串 '{data}' 转换为布尔值")

        # 尝试转换数字为布尔值
        if isinstance(data, (int, float)):
            return bool(data)

        raise ValueError("aiBoolean必须返回布尔类型或可转换为布尔值的类型")

    @staticmethod
    def validate_dataDemand_format(dataDemand: str) -> bool:
        """
        验证dataDemand格式是否正确

        Args:
            dataDemand: 数据需求描述

        Returns:
            是否有效
        """
        if not isinstance(dataDemand, str):
            return False

        if not dataDemand.strip():
            return False

        # 检查是否包含基本的对象结构
        if not ("{" in dataDemand and "}" in dataDemand):
            return False

        # 尝试解析为基本的类型定义
        try:
            # 简单的格式验证，检查是否包含字段和类型
            if ":" not in dataDemand:
                return False

            return True
        except Exception:
            return False

    @staticmethod
    def _check_field_type(value: Any, expected_type: str) -> bool:
        """检查字段类型是否匹配"""
        type_map = {
            "string": str,
            "number": (int, float),
            "boolean": bool,
            "object": dict,
            "array": list,
            "null": type(None),
        }

        expected_python_type = type_map.get(expected_type.lower())
        if expected_python_type is None:
            return True  # 未知类型，跳过验证

        return isinstance(value, expected_python_type)

    @staticmethod
    def _validate_value_range(value: Any, range_config: Dict, field_name: str):
        """验证值范围"""
        if isinstance(value, (int, float)):
            if "min" in range_config and value < range_config["min"]:
                raise ValueError(
                    f"字段 {field_name} 值 {value} 小于最小值 {range_config['min']}"
                )
            if "max" in range_config and value > range_config["max"]:
                raise ValueError(
                    f"字段 {field_name} 值 {value} 大于最大值 {range_config['max']}"
                )

        elif isinstance(value, str):
            if "min_length" in range_config and len(value) < range_config["min_length"]:
                raise ValueError(
                    f"字段 {field_name} 长度 {len(value)} 小于最小长度 {range_config['min_length']}"
                )
            if "max_length" in range_config and len(value) > range_config["max_length"]:
                raise ValueError(
                    f"字段 {field_name} 长度 {len(value)} 大于最大长度 {range_config['max_length']}"
                )

    @staticmethod
    def _contains_suspicious_content(text: str) -> bool:
        """检查是否包含可疑内容"""
        # 检查SQL注入模式
        sql_patterns = [
            r"(union|select|insert|delete|update|drop|create|alter)\s+",
            r"--\s*$",
            r";\s*(drop|delete|truncate)",
        ]

        for pattern in sql_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # 检查XSS模式
        xss_patterns = [
            r"<script[^>]*>",
            r"javascript:",
            r"on\w+\s*=",
        ]

        for pattern in xss_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def parse_dataDemand_schema(dataDemand: str) -> Dict:
        """
        解析dataDemand为结构化Schema

        Args:
            dataDemand: 数据需求描述

        Returns:
            解析后的Schema字典
        """
        try:
            # 简单的解析逻辑，将类似 "{name: string, price: number}" 转换为字典
            # 移除花括号
            content = dataDemand.strip().strip("{}")

            schema = {}
            if content:
                pairs = content.split(",")
                for pair in pairs:
                    if ":" in pair:
                        key, value = pair.split(":", 1)
                        key = key.strip().strip("'\"")
                        value = value.strip().strip("'\"")
                        schema[key] = value

            return schema
        except Exception:
            return {}

    @staticmethod
    def validate_ai_ask_result(data: Any) -> str:
        """
        验证aiAsk返回的文本数据

        Args:
            data: 要验证的数据

        Returns:
            验证后的字符串

        Raises:
            ValueError: 数据验证失败
        """
        if data is None:
            return ""

        if not isinstance(data, str):
            # 尝试转换为字符串
            try:
                data = str(data)
            except Exception:
                raise ValueError("aiAsk必须返回可转换为字符串的数据")

        # 检查是否包含可疑内容
        if DataValidator._contains_suspicious_content(data):
            raise ValueError("aiAsk返回的文本包含可疑内容")

        return data

    @staticmethod
    def validate_ai_locate_result(data: Any) -> Dict[str, Any]:
        """
        验证aiLocate返回的位置对象数据

        Args:
            data: 要验证的数据

        Returns:
            验证后的位置对象

        Raises:
            ValueError: 数据验证失败
        """
        if data is None:
            raise ValueError("aiLocate不能返回None")

        if not isinstance(data, dict):
            raise ValueError("aiLocate必须返回对象类型")

        # 验证必需的字段
        required_fields = ["rect", "center"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"aiLocate结果缺少必需字段: {field}")

        # 验证rect结构
        rect = data["rect"]
        if not isinstance(rect, dict):
            raise ValueError("rect字段必须是对象类型")

        rect_fields = ["x", "y", "width", "height"]
        for field in rect_fields:
            if field not in rect:
                raise ValueError(f"rect对象缺少必需字段: {field}")

            value = rect[field]
            if not isinstance(value, (int, float)):
                raise ValueError(f"rect.{field}必须是数字类型")

            if field in ["width", "height"] and value <= 0:
                raise ValueError(f"rect.{field}必须是正数")

        # 验证center结构
        center = data["center"]
        if not isinstance(center, dict):
            raise ValueError("center字段必须是对象类型")

        center_fields = ["x", "y"]
        for field in center_fields:
            if field not in center:
                raise ValueError(f"center对象缺少必需字段: {field}")

            value = center[field]
            if not isinstance(value, (int, float)):
                raise ValueError(f"center.{field}必须是数字类型")

        # 验证可选的scale字段
        if "scale" in data:
            scale = data["scale"]
            if not isinstance(scale, (int, float)):
                raise ValueError("scale字段必须是数字类型")
            if scale <= 0:
                raise ValueError("scale必须是正数")

        return data

    @staticmethod
    def validate_evaluate_javascript_result(data: Any) -> Any:
        """
        验证evaluateJavaScript返回的数据

        Args:
            data: 要验证的数据

        Returns:
            验证后的数据

        Raises:
            ValueError: 数据验证失败
        """
        # JavaScript可以返回任何类型，包括null/undefined
        # 主要验证是否是可JSON序列化的类型
        try:
            json.dumps(data)
            return data
        except (TypeError, ValueError) as e:
            raise ValueError(f"evaluateJavaScript返回了不可序列化的数据: {str(e)}")
