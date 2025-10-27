#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器测试脚本
用于测试自动重试和签到状态检测功能
"""

import json
import sys
from datetime import datetime
from stats_manager import StatsManager

def test_checkin_status():
    """测试签到状态检测"""
    print("=" * 60)
    print("🧪 测试签到状态检测功能")
    print("=" * 60)
    
    stats = StatsManager()
    today_stats = stats.get_today_stats()
    
    print(f"📅 今日日期: {today_stats['date']}")
    print(f"💬 回复数量: {today_stats['reply_count']}")
    
    if today_stats['checkin_success']:
        print(f"✅ 签到状态: 已签到")
        print(f"⏰ 签到时间: {today_stats['checkin_time']}")
    else:
        print(f"✅ 签到状态: 未签到")
    
    print("=" * 60)
    return today_stats['checkin_success']

def test_config():
    """测试配置文件"""
    print("\n" + "=" * 60)
    print("🧪 测试配置文件")
    print("=" * 60)
    
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查必要配置
        enable_scheduler = config.get('enable_scheduler', False)
        schedule_times = config.get('schedule_times', [])
        
        # 兼容旧配置
        if 'schedule_time' in config and not schedule_times:
            schedule_times = [config['schedule_time']]
        
        print(f"📋 定时任务状态: {'已启用 ✅' if enable_scheduler else '未启用 ⚠️'}")
        print(f"⏰ 调度时间点: {', '.join(schedule_times)}")
        print(f"📊 配置的时间点数量: {len(schedule_times)}")
        
        if not enable_scheduler:
            print("\n⚠️  提示: 需要在 config.json 中设置 'enable_scheduler': true")
        
        if not schedule_times:
            print("\n⚠️  警告: 未配置任何调度时间点！")
            print("   建议添加 'schedule_times': ['03:00', '09:00', '15:00', '21:00']")
        
        print("=" * 60)
        return True
        
    except FileNotFoundError:
        print("❌ 错误: 找不到 config.json 文件")
        print("=" * 60)
        return False
    except json.JSONDecodeError as e:
        print(f"❌ 错误: config.json 格式错误 - {e}")
        print("=" * 60)
        return False

def test_schedule_logic():
    """测试调度逻辑"""
    print("\n" + "=" * 60)
    print("🧪 测试调度逻辑")
    print("=" * 60)
    
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        schedule_times = config.get('schedule_times', ['03:00', '09:00', '15:00', '21:00'])
        
        # 兼容旧配置
        if 'schedule_time' in config and not schedule_times:
            schedule_times = [config['schedule_time']]
        
        print("📅 调度计划:")
        for i, time_str in enumerate(schedule_times, 1):
            print(f"   {i}. 每天 {time_str}")
        
        print("\n🔄 重试机制:")
        print("   - 最大重试次数: 3次")
        print("   - 重试间隔: 300秒（5分钟）")
        print("   - 总耗时: 最多约15分钟")
        
        print("\n🎯 智能检测:")
        print("   - 每次运行前检查签到状态")
        print("   - 已签到则自动跳过")
        print("   - 未签到则继续执行任务")
        
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print("=" * 60)
        return False

def simulate_checkin_success():
    """模拟签到成功（用于测试）"""
    print("\n" + "=" * 60)
    print("🧪 模拟签到成功")
    print("=" * 60)
    
    try:
        stats = StatsManager()
        stats.mark_checkin_success()
        print("✅ 已标记今日签到成功")
        print(f"⏰ 签到时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"❌ 模拟失败: {e}")
        print("=" * 60)
        return False

def reset_checkin_status():
    """重置签到状态（用于测试）"""
    print("\n" + "=" * 60)
    print("🧪 重置签到状态")
    print("=" * 60)
    
    try:
        import os
        stats_file = 'data/stats.json'
        
        if os.path.exists(stats_file):
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats_data = json.load(f)
            
            stats_data['checkin_success'] = False
            stats_data['checkin_time'] = None
            
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
            
            print("✅ 已重置签到状态为未签到")
        else:
            print("ℹ️  统计文件不存在，无需重置")
        
        print("=" * 60)
        return True
    except Exception as e:
        print(f"❌ 重置失败: {e}")
        print("=" * 60)
        return False

def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("🌸 色花堂智能助手 Pro - 调度器测试工具")
    print("=" * 70)
    print("用途: 测试自动重试和签到状态检测功能")
    print("=" * 70)
    
    # 测试配置文件
    if not test_config():
        print("\n❌ 配置文件测试失败，请检查配置")
        return
    
    # 测试调度逻辑
    test_schedule_logic()
    
    # 测试签到状态检测
    checkin_status = test_checkin_status()
    
    # 根据签到状态给出建议
    print("\n" + "=" * 60)
    print("💡 测试结果分析")
    print("=" * 60)
    
    if checkin_status:
        print("✅ 今天已经签到成功")
        print("📋 如果现在运行调度器，会自动跳过")
        print("\n🔧 测试命令:")
        print("   python test_scheduler.py reset   # 重置签到状态")
    else:
        print("ℹ️  今天还未签到")
        print("📋 如果现在运行调度器，会正常执行任务")
        print("\n🔧 测试命令:")
        print("   python test_scheduler.py simulate   # 模拟签到成功")
    
    print("\n🚀 启动调度器:")
    print("   python scheduler.py")
    
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "simulate":
            simulate_checkin_success()
            test_checkin_status()
        elif command == "reset":
            reset_checkin_status()
            test_checkin_status()
        elif command == "status":
            test_checkin_status()
        else:
            print(f"❌ 未知命令: {command}")
            print("\n可用命令:")
            print("  python test_scheduler.py          # 运行完整测试")
            print("  python test_scheduler.py simulate # 模拟签到成功")
            print("  python test_scheduler.py reset    # 重置签到状态")
            print("  python test_scheduler.py status   # 查看签到状态")
    else:
        main()

