#!/bin/bash

echo "========================================"
echo "🌸 色花堂智能助手 Pro - Docker版"
echo "========================================"
echo ""
echo "选择操作："
echo ""
echo "1. 启动服务（Web + 定时任务）"
echo "2. 停止服务"
echo "3. 查看实时日志"
echo "4. 重启服务"
echo "5. 查看容器状态"
echo ""
read -p "请选择 (1-5): " choice

case $choice in
    1)
        echo ""
        echo "🚀 启动 AW98tang 服务..."
        docker-compose up -d
        echo ""
        echo "✅ 服务已启动"
        ;;
    2)
        echo ""
        echo "⏹️ 停止 AW98tang 服务..."
        docker-compose down
        echo ""
        echo "✅ 服务已停止"
        exit 0
        ;;
    3)
        echo ""
        echo "📝 实时日志（Ctrl+C退出）："
        echo ""
        docker-compose logs -f
        exit 0
        ;;
    4)
        echo ""
        echo "🔄 重启 AW98tang 服务..."
        docker-compose restart
        echo ""
        echo "✅ 服务已重启"
        ;;
    5)
        echo ""
        echo "📊 容器状态："
        echo ""
        docker-compose ps
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "📍 访问地址: http://localhost:5000"
echo "🔐 登录账号: admin / admin123"
echo "⏰ 定时任务: 在config.json中配置"
echo "========================================"

