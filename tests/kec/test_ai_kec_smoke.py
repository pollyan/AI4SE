"""
完全依赖AI功能的自动化测试 - 不使用传统方法
演示纯AI驱动的web UI自动化测试
"""
import pytest
import time
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from midscene_python import MidSceneAI

class TestAIKECSmoke:
    """完全依赖AI功能的自动化测试类"""
    
    @pytest.fixture(autouse=True)
    def setup_ai(self, nodejs_midscene_server):
        """设置AI测试环境"""
        self.ai = MidSceneAI(nodejs_midscene_server)
        yield
        # 测试结束后清理
        try:
            self.ai.cleanup()
        except:
            pass
    
    def test_ai_kec_smoke_workflow(self, ksyun_environment, auto_login_ksyun):
        """完整的AI驱动KEC smoke测试工作流"""
        print("🚀 开始完全AI驱动的KEC测试工作流...")
        ai = auto_login_ksyun
        
        # 步骤1: AI导航到KEC控制台首页
        print("\n📍 步骤1: 访问KEC控制台首页")
        page_info = self.ai.goto("https://kec.console.ksyun.com/v2/#/kec")
        assert "云服务器" in page_info["title"]
        
        # 步骤2: AI截图记录初始状态
        print("\n📍 步骤2: 截图记录")
        ai.take_screenshot("AI测试_KEC首页")
        
        # 步骤3: AI点击创建云服务器
        print("\n📍 步骤3: AI点击新建按钮")
        ai.ai_tap("新建按钮")        
               
        # 步骤4: AI断言新建页面加载完成
        print("\n📍 步骤7: AI验证新建页面加载完成")
        ai.ai_assert("页面显示了自定义购买")
        
        print("\n🎉 AIKECSmoke测试完成！")

if __name__ == "__main__":
    print("这是一个pytest测试文件，请使用以下命令运行:")
    print("pytest tests/kec/test_ai_kec_smoke.py -v -s")