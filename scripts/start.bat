@echo off
chcp 65001 >nul
cd ..
title 色花堂智能助手 Pro

echo ========================================
echo 🌸 色花堂智能助手 Pro
echo ========================================
echo 🚀 直接运行模式
echo ========================================
echo.

REM 检查配置文件
if not exist "config.json" (
    echo ❌ 配置文件 config.json 不存在！
    echo 请复制 config.json.example 为 config.json 并填入你的配置信息
    echo.
    echo 执行以下命令：
    echo 1. copy config.json.example config.json
    echo 2. python check_security_questions.py  （检测安全提问）
    echo 3. 编辑 config.json 文件填入账号和安全提问信息
    pause
    exit /b 1
)

echo ✅ 配置文件检查通过

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python 未安装，请先安装 Python
    pause
    exit /b 1
)

echo ✅ Python环境检查通过

REM 检查依赖包
echo 📦 检查Python依赖包...
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ 依赖包安装失败
    pause
    exit /b 1
)

echo ✅ 依赖包安装完成
echo.
echo 🚀 启动自动回帖程序...
echo 按 Ctrl+C 停止程序
echo.

REM 启动程序
python auto_reply.py

pause
