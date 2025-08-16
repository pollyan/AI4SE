#!/usr/bin/env python3
"""
调试不同模块中的SQLAlchemy实例ID
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=== 调试不同模块中的db实例ID ===")

# 1. 检查models.py中的db实例
print("\n1. 检查models.py中的db实例：")
from models import db as models_db
print(f"   models.db 实例ID: {id(models_db)}")

# 2. 检查app_enhanced.py中的db实例
print("\n2. 检查app_enhanced.py中的db实例：")
from app_enhanced import db as app_db
print(f"   app_enhanced.db 实例ID: {id(app_db)}")

# 3. 检查api.base.py中的db实例
print("\n3. 检查api.base.py中的db实例：")
from api.base import db as base_db
print(f"   api.base.db 实例ID: {id(base_db)}")

# 4. 检查api.executions.py中的db实例  
print("\n4. 检查api.executions.py中的db实例：")
sys.path.append('/Users/huian@thoughtworks.com/Program/intent-test-framework/web_gui')
from api.executions import db as executions_db
print(f"   api.executions.db 实例ID: {id(executions_db)}")

# 5. 检查services.database_service.py中的db实例
print("\n5. 检查services.database_service.py中的db实例：")
from services.database_service import db as service_db
print(f"   services.database_service.db 实例ID: {id(service_db)}")

print("\n=== 所有实例ID对比 ===")
print(f"models.db:        {id(models_db)}")
print(f"app_enhanced.db:  {id(app_db)}")
print(f"api.base.db:      {id(base_db)}")
print(f"api.executions.db: {id(executions_db)}")
print(f"services.db:      {id(service_db)}")

# 检查是否所有实例都相同
all_ids = [id(models_db), id(app_db), id(base_db), id(executions_db), id(service_db)]
if len(set(all_ids)) == 1:
    print("✅ 所有db实例ID都相同")
else:
    print("❌ 发现不同的db实例ID，这是问题的根源！")
    
print("\n=== 调试完成 ===")