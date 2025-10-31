#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
色花堂智能助手 Pro - Web控制面板
"""

import json
import os
import threading
import time
import schedule
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from stats_manager import StatsManager
from selenium_auto_bot import SeleniumAutoBot
from update_manager import UpdateManager
import logging
from functools import wraps
try:
    from croniter import croniter
except ImportError:
    croniter = None

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production-2024')

# 从环境变量读取用户配置
WEB_USERNAME = os.getenv('WEB_USERNAME', 'admin')
WEB_PASSWORD = os.getenv('WEB_PASSWORD', 'password')

TEST_USERS = {
    WEB_USERNAME: WEB_PASSWORD
}

# 全局变量
bot_instance = None
bot_thread = None
bot_stop_flag = False  # 停止标志
scheduler_thread = None  # 定时任务线程
scheduler_stop_flag = False  # 定时任务停止标志
stats_manager = StatsManager()  # 统计管理器
update_manager = UpdateManager()  # 更新管理器
bot_status = {
    'running': False,
    'last_start': None,
    'last_stop': None,
    'total_replies': 0,
    'today_replies': 0,
    'errors': 0,
    'last_error': None
}

# 日志记录
log_messages = []
MAX_LOG_MESSAGES = 500  # 增加到500条

class WebLogHandler(logging.Handler):
    """自定义日志处理器，将日志发送到web界面"""
    def emit(self, record):
        # 过滤掉Flask的API请求日志和其他噪音日志
        message = self.format(record)
        if any(x in message for x in [
            'GET /api/',
            'POST /api/',
            'HTTP/1.1',
            '127.0.0.1 - -',
            'GET /favicon.ico',
            'Retrying (Retry',
            'NewConnectionError',
            'Failed to establish a new connection',
            'WinError 10061',
            'connection broken',
            'WebDriver manager',
            'Get LATEST chromedriver',
            'Driver [C:\\Users\\',
            'found in cache',
            'Connection pool is full'
        ]):
            return  # 跳过这些日志
        
        log_entry = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'level': record.levelname,
            'message': message
        }
        log_messages.append(log_entry)
        if len(log_messages) > MAX_LOG_MESSAGES:
            log_messages.pop(0)

# 添加web日志处理器
web_handler = WebLogHandler()
web_handler.setFormatter(logging.Formatter('%(message)s'))
logging.getLogger().addHandler(web_handler)

# 禁用Werkzeug的默认日志
import logging as sys_logging
werkzeug_logger = sys_logging.getLogger('werkzeug')
werkzeug_logger.setLevel(sys_logging.ERROR)  # 只显示错误

def load_config():
    """加载配置文件"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载配置失败: {e}")
        return {}

def save_config(config):
    """保存配置文件"""
    try:
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"保存配置失败: {e}")
        return False

def check_today_checkin_status():
    """检查今天是否已经签到成功"""
    try:
        fresh_stats = StatsManager()
        today_stats = fresh_stats.get_today_stats()
        return today_stats.get('checkin_success', False)
    except Exception as e:
        logging.error(f"检查签到状态失败: {e}")
        return False

