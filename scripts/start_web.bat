@echo off
chcp 65001 >nul
cd ..
echo ========================================
echo 🌸 色花堂智能助手 Pro
echo ========================================
echo 🌐 Web控制面板启动中...
echo ========================================
echo.
echo 正在启动服务器...
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 停止服务器
echo.
python web_app.py
pause
