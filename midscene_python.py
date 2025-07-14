"""
MidSceneJS Python封装类 - 通过HTTP API调用MidSceneJS功能，完全依赖AI
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class MidSceneAI:
    """MidSceneJS Python封装类 - 纯AI驱动，无传统方法fallback"""

    def __init__(self, server_url: str = "http://127.0.0.1:3001"):
        """
        初始化MidSceneAI

        Args:
            server_url: MidSceneJS服务器地址
        """
        self.server_url = server_url.rstrip("/")
        self.config = self._load_config()
        self.current_mode = "headless"  # 默认无头模式
        self._verify_server_connection()

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        return {
            "model_name": os.getenv("MIDSCENE_MODEL_NAME", "qwen-vl-max-latest"),
            "api_key": os.getenv("OPENAI_API_KEY"),
            "base_url": os.getenv(
                "OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
            "timeout": int(os.getenv("TIMEOUT", "30000")),
            "use_qwen_vl": os.getenv("MIDSCENE_USE_QWEN_VL", "1") == "1",
        }

    def _verify_server_connection(self):
        """验证MidSceneJS服务器连接"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ MidSceneJS服务器连接成功")
            else:
                raise Exception(f"服务器返回状态码: {response.status_code}")
        except Exception as e:
            raise Exception(f"❌ 无法连接MidSceneJS服务器: {e}")

    def _make_request(
        self, endpoint: str, method: str = "POST", data: Dict = None, retries: int = 2
    ) -> Dict[str, Any]:
        """发送HTTP请求到MidSceneJS服务器，带重试机制"""
        url = f"{self.server_url}{endpoint}"

        for attempt in range(retries + 1):
            try:
                if method == "POST":
                    response = requests.post(
                        url, json=data or {}, timeout=90
                    )  # 增加超时时间
                else:
                    response = requests.get(url, timeout=30)

                response.raise_for_status()
                result = response.json()

                if not result.get("success"):
                    error_msg = result.get("error", "未知错误")
                    if attempt < retries:
                        print(f"⚠️  AI操作失败，第{attempt + 1}次重试: {error_msg}")
                        import time

                        time.sleep(2)  # 重试前等待2秒
                        continue
                    else:
                        raise Exception(f"AI操作失败: {error_msg}")

                return result

            except requests.exceptions.Timeout:
                if attempt < retries:
                    print(f"⚠️  请求超时，第{attempt + 1}次重试...")
                    import time

                    time.sleep(3)
                    continue
                else:
                    raise Exception("请求超时，AI模型响应较慢")

            except requests.exceptions.ConnectionError:
                if attempt < retries:
                    print(f"⚠️  连接失败，第{attempt + 1}次重试...")
                    import time

                    time.sleep(2)
                    continue
                else:
                    raise Exception("无法连接到MidSceneJS服务器")

            except Exception as e:
                if attempt < retries and "500 Server Error" in str(e):
                    print(f"⚠️  服务器错误，第{attempt + 1}次重试: {str(e)}")
                    import time

                    time.sleep(3)
                    continue
                else:
                    raise Exception(f"AI操作失败: {str(e)}")

        raise Exception("重试次数已用完")

    def set_browser_mode(self, mode: str) -> Dict[str, Any]:
        """
        设置浏览器模式

        Args:
            mode: 'browser' (浏览器模式) 或 'headless' (无头模式)

        Returns:
            设置结果
        """
        if mode not in ["browser", "headless"]:
            raise ValueError("模式必须是 'browser' 或 'headless'")

        print(f"🔧 设置浏览器模式: {mode}")
        result = self._make_request("/set-browser-mode", data={"mode": mode})
        self.current_mode = mode
        print(f"✅ {result.get('message', '模式设置成功')}")
        return result

    def goto(self, url: str, mode: str = None) -> Dict[str, Any]:
        """
        导航到指定URL

        Args:
            url: 目标URL
            mode: 浏览器模式 ('browser' 或 'headless')，如果不指定则使用当前模式
        """
        # 如果指定了模式且与当前模式不同，先设置模式
        if mode and mode != self.current_mode:
            self.set_browser_mode(mode)

        print(f"🌐 正在访问: {url}")
        result = self._make_request(
            "/goto", data={"url": url, "mode": self.current_mode}
        )
        print(f"✅ 页面加载成功: {result['url']}")
        return result

    def ai_action(self, prompt: str) -> Dict[str, Any]:
        """
        执行AI动作 - 纯AI驱动，无传统方法fallback

        Args:
            prompt: 自然语言描述的动作

        Returns:
            操作结果
        """
        print(f"🤖 AI动作: {prompt}")
        result = self._make_request("/ai-action", data={"prompt": prompt})
        print(f"✅ AI动作执行成功")
        return result.get("result", result)

    def ai_query(self, prompt: str) -> Any:
        """
        执行AI查询，提取页面数据 - 纯AI驱动

        Args:
            prompt: 查询描述

        Returns:
            查询结果
        """
        print(f"🔍 AI查询: {prompt}")
        result = self._make_request("/ai-query", data={"prompt": prompt})
        query_result = result.get("result", result)
        print(f"✅ AI查询完成，结果: {query_result}")
        return query_result

    def ai_assert(self, prompt: str) -> bool:
        """
        执行AI断言 - 纯AI驱动

        Args:
            prompt: 断言描述

        Returns:
            断言是否通过
        """
        print(f"🔍 AI断言: {prompt}")
        try:
            result = self._make_request("/ai-assert", data={"prompt": prompt})
            print(f"✅ AI断言通过")
            return True
        except Exception as e:
            print(f"❌ AI断言失败: {e}")
            raise Exception(f"AI断言失败: {e}")

    def ai_tap(self, prompt: str) -> Dict[str, Any]:
        """
        AI点击元素 - 纯AI驱动

        Args:
            prompt: 元素描述

        Returns:
            操作结果
        """
        print(f"👆 AI点击: {prompt}")
        result = self._make_request("/ai-tap", data={"prompt": prompt})
        print(f"✅ AI点击成功")
        return result.get("result", result)

    def ai_input(self, text: str, locate_prompt: str) -> Dict[str, Any]:
        """
        AI输入文本 - 纯AI驱动

        Args:
            text: 要输入的文本
            locate_prompt: 输入框的描述

        Returns:
            操作结果
        """
        print(f"⌨️  AI输入: '{text}' 到 '{locate_prompt}'")
        result = self._make_request(
            "/ai-input", data={"text": text, "locate": locate_prompt}
        )
        print(f"✅ AI输入成功")
        return result.get("result", result)

    def ai_wait_for(self, prompt: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        AI等待条件满足 - 纯AI驱动

        Args:
            prompt: 等待条件描述
            timeout: 超时时间（毫秒）

        Returns:
            操作结果
        """
        timeout = timeout or self.config["timeout"]
        print(f"⏳ AI等待: {prompt} (超时: {timeout}ms)")
        result = self._make_request(
            "/ai-wait-for", data={"prompt": prompt, "timeout": timeout}
        )
        print(f"✅ AI等待条件满足")
        return result.get("result", result)

    def smart_wait_and_verify(self, condition: str, max_wait: int = 5) -> bool:
        """
        智能等待和验证 - 更稳定的等待策略

        Args:
            condition: 验证条件描述
            max_wait: 最大等待时间（秒）

        Returns:
            验证是否成功
        """
        import time

        print(f"🔍 智能等待验证: {condition}")

        for i in range(max_wait):
            try:
                time.sleep(1)
                self.ai_assert(condition)
                print(f"✅ 验证成功（等待{i+1}秒）")
                return True
            except Exception as e:
                if i < max_wait - 1:
                    print(f"⏳ 等待中... ({i+1}/{max_wait})")
                    continue
                else:
                    print(f"⚠️  验证失败: {e}")
                    return False

        return False

    def ai_scroll(
        self,
        direction: str = "down",
        scroll_type: str = "once",
        locate_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        AI滚动页面 - 纯AI驱动

        Args:
            direction: 滚动方向 (up/down/left/right)
            scroll_type: 滚动类型 (once/untilTop/untilBottom/untilLeft/untilRight)
            locate_prompt: 滚动元素描述（可选）

        Returns:
            操作结果
        """
        options = {"direction": direction, "scrollType": scroll_type}

        print(f"📜 AI滚动: {direction} ({scroll_type})")
        if locate_prompt:
            print(f"   目标: {locate_prompt}")

        result = self._make_request(
            "/ai-scroll", data={"options": options, "locate": locate_prompt}
        )
        print(f"✅ AI滚动完成")
        return result.get("result", result)

    def take_screenshot(self, title: str = "screenshot") -> str:
        """
        截取屏幕截图

        Args:
            title: 截图标题

        Returns:
            截图文件路径
        """
        # 确保截图保存到正确的静态文件目录
        screenshot_filename = f"{title}.png"
        screenshot_path = f"web_gui/static/screenshots/{screenshot_filename}"

        # 确保目录存在
        os.makedirs("web_gui/static/screenshots", exist_ok=True)

        print(f"📸 截图: {screenshot_path}")
        result = self._make_request("/screenshot", data={"path": screenshot_path})
        print(f"✅ 截图保存到: {screenshot_path}")
        return screenshot_path

    def get_page_info(self) -> Dict[str, Any]:
        """获取页面信息"""
        print("📄 获取页面信息")
        result = self._make_request("/page-info", method="GET")
        info = result["info"]
        print(f"✅ 页面信息: {info['title']} - {info['url']}")
        return info

    def cleanup(self):
        """清理资源"""
        print("🧹 清理资源")
        try:
            self._make_request("/cleanup")
            print("✅ 资源清理完成")
        except Exception as e:
            print(f"⚠️  清理资源时出错: {e}")
