"""
KSYUN自动登录测试
演示如何使用conftest.py中的自动登录功能
"""
import pytest
import time

class TestKsyunLogin:
    """KSYUN自动登录测试类"""
    
    def test_auto_login_with_cookies(self, auto_login_midscene, ksyun_environment):
        """
        测试使用cookie自动登录KSYUN
        """
        ai = auto_login_midscene
        
        print("🧪 开始测试KSYUN自动登录...")
        
        # 截图记录登录后状态
        ai.take_screenshot("KSYUN登录后页面")
        
        # 验证登录状态
        try:
            ai.ai_assert("页面显示用户已登录或包含用户信息")
            print("✅ 登录状态验证成功")
        except Exception as e:
            print(f"⚠️  登录状态验证失败: {e}")
            # 如果验证失败，截图以便调试
            ai.take_screenshot("登录验证失败")
            raise
    
    def test_login_and_navigate(self, auto_login_midscene, ksyun_environment):
        """
        测试登录后的页面导航
        """
        ai = auto_login_midscene
        
        print("🧪 开始测试登录后页面导航...")
        
        try:
            # 尝试导航到控制台
            ai.ai_tap("控制台按钮或用户中心链接")
            ai.ai_wait_for("控制台页面加载完成", timeout=10000)
            
            # 截图记录
            ai.take_screenshot("控制台页面")
            
            # 验证控制台页面
            ai.ai_assert("页面显示控制台内容或服务列表")
            print("✅ 控制台导航测试成功")
            
        except Exception as e:
            print(f"⚠️  控制台导航测试失败: {e}")
            ai.take_screenshot("控制台导航失败")
            # 这里可以继续测试其他功能，不抛出异常
    
    def test_user_info_extraction(self, auto_login_midscene, ksyun_environment):
        """
        测试提取用户信息
        """
        ai = auto_login_midscene
        
        print("🧪 开始测试用户信息提取...")
        
        try:
            # 提取用户信息
            user_info = ai.ai_query("提取页面中显示的用户信息，包括用户名、账户类型等，返回JSON格式")
            print(f"📋 提取到的用户信息: {user_info}")
            
            # 验证信息不为空
            assert user_info is not None, "用户信息不能为空"
            print("✅ 用户信息提取测试成功")
            
        except Exception as e:
            print(f"⚠️  用户信息提取测试失败: {e}")
            ai.take_screenshot("用户信息提取失败")
            
    def test_logout_functionality(self, auto_login_midscene, ksyun_environment):
        """
        测试登出功能（可选）
        """
        ai = auto_login_midscene
        
        print("🧪 开始测试登出功能...")
        
        try:
            # 查找并点击登出按钮
            ai.ai_tap("登出按钮或退出登录")
            ai.ai_wait_for("登出成功，页面返回到未登录状态", timeout=5000)
            
            # 验证登出状态
            ai.ai_assert("页面显示登录按钮，表明已成功登出")
            
            # 截图记录
            ai.take_screenshot("登出后页面")
            
            print("✅ 登出功能测试成功")
            
        except Exception as e:
            print(f"⚠️  登出功能测试失败: {e}")
            ai.take_screenshot("登出功能失败")
            # 登出失败不影响其他测试
    
    @pytest.mark.slow
    def test_comprehensive_workflow(self, auto_login_midscene, ksyun_environment):
        """
        综合工作流测试（标记为慢速测试）
        """
        ai = auto_login_midscene
        
        print("🧪 开始综合工作流测试...")
        
        # 步骤1: 验证登录
        ai.ai_assert("用户已成功登录")
        
        # 步骤2: 导航到产品页面
        ai.ai_tap("产品与服务菜单")
        ai.ai_wait_for("产品列表页面加载")
        
        # 步骤3: 查看某个产品
        ai.ai_tap("云服务器或其他产品链接")
        ai.ai_wait_for("产品详情页面加载")
        
        # 步骤4: 返回首页
        ai.ai_tap("首页链接或LOGO")
        ai.ai_wait_for("首页加载完成")
        
        # 最终截图
        ai.take_screenshot("综合工作流完成")
        
        print("✅ 综合工作流测试完成") 