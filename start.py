#!/usr/bin/env python3
"""
AI4SE工具集启动脚本
简化版本，直接启动统一的API应用
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.getcwd())

# 导入应用
from api.index import app

if __name__ == "__main__":
    print("=== AI4SE工具集启动中 ===")
    print("📍 Web界面: http://localhost:5001")
    print("📍 API接口: http://localhost:5001/api/v1/")
    print("📍 MidSceneJS: http://localhost:3001") 
    print("=========================")
    
    # 启动应用
    app.run(debug=True, host="0.0.0.0", port=5001)