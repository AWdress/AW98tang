#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
色花堂智能助手 Pro - 定时任务调度器
每天自动运行机器人（回复+签到）
"""

import json
import time
import schedule
import logging
from datetime import datetime
from selenium_auto_bot import SeleniumAutoBot

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def load_config():
    """加载配置文件"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载配置失败: {e}")
        return {}

def run_bot_task():
    """执行机器人任务"""
    try:
        logging.info("⏰ 定时任务触发，开始运行机器人...")
        bot = SeleniumAutoBot()
        success = bot.run()
        
        if success:
            logging.info("✅ 定时任务执行成功")
        else:
            logging.error("❌ 定时任务执行失败")
            
    except Exception as e:
        logging.error(f"❌ 定时任务执行异常: {e}")

def main():
    """主函数"""
    config = load_config()
    
    if not config.get('enable_scheduler', False):
        print("⚠️ 定时任务未启用")
        print("请在 config.json 中设置 'enable_scheduler': true")
        return
    
    schedule_time = config.get('schedule_time', '03:00')
    
    print("=" * 50)
    print("🌸 色花堂智能助手 Pro - 定时任务")
    print("=" * 50)
    print(f"📅 每日运行时间: {schedule_time}")
    print(f"🔄 下次运行: 今天 {schedule_time}")
    print("💡 按 Ctrl+C 停止调度器")
    print("=" * 50)
    
    # 设置定时任务
    schedule.every().day.at(schedule_time).do(run_bot_task)
    
    # 持续运行
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
            
    except KeyboardInterrupt:
        print("\n⏹️ 定时任务调度器已停止")

if __name__ == "__main__":
    main()



