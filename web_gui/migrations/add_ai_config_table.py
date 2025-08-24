#!/usr/bin/env python3
"""
添加AI配置表的数据库迁移脚本 - 简化版
用于支持Story 1.4: AI配置管理功能
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from web_gui.app_enhanced import create_app
from web_gui.models import db, RequirementsAIConfig


def create_ai_config_table():
    """创建AI配置表"""
    
    app = create_app()
    
    with app.app_context():
        try:
            print("🔄 开始创建AI配置表...")
            
            # 创建RequirementsAIConfig表
            db.create_all()
            
            print("✅ AI配置表创建完成")
            
            # 检查表是否存在并插入默认配置
            if db.engine.dialect.has_table(db.engine.connect(), "requirements_ai_configs"):
                
                # 检查是否已有默认配置
                existing_default = RequirementsAIConfig.get_default_config()
                
                if not existing_default:
                    # 创建默认配置（使用环境变量或占位符）
                    default_config = RequirementsAIConfig(
                        config_name="默认DashScope配置",
                        provider="dashscope",
                        api_key=os.getenv("OPENAI_API_KEY", "your_api_key_here"),
                        base_url=os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
                        model_name=os.getenv("MIDSCENE_MODEL_NAME", "qwen-vl-max-latest"),
                        is_default=True,
                        is_active=True
                    )
                    
                    db.session.add(default_config)
                    db.session.commit()
                    
                    print("✅ 默认AI配置创建完成")
                else:
                    print("ℹ️  默认AI配置已存在，跳过创建")
                
                print("🎉 AI配置表迁移完成！")
            else:
                print("❌ 表创建失败")
                
        except Exception as e:
            print(f"❌ 创建AI配置表时出错: {str(e)}")
            db.session.rollback()
            raise e


if __name__ == "__main__":
    print("=" * 60)
    print("AI配置表数据库迁移脚本")
    print("=" * 60)
    
    try:
        create_ai_config_table()
    except Exception as e:
        print(f"💥 迁移失败: {str(e)}")
        sys.exit(1)
    
    print("🏆 数据库迁移成功完成！")