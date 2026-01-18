
import pytest
from backend.agents.shared.progress_utils import clean_response_streaming

def test_clean_response_streaming_corrupts_markdown():
    """
    [TDD] 复现 Markdown 格式（加粗、换行、反引号）被 clean_response_streaming 损坏的问题
    """
    input_text = """---**第一议题：系统边界与身份验证模式** 我已收到您提供的详细需求文档。

基于文档内容，我已确认了部分信息，现在需要聚焦澄清 **剩余的模糊点**。我们已经完成了 `1/3` 模糊点的确认：
* ✅ **问题 1 (系统边界)**: “登录功能”是一个 **具体产品/系统/网站** 中的业务环节。系统是“校园宝” - 面向大学生的二手交易平台。这是一个 **ToC的互联网应用**。我们还有 **2个** 模糊点需要澄清：---"""

    cleaned = clean_response_streaming(input_text)
    
    # 验证关键格式是否保留
    assert "**第一议题" in cleaned, "标题加粗丢失"
    assert "\n\n" in cleaned, "段落换行丢失"
    assert "`1/3`" in cleaned, "行内代码反引号丢失"
    assert "**ToC的互联网应用**" in cleaned, "正文加粗丢失"
    assert "**2个**" in cleaned, "数字加粗丢失"
    
    # 验证是否出现了损坏的特征 (根据用户反馈)
    assert "ToC的互联网应用我们还有" not in cleaned, "换行被吞导致文字粘连"
