@echo off
chcp 65001 >nul
echo ========================================
echo 🌸 色花堂智能助手 Pro - Docker版
echo ========================================
echo.
echo 选择操作：
echo.
echo 1. 启动服务（Web + 定时任务）
echo 2. 停止服务
echo 3. 查看实时日志
echo 4. 重启服务
echo.
choice /C 1234 /N /M "请选择 (1-4): "

if errorlevel 4 goto restart
if errorlevel 3 goto logs
if errorlevel 2 goto stop
if errorlevel 1 goto start

:start
echo.
echo 🚀 启动 AW98tang 服务...
docker-compose up -d
echo.
echo ✅ 服务已启动
goto info

:stop
echo.
echo ⏹️ 停止 AW98tang 服务...
docker-compose down
echo.
echo ✅ 服务已停止
goto end

:restart
echo.
echo 🔄 重启 AW98tang 服务...
docker-compose restart
echo.
echo ✅ 服务已重启
goto info

:logs
echo.
echo 📝 实时日志（Ctrl+C退出）：
echo.
docker-compose logs -f
goto end

:info
echo.
echo ========================================
echo 📍 访问地址: http://localhost:5000
echo 🔐 默认账号: admin / admin123
echo 💡 自定义账号: 创建.env文件设置环境变量
echo ⏰ 定时任务: 在config.json中配置
echo ========================================
goto end

:end
pause