def run_bot():
    """在后台线程中运行机器人（带重试机制）"""
    global bot_instance, bot_status, bot_stop_flag
    
    # 检查是否是测试模式
    config = load_config()
    is_test_mode = (config.get('enable_test_mode', False) or 
                    config.get('enable_test_checkin', False) or 
                    config.get('enable_test_reply', False))
    
    # 检查今天是否已经签到成功（测试模式下跳过此检查）
    if not is_test_mode and check_today_checkin_status():
        logging.info("✅ 今天已经签到成功，跳过本次运行")
        return
    
    max_retries = 3  # 最大重试次数
    retry_delay = 300  # 重试间隔（秒）= 5分钟
    
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                logging.info(f"🔄 第 {attempt}/{max_retries} 次尝试...")
            else:
                logging.info("🚀 机器人启动中...")
            
            bot_stop_flag = False  # 重置停止标志
            bot_status['running'] = True
            bot_status['last_start'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            bot_instance = SeleniumAutoBot()
            bot_instance.stop_flag = lambda: bot_stop_flag  # 传递停止标志检查函数
            
            # 检查停止标志
            if bot_stop_flag:
                logging.info("🛑 机器人已被停止")
                bot_status['running'] = False
                return
            
            # 设置浏览器
            if not bot_instance.setup_driver():
                logging.error(f"❌ 第 {attempt} 次尝试 - 浏览器启动失败")
                bot_status['last_error'] = "浏览器启动失败"
                if attempt < max_retries:
                    logging.info(f"⏰ {retry_delay}秒后进行第 {attempt + 1} 次重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    bot_status['running'] = False
                    logging.error("❌ 已达到最大重试次数，任务失败")
                    return
            
            # 检查停止标志
            if bot_stop_flag:
                logging.info("🛑 机器人已被停止")
                bot_status['running'] = False
                return
            
            # 登录
            if not bot_instance.login():
                logging.error(f"❌ 第 {attempt} 次尝试 - 登录失败")
                bot_status['last_error'] = "登录失败"
                
                # 关闭浏览器
                if bot_instance.driver:
                    try:
                        bot_instance.driver.quit()
                    except:
                        pass
                
                if attempt < max_retries:
                    logging.info(f"⏰ {retry_delay}秒后进行第 {attempt + 1} 次重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    bot_status['running'] = False
                    logging.error("❌ 已达到最大重试次数，任务失败")
                    return
            
            # 检查停止标志
            if bot_stop_flag:
                logging.info("🛑 机器人已被停止")
                bot_status['running'] = False
                return
            
            # 运行自动化任务
            bot_instance.run_auto_tasks()
            
            # 测试模式：不检查签到状态，直接完成
            if is_test_mode:
                logging.info("🧪 测试模式完成")
                bot_status['running'] = False
                bot_status['last_stop'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                return
            
            # 正常模式：检查签到是否成功
            if check_today_checkin_status():
                logging.info("🎉 签到已完成，任务成功")
                bot_status['running'] = False
                bot_status['last_stop'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                return
            else:
                logging.warning("⚠️ 任务执行完成但签到未成功")
                if attempt < max_retries:
                    logging.info(f"⏰ {retry_delay}秒后进行第 {attempt + 1} 次重试...")
                    # 关闭浏览器
                    if bot_instance.driver:
                        try:
                            bot_instance.driver.quit()
                        except:
                            pass
                    time.sleep(retry_delay)
                    continue
                else:
                    bot_status['running'] = False
                    bot_status['last_stop'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    logging.error("❌ 已达到最大重试次数，签到未完成")
                    return
            
        except Exception as e:
            logging.error(f"❌ 第 {attempt} 次尝试异常: {e}")
            bot_status['errors'] += 1
            bot_status['last_error'] = str(e)
            
            # 关闭浏览器
            if bot_instance and bot_instance.driver:
                try:
                    bot_instance.driver.quit()
                except:
                    pass
            
            if attempt < max_retries:
                logging.info(f"⏰ {retry_delay}秒后进行第 {attempt + 1} 次重试...")
                time.sleep(retry_delay)
            else:
                bot_status['running'] = False
                logging.error("❌ 已达到最大重试次数，任务失败")
                return
        finally:
            # 确保浏览器被关闭
            if bot_instance and bot_instance.driver:
                try:
                    bot_instance.driver.quit()
                    logging.info("🔚 浏览器已关闭")
                except:
                    pass
    
    bot_status['running'] = False
    bot_status['last_stop'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember')  # 获取"记住我"选项
        
        if username in TEST_USERS and TEST_USERS[username] == password:
            session['logged_in'] = True
            session['username'] = username
            
            # 如果勾选了"记住我"，设置session永久有效（7天）
            if remember:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=7)
                logging.info(f"用户 {username} 登录成功（已记住7天）")
            else:
                session.permanent = False
                logging.info(f"用户 {username} 登录成功")
            
            return redirect(url_for('index'))
        else:
            logging.warning(f"登录失败: {username}")
            return render_template('login.html', error='用户名或密码错误')
    
    # 如果已登录，直接跳转到首页
    if 'logged_in' in session:
        return redirect(url_for('index'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """退出登录"""
    username = session.get('username', 'Unknown')
    session.clear()
    logging.info(f"用户 {username} 已退出")
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """首页"""
    return render_template('index.html', username=session.get('username'))

@app.route('/api/status')
@login_required
def get_status():
    """获取机器人状态"""
    config = load_config()
    # 读取最新统计（避免与机器人线程各自内存不同步）
    fresh_stats_manager = StatsManager()
    today_stats = fresh_stats_manager.get_today_stats()
    response = jsonify({
        'status': bot_status,
        'config': {
            'max_replies_per_day': config.get('max_replies_per_day', 0),
            'target_forums': config.get('target_forums', []),
            'forum_names': config.get('forum_names', {}),
            'enable_daily_checkin': config.get('enable_daily_checkin', False),
            'reply_interval': config.get('reply_interval', [60, 180])
        },
        'stats': {
            'today_replies': today_stats['reply_count'],
            'checkin_success': today_stats['checkin_success'],
            'checkin_time': today_stats['checkin_time']
        }
    })
    # 禁用缓存，确保实时更新
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/stats')
@login_required
def get_stats():
    """获取详细统计信息"""
    # 每次请求从磁盘读取最新统计，确保实时性
    response = jsonify(StatsManager().get_all_stats())
    # 禁用缓存，确保每次都获取最新数据
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/logs')
@login_required
def get_logs():
    """获取日志"""
    response = jsonify({
        'logs': log_messages[-200:]  # 返回最新200条日志
    })
    # 禁用缓存，确保实时更新
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/config', methods=['GET', 'POST'])
@login_required
def manage_config():
    """管理配置"""
    if request.method == 'GET':
        config = load_config()
        # 隐藏敏感信息
        if 'password' in config:
            config['password'] = '******'
        return jsonify(config)
    
    elif request.method == 'POST':
        try:
            new_config = request.json
            old_config = load_config()
            
            # 如果密码是******，则保留原密码
            if new_config.get('password') == '******':
                new_config['password'] = old_config.get('password', '')
            
            # 检查定时任务配置是否变更
            scheduler_config_changed = (
                new_config.get('enable_scheduler') != old_config.get('enable_scheduler') or
                new_config.get('schedule_time') != old_config.get('schedule_time') or
                new_config.get('schedule_times') != old_config.get('schedule_times') or
                new_config.get('schedule_cron') != old_config.get('schedule_cron')
            )
            
            if save_config(new_config):
                # 如果定时任务配置变更且启用了scheduler，自动重启
                if scheduler_config_changed and new_config.get('enable_scheduler', False):
                    try:
                        restart_scheduler_thread()
                        message = '配置保存成功，定时任务已自动重新加载 ✅'
                    except Exception as e:
                        logging.error(f"重启定时任务失败: {e}")
                        message = f'配置保存成功，但定时任务重启失败: {e}'
                else:
                    message = '配置保存成功'
                
                return jsonify({'success': True, 'message': message})
            else:
                return jsonify({'success': False, 'message': '配置保存失败'}), 500
                
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/test_ai', methods=['POST'])
@login_required
def test_ai():
    """测试AI接口连接"""
    try:
        from ai_reply_service import AIReplyService
        
        config = load_config()
        ai_service = AIReplyService(config)
        
        if not ai_service.is_enabled():
            return jsonify({
                'success': False,
                'message': 'AI回复未启用或API Key未配置'
            })
        
        # 测试生成回复
        test_reply = ai_service.generate_reply("测试帖子：分享一些有趣的内容", "这是测试内容")
        
        if test_reply:
            return jsonify({
                'success': True,
                'message': f'AI接口连接成功！测试回复: {test_reply}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'AI接口调用失败，请检查配置（API URL、API Key、模型名称）'
            })
            
    except Exception as e:
        logging.error(f"AI测试失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'测试失败: {str(e)}'
        })

@app.route('/api/start', methods=['POST'])
@login_required
def start_bot():
    """启动机器人"""
    global bot_thread, bot_status
    
    if bot_status['running']:
        return jsonify({'success': False, 'message': '机器人已在运行中'})
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    return jsonify({'success': True, 'message': '机器人已启动'})

@app.route('/api/stop', methods=['POST'])
@login_required
def stop_bot():
    """停止机器人"""
    global bot_instance, bot_status, bot_stop_flag
    
    if not bot_status['running']:
        return jsonify({'success': False, 'message': '机器人未在运行'})
    
    try:
        # 设置停止标志
        bot_stop_flag = True
        logging.info("🛑 收到停止指令，正在停止机器人...")
        
        # 关闭浏览器
        if bot_instance and bot_instance.driver:
            try:
                bot_instance.driver.quit()
                logging.info("✅ 浏览器已关闭")
            except Exception as e:
                logging.warning(f"关闭浏览器时出错: {e}")
        
        # 更新状态
        bot_status['running'] = False
        bot_status['last_stop'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({'success': True, 'message': '机器人已停止'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/version')
@login_required
def get_version():
    """获取版本信息"""
    try:
        current_version = update_manager.get_current_version()
        current_commit = update_manager.get_local_commit_hash()
        
        return jsonify({
            'success': True,
            'current_version': current_version,
            'current_commit': current_commit or '未知'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/check_update')
@login_required
def check_update():
    """检查更新"""
    try:
        result = update_manager.check_update()
        return jsonify(result)
    except Exception as e:
        logging.error(f"检查更新失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/do_update', methods=['POST'])
@login_required
def do_update():
    """执行更新"""
    try:
        # 检查机器人是否在运行
        if bot_status['running']:
            return jsonify({
                'success': False,
                'message': '机器人正在运行，请先停止后再更新'
            })
        
        logging.info("开始执行系统更新...")
        result = update_manager.do_update()
        
        if result['success']:
            logging.info("系统更新成功，3秒后自动重启容器...")
            
            # 在后台线程中延迟退出进程，让Docker自动重启
            def restart_container():
                time.sleep(3)  # 给前端足够时间接收响应
                logging.info("正在重启容器...")
                os._exit(0)  # 退出进程，Docker会自动重启
            
            restart_thread = threading.Thread(target=restart_container, daemon=True)
            restart_thread.start()
            
            result['auto_restart'] = True
            result['message'] = result.get('message', '更新成功') + '\n\n容器将在3秒后自动重启...'
        else:
            logging.error(f"系统更新失败: {result.get('message')}")
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"更新失败: {e}")
        return jsonify({
            'success': False,
            'message': f'更新失败: {str(e)}'
        }), 500

@app.route('/api/update_logs')
@login_required
def get_update_logs():
    """获取更新日志"""
    try:
        limit = request.args.get('limit', 10, type=int)
        result = update_manager.get_update_log(limit)
        return jsonify(result)
    except Exception as e:
        logging.error(f"获取更新日志失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def calculate_uptime():
    """计算运行时间"""
    if bot_status.get('last_start'):
        start_time = datetime.strptime(bot_status['last_start'], '%Y-%m-%d %H:%M:%S')
        if bot_status['running']:
            delta = datetime.now() - start_time
            return str(delta).split('.')[0]  # 移除微秒
    return "未运行"

def scheduled_task():
    """定时任务 - 在后台线程运行（支持动态重载）"""
    global scheduler_stop_flag
    
    def run_scheduled_bot():
        """执行定时任务"""
        logging.info("⏰ 定时任务触发，开始运行机器人...")
        run_bot()
    
    while not scheduler_stop_flag:
        # 每次循环都重新加载配置，支持动态更新
        config = load_config()
        
        if not config.get('enable_scheduler', False):
            logging.info("⏰ 定时任务已禁用，等待重新启用...")
            time.sleep(60)
            continue
        
        # 清空之前的任务
        schedule.clear()
        
        # 支持三种配置方式
        cron_expr = config.get('schedule_cron', '').strip()
        schedule_times = config.get('schedule_times', [])
        schedule_time = config.get('schedule_time', '03:00')
        
        # 优先使用cron表达式
        if cron_expr and croniter:
            try:
                # 使用cron表达式
                cron = croniter(cron_expr, datetime.now())
                next_time = cron.get_next(datetime)
                logging.info(f"⏰ 使用Cron表达式: {cron_expr}")
                logging.info(f"⏰ 下次运行: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 持续检查cron触发时间
                while not scheduler_stop_flag:
                    now = datetime.now()
                    if now >= next_time:
                        run_scheduled_bot()
                        # 计算下一次运行时间
                        cron = croniter(cron_expr, now)
                        next_time = cron.get_next(datetime)
                        logging.info(f"⏰ 下次运行: {next_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    time.sleep(30)  # 每30秒检查一次
                    
                    # 检查配置是否改变
                    new_config = load_config()
                    if new_config.get('schedule_cron', '').strip() != cron_expr:
                        logging.info("🔄 检测到配置变更，重新加载...")
                        break
            except Exception as e:
                logging.error(f"Cron表达式解析失败: {e}")
                time.sleep(60)
                continue
        
        # 使用多时间段
        elif schedule_times and isinstance(schedule_times, list):
            for time_str in schedule_times:
                if time_str and isinstance(time_str, str):
                    try:
                        schedule.every().day.at(time_str.strip()).do(run_scheduled_bot)
                        logging.info(f"⏰ 已设置定时任务: 每天 {time_str}")
                    except Exception as e:
                        logging.error(f"设置定时任务失败 ({time_str}): {e}")
        
        # 使用单一时间（兼容旧配置）
        else:
            try:
                schedule.every().day.at(schedule_time).do(run_scheduled_bot)
                logging.info(f"⏰ 已设置定时任务: 每天 {schedule_time}")
            except Exception as e:
                logging.error(f"设置定时任务失败: {e}")
        
        # 运行调度器（每60秒检查一次配置变更）
        check_count = 0
        last_config = config.copy()
        
        while not scheduler_stop_flag:
            schedule.run_pending()
            time.sleep(10)  # 每10秒检查一次任务
            
            check_count += 1
            if check_count >= 6:  # 每60秒检查配置变更
                check_count = 0
                new_config = load_config()
                # 检查关键配置是否变化
                if (new_config.get('schedule_time') != last_config.get('schedule_time') or
                    new_config.get('schedule_times') != last_config.get('schedule_times') or
                    new_config.get('schedule_cron') != last_config.get('schedule_cron') or
                    new_config.get('enable_scheduler') != last_config.get('enable_scheduler')):
                    logging.info("🔄 检测到定时任务配置变更，正在重新加载...")
                    break

def start_scheduler_thread():
    """在后台线程启动定时任务调度器"""
    global scheduler_thread, scheduler_stop_flag
    
    scheduler_stop_flag = False
    scheduler_thread = threading.Thread(target=scheduled_task, daemon=True)
    scheduler_thread.start()
    logging.info("🔄 定时任务调度器已在后台启动")

def stop_scheduler_thread():
    """停止定时任务调度器"""
    global scheduler_stop_flag
    scheduler_stop_flag = True
    schedule.clear()
    logging.info("⏸️ 定时任务调度器已停止")

def restart_scheduler_thread():
    """重启定时任务调度器（配置更新后调用）"""
    logging.info("🔄 重启定时任务调度器...")
    stop_scheduler_thread()
    time.sleep(1)  # 等待线程完全停止
    start_scheduler_thread()
    logging.info("✅ 定时任务调度器已重启，新配置已生效")

if __name__ == '__main__':
    print("=" * 50)
    print("🌸 色花堂智能助手 Pro - Web控制面板")
    print("=" * 50)
    print("📍 访问地址: http://localhost:5000")
    print(f"🔐 登录账号: {WEB_USERNAME} / {'*' * len(WEB_PASSWORD)}")
    print("=" * 50)
    
    # 启动定时任务后台线程
    config = load_config()
    if config.get('enable_scheduler', False):
        cron_expr = config.get('schedule_cron', '').strip()
        schedule_times = config.get('schedule_times', [])
        schedule_time = config.get('schedule_time', '03:00')
        
        if cron_expr:
            print(f"⏰ 定时任务已启用（Cron模式）: {cron_expr}")
        elif schedule_times and isinstance(schedule_times, list):
            print(f"⏰ 定时任务已启用（多时间段）: {', '.join(schedule_times)}")
        else:
            print(f"⏰ 定时任务已启用: 每天 {schedule_time}")
        
        print("💡 配置修改后会自动重新加载，无需重启")
        start_scheduler_thread()
    
    print("=" * 50)
    
    # 启动Flask Web服务
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

