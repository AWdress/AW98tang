#!/bin/bash
echo "========================================"
echo "🌸 色花堂智能助手 Pro"
echo "========================================"
echo "🌐 Web控制面板启动中..."
echo "========================================"
echo ""

# 返回项目根目录
cd "$(dirname "$0")/.." || exit

echo "正在启动服务器..."
echo "📍 访问地址: http://localhost:5000"
echo "🔐 登录账号: admin / admin123"
echo "💡 按 Ctrl+C 停止服务器"
echo ""

python3 web_app.py
