"""
统计管理器 - 记录每日回复和签到数据
"""
import json
import os
from datetime import datetime
from typing import Dict, List

class StatsManager:
    def __init__(self, stats_file="data/stats.json"):
        self.stats_file = stats_file
        self.ensure_data_dir()
        self.stats = self.load_stats()
    
    def ensure_data_dir(self):
        """确保数据目录存在"""
        data_dir = os.path.dirname(self.stats_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def load_stats(self) -> Dict:
        """加载统计数据"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载统计数据失败: {e}")
                return self.get_default_stats()
        return self.get_default_stats()
    
    def get_default_stats(self) -> Dict:
        """获取默认统计数据结构"""
        return {
            "today": datetime.now().strftime("%Y-%m-%d"),
            "reply_count": 0,
            "checkin_success": False,
            "checkin_time": None,
            "replies": [],
            "history": []
        }
    
    def save_stats(self):
        """保存统计数据"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存统计数据失败: {e}")
    
    def check_and_reset_daily(self):
        """检查并重置每日统计"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.stats.get("today") != today:
            # 保存昨天的数据到历史
            if self.stats.get("reply_count", 0) > 0 or self.stats.get("checkin_success", False):
                history_entry = {
                    "date": self.stats.get("today"),
                    "reply_count": self.stats.get("reply_count", 0),
                    "checkin_success": self.stats.get("checkin_success", False),
                    "checkin_time": self.stats.get("checkin_time"),
                    "replies_summary": len(self.stats.get("replies", []))
                }
                if "history" not in self.stats:
                    self.stats["history"] = []
                self.stats["history"].insert(0, history_entry)
                # 只保留最近30天的历史
                self.stats["history"] = self.stats["history"][:30]
            
            # 重置今日数据
            self.stats["today"] = today
            self.stats["reply_count"] = 0
            self.stats["checkin_success"] = False
            self.stats["checkin_time"] = None
            self.stats["replies"] = []
            self.save_stats()
    
    def add_reply(self, thread_title: str, thread_url: str, reply_content: str):
        """添加回复记录"""
        self.check_and_reset_daily()
        
        reply_record = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": thread_title,
            "url": thread_url,
            "content": reply_content
        }
        
        if "replies" not in self.stats:
            self.stats["replies"] = []
        
        self.stats["replies"].append(reply_record)
        self.stats["reply_count"] = len(self.stats["replies"])
        self.save_stats()
    
    def mark_checkin_success(self):
        """标记签到成功"""
        self.check_and_reset_daily()
        self.stats["checkin_success"] = True
        self.stats["checkin_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_stats()
    
    def get_today_stats(self) -> Dict:
        """获取今日统计"""
        self.check_and_reset_daily()
        return {
            "date": self.stats.get("today"),
            "reply_count": self.stats.get("reply_count", 0),
            "checkin_success": self.stats.get("checkin_success", False),
            "checkin_time": self.stats.get("checkin_time"),
            "replies": self.stats.get("replies", [])
        }
    
    def get_history(self, days: int = 7) -> List[Dict]:
        """获取历史统计"""
        return self.stats.get("history", [])[:days]
    
    def get_all_stats(self) -> Dict:
        """获取完整统计数据"""
        self.check_and_reset_daily()
        return {
            "today": self.get_today_stats(),
            "history": self.get_history()
        }

