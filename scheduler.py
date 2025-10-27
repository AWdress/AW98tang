#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
色花堂智能助手 Pro - 定时任务调度器
每天自动运行机器人（回复+签到）
支持自动重试和多次调度
支持标准cron表达式
"""

import json
import time
import schedule
import logging
from datetime import datetime
from croniter import croniter
from selenium_auto_bot import SeleniumAutoBot
from stats_manager import StatsManager

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

def check_today_checkin_status():
    """检查今天是否已经签到成功"""
    try:
        stats = StatsManager()
        today_stats = stats.get_today_stats()
        return today_stats.get('checkin_success', False)
    except Exception as e:
        logging.error(f"检查签到状态失败: {e}")
        return False

def run_bot_task():
    """执行机器人任务（带重试机制）"""
    # 检查今天是否已经签到成功
    if check_today_checkin_status():
        logging.info("✅ 今天已经签到成功，跳过本次运行")
        return True
    
    max_retries = 3  # 最大重试次数
    retry_delay = 300  # 重试间隔（秒）
    
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                logging.info(f"🔄 第 {attempt}/{max_retries} 次尝试...")
            else:
                logging.info("⏰ 定时任务触发，开始运行机器人...")
            
            bot = SeleniumAutoBot()
            success = bot.run()
            
            if success:
                logging.info("✅ 定时任务执行成功")
                
                # 再次检查签到是否成功
                if check_today_checkin_status():
                    logging.info("🎉 签到已完成，今天不再运行")
                    return True
                else:
                    logging.warning("⚠️ 任务执行成功但签到未完成")
                    if attempt < max_retries:
                        logging.info(f"⏰ {retry_delay}秒后进行第 {attempt + 1} 次重试...")
                        time.sleep(retry_delay)
                    continue
            else:
                logging.error(f"❌ 第 {attempt} 次尝试失败")
                if attempt < max_retries:
                    logging.info(f"⏰ {retry_delay}秒后进行第 {attempt + 1} 次重试...")
                    time.sleep(retry_delay)
                else:
                    logging.error("❌ 已达到最大重试次数，本次任务失败")
                    return False
                    
        except Exception as e:
            logging.error(f"❌ 第 {attempt} 次尝试异常: {e}")
            if attempt < max_retries:
                logging.info(f"⏰ {retry_delay}秒后进行第 {attempt + 1} 次重试...")
                time.sleep(retry_delay)
            else:
                logging.error("❌ 已达到最大重试次数，本次任务失败")
                return False
    
    return False

def parse_cron_to_next_run(cron_expr):
    """解析cron表达式并返回下次运行时间"""
    try:
        base_time = datetime.now()
        cron = croniter(cron_expr, base_time)
        next_time = cron.get_next(datetime)
        return next_time
    except Exception as e:
        logging.error(f"解析cron表达式失败: {e}")
        return None

def is_cron_expression(expr):
    """判断是否为cron表达式（5个或6个字段）"""
    if isinstance(expr, str):
        parts = expr.strip().split()
        return len(parts) in [5, 6]
    return False

def main():
    """主函数"""
    config = load_config()
    
    if not config.get('enable_scheduler', False):
        print("⚠️ 定时任务未启用")
        print("请在 config.json 中设置 'enable_scheduler': true")
        return
    
    # 支持三种配置方式
    cron_expr = config.get('schedule_cron')  # 新增：cron表达式
    schedule_times = config.get('schedule_times', ['03:00', '09:00', '15:00', '21:00'])
    
    # 兼容旧配置
    if 'schedule_time' in config and 'schedule_times' not in config and not cron_expr:
        schedule_times = [config.get('schedule_time', '03:00')]
    
    print("=" * 60)
    print("🌸 色花堂智能助手 Pro - 定时任务调度器")
    print("=" * 60)
    
    # 优先使用cron表达式
    if cron_expr:
        try:
            # 验证cron表达式
            if is_cron_expression(cron_expr):
                next_run_time = parse_cron_to_next_run(cron_expr)
                if next_run_time:
                    print(f"📅 调度模式: Cron表达式")
                    print(f"⏰ Cron: {cron_expr}")
                    print(f"🔄 自动重试: 开启（每次最多重试3次）")
                    print(f"🎯 智能检测: 签到成功后自动跳过")
                    print(f"⏰ 下次运行: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print("💡 按 Ctrl+C 停止调度器")
                    print("=" * 60)
                    logging.info(f"✅ 已设置cron定时任务: {cron_expr}")
                    
                    # 使用cron模式运行
                    last_run = None
                    try:
                        while True:
                            now = datetime.now()
                            cron = croniter(cron_expr, now)
                            next_time = cron.get_next(datetime)
                            
                            # 检查是否到达运行时间
                            if last_run is None or now >= next_time:
                                # 避免重复运行
                                if last_run is None or (now - last_run).total_seconds() > 60:
                                    logging.info(f"⏰ Cron触发: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                                    run_bot_task()
                                    last_run = now
                            
                            time.sleep(30)  # 每30秒检查一次
                    except KeyboardInterrupt:
                        print("\n⏹️ 定时任务调度器已停止")
                    return
                else:
                    print(f"❌ Cron表达式无效: {cron_expr}")
                    print("将使用时间点模式...")
            else:
                print(f"❌ Cron表达式格式错误: {cron_expr}")
                print("Cron表达式应为5个或6个字段，例如: 0 3,9,15,21 * * *")
                print("将使用时间点模式...")
        except Exception as e:
            logging.error(f"Cron模式初始化失败: {e}")
            print(f"❌ Cron模式错误: {e}")
            print("将使用时间点模式...")
    
    # 使用时间点模式
    print(f"📅 调度模式: 固定时间点")
    print(f"⏰ 运行时间: {', '.join(schedule_times)}")
    print(f"🔄 自动重试: 开启（每次最多重试3次）")
    print(f"🎯 智能检测: 签到成功后自动跳过")
    print("💡 按 Ctrl+C 停止调度器")
    print("=" * 60)
    
    # 设置多个定时任务
    for schedule_time in schedule_times:
        schedule.every().day.at(schedule_time).do(run_bot_task)
        logging.info(f"✅ 已设置定时任务: 每天 {schedule_time}")
    
    # 显示下次运行时间
    next_run = schedule.next_run()
    if next_run:
        print(f"⏰ 下次运行时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 持续运行
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
            
    except KeyboardInterrupt:
        print("\n⏹️ 定时任务调度器已停止")

if __name__ == "__main__":
    main()



