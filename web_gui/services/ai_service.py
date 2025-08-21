"""
AI Service - AI服务抽象层
提供统一的AI服务接口，支持真实AI和模拟AI实现
"""

import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AIServiceInterface(ABC):
    """AI服务接口"""
    
    @abstractmethod
    def set_browser_mode(self, mode: str):
        """设置浏览器模式"""
        pass
    
    @abstractmethod  
    def goto(self, url: str):
        """访问页面"""
        pass
    
    @abstractmethod
    def ai_input(self, text: str, locate: str):
        """AI输入"""
        pass
    
    @abstractmethod
    def ai_tap(self, prompt: str):
        """AI点击"""
        pass
    
    @abstractmethod
    def ai_assert(self, prompt: str):
        """AI断言"""
        pass
    
    @abstractmethod
    def ai_wait_for(self, prompt: str, timeout: int = 10000):
        """AI等待"""
        pass
    
    @abstractmethod
    def ai_scroll(self, direction: str = 'down', scroll_type: str = 'once', locate_prompt: str = None):
        """AI滚动"""
        pass
    
    @abstractmethod
    def take_screenshot(self, title: str) -> str:
        """截图"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """清理资源"""
        pass

class RealAIService(AIServiceInterface):
    """真实AI服务实现"""
    
    def __init__(self):
        self.current_url = None
        try:
            from midscene_python import MidSceneAI
            self.ai = MidSceneAI()
            logger.info("真实AI引擎初始化成功")
        except ImportError as e:
            logger.error(f"MidSceneAI导入失败: {e}")
            raise ImportError("MidSceneAI库未安装或导入失败")
    
    def set_browser_mode(self, mode: str):
        """设置浏览器模式"""
        if hasattr(self.ai, 'set_browser_mode'):
            self.ai.set_browser_mode(mode)
    
    def goto(self, url: str):
        self.current_url = url
        self.ai.goto(url)
    
    def ai_input(self, text: str, locate: str):
        self.ai.ai_input(text, locate)
    
    def ai_tap(self, prompt: str):
        self.ai.ai_tap(prompt)
    
    def ai_assert(self, prompt: str):
        self.ai.ai_assert(prompt)
    
    def ai_wait_for(self, prompt: str, timeout: int = 10000):
        self.ai.ai_wait_for(prompt, timeout)
    
    def ai_scroll(self, direction: str = 'down', scroll_type: str = 'once', locate_prompt: str = None):
        self.ai.ai_scroll(direction, scroll_type, locate_prompt)
    
    def take_screenshot(self, title: str) -> str:
        return self.ai.take_screenshot(title)
    
    def cleanup(self):
        if hasattr(self.ai, 'cleanup'):
            self.ai.cleanup()

class MockAIService(AIServiceInterface):
    """模拟AI服务实现"""
    
    def __init__(self):
        self.current_url = None
        logger.info("模拟AI引擎初始化成功")
    
    def set_browser_mode(self, mode: str):
        """设置浏览器模式（模拟）"""
        logger.info(f"[模拟] 设置浏览器模式: {mode}")
    
    def goto(self, url: str):
        self.current_url = url
        logger.info(f"[模拟] 访问页面: {url}")
        time.sleep(1)  # 模拟加载时间
    
    def ai_input(self, text: str, locate: str):
        logger.info(f"[模拟] 在 '{locate}' 中输入: {text}")
        time.sleep(0.5)
    
    def ai_tap(self, prompt: str):
        logger.info(f"[模拟] 点击: {prompt}")
        time.sleep(0.5)
    
    def ai_assert(self, prompt: str):
        logger.info(f"[模拟] 验证: {prompt}")
        time.sleep(0.5)
    
    def ai_wait_for(self, prompt: str, timeout: int = 10000):
        logger.info(f"[模拟] 等待: {prompt} (超时: {timeout}ms)")
        time.sleep(1)
    
    def ai_scroll(self, direction: str = 'down', scroll_type: str = 'once', locate_prompt: str = None):
        logger.info(f"[模拟] 滚动: {direction} ({scroll_type})")
        time.sleep(0.5)
    
    def take_screenshot(self, title: str) -> str:
        """模拟截图功能"""
        screenshot_filename = f"{title}.png"
        screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static', 'screenshots')
        screenshot_path = os.path.join(screenshot_dir, screenshot_filename)
        
        logger.info(f"[模拟] 截图保存到: {screenshot_path}")
        
        # 确保目录存在
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # 创建一个简单的模拟截图
        try:
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)
            
            draw.rectangle([50, 50, 750, 550], outline='black', width=2)
            draw.text((100, 100), "模拟截图", fill='black')
            draw.text((100, 150), f"URL: {getattr(self, 'current_url', 'Unknown')}", fill='blue')
            draw.text((100, 200), f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", fill='gray')
            draw.text((100, 250), "这是AI执行引擎的模拟截图", fill='green')
            
            img.save(screenshot_path, 'PNG')
            logger.info(f"[模拟] 截图已保存: {screenshot_path}")
        except ImportError:
            # 如果没有PIL库，创建一个简单的文本文件
            with open(screenshot_path.replace('.png', '.txt'), 'w') as f:
                f.write(f"模拟截图 - {time.strftime('%Y-%m-%d %H:%M:%S')}\nURL: {getattr(self, 'current_url', 'Unknown')}")
            logger.info(f"[模拟] 截图文本文件已保存: {screenshot_path.replace('.png', '.txt')}")
        except Exception as e:
            logger.warning(f"[模拟] 截图保存失败: {e}")
            # 创建一个空文件作为占位符
            with open(screenshot_path, 'w') as f:
                f.write("")
        
        return f"static/screenshots/{screenshot_filename}"
    
    def cleanup(self):
        logger.info("[模拟] 清理AI资源")

# 全局AI服务实例管理
_ai_service_instance = None

def get_ai_service(force_mock: bool = False) -> AIServiceInterface:
    """
    获取AI服务实例（单例模式）
    
    Args:
        force_mock: 是否强制使用模拟服务
    
    Returns:
        AI服务实例
    """
    global _ai_service_instance
    
    if _ai_service_instance is None:
        if force_mock:
            _ai_service_instance = MockAIService()
        else:
            try:
                _ai_service_instance = RealAIService()
            except ImportError:
                logger.warning("真实AI服务不可用，使用模拟AI服务")
                _ai_service_instance = MockAIService()
    
    return _ai_service_instance

def reset_ai_service():
    """重置AI服务实例（主要用于测试）"""
    global _ai_service_instance
    if _ai_service_instance:
        _ai_service_instance.cleanup()
    _ai_service_instance = None
