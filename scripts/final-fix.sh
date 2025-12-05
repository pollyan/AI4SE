#!/bin/bash

set -e

echo "🔧 最后的修复：直接修改服务器配置..."

# 1. 修改配置文件
echo "📝 修改nginx配置..."
sudo sed -i 's/web-app:5001/intent-test-web:5001/g' /opt/intent-test-framework/nginx/nginx.conf

# 2. 验证修改
echo "✅ 验证配置已修改："
sudo grep "intent-test-web" /opt/intent-test-framework/nginx/nginx.conf | head -2

# 3. 重启nginx
echo "🔄 重启Nginx容器..."
sudo docker restart intent-test-nginx

# 4. 等待启动
echo "⏳ 等待Nginx启动（10秒）..."
sleep 10

# 5. 检查日志
echo "📋 检查Nginx日志..."
sudo docker logs intent-test-nginx --tail 5

# 6. 测试访问
echo ""
echo "🧪 测试网站访问..."
curl -I http://localhost/testcases 2>&1 | head -10

echo ""
echo "✅ 修复完成！请刷新浏览器测试"
