@echo off
chcp 65001 >nul
cd ..
echo ========================================
echo 🌸 色花堂智能助手 Pro
echo ========================================
echo ⏰ 定时任务调度器启动中...
echo ========================================
echo.
echo 定时任务将在每天指定时间自动运行
echo 配置文件: config.json
echo.
python scheduler.py
pause
