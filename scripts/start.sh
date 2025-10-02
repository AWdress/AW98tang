#!/bin/bash
echo "========================================"
echo "🌸 色花堂智能助手 Pro"
echo "========================================"
echo "🚀 直接运行模式"
echo "========================================"
echo ""

# 返回项目根目录
cd "$(dirname "$0")/.." || exit

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo "❌ 配置文件 config.json 不存在！"
    echo "请复制 config.json.example 为 config.json 并填入配置信息"
    exit 1
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python"
    exit 1
fi

# 检查依赖
echo "🔍 检查依赖..."
pip3 install -q -r requirements.txt

echo "🚀 启动机器人..."
echo ""
python3 selenium_auto_bot.py

echo ""
echo "任务完成，按任意键退出..."
read -n 1
