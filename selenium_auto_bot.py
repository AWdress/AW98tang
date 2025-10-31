#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
色花堂智能助手 Pro - 核心机器人程序
智能回复 · 自动签到 · 验证码识别 · 完全自动化
"""

import json
import time
import random
import logging
import pickle
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from stats_manager import StatsManager
from ai_reply_service import AIReplyService

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/selenium_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class SeleniumAutoBot:
    def __init__(self, config_file='config.json'):
        """初始化Selenium自动化机器人"""
        self.config = self.load_config(config_file)
        self.driver = None
        self.wait = None
        self.stop_flag = lambda: False  # 停止标志检查函数
        self.stats = StatsManager()  # 初始化统计管理器
        self.ai_service = AIReplyService(self.config)  # 初始化AI服务
        
        # 配置信息
        self.base_url = self.config.get('base_url', 'https://sehuatang.org/')
        self.username = self.config.get('username', '')
        self.password = self.config.get('password', '')
        self.security_question_id = self.config.get('security_question_id', '')
        self.security_answer = self.config.get('security_answer', '')
        
        # Cookies 保存路径
        self.cookies_file = 'data/cookies.pkl'
        os.makedirs('data', exist_ok=True)
        
        # 自动化配置
        self.daily_reply_limit = self.config.get('max_replies_per_day', 10)
        reply_interval = self.config.get('reply_interval', 120)
        # 处理reply_interval可能是数组的情况
        if isinstance(reply_interval, list) and len(reply_interval) == 2:
            self.reply_interval_min = reply_interval[0]
            self.reply_interval_max = reply_interval[1]
        else:
            self.reply_interval_min = reply_interval
            self.reply_interval_max = reply_interval
        self.target_forums = self.config.get('target_forums', ['fid=141'])
        self.enable_daily_checkin = self.config.get('enable_daily_checkin', True)
        self.enable_auto_reply = self.config.get('enable_auto_reply', True)
        self.enable_test_mode = self.config.get('enable_test_mode', False)
        self.enable_test_checkin = self.config.get('enable_test_checkin', False)
        self.enable_test_reply = self.config.get('enable_test_reply', False)
        self.enable_smart_reply = self.config.get('enable_smart_reply', True)
        self.skip_keywords = self.config.get('skip_keywords', [])
        self.skip_prefixes = self.config.get('skip_prefixes', [])
        self.forum_names = self.config.get('forum_names', {})
        
        # 智能回复模板
        self.smart_reply_templates = self.config.get('smart_reply_templates', {})
        
        # 回复模板
        self.reply_templates = self.config.get('reply_templates', [
            '感谢分享！',
            '很不错的内容',
            '支持楼主！',
            '谢谢分享，收藏了'
        ])
        
    def load_config(self, config_file):
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"配置文件 {config_file} 不存在")
            return {}
        except json.JSONDecodeError as e:
            logging.error(f"配置文件格式错误: {e}")
            return {}
    
    def setup_driver(self, headless=False):
        """设置Chrome浏览器"""
        chrome_options = Options()
        
        # Docker环境自动启用headless模式
        import os
        is_docker = os.path.exists('/.dockerenv')
        
        if headless or is_docker:
            chrome_options.add_argument('--headless=new')  # 新版headless模式
            if is_docker:
                logging.info("🐳 检测到Docker环境，启用headless模式")
        
        # 反检测设置
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        chrome_options.add_argument('--remote-debugging-port=9222')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 设置用户代理
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            from selenium.webdriver.chrome.service import Service
            import os
            
            # Docker环境优先使用预装的ChromeDriver
            if os.path.exists('/usr/local/bin/chromedriver'):
                logging.info("🚀 使用系统预装的 ChromeDriver")
                service = Service('/usr/local/bin/chromedriver')
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # 本地环境使用webdriver-manager自动管理
                from webdriver_manager.chrome import ChromeDriverManager
                logging.info("📥 使用 webdriver-manager 自动下载 ChromeDriver")
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 20)
            
            # 设置页面加载超时（防止页面加载卡住）
            self.driver.set_page_load_timeout(60)
            logging.info("⏱️ 设置页面加载超时: 60秒")
            
            logging.info("✅ Chrome浏览器启动成功")
            return True
            
        except Exception as e:
            logging.error(f"❌ 浏览器启动失败: {e}")
            logging.error("请确保已安装Chrome浏览器和ChromeDriver")
            
            # 提供详细的解决方案
            logging.error("解决方案:")
            logging.error("1. 确保Chrome浏览器已安装")
            logging.error("2. 下载对应版本的ChromeDriver")
            logging.error("3. 将chromedriver.exe放在程序目录中")
            return False
    
    def handle_age_verification(self):
        """处理年龄验证"""
        try:
            # 检查是否有年龄验证页面
            if "满18岁" in self.driver.page_source or "If you are over 18" in self.driver.page_source:
                logging.info("🔞 检测到年龄验证页面")
                
                # 查找进入按钮
                enter_buttons = self.driver.find_elements(By.XPATH, "//*[contains(text(), '进入') or contains(text(), 'click here') or contains(text(), 'enter')]")
                
                if enter_buttons:
                    logging.info("点击年龄验证按钮...")
                    enter_buttons[0].click()
                    time.sleep(3)
                    logging.info("✅ 年龄验证完成")
                else:
                    logging.warning("未找到年龄验证按钮")
                    
        except Exception as e:
            logging.warning(f"年龄验证处理异常: {e}")
    
    def wait_for_cloudflare(self):
        """等待Cloudflare验证完成"""
        max_wait = 60  # 最多等待60秒
        start_time = time.time()
        
        logging.info("🛡️ 等待Cloudflare验证...")
        
        while time.time() - start_time < max_wait:
            try:
                # 检查是否还在Cloudflare页面
                if "safeid" not in self.driver.page_source and "CF$cv$params" not in self.driver.page_source:
                    logging.info("✅ Cloudflare验证完成")
                    return True
                
                # 检查是否需要点击验证框
                try:
                    checkbox = self.driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                    if checkbox.is_displayed() and not checkbox.is_selected():
                        logging.info("点击Cloudflare验证框...")
                        checkbox.click()
                except:
                    pass
                
                time.sleep(2)
                
            except Exception as e:
                logging.debug(f"Cloudflare检查异常: {e}")
                time.sleep(2)
        
        logging.warning("⚠️ Cloudflare验证超时，继续尝试...")
        return False
    
    def login(self):
        """自动登录"""
        try:
            logging.info("🔐 开始自动登录...")
            
            # 访问登录页面
            login_url = f"{self.base_url}member.php?mod=logging&action=login"
            logging.info(f"🌐 正在访问登录页面: {login_url}")
            
            try:
                self.driver.get(login_url)
                logging.info(f"✅ 登录页面加载完成，当前URL: {self.driver.current_url}")
            except Exception as e:
                logging.error(f"❌ 访问登录页面失败: {e}")
                logging.error(f"❌ 这可能是网络问题或网站访问受限")
                return False
            
            # 处理年龄验证
            self.handle_age_verification()
            
            # 等待页面加载完成
            time.sleep(3)
            
            # 等待登录表单加载
            try:
                username_field = self.wait.until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                logging.info("✅ 登录表单加载完成")
            except TimeoutException:
                # 尝试其他可能的用户名字段
                try:
                    username_field = self.driver.find_element(By.NAME, "user")
                except:
                    logging.error("❌ 找不到用户名输入框")
                    return False
            
            # 填写用户名
            username_field.clear()
            username_field.send_keys(self.username)
            logging.info(f"📝 填写用户名: {self.username}")
            
            # 填写密码
            password_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_field.clear()
            password_field.send_keys(self.password)
            logging.info("🔑 填写密码")
            
            # 处理安全提问
            if self.security_question_id and self.security_answer:
                try:
                    question_select = self.driver.find_element(By.NAME, "questionid")
                    select = Select(question_select)
                    select.select_by_value(self.security_question_id)
                    logging.info(f"🔒 选择安全提问: {self.security_question_id}")
                    
                    # 等待选择生效
                    time.sleep(1)
                    
                    answer_field = self.driver.find_element(By.NAME, "answer")
                    answer_field.clear()
                    answer_field.send_keys(self.security_answer)
                    logging.info("✅ 填写安全提问答案")
                    
                    # 等待输入完成
                    time.sleep(2)
                    
                except NoSuchElementException:
                    logging.info("ℹ️ 未发现安全提问，跳过")
            
            # 等待表单完全准备好
            logging.info("⏳ 等待表单准备完成...")
            time.sleep(3)
            
            # 查找正确的登录按钮
            login_button = None
            
            # 尝试多种登录按钮选择器，按优先级排序
            login_selectors = [
                "button[name='loginsubmit']",  # Discuz论坛常用
                "input[name='loginsubmit']",   # Discuz变体
                "button.pn.pnc",               # Discuz样式
                "input[value='登录']",
                "input[value='登錄']", 
                ".btn_submit",
                "input[type='submit'][value*='登']",
                "form button[type='submit']",  # 表单中的提交按钮
                "form input[type='submit']:last-child"  # 表单中最后一个提交按钮
            ]
            
            for selector in login_selectors:
                try:
                    if ":contains(" in selector:
                        # 使用XPath查找包含文本的按钮
                        buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), '登录')] | //input[contains(@value, '登录')]")
                    else:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for btn in buttons:
                        try:
                            if btn.is_displayed() and btn.is_enabled():
                                # 对于name='loginsubmit'的按钮，直接认可
                                if 'loginsubmit' in selector.lower():
                                    login_button = btn
                                    btn_text = (btn.text or btn.get_attribute('value') or '').strip()
                                    logging.info(f"✅ 找到登录按钮 (选择器: {selector})")
                                    break
                                
                                # 其他按钮需要检查文本
                                btn_text = (btn.text or btn.get_attribute('value') or btn.get_attribute('textContent') or '').strip()
                                if '登录' in btn_text or '登錄' in btn_text or 'login' in btn_text.lower():
                                    login_button = btn
                                    logging.info(f"✅ 找到登录按钮: {btn_text} (选择器: {selector})")
                                    break
                        except:
                            continue
                    
                    if login_button:
                        break
                        
                except Exception as e:
                    logging.debug(f"选择器 {selector} 失败: {e}")
                    continue
            
            if not login_button:
                logging.error("❌ 找不到登录按钮，尝试备用方案...")
                # 备用方案：只查找可点击的按钮/输入元素，排除标题等
                try:
                    # 只查找 button 和 input 元素，排除 h1-h6, div, span 等
                    all_login_elements = self.driver.find_elements(By.XPATH, 
                        "//button[contains(text(), '登录') or contains(@value, '登录')] | //input[contains(@value, '登录')]")
                    
                    for elem in all_login_elements:
                        try:
                            if elem.is_displayed() and elem.is_enabled():
                                elem_tag = elem.tag_name
                                elem_text = (elem.text or elem.get_attribute('value') or '').strip()
                                logging.info(f"🔍 尝试使用备用登录元素: <{elem_tag}> {elem_text}")
                                login_button = elem
                                break
                        except:
                            continue
                except Exception as e:
                    logging.debug(f"备用方案失败: {e}")
                
                if not login_button:
                    logging.error("❌ 所有登录按钮查找方案均失败")
                    # 保存页面HTML用于调试
                    try:
                        with open('debug/login_page_debug.html', 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        logging.info("📄 已保存页面HTML到 debug/login_page_debug.html")
                    except:
                        pass
                    return False
            
            # 滚动到登录按钮位置，确保可见
            self.driver.execute_script("arguments[0].scrollIntoView();", login_button)
            time.sleep(1)
            
            # 高亮显示按钮（调试用）
            self.driver.execute_script("arguments[0].style.border='3px solid red';", login_button)
            time.sleep(1)
            
            login_button.click()
            logging.info("🚀 点击登录按钮")
            
            # 等待登录结果
            time.sleep(5)
            
            # 检查登录是否成功
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            
            # 多种登录成功的判断条件
            success_indicators = [
                "欢迎您回来" in page_source,
                "退出" in page_source,
                "个人资料" in page_source,
                "我的帖子" in page_source,
                "member.php?mod=logging&action=logout" in page_source,
                "搜索内容不能少于2位" in page_source,  # 这个错误说明已经登录了
                current_url != login_url and "login" not in current_url
            ]
            
            if any(success_indicators):
                logging.info("🎉 登录成功！")
                logging.info(f"当前页面: {current_url}")
                
                # 保存登录状态
                self.save_cookies()
                
                return True
            else:
                logging.error("❌ 登录失败，请检查账号信息")
                logging.error(f"当前页面: {current_url}")
                # 保存页面截图用于调试
                try:
                    self.driver.save_screenshot("debug/login_failed.png")
                    logging.info("📸 登录失败截图已保存: debug/login_failed.png")
                except:
                    pass
                return False
                
        except Exception as e:
            logging.error(f"❌ 登录过程发生错误: {e}")
            return False
    
    def save_cookies(self):
        """保存登录cookies到文件"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            logging.info(f"🍪 登录状态已保存到 {self.cookies_file}")
            return True
        except Exception as e:
            logging.error(f"❌ 保存cookies失败: {e}")
            return False
    
    def load_cookies(self):
        """从文件加载cookies"""
        try:
            if not os.path.exists(self.cookies_file):
                logging.info("ℹ️ 未找到已保存的登录状态")
                return False
            
            # 先访问网站，确保域名匹配
            logging.info("🌐 正在访问网站...")
            self.driver.get(self.base_url)
            time.sleep(2)
            
            # 加载cookies
            with open(self.cookies_file, 'rb') as f:
                cookies = pickle.load(f)
            
            for cookie in cookies:
                try:
                    # 移除可能导致问题的字段
                    if 'expiry' in cookie:
                        cookie['expiry'] = int(cookie['expiry'])
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logging.debug(f"添加cookie失败: {e}")
            
            logging.info("✅ 登录状态已加载")
            
            # 刷新页面以应用cookies
            self.driver.refresh()
            time.sleep(3)
            
            return True
            
        except Exception as e:
            logging.error(f"❌ 加载cookies失败: {e}")
            return False
    
    def check_login_status(self):
        """检查当前是否已登录"""
        try:
            # 先检查当前页面
            page_source = self.driver.page_source
            
            # 首页快速检查（避免额外跳转）
            quick_indicators = [
                "member.php?mod=logging&action=logout" in page_source,
                "space-username" in page_source,  # 论坛常见的用户名class
                f'>{self.username}<' in page_source  # 用户名标签
            ]
            
            if any(quick_indicators):
                logging.info(f"✅ 快速检测到已登录状态（用户: {self.username}）")
                return True
            
            # 如果快速检查未通过，访问个人中心确认
            logging.info("🔍 快速检查未通过，访问个人中心确认登录状态...")
            try:
                # 访问个人中心页面
                profile_url = f"{self.base_url}home.php?mod=space&do=profile"
                self.driver.get(profile_url)
                time.sleep(2)
                
                page_source = self.driver.page_source
                current_url = self.driver.current_url
                
                # 详细检查登录标识
                login_indicators = [
                    "退出" in page_source,
                    "个人资料" in page_source,
                    "我的帖子" in page_source,
                    "member.php?mod=logging&action=logout" in page_source,
                    self.username in page_source,
                    "space-username" in page_source
                ]
                
                # 如果跳转到登录页面，说明未登录
                if "member.php?mod=logging" in current_url and "action=login" in current_url:
                    logging.info("ℹ️ 已跳转到登录页面，登录状态已过期")
                    return False
                
                if any(login_indicators):
                    logging.info(f"✅ 确认已登录状态（用户: {self.username}）")
                    return True
                else:
                    logging.info("ℹ️ 未检测到登录状态")
                    return False
                    
            except Exception as e:
                logging.warning(f"⚠️ 访问个人中心失败: {e}，尝试其他方式检查")
                # 降级：只要没有跳转到登录页面，就认为已登录
                current_url = self.driver.current_url
                if "member.php?mod=logging" not in current_url:
                    logging.info("✅ 未跳转到登录页面，认为已登录")
                    return True
                return False
                
        except Exception as e:
            logging.error(f"❌ 检查登录状态失败: {e}")
            return False
    
    def daily_checkin(self, test_mode=False):
        """每日签到"""
        try:
            if test_mode:
                logging.info("🧪 [测试模式] 开始测试签到流程...")
            else:
                logging.info("📅 开始每日签到...")
            
            # 尝试多个可能的签到URL
            checkin_urls = [
                f"{self.base_url}plugin.php?id=dd_sign&ac=sign",
                f"{self.base_url}plugin.php?id=dsu_paulsign:sign",
                f"{self.base_url}home.php?mod=task&do=apply&id=1",
                f"{self.base_url}plugin.php?id=checkin"
            ]
            
            for i, checkin_url in enumerate(checkin_urls, 1):
                try:
                    if test_mode:
                        logging.info(f"🧪 [测试 {i}/{len(checkin_urls)}] 尝试签到页面: {checkin_url}")
                    else:
                        logging.info(f"🔍 [{i}/{len(checkin_urls)}] 尝试签到页面: {checkin_url}")
                    
                    self.driver.get(checkin_url)
                    time.sleep(3)
                    
                    # 检查页面是否有效
                    if "404" in self.driver.page_source or "页面不存在" in self.driver.page_source:
                        if test_mode:
                            logging.info(f"⚠️ [测试] 页面无效，跳过")
                        continue
                    
                    # 检查是否有验证码
                    page_text = self.driver.page_source
                    import re
                    
                    # 查找数学验证码（如 47 - 2 = ?）
                    math_pattern = r'(\d+)\s*([+\-×x*÷/])\s*(\d+)\s*=\s*\?'
                    math_match = re.search(math_pattern, page_text)
                    
                    if math_match:
                        num1 = int(math_match.group(1))
                        operator = math_match.group(2)
                        num2 = int(math_match.group(3))
                        
                        # 计算结果
                        if operator in ['+', '＋']:
                            result = num1 + num2
                        elif operator in ['-', '－', '—']:
                            result = num1 - num2
                        elif operator in ['×', 'x', '*', '＊']:
                            result = num1 * num2
                        elif operator in ['÷', '/', '／']:
                            result = num1 // num2
                        else:
                            result = 0
                        
                        if test_mode:
                            logging.info(f"🧪 [测试] 检测到验证码: {num1} {operator} {num2} = ?")
                            logging.info(f"🧪 [测试] 计算结果: {result}")
                        else:
                            logging.info(f"🔢 检测到验证码: {num1} {operator} {num2} = ?")
                            logging.info(f"✅ 计算结果: {result}")
                        
                        # 查找验证码输入框
                        captcha_input = None
                        captcha_selectors = [
                            "input[name*='answer']",
                            "input[name*='seccode']",
                            "input[type='text'][name*='验证']",
                            "input[placeholder*='答案']",
                            "input[placeholder*='验证']"
                        ]
                        
                        for selector in captcha_selectors:
                            try:
                                inputs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                for inp in inputs:
                                    if inp.is_displayed() and inp.is_enabled():
                                        captcha_input = inp
                                        break
                                if captcha_input:
                                    break
                            except:
                                continue
                        
                        if captcha_input:
                            if test_mode:
                                logging.info(f"✅ [测试] 找到验证码输入框")
                                captcha_input.send_keys(str(result))
                                logging.info(f"✅ [测试] 已输入验证码答案: {result}")
                            else:
                                captcha_input.send_keys(str(result))
                                logging.info(f"✅ 已输入验证码答案: {result}")
                            time.sleep(1)
                        else:
                            logging.warning(f"⚠️ 未找到验证码输入框")
                    
                    # 查找签到按钮的多种可能
                    button_selectors = [
                        "input[value*='签到']",
                        "button:contains('签到')",
                        ".btn:contains('签到')",
                        "input[type='submit']",
                        "button[type='submit']",
                        ".sign_btn",
                        "#sign_btn",
                        "a[href*='sign']"
                    ]
                    
                    button_found = False
                    found_button = None
                    found_selector = ""
                    
                    for selector in button_selectors:
                        try:
                            if ":contains(" in selector:
                                # 使用XPath查找包含文本的元素
                                xpath = f"//*[contains(text(), '签到')]"
                                buttons = self.driver.find_elements(By.XPATH, xpath)
                            else:
                                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            
                            for button in buttons:
                                if button.is_displayed() and button.is_enabled():
                                    found_button = button
                                    found_selector = selector
                                    button_found = True
                                    
                                    if test_mode:
                                        # 测试模式：只找到按钮，不点击
                                        button_text = button.text or button.get_attribute('value') or '签到按钮'
                                        logging.info(f"✅ [测试] 找到签到按钮: {selector}")
                                        logging.info(f"✅ [测试] 按钮文本: {button_text}")
                                        logging.info(f"✅ [测试] 签到URL: {checkin_url}")
                                        logging.info(f"🚫 [测试] 测试模式 - 不点击签到按钮")
                                    else:
                                        # 正常模式：点击签到
                                        button.click()
                                        logging.info(f"✅ 签到成功 (选择器: {selector})")
                                        # 记录签到统计
                                        self.stats.mark_checkin_success()
                                        time.sleep(2)
                                    break
                            
                            if button_found:
                                break
                                
                        except Exception as e:
                            if test_mode:
                                logging.debug(f"选择器 {selector} 失败: {e}")
                            continue
                    
                    if button_found:
                        if test_mode:
                            logging.info(f"🧪 [测试] 签到流程测试完成")
                        return True
                    
                    # 检查是否已经签到
                    if "已签到" in self.driver.page_source or "已经签到" in self.driver.page_source:
                        if test_mode:
                            logging.info("ℹ️ [测试] 检测到今日已签到")
                        else:
                            logging.info("ℹ️ 今日已签到")
                        return True
                        
                except Exception as e:
                    logging.debug(f"签到URL {checkin_url} 失败: {e}")
                    continue
            
            # 如果所有URL都失败，尝试从首页找签到链接
            if not button_found:
                try:
                    if test_mode:
                        logging.info("🧪 [测试] 尝试从首页查找签到链接...")
                    else:
                        logging.info("🏠 从首页查找签到链接...")
                    
                    self.driver.get(self.base_url)
                    time.sleep(3)
                    
                    # 查找签到相关链接
                    sign_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), '签到') or contains(@href, 'sign')]")
                    
                    if sign_links:
                        link = sign_links[0]
                        link_text = link.text or '签到'
                        link_href = link.get_attribute('href')
                        
                        if test_mode:
                            logging.info(f"✅ [测试] 找到签到链接")
                            logging.info(f"✅ [测试] 链接文本: {link_text}")
                            logging.info(f"✅ [测试] 链接地址: {link_href}")
                            logging.info(f"🚫 [测试] 测试模式 - 不点击签到链接")
                        else:
                            link.click()
                            time.sleep(3)
                            logging.info(f"✅ 找到并点击签到链接: {link_text}")
                    else:
                        if test_mode:
                            logging.info("⚠️ [测试] 首页未找到签到功能")
                        else:
                            logging.info("ℹ️ 未找到签到功能")
                        
                except Exception as e:
                    logging.debug(f"从首页查找签到失败: {e}")
                
        except Exception as e:
            if test_mode:
                logging.error(f"❌ [测试] 签到测试失败: {e}")
            else:
                logging.error(f"❌ 签到失败: {e}")
    
    def get_forum_posts(self, forum_id="fid=141", max_posts=20):
        """获取论坛帖子列表"""
        try:
            forum_display = self.forum_names.get(forum_id, forum_id)
            logging.info(f"📋 获取论坛帖子: {forum_id} - {forum_display}")
            
            # 访问论坛页面
            forum_url = f"{self.base_url}forum.php?mod=forumdisplay&{forum_id}"
            self.driver.get(forum_url)
            time.sleep(3)
            
            # 查找帖子链接
            post_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='thread-'], a[href*='tid=']")
            
            posts = []
            seen_tids = set()  # 用于去重
            
            for link in post_links:
                if len(posts) >= max_posts:
                    break
                    
                href = link.get_attribute('href')
                title = link.text.strip()
                
                if not href or not title or 'thread' not in href:
                    continue
                
                # 提取tid进行去重
                import re
                tid_match = re.search(r'tid[=-](\d+)', href)
                if tid_match:
                    tid = tid_match.group(1)
                    if tid in seen_tids:
                        continue  # 跳过重复的帖子
                    seen_tids.add(tid)
                    
                    # 清理URL，只保留主要的帖子链接（去掉页码）
                    clean_url = re.sub(r'&page=\d+', '', href)
                    clean_url = re.sub(r'&extra=.*', '', clean_url)
                    
                    posts.append({
                        'url': clean_url,
                        'title': title,
                        'tid': tid
                    })
            
            logging.info(f"✅ 找到 {len(posts)} 个帖子")
            return posts
            
        except Exception as e:
            logging.error(f"❌ 获取帖子失败: {e}")
            return []
    
    def reply_to_post(self, post_url, reply_content=None, post_title=""):
        """回复帖子"""
        try:
            logging.info(f"💬 回复帖子: {post_url}")
            
            # 访问帖子页面
            self.driver.get(post_url)
            time.sleep(3)
            
            # 使用智能回复选择内容
            if not reply_content:
                # 尝试获取帖子内容（首楼部分文字）
                post_content = ""
                try:
                    # 尝试获取帖子正文的前500字符
                    content_selectors = [
                        ".t_f",  # Discuz帖子内容
                        ".pcb",  # Discuz帖子内容区
                        "#postmessage_",  # 帖子消息
                        ".message"
                    ]
                    for selector in content_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                post_content = elements[0].text[:500]  # 只取前500字符
                                break
                        except:
                            continue
                except Exception as e:
                    logging.debug(f"获取帖子内容失败: {e}")
                
                # 使用标题和内容生成智能回复
                if post_title:
                    reply_content = self.get_smart_reply(post_title, post_content)
                else:
                    reply_content = random.choice(self.reply_templates)
            
            # 查找回复框
            try:
                # 尝试不同的回复框选择器（针对Discuz论坛优化）
                reply_selectors = [
                    "textarea[name='message']",      # 标准Discuz
                    "#fastpostmessage",               # 快速回复
                    "textarea#e_textarea",            # 编辑器
                    "textarea.pt",                    # Discuz样式
                    ".reply_textarea",
                    "textarea"                        # 通用
                ]
                
                reply_box = None
                for selector in reply_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.is_enabled():
                                reply_box = elem
                                logging.info(f"✅ 找到回复框: {selector}")
                                break
                        if reply_box:
                            break
                    except Exception as e:
                        logging.debug(f"选择器 {selector} 失败: {e}")
                        continue
                
                if not reply_box:
                    logging.error("❌ 找不到回复框")
                    # 保存页面HTML用于调试
                    try:
                        with open('debug/reply_page_debug.html', 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        logging.info("📄 已保存页面HTML到 debug/reply_page_debug.html")
                    except:
                        pass
                    return False
                
                # 填写回复内容
                reply_box.clear()
                reply_box.send_keys(reply_content)
                logging.info(f"📝 填写回复内容: {reply_content}")
                
                # 查找并点击提交按钮（排除搜索按钮）
                submit_selectors = [
                    "input[type='submit'][value*='回复']",
                    "input[type='submit'][value*='发表']",
                    "button[name='replysubmit']",  # Discuz回复按钮
                    "button[name='topicsubmit']",  # Discuz发帖按钮
                    ".btn_submit"
                ]
                
                submit_button = None
                for selector in submit_selectors:
                    try:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for btn in buttons:
                            # 排除搜索按钮
                            if btn.is_displayed():
                                btn_name = btn.get_attribute('name') or ''
                                btn_id = btn.get_attribute('id') or ''
                                btn_value = btn.get_attribute('value') or ''
                                btn_text = btn.text or ''
                                
                                # 排除搜索相关按钮
                                if 'search' in btn_name.lower() or 'search' in btn_id.lower():
                                    continue
                                if 'scbar' in btn_id.lower():
                                    continue
                                
                                # 确认是回复按钮
                                if '回复' in btn_value or '发表' in btn_value or '回复' in btn_text or '发表' in btn_text or 'reply' in btn_name.lower():
                                    submit_button = btn
                                    logging.info(f"✅ 找到回复提交按钮: {selector}")
                                    break
                        
                        if submit_button:
                            break
                    except:
                        continue
                
                if submit_button:
                    # 使用JavaScript点击，避免被其他元素遮挡
                    try:
                        # 先尝试滚动到按钮位置
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                        time.sleep(0.5)
                        
                        # 使用JavaScript点击，绕过遮挡问题
                        self.driver.execute_script("arguments[0].click();", submit_button)
                        logging.info("🚀 提交回复")
                        time.sleep(3)
                    except Exception as e:
                        logging.error(f"❌ 点击提交按钮失败: {e}")
                        return False
                    
                    # 检查回复是否成功（多种成功标识）
                    page_source = self.driver.page_source
                    current_url = self.driver.current_url
                    
                    success_indicators = [
                        "回复发表成功" in page_source,
                        "感谢您的回复" in page_source,
                        "回复成功" in page_source,
                        "发表成功" in page_source,
                        "帖子已提交" in page_source,
                        # 如果页面有跳转或刷新，也认为成功
                        "tid=" in current_url and "forum.php" in current_url
                    ]
                    
                    if any(success_indicators):
                        logging.info("✅ 回复成功")
                        # 记录回复统计
                        self.stats.add_reply(post_title, post_url, reply_content)
                        return True
                    else:
                        # 保存页面用于调试
                        try:
                            with open('debug/reply_result_debug.html', 'w', encoding='utf-8') as f:
                                f.write(page_source)
                            logging.info("📄 已保存回复结果页面到 debug/reply_result_debug.html")
                        except:
                            pass
                        logging.warning("⚠️ 回复可能失败，请检查调试文件")
                        return False
                else:
                    logging.error("❌ 找不到提交按钮")
                    return False
                    
            except Exception as e:
                logging.error(f"❌ 回复过程出错: {e}")
                return False
                
        except Exception as e:
            logging.error(f"❌ 访问帖子失败: {e}")
            return False
    
    def should_skip_post(self, title, post_url=""):
        """判断是否应该跳过该帖子"""
        # 检查跳过关键词
        for keyword in self.skip_keywords:
            if keyword in title:
                logging.info(f"⏭️ 跳过包含关键词 '{keyword}' 的帖子: {title}")
                return True
        
        # 检查跳过前缀
        for prefix in self.skip_prefixes:
            if title.startswith(prefix):
                logging.info(f"⏭️ 跳过前缀为 '{prefix}' 的帖子: {title}")
                return True
        
        # 检查是否已经回复过该帖子（根据URL）
        if post_url:
            all_replies = self.stats.get_all_replies(limit=1000)  # 获取最近1000条回复记录
            for reply in all_replies:
                if reply.get('url') == post_url:
                    logging.info(f"⏭️ 跳过已回复过的帖子: {title}")
                    return True
        
        return False
    
    def get_smart_reply(self, title, content=""):
        """根据帖子标题和内容生成纯色情风格回复"""
        if not self.enable_smart_reply:
            return random.choice(self.reply_templates)
        
        # 优先尝试使用AI生成回复
        if self.ai_service.is_enabled():
            logging.info("🤖 尝试使用AI生成回复...")
            ai_reply = self.ai_service.generate_reply(title, content)
            if ai_reply:
                logging.info(f"✅ AI回复成功: {ai_reply}")
                return ai_reply
            else:
                logging.warning("⚠️ AI回复失败，降级使用规则回复")
        
        # AI未启用或失败时，使用规则生成回复
        # 合并标题和内容
        full_text = title + " " + content
        import re
        
        # 提取明星名字（中国明星优先）
        star_name = ""
        
        # 中国明星名字列表
        chinese_stars = [
            '刘亦菲', '杨幂', '赵丽颖', '古力娜扎', '迪丽热巴', 
            '范冰冰', '杨颖', 'Angelababy', '唐嫣', '郑爽',
            '关晓彤', '欧阳娜娜', '宋茜', '倪妮', '周冬雨',
            '刘诗诗', '高圆圆', '林志玲', '舒淇', '徐若瑄'
        ]
        
        for star in chinese_stars:
            if star in full_text:
                star_name = star
                break
        
        # 如果没找到中国明星，尝试提取日本女优名字
        if not star_name:
            # 日本女优名字模式
            jp_patterns = [
                r'[^\x00-\xff]{2,5}(?:かな|なるみ|みゆ|結衣|美穂|百合香)',
                r'京野結衣|森沢かな|綾瀬なるみ|鳳みゆ|沢北みなみ|川北メイサ|三宮つばき|葵百合香'
            ]
            for pattern in jp_patterns:
                name_match = re.search(pattern, title)
                if name_match:
                    star_name = name_match.group(0)
                    break
        
        # 详细特征检测
        has_高清 = any(x in full_text for x in ['4K', '8K', '1080P', '2160P', 'HEVC', '高清', '原档'])
        
        # 身材细节特征
        has_巨乳 = any(x in full_text for x in ['巨乳', '爆乳', '大奶', 'G罩杯', 'H罩杯', 'I罩杯', '大きな'])
        has_美腿 = any(x in full_text for x in ['美腿', '长腿', '美脚', '腿'])
        has_翘臀 = any(x in full_text for x in ['翘臀', '美臀', '屁股', 'お尻'])
        has_细腰 = any(x in full_text for x in ['细腰', '小蛮腰', 'A4腰', '纤腰'])
        has_嫩 = any(x in full_text for x in ['嫩', '粉嫩', '少女', '清纯'])
        has_紧 = any(x in full_text for x in ['激狭', '狭', '紧', '紧致', 'マ◯コ', 'きつい'])
        has_湿润 = any(x in full_text for x in ['湿', '濡れ', '潮吹', '喷水'])
        
        # 性格特征
        has_淫荡 = any(x in full_text for x in ['淫荡', '骚', '浪', '淫乱', 'エロい'])
        has_可爱 = any(x in full_text for x in ['可爱', 'かわいい', '愛嬌', '甜美'])
        
        # 内容特征
        has_无码 = '无码' in full_text
        has_VR = 'VR' in full_text
        has_中出 = any(x in full_text for x in ['中出', '内射', '射精'])
        has_多P = any(x in full_text for x in ['3P', '4P', '多P', '群交', '輪姦'])
        has_口交 = any(x in full_text for x in ['口交', 'フェラ', '吹箫'])
        has_肛交 = any(x in full_text for x in ['肛交', 'アナル', '后入'])
        has_AI换脸 = any(x in full_text for x in ['AI换脸', 'AI增强', 'deepfake', 'Deepfake'])
        has_明星 = any(x in full_text for x in ['刘亦菲', '杨幂', '赵丽颖', '古力娜扎', '迪丽热巴', '明星'])
        
        # 构建有文采的色情回复（参考示例风格）
        reply_sentences = []
        
        # 根据特征构建描述性句子
        
        # 紧致特征（100个回复）
        if has_紧:
            tight_phrases = [
                "激狭美穴让人心痒难耐，真想亲身体验那种紧致的快感",
                "那紧致的小穴一定爽到爆，想狠狠插进去感受",
                "光是想象那紧窄的感觉就让人欲罢不能",
                "紧致的蜜穴肯定能把鸡巴夹得死死的，太爽了",
                "紧窄的小逼插进去肯定爽翻天",
                "激狭名器，想插进去感受那极致的包裹感",
                "这么紧的屄，进去肯定夹得很舒服",
                "紧致蜜穴，每次抽插都能爽到头皮发麻",
                "狭窄小穴太诱人了，想狠狠贯穿",
                "那种紧致感想想就硬了，太想操了",
                "激狭逼穴，鸡巴插进去肯定爽爆",
                "紧到不行的小穴，想体验被夹得动弹不得的感觉",
                "这紧致度绝了，插进去肯定舒服得要命",
                "名器级的紧致感，想好好开发一番",
                "狭窄湿润，插入的瞬间肯定爽翻",
                "紧窄小穴夹得鸡巴要爆炸了",
                "激狭美穴，想一插到底感受那极致快感",
                "紧致得让人欲罢不能，真想狠狠操烂",
                "这紧度太顶了，想插进去慢慢品味",
                "狭小蜜穴，抽插起来肯定摩擦感十足",
                "紧窄逼洞夹得我射得特别快",
                "激狭小屄，插一次爽一次",
                "这紧致感太上瘾了，想天天插",
                "名器般的紧致，每次都能榨干我",
                "狭窄蜜洞，插进去就不想出来",
                "紧得像处女一样，太爽了",
                "激狭美逼，想狠狠开拓",
                "紧致小穴吸得我欲罢不能",
                "这紧度堪称完美，想插烂它",
                "狭窄逼眼太诱人，想用力捅进去",
                "紧致感爆表，插进去爽到起飞",
                "激狭蜜穴夹得鸡巴疼痛又爽",
                "这紧窄程度绝了，想慢慢享受",
                "名器级小屄，想好好品味",
                "紧致湿滑，插入感太完美了",
                "激狭逼洞，每次抽插都爽翻",
                "紧得让人射精都困难，太爽了",
                "狭窄蜜穴，想插到最深处",
                "这紧致度让我疯狂，想狂插不止",
                "激狭美穴包裹感太强了",
                "紧窄小逼，插着插着就射了",
                "紧致蜜洞，想一整晚都插着",
                "激狭屄眼，进出都是极致享受",
                "这紧度太犯规了，根本把持不住",
                "狭窄逼穴，想用鸡巴撑开",
                "紧致感让每次抽插都爽爆",
                "激狭名器，想插到她求饶",
                "紧窄蜜穴，夹得我头皮发麻",
                "这紧致小屄太销魂了",
                "激狭美逼，想狠狠贯穿到底",
                "紧得让人欲仙欲死，太爽了",
                "狭窄小穴，想插得她腿发软",
                "紧致蜜洞吸力太强了",
                "激狭逼穴，想天天操",
                "这紧窄感让我射得特别爽",
                "名器级紧致，想好好开发",
                "狭窄美穴，插进去就硬了",
                "紧致小逼，想插到精尽人亡",
                "激狭蜜穴，每一下都爽到极致",
                "紧窄屄眼，想慢慢磨蹭",
                "这紧致度太犯规，想狂操",
                "激狭美屄夹得我动不了",
                "紧致小穴，想插得她浪叫",
                "狭窄蜜洞，抽插声音太刺激",
                "紧得像要把我夹断，爽翻了",
                "激狭逼洞，想用力顶到最深",
                "这紧致感太完美，欲罢不能",
                "名器般小穴，想狠狠蹂躏",
                "紧窄美逼，插着太舒服了",
                "激狭蜜穴，想射在里面",
                "紧致屄眼，每次都能榨干",
                "狭窄小屄太诱人，想日夜不停",
                "这紧度让我疯狂，想插烂",
                "激狭美穴，插进去就不想拔出来",
                "紧窄蜜洞夹得我要射了",
                "紧致逼穴，想狠狠冲刺",
                "激狭小逼，插着太爽了",
                "这紧致感太上头，想一直插",
                "狭窄美穴吸得我魂都没了",
                "紧致蜜洞，想插到她崩溃",
                "激狭屄眼，每次都爽到颤抖",
                "紧窄小穴太完美，想天天操",
                "这紧致度堪称极品",
                "激狭美逼，想插得她求饶",
                "紧致蜜穴，夹得我欲仙欲死",
                "狭窄逼洞，想狠狠贯穿",
                "这紧度太销魂，控制不住",
                "激狭小屄，想插到射不出来",
                "紧窄美穴包裹感太强",
                "紧致蜜洞，想慢慢品尝",
                "激狭逼眼，插进去爽炸了",
                "这紧致小穴太犯规了",
                "狭窄屄洞，想用力捅进去",
                "紧致美逼，每次都射得特别爽",
                "激狭蜜穴，想插到腿软",
                "紧窄小逼太诱人，想狂插",
                "这紧度让人发疯，太爽了",
                "激狭美穴夹得我要崩溃",
                "紧致蜜洞，想插个够本"
            ]
            reply_sentences.append(random.choice(tight_phrases))
        
        # 巨乳特征（100个回复）
        if has_巨乳:
            breast_phrases = [
                "那对巨乳摇曳的样子肯定很诱人，想狠狠揉捏",
                "大奶子晃来晃去太刺激了，忍不住想埋进去",
                "丰满的胸部让人食指大动，真想好好玩弄一番",
                "爆乳太诱人了，想边插边抓着那对大奶",
                "奶子又大又软，想狠狠揉搓",
                "巨乳在身下摇晃的景象肯定很爽",
                "大波霸看着就想含在嘴里吸",
                "丰满巨乳，想埋进去窒息而亡",
                "奶子这么大，乳交肯定很舒服",
                "波涛汹涌，看着就想上手揉",
                "巨乳女优就是好，奶子大操着爽",
                "爆乳摇晃太刺激，想抓着奶子狠狠插",
                "大奶子太诱人，想边吸边操",
                "胸这么大，夹鸡巴肯定很爽",
                "丰乳肥臀，奶子看着就想舔",
                "巨乳晃得我眼花，鸡巴都硬了",
                "波霸级别，想把脸埋进去",
                "奶子又圆又大，想狠狠玩弄",
                "巨乳诱惑太大了，看着就流口水",
                "大胸美女最骚了，想抓着奶子后入",
                "这对奶子太完美了，想日夜把玩",
                "巨乳摇晃的样子太销魂，硬了",
                "大奶抖动起来太诱人，想舔个够",
                "爆乳太犯规了，想夹着鸡巴射",
                "丰满双乳，想边操边捏",
                "奶子大得夸张，想狠狠蹂躏",
                "巨乳晃动的节奏太撩人",
                "大波浪看着就受不了，想埋进去",
                "胸部这么饱满，想好好享受",
                "爆乳女优最爽，奶子揉着特舒服",
                "巨大奶子，想用鸡巴戳",
                "丰乳配小蛮腰，身材绝了",
                "大奶晃得我把持不住",
                "巨乳诱惑力太强，想狠狠吸",
                "奶子又软又弹，想玩一整晚",
                "爆乳摇起来太刺激，看着就射",
                "丰满巨乳夹着鸡巴肯定爽翻",
                "大胸器太诱人，想抓着不放",
                "巨乳女神，奶子看着就硬",
                "波霸身材，想边插边揉奶",
                "奶子这么大只，想狠狠抓",
                "巨乳晃动太淫荡，看着就想操",
                "大奶子软软的，想捏爆",
                "爆乳太顶了，想含在嘴里",
                "丰满双峰，想埋脸进去",
                "巨乳摇晃声都听得见，太骚了",
                "大奶子看着就流水，想摸",
                "胸部太饱满，想边操边玩",
                "爆乳级别，夹鸡巴肯定爽",
                "巨大奶子晃得人心痒",
                "丰乳美臀，身材太犯规",
                "大胸妹子，奶子揉着最爽",
                "巨乳诱惑，想狠狠吸奶",
                "奶子又大又挺，想玩弄",
                "爆乳摇晃画面太刺激",
                "丰满巨乳，想边插边抓",
                "大波浪太诱人，想埋进去吸",
                "巨乳女优最骚，奶子大操着舒服",
                "胸器太犯规，看着就硬了",
                "爆乳晃动太淫荡",
                "巨大双乳，想狠狠揉捏",
                "丰满奶子，想含住不放",
                "大胸美女操起来最爽",
                "巨乳摇曳太销魂",
                "奶子饱满，想边操边玩弄",
                "爆乳太诱惑，想夹射",
                "丰乳配骚脸，绝配",
                "大奶子抖动太刺激",
                "巨乳晃得我要射了",
                "胸部太大，想狠狠蹂躏",
                "爆乳女优，奶子最好玩",
                "巨大双峰，想埋进去",
                "丰满巨乳夹着最舒服",
                "大胸器晃动太骚",
                "巨乳诱惑，看着就想摸",
                "奶子又圆又软，想捏",
                "爆乳摇晃太淫荡",
                "丰满奶子想边吸边插",
                "大波霸太诱人",
                "巨乳女神，想抓着奶子操",
                "胸这么大，乳交肯定爽爆",
                "爆乳级身材，太完美了",
                "巨大奶子，想狠狠玩",
                "丰乳肥臀，想从后面抓奶操",
                "大奶晃动节奏太撩人",
                "巨乳美女，奶子看着就想射",
                "奶子太饱满，想揉到她叫",
                "爆乳摇起来太骚",
                "丰满双乳，想边插边吸",
                "大胸妹最好操，奶子能玩很久",
                "巨乳晃动画面太刺激",
                "胸器太犯规，想狠狠抓",
                "爆乳太诱惑，看着就硬",
                "巨大奶子，想埋脸窒息",
                "丰满巨乳，想夹着鸡巴射",
                "大波浪太性感，想好好品尝",
                "巨乳女优最香，奶子又大又软"
            ]
            reply_sentences.append(random.choice(breast_phrases))
        
        # 美腿特征（100个回复）
        if has_美腿:
            leg_phrases = [
                "那双美腿修长诱人，真想架在肩上好好操",
                "美腿太性感了，想边抚摸边深入",
                "看着那双腿就硬了，想舔遍每一寸",
                "纤细的美腿缠上来肯定很爽",
                "大长腿太诱人，想分开狠狠插",
                "美腿玩年，想从脚趾舔到大腿根",
                "这腿又长又直，想架在肩上狂操",
                "美腿太骚了，想边舔边插",
                "修长美腿，想让她用腿夹着我",
                "腿这么美，想把玩一整晚",
                "纤细美腿太性感，想咬一口",
                "长腿妹子就是诱人，想把她腿掰开",
                "美腿夹腰的感觉肯定很爽",
                "这双腿太完美了，想好好品尝",
                "美腿翘臀，想从后面抱着操",
                "长腿太骚，想让她用腿勾着我",
                "腿型太美了，想抚摸每一寸肌肤",
                "美腿丝袜，想撕开狠狠干",
                "修长双腿，想分开到极限",
                "美腿控福利，看着就想射在腿上",
                "大长腿太勾人，想扛在肩上操",
                "美腿白皙光滑，想好好舔",
                "修长双腿分开的样子太淫荡",
                "腿这么长，缠腰上肯定爽",
                "美腿太诱人，想从上舔到下",
                "纤细长腿，想掰开狠狠插",
                "大长腿妹子最骚，想操",
                "美腿控的天堂，看着就硬",
                "修长美腿太性感，想把玩",
                "腿型完美，想架着狂插",
                "美腿丝袜诱惑太大",
                "长腿美女最诱人，想操翻",
                "纤细双腿，想让她夹紧我",
                "美腿太养眼，想边摸边插",
                "大长腿分开的瞬间最刺激",
                "修长美腿缠上来肯定很爽",
                "腿这么美，想舔个够",
                "美腿白嫩，想咬上一口",
                "长腿妹子操起来最舒服",
                "纤细美腿太勾魂，想玩",
                "美腿夹腰的画面太刺激",
                "大长腿太诱惑，想掰开",
                "修长双腿太完美，想品尝",
                "腿型这么好，想狠狠把玩",
                "美腿丝袜，撕开就干",
                "长腿美女最骚浪",
                "纤细美腿，想从脚舔起",
                "美腿控看了都硬",
                "大长腿架肩上操最爽",
                "修长美腿太性感了",
                "腿这么直，想掰开到极限",
                "美腿诱惑让人把持不住",
                "长腿妹子想狠狠操",
                "纤细双腿缠着最舒服",
                "美腿太勾人，想边舔边干",
                "大长腿分开插进去最爽",
                "修长美腿，想好好享受",
                "腿型太犯规，看着就想摸",
                "美腿白嫩光滑，想舔遍",
                "长腿美女操着最带劲",
                "纤细美腿太诱人了",
                "美腿夹腰爽到飞起",
                "大长腿太骚，想狂操",
                "修长双腿，想让她用腿勾我",
                "腿这么美，想玩一整晚",
                "美腿丝袜太刺激",
                "长腿控的最爱，想操",
                "纤细美腿分开的样子绝了",
                "美腿太性感，想边摸边插",
                "大长腿架着操太爽了",
                "修长美腿缠腰上肯定舒服",
                "腿型完美，想好好品尝",
                "美腿白皙，想从上舔到下",
                "长腿妹最好操",
                "纤细双腿太养眼",
                "美腿诱惑力爆表",
                "大长腿掰开最刺激",
                "修长美腿太勾魂",
                "腿这么直，想狠狠玩",
                "美腿丝袜想撕了干",
                "长腿美女最淫荡",
                "纤细美腿想边舔边操",
                "美腿夹紧的感觉太爽",
                "大长腿太完美了",
                "修长双腿想掰到极限",
                "腿型太诱人，想摸个够",
                "美腿白嫩想咬",
                "长腿控福利，看着就射",
                "纤细美腿太勾人",
                "美腿太骚浪",
                "大长腿分开插最爽",
                "修长美腿想好好把玩",
                "腿这么美想舔遍每寸",
                "美腿丝袜太刺激了",
                "长腿妹子想狂操不止",
                "纤细双腿缠着太舒服",
                "美腿诱惑太犯规",
                "大长腿架肩上最爽",
                "修长美腿太性感了"
            ]
            reply_sentences.append(random.choice(leg_phrases))
        
        # 嫩/粉嫩特征（100个回复）
        if has_嫩:
            tender_phrases = [
                "粉嫩的小穴一看就很敏感，轻轻一碰就出水",
                "嫩得让人想温柔疼爱，又想狠狠蹂躏",
                "粉嫩嫩的屄水肯定很多，想舔个够",
                "看着那粉嫩的小逼就想狠狠插入",
                "嫩屄太诱人，想慢慢品尝那青涩的味道",
                "粉嫩小穴，插进去肯定嫩滑湿润",
                "嫩得出水，想好好疼爱这小骚货",
                "粉粉嫩嫩的，看着就想舔",
                "嫩逼太骚了，想狠狠开苞",
                "粉嫩美穴，想温柔插入感受那紧致",
                "嫩到极致，想好好调教",
                "粉嫩小屄，想舔得她浪叫",
                "嫩屄水多，插进去肯定滑溜溜",
                "粉嫩蜜穴，想慢慢开发",
                "嫩得让人心痒，真想狠狠疼爱",
                "粉嫩逼穴，舔起来肯定很爽",
                "嫩屄嫩逼，想插得她求饶",
                "粉嫩小穴太诱惑，控制不住想插",
                "嫩滑湿润，想一插到底",
                "粉嫩美屄，想好好玩弄",
                "嫩穴太诱人，想狠狠品尝",
                "粉嫩嫩的看着就硬了",
                "嫩逼水多，想舔干净",
                "粉嫩小屄，想慢慢疼爱",
                "嫩得像少女，想好好开发",
                "粉嫩蜜洞，插进去肯定爽",
                "嫩屄太骚，想狠狠插",
                "粉嫩逼眼，舔着肯定很爽",
                "嫩滑的触感想象就硬了",
                "粉嫩小穴，想插到她叫",
                "嫩屄嫩得出水",
                "粉嫩美逼，想好好玩",
                "嫩到极致的小穴太诱人",
                "粉嫩蜜穴，想狠狠开拓",
                "嫩逼太嫩，想慢慢品味",
                "粉嫩小屄，看着就想舔",
                "嫩得让人心动，想插",
                "粉嫩逼洞，想用力插进去",
                "嫩屄水润，插着肯定舒服",
                "粉嫩美穴太完美",
                "嫩逼嫩屄，想狠狠疼爱",
                "粉嫩小穴太诱惑",
                "嫩得像处子，想开苞",
                "粉嫩蜜洞，想一插到底",
                "嫩屄太骚浪",
                "粉嫩逼穴，想慢慢享受",
                "嫩滑湿润的感觉绝了",
                "粉嫩小屄，想插得她哭",
                "嫩得出水的样子太骚",
                "粉嫩美逼，想好好调教",
                "嫩屄嫩穴，想狠狠插",
                "粉嫩蜜穴太诱人了",
                "嫩逼水多肉滑",
                "粉嫩小穴，想边舔边插",
                "嫩得让人疯狂",
                "粉嫩逼洞，插进去肯定爽翻",
                "嫩屄太嫩，想温柔对待",
                "粉嫩美穴，想狠狠品尝",
                "嫩逼嫩得流水",
                "粉嫩小屄太完美",
                "嫩穴嫩逼，想好好玩弄",
                "粉嫩蜜洞，看着就想插",
                "嫩得像花瓣，想轻轻抚摸",
                "粉嫩逼穴太骚了",
                "嫩屄水润润的",
                "粉嫩小穴，想插到最深",
                "嫩得让人把持不住",
                "粉嫩美逼，想慢慢开发",
                "嫩逼太诱人，想舔",
                "粉嫩蜜穴，想狠狠蹂躏",
                "嫩屄嫩到极致",
                "粉嫩小屄，插着肯定爽",
                "嫩穴太骚浪",
                "粉嫩逼洞，想好好疼爱",
                "嫩得出水的小穴绝了",
                "粉嫩美穴太刺激",
                "嫩逼嫩屄，想插烂",
                "粉嫩小穴太嫩了",
                "嫩得让人想狠狠插",
                "粉嫩蜜洞，舔着肯定爽",
                "嫩屄太完美",
                "粉嫩逼穴，想插得她浪叫",
                "嫩滑的触感太诱人",
                "粉嫩小屄，想好好品味",
                "嫩得像婴儿肌肤",
                "粉嫩美逼，想狠狠操",
                "嫩逼水多肉嫩",
                "粉嫩蜜穴，想插到她崩溃",
                "嫩屄嫩穴太骚",
                "粉嫩小穴，看着就流水",
                "嫩得让人欲罢不能",
                "粉嫩逼洞，想慢慢享受",
                "嫩屄太诱惑了",
                "粉嫩美穴，想边舔边玩",
                "嫩逼嫩得不行",
                "粉嫩小屄，想插个够本",
                "嫩穴太嫩太爽",
                "粉嫩蜜洞，想好好疼爱"
            ]
            reply_sentences.append(random.choice(tender_phrases))
        
        # 湿润/潮吹特征（100个回复）
        if has_湿润:
            wet_phrases = [
                "淫水泛滥的样子太骚了，想舔干净",
                "潮吹喷得到处都是的景象光想就硬了",
                "那湿润的蜜穴肯定水声很大",
                "屄水流得满床都是，太淫荡了",
                "湿淋淋的小穴太诱人",
                "潮吹的瞬间最刺激",
                "淫水直流，想舔个够",
                "湿透的样子太骚浪",
                "潮喷画面太刺激",
                "屄水多得流出来",
                "湿润蜜穴，插着肯定爽",
                "潮吹喷射太淫荡",
                "淫水横流的样子绝了",
                "湿得不行，想狠狠插",
                "潮吹高潮太刺激",
                "屄水泛滥，舔着最爽",
                "湿润小穴太诱惑",
                "潮喷瞬间想看",
                "淫水多得吓人",
                "湿透的逼穴太骚",
                "潮吹画面太淫荡",
                "屄水流不停",
                "湿润蜜洞，插进去爽翻",
                "潮喷得到处都是",
                "淫水直流太骚",
                "湿得一塌糊涂",
                "潮吹高潮最刺激",
                "屄水多到爆",
                "湿润小穴想舔",
                "潮喷场景太淫乱",
                "淫水泛滥成灾",
                "湿透的样子太诱人",
                "潮吹瞬间最爽",
                "屄水横流太骚浪",
                "湿润蜜穴太完美",
                "潮喷画面绝了",
                "淫水多得流出来",
                "湿得要命",
                "潮吹高潮太淫荡",
                "屄水流满床",
                "湿润逼穴想插",
                "潮喷瞬间太刺激",
                "淫水泛滥太骚",
                "湿透小穴太爽",
                "潮吹画面太销魂",
                "屄水多到夸张",
                "湿润蜜洞想舔",
                "潮喷高潮绝了",
                "淫水横流太淫乱",
                "湿得不像话",
                "潮吹瞬间最淫荡",
                "屄水流不停太骚",
                "湿润小穴想插个够",
                "潮喷画面太诱人",
                "淫水多得吓死人",
                "湿透逼穴太刺激",
                "潮吹高潮最淫乱",
                "屄水泛滥想舔",
                "湿润蜜穴太诱惑",
                "潮喷瞬间太销魂",
                "淫水直流太淫荡",
                "湿得一发不可收拾",
                "潮吹画面最刺激",
                "屄水横流想舔干净",
                "湿润小穴太骚浪",
                "潮喷高潮太刺激",
                "淫水泛滥成河",
                "湿透蜜洞想插",
                "潮吹瞬间绝了",
                "屄水多得离谱",
                "湿润逼穴太完美",
                "潮喷画面最淫荡",
                "淫水横流太刺激",
                "湿得要死",
                "潮吹高潮最销魂",
                "屄水流满地",
                "湿润小穴想好好品尝",
                "潮喷瞬间最淫乱",
                "淫水泛滥太淫荡",
                "湿透逼穴想插烂",
                "潮吹画面绝配",
                "屄水多到溢出",
                "湿润蜜穴想狠狠插",
                "潮喷高潮太淫乱",
                "淫水直流太刺激",
                "湿得不得了",
                "潮吹瞬间太诱人",
                "屄水横流太完美",
                "湿润小穴最骚",
                "潮喷画面最销魂",
                "淫水泛滥想舔干净",
                "湿透蜜洞太刺激",
                "潮吹高潮绝了",
                "屄水流个不停",
                "湿润逼穴太淫荡",
                "潮喷瞬间最刺激"
            ]
            reply_sentences.append(random.choice(wet_phrases))
        
        # 明星/女优名字特征
        if star_name:
            # 区分是中国明星还是日本女优
            is_chinese = star_name in chinese_stars
            
            if is_chinese:
                # 中国明星专用回复
                star_phrases = [
                    f"{star_name}的脸太美了，看着被操的样子简直绝了",
                    f"终于能看到{star_name}被狂操的样子，AI技术万岁",
                    f"{star_name}这种女神级的，想象着操她就硬了",
                    f"看{star_name}被插的样子太爽了，虽然是换脸也很带劲"
                ]
            else:
                # 日本女优专用回复
                star_phrases = [
                    f"{star_name}的身体太诱人了，想好好品尝",
                    f"就喜欢{star_name}这种骚浪的，叫床声肯定很撩人",
                    f"{star_name}真是极品，想和她来一发",
                    f"看{star_name}的表演就能射，太他妈骚了"
                ]
            reply_sentences.append(random.choice(star_phrases))
        
        # 无码特征（100个回复）
        if has_无码:
            uncensored_phrases = [
                "无码看得一清二楚，连屄毛都看得见",
                "无码真爽，能清楚看到鸡巴插入的每个细节",
                "就爱看无码的，有码根本不够劲",
                "无码高清，屄的每个褶皱都看得清清楚楚",
                "无码才是王道，看着鸡巴进出太爽了",
                "无码看着真实，插入的感觉看得一清二楚",
                "就喜欢无码的，能看清逼穴被撑开的样子",
                "无码画质，连阴蒂都看得清清楚楚",
                "无马赛克真爽，小穴被插得变形都看得见",
                "无码就是好，屄水流出来都看得清",
                "无码片才够劲，能看到每一下抽插",
                "无码高清，鸡巴进出小穴的画面太刺激",
                "无遮挡看着爽，阴唇被顶开的瞬间绝了",
                "无码才真实，能看清屄被操烂的过程",
                "就爱无码，看着鸡巴插进粉穴的样子硬了",
                "无码清晰，连淫水都看得一清二楚",
                "无码版本太赞，能看清逼穴的每个细节",
                "无遮挡真爽，看着小穴被撑满太刺激",
                "无码画面，插入抽出都看得清清楚楚",
                "就要看无码的，有码太不过瘾了",
                "无码片看得最爽，细节都能看清",
                "无马赛克最刺激，插入瞬间太真实",
                "无码高清画质绝了",
                "无遮挡才过瘾，屄看得清清楚楚",
                "无码版本最带劲",
                "就爱无码片，有码不看",
                "无码看着最真实",
                "无马赛克太爽了，每个细节都清晰",
                "无码高清才是王道",
                "无遮挡画面太刺激",
                "无码片最过瘾，看得清清楚楚",
                "就要看无码，有码太假",
                "无码版本太完美",
                "无马赛克看着爽",
                "无码高清画面绝配",
                "无遮挡才够劲",
                "无码片看着最真",
                "就喜欢无码版",
                "无码画质太清晰",
                "无马赛克最真实",
                "无码高清最刺激",
                "无遮挡画面绝了",
                "无码片才过瘾",
                "就要无码的，有码不看",
                "无码版本最爽",
                "无马赛克太清楚",
                "无码高清太带劲",
                "无遮挡最刺激",
                "无码片最真实",
                "就爱看无码版本",
                "无码画质完美",
                "无马赛克看得爽",
                "无码高清绝了",
                "无遮挡才真实",
                "无码片最刺激",
                "就要无码高清",
                "无码版本太清晰",
                "无马赛克最爽",
                "无码高清过瘾",
                "无遮挡太真实",
                "无码片太完美",
                "就喜欢无码高清",
                "无码画质绝配",
                "无马赛克太刺激",
                "无码高清最真",
                "无遮挡太爽了",
                "无码片看着舒服",
                "就要看无码高清",
                "无码版本太真实",
                "无马赛克太完美",
                "无码高清太清晰",
                "无遮挡最过瘾",
                "无码片太刺激",
                "就爱无码高清版",
                "无码画质太真实",
                "无马赛克绝了",
                "无码高清最完美",
                "无遮挡太清楚",
                "无码片最带劲",
                "就要无码版本",
                "无码画质最爽",
                "无马赛克太真",
                "无码高清太刺激",
                "无遮挡最真实",
                "无码片太爽了",
                "就喜欢看无码",
                "无码版本最刺激",
                "无马赛克最清晰",
                "无码高清太过瘾",
                "无遮挡太完美",
                "无码片最清晰",
                "就要无码的看",
                "无码画质最刺激",
                "无马赛克太过瘾",
                "无码高清太真实",
                "无遮挡最爽",
                "无码片太清晰",
                "就爱看无码的"
            ]
            reply_sentences.append(random.choice(uncensored_phrases))
        
        # 中出特征（100个回复）
        if has_中出:
            creampie_phrases = [
                "中出内射最刺激，看着精液流出来太爽了",
                "就爱看中出，射在里面的感觉一定爽翻",
                "内射画面太带感了，想象自己也射进去",
                "中出最爽，看着精液从逼里流出来硬了",
                "内射瞬间太刺激，想狠狠射满她",
                "就喜欢中出结局，看着精液溢出太爽",
                "射在里面的画面绝了，想感受那温热",
                "中出才够劲，看着被灌满的样子硬了",
                "内射深处，想把精液全射进去",
                "中出画面太刺激，看着就想射",
                "射进去的瞬间肯定爽翻，真想体验",
                "中出特写太诱人，精液流出来的样子绝了",
                "就爱看内射，被射满的屄太骚了",
                "中出完的小穴流着精液，太淫荡了",
                "内射最带感，想狠狠射进最深处",
                "中出镜头绝了，看着就忍不住想射",
                "射满小穴的画面太爽，想亲身体验",
                "中出高潮，看着精液喷涌而出硬了",
                "内射特写，逼穴里满是精液太刺激",
                "中出结束，看着精液慢慢流出来绝了",
                "内射画面最刺激，精液溢出太爽",
                "中出才过瘾，射在里面最舒服",
                "就爱中出结局，看着流出来硬了",
                "内射瞬间绝了，想射满她",
                "中出画面太淫荡",
                "就要看中出的，外射不过瘾",
                "内射深处最爽",
                "中出特写太诱人",
                "就喜欢看内射画面",
                "中出高潮太刺激",
                "内射完流出来的样子绝了",
                "中出才够劲，外射太浪费",
                "就爱看中出特写",
                "内射画面最淫荡",
                "中出瞬间太爽了",
                "就要中出结局",
                "内射深处太刺激",
                "中出完的样子太骚",
                "就喜欢内射画面",
                "中出特写绝配",
                "内射瞬间最爽",
                "中出画面最带劲",
                "就爱看中出高潮",
                "内射深处绝了",
                "中出才最爽",
                "就要看内射的",
                "中出瞬间太淫荡",
                "内射画面太完美",
                "中出结局最刺激",
                "就喜欢中出特写",
                "内射深处最淫乱",
                "中出高潮绝了",
                "就爱中出画面",
                "内射瞬间太诱人",
                "中出完太骚了",
                "就要中出的看",
                "内射画面最刺激",
                "中出特写太爽",
                "就喜欢看中出的",
                "内射深处太淫荡",
                "中出瞬间最淫乱",
                "就爱内射结局",
                "中出画面太诱人",
                "内射高潮绝了",
                "中出才最刺激",
                "就要内射画面",
                "中出瞬间太完美",
                "内射深处最爽",
                "中出结局绝配",
                "就喜欢中出高潮",
                "内射画面太淫乱",
                "中出特写最爽",
                "就爱看内射的",
                "中出瞬间太刺激",
                "内射深处绝配",
                "中出画面最淫荡",
                "就要中出特写",
                "内射瞬间最淫荡",
                "中出高潮太爽",
                "就喜欢内射深处",
                "中出完最淫乱",
                "内射画面绝了",
                "中出才最淫荡",
                "就爱中出瞬间",
                "内射深处太爽",
                "中出特写最刺激",
                "就要看中出画面",
                "内射瞬间太淫乱",
                "中出结局太爽",
                "就喜欢中出完的样子",
                "内射画面最爽",
                "中出瞬间绝配",
                "就爱内射特写",
                "中出深处太刺激",
                "内射高潮最爽",
                "中出画面绝了",
                "就要内射瞬间",
                "中出完太淫荡",
                "内射深处最淫荡",
                "中出特写太淫乱"
            ]
            reply_sentences.append(random.choice(creampie_phrases))
        
        # 多P特征（100个回复）
        if has_多P:
            group_phrases = [
                "多P场面太刺激了，几根鸡巴同时插肯定爽爆",
                "群交看着就硬，这种淫乱场面我最爱",
                "被轮流操的样子太淫荡了，骚货",
                "3P画面太刺激，前后一起插肯定爽翻",
                "群P太淫乱，看着几个男人轮流上硬了",
                "多人运动最带劲，看着就想加入",
                "轮奸场景太刺激，一个接一个操真骚",
                "群交淫乱，看着被多根鸡巴填满太爽",
                "多P最爽，各种姿势各种插",
                "被几个男人同时玩弄，骚屄一个",
                "群交画面绝了，看着就想射",
                "多人齐上，看着被操到崩溃太刺激",
                "轮流内射，看着被灌满精液太淫荡",
                "群P场面太劲爆，几个洞都被填满",
                "多人运动太骚，看着就硬邦邦",
                "被群操的样子绝了，淫娃一个",
                "多P淫乱派对，看着就想参与",
                "轮番上阵，看着被操到求饶太爽",
                "群交高潮，被操得浪叫连连",
                "多根鸡巴同时伺候，骚屄享福了",
                "多P画面最淫荡，看着就硬",
                "群交场面太刺激",
                "被轮流插的样子太骚",
                "3P最爽，前后齐插",
                "群P淫乱，几个男人轮着来",
                "多人运动太刺激了",
                "轮奸画面绝了",
                "群交淫乱派对最爽",
                "多P场面太带劲",
                "被几根鸡巴同时插太淫荡",
                "群交高潮最刺激",
                "多人齐上太骚",
                "轮流内射画面绝配",
                "群P最淫乱",
                "多人运动场面太爽",
                "被群操太刺激",
                "多P淫乱最带劲",
                "轮番上阵太骚浪",
                "群交画面最淫荡",
                "多根鸡巴伺候太爽",
                "多P场面最刺激",
                "群交淫乱太骚",
                "被轮流操绝了",
                "3P画面最淫荡",
                "群P太刺激",
                "多人运动最淫乱",
                "轮奸场景最骚",
                "群交高潮绝配",
                "多P最淫荡",
                "被几个男人同时玩太爽",
                "群交画面太刺激",
                "多人齐上最淫乱",
                "轮流内射最骚",
                "群P场面绝了",
                "多人运动太淫荡",
                "被群操最刺激",
                "多P淫乱派对绝配",
                "轮番上阵最淫乱",
                "群交最骚浪",
                "多根鸡巴最爽",
                "多P画面太淫荡",
                "群交淫乱最刺激",
                "被轮流插最骚",
                "3P场面绝了",
                "群P最骚浪",
                "多人运动绝配",
                "轮奸画面最淫荡",
                "群交高潮最淫乱",
                "多P太骚",
                "被几个男人操最爽",
                "群交画面最刺激",
                "多人齐上绝了",
                "轮流内射最淫荡",
                "群P场面最淫乱",
                "多人运动最骚",
                "被群操绝配",
                "多P淫乱最骚浪",
                "轮番上阵最刺激",
                "群交太淫荡",
                "多根鸡巴最淫乱",
                "多P场面太骚",
                "群交淫乱绝了",
                "被轮流操最淫荡",
                "3P画面最刺激",
                "群P淫乱最骚",
                "多人运动最刺激",
                "轮奸场景绝配",
                "群交高潮太骚",
                "多P最刺激",
                "被几个男人玩最淫荡",
                "群交画面绝了",
                "多人齐上最骚",
                "轮流内射绝配",
                "群P场面太骚浪",
                "多人运动太刺激",
                "被群操最淫荡",
                "多P淫乱绝了",
                "轮番上阵太淫荡"
            ]
            reply_sentences.append(random.choice(group_phrases))
        
        # AI换脸/明星特征（100个回复）
        if has_AI换脸 or has_明星:
            ai_phrases = [
                "AI换脸技术太牛了，看着和真的一样，撸得更带劲",
                "换脸换得真像，想象着操女神的感觉太爽了",
                "AI技术真是造福宅男，终于能看到女神被操了",
                "换脸效果太逼真了，看着明星被狂操心里爽翻",
                "科技改变生活，AI让我们能看到平时看不到的画面",
                "AI技术万岁，女神终于肯下海了",
                "换脸太真实，看着女神被插就硬了",
                "AI增强版画质更清晰，看得更爽",
                "deepfake技术绝了，满足了所有幻想",
                "看着女神被操的样子，AI技术真牛逼",
                "换脸效果堪比真人，撸得太带劲了",
                "AI让梦想成真，终于看到了",
                "换脸技术越来越好，逼真度爆表",
                "AI换脸满足了无数人的yy",
                "看着平时高高在上的女神被操，爽翻",
                "换脸片越来越真实，科技改变生活",
                "AI技术造福人类，能看到女神的各种姿势",
                "deepfake让幻想变现实，太爽了",
                "换得跟真的一样，看着女神淫荡的样子硬了",
                "AI换脸圆梦，终于能撸女神了",
                "AI换脸太逼真，看着就硬",
                "换脸技术绝了，女神被操的样子太刺激",
                "AI技术真牛，终于能看到明星下海",
                "换脸效果完美，撸得爽翻",
                "科技万岁，AI让幻想成真",
                "AI换脸技术，造福宅男",
                "换脸太真实了，看着女神被插太爽",
                "AI增强画质绝了",
                "deepfake太牛逼，满足所有幻想",
                "看着明星被操，AI技术真伟大",
                "换脸效果太好，撸得特爽",
                "AI让梦想实现，看到女神被干了",
                "换脸技术进步神速",
                "AI换脸满足yy",
                "看着女神被狂操，爽死了",
                "换脸片越来越真",
                "AI技术造福人类",
                "deepfake让幻想成真",
                "换得太像，女神淫荡样子硬了",
                "AI换脸圆了撸女神的梦",
                "AI技术太强，换脸逼真",
                "换脸效果绝配，看着爽",
                "AI让女神下海成真",
                "换脸太完美，撸得爽",
                "科技改变撸管体验",
                "AI换脸太给力",
                "换脸真实度爆表",
                "AI技术让女神被操",
                "换脸画面太刺激",
                "deepfake技术太强",
                "看着明星淫荡样子，AI真牛",
                "换脸效果满分",
                "AI实现了所有幻想",
                "换脸技术太逼真",
                "AI让女神各种姿势都能看",
                "换脸片撸得爽",
                "看着女神被插，科技万岁",
                "AI换脸技术绝了",
                "换脸太真，硬了",
                "AI技术圆梦",
                "换脸效果太刺激",
                "科技让女神下海",
                "AI换脸太完美",
                "换脸逼真度满分",
                "AI让明星被操",
                "换脸画面绝配",
                "deepfake太真实",
                "看着女神淫荡，AI牛逼",
                "换脸效果爆表",
                "AI满足所有yy",
                "换脸技术完美",
                "AI让女神被干",
                "换脸片太爽",
                "看着明星被插，科技伟大",
                "AI换脸太真",
                "换脸太逼真，撸得爽",
                "AI技术让梦成真",
                "换脸效果太好",
                "科技让明星下海",
                "AI换脸绝配",
                "换脸真实爆表",
                "AI让女神被操成真",
                "换脸画面太爽",
                "deepfake技术完美",
                "看着女神被狂干，AI真强",
                "换脸效果太真",
                "AI圆了所有幻想",
                "换脸技术太强",
                "AI让明星各种姿势",
                "换脸片太刺激",
                "看着女神淫荡样，科技牛",
                "AI换脸太刺激",
                "换脸逼真撸得爽",
                "AI技术太牛了",
                "换脸效果完美爆表",
                "科技让女神被操",
                "AI换脸技术强",
                "换脸太真实爽翻",
                "AI让女神下海了"
            ]
            reply_sentences.append(random.choice(ai_phrases))
        
        # 如果没有明显特征，添加通用描述（200个回复）
        if not reply_sentences:
            general_sexy_phrases = [
                "看着那骚浪的样子就想狠狠插进去，操到她求饶",
                "淫荡的表情太勾人了，真想好好调教一番",
                "骚屄一个，看着那浪样就知道很会叫床",
                "这种骚货最好操了，肯定水很多",
                "看得鸡巴硬邦邦的，恨不得马上操进去",
                "骚浪贱，看着就想狠狠蹂躏",
                "淫荡小骚货，想操得她欲仙欲死",
                "这身材太顶了，想从头玩到尾",
                "骚到骨子里了，想好好品尝",
                "淫娃一个，看着就想狂操不止",
                "骚屄水肯定很多，想舔干净",
                "浪叫声肯定很撩人，想听她求饶",
                "这骚样太诱人，想插到她腿软",
                "淫荡表情绝了，想操到她崩溃",
                "骚货身材真好，想好好玩弄",
                "浪屄一个，想插得她直叫",
                "骚得流水，想狠狠贯穿",
                "淫乱小妖精，想调教到服服帖帖",
                "这么骚的货，不操太可惜了",
                "浪到不行，想操得她求饶",
                "骚屄水真多，插进去肯定滑溜溜",
                "淫荡骚货，想各种姿势都试一遍",
                "骚浪贱货，想狠狠惩罚",
                "淫娃太骚，想操到她精疲力尽",
                "这么浪的屄，想插个够本",
                "骚穴太诱人，看着就硬了",
                "淫荡样子太刺激，想狠狠干",
                "骚货太骚浪，想操翻她",
                "这身材绝了，想好好玩",
                "骚屄太淫荡，想插到底",
                "浪叫起来肯定很爽",
                "这骚样太勾魂，想蹂躏",
                "淫荡表情太诱惑",
                "骚货水多肉滑",
                "浪屄想狠狠插",
                "骚得不行，想操烂",
                "淫乱小妖精想调教",
                "这骚货不操可惜",
                "浪样太诱人",
                "骚屄想舔干净",
                "淫荡骚货想操",
                "骚浪贱想惩罚",
                "淫娃想操到爽",
                "浪屄想插个够",
                "骚穴诱人想插",
                "淫荡刺激想干",
                "骚货骚浪想操",
                "身材好想玩",
                "骚屄淫荡想插",
                "浪叫很爽想听",
                "骚样勾魂想蹂躏",
                "淫荡诱惑想操",
                "骚货肉滑想插",
                "浪屄想插烂",
                "骚得想操翻",
                "淫乱想调教",
                "骚货想狠狠操",
                "浪样诱人想插",
                "骚屄想舔",
                "淫荡想狠干",
                "骚浪想惩罚",
                "淫娃想操爽",
                "浪屄想插够",
                "看着就想操，骚样太刺激",
                "淫荡得不行，想插烂她",
                "骚货身材顶，想玩翻",
                "这屄太诱人，想狠狠插",
                "骚浪样子绝了",
                "淫荡表情太骚",
                "骚货太勾人",
                "浪屄水多想舔",
                "骚穴太刺激",
                "淫荡想蹂躏",
                "骚货想调教",
                "浪样想操翻",
                "骚屄太骚想插",
                "淫荡太诱惑",
                "骚货太淫乱",
                "浪屄想狠插",
                "骚样太销魂",
                "淫荡太勾魂",
                "骚货想操烂",
                "浪屄太骚浪",
                "骚穴想插到底",
                "淫荡想狠狠操",
                "骚货太完美",
                "浪样太淫荡",
                "骚屄想玩弄",
                "淫荡太刺激",
                "骚货想插翻",
                "浪屄太诱人",
                "骚样想蹂躏",
                "淫荡想调教",
                "骚货想操爽",
                "浪屄想插够",
                "骚穴太淫乱",
                "看着硬了，想操",
                "淫荡样太骚",
                "骚货想狠干",
                "浪屄想插烂",
                "骚样太诱惑",
                "淫荡想惩罚",
                "骚货想操到爽",
                "浪屄想插个够",
                "骚穴想舔",
                "淫荡太骚浪",
                "骚货想玩翻",
                "浪样想插到底",
                "骚屄想狠狠操",
                "淫荡太销魂",
                "骚货想蹂躏",
                "浪屄想调教",
                "骚样想操翻",
                "淫荡想插烂",
                "骚货太诱人想操",
                "浪屄太骚想插",
                "骚穴太刺激想舔",
                "淫荡太勾人想干",
                "骚货太淫乱想操",
                "浪样太完美想插",
                "骚屄太骚浪想狠插",
                "淫荡太诱惑想蹂躏",
                "骚货想狠狠调教",
                "浪屄想操到崩溃",
                "骚样想插个够本",
                "淫荡想玩弄一番",
                "骚货想各种姿势操",
                "浪屄想插到腿软",
                "骚穴想舔干净",
                "淫荡想操得求饶",
                "骚货想从头玩到尾",
                "浪样想狠狠贯穿",
                "骚屄想插到精尽人亡",
                "淫荡想操到精疲力尽",
                "骚货太骚了想操",
                "浪屄太淫荡想插",
                "骚样太销魂想干",
                "淫荡太刺激想狠操",
                "骚货太诱惑想玩",
                "浪屄太完美想插烂",
                "骚穴太勾人想舔",
                "淫荡太骚浪想蹂躏",
                "骚货太淫乱想调教",
                "浪样绝了想操翻",
                "骚屄水多想插",
                "淫荡诱人想狠干",
                "骚货刺激想操烂",
                "浪屄骚浪想插够",
                "骚样勾魂想狠插",
                "淫荡销魂想玩弄",
                "骚货完美想操爽",
                "浪屄淫乱想插到底",
                "骚穴诱惑想舔遍",
                "淫荡骚样想蹂躏",
                "骚货浪屄想调教",
                "浪样刺激想操翻",
                "骚屄淫荡想狠插",
                "淫荡勾人想狠干",
                "骚货骚浪想操烂",
                "浪屄销魂想插够",
                "骚样完美想狠插",
                "淫荡淫乱想玩翻",
                "骚货诱惑想操到爽",
                "浪屄勾魂想插个够",
                "骚穴刺激想舔干净",
                "淫荡完美想蹂躏",
                "骚货淫乱想调教好",
                "浪样诱人想操翻天",
                "骚屄骚浪想狠狠插",
                "淫荡销魂想狠狠干",
                "骚货勾魂想操到底",
                "浪屄刺激想插烂她",
                "骚样淫乱想狠插她",
                "淫荡诱惑想玩弄她",
                "骚货完美想操爽她",
                "浪屄淫荡想插够她",
                "骚穴勾人想舔遍她",
                "淫荡刺激想蹂躏她",
                "骚货骚浪想调教她",
                "浪样销魂想操翻她",
                "骚屄完美想狠插她"
            ]
            reply_sentences.append(random.choice(general_sexy_phrases))
        
        # 随机选择1-2个句子组合
        if len(reply_sentences) > 1:
            num_sentences = random.randint(1, min(2, len(reply_sentences)))
            selected = random.sample(reply_sentences, k=num_sentences)
            reply = "，".join(selected) + "！"
        else:
            reply = reply_sentences[0] + "！"
        
        logging.info(f"💡 智能回复 - 特征: 紧={has_紧}, 巨乳={has_巨乳}, 美腿={has_美腿}, 嫩={has_嫩}, 无码={has_无码}")
        
        return reply
    
    def _run_test_mode(self):
        """测试模式：打开帖子读取内容并显示智能回复，但不实际回复"""
        try:
            for forum_id in self.target_forums:
                logging.info(f"📋 [测试模式] 获取论坛帖子: {forum_id}")
                posts = self.get_forum_posts(forum_id)
                
                logging.info(f"🧪 [测试模式] 开始分析帖子...")
                will_process = []
                
                for post in posts:
                    if self.should_skip_post(post['title'], post['url']):
                        continue  # 已经在 should_skip_post 中显示了跳过信息
                    will_process.append(post)
                    if len(will_process) >= self.daily_reply_limit:
                        break
                
                if will_process:
                    logging.info(f"🧪 [测试模式] ✅ 找到 {len(will_process)} 个符合条件的帖子")
                    logging.info(f"🧪 [测试模式] 正在打开帖子读取内容生成智能回复...")
                    logging.info(f"")
                    
                    for i, post in enumerate(will_process, 1):
                        # 打开帖子读取内容
                        logging.info(f"🧪 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        logging.info(f"🧪 [{i}] 正在打开帖子...")
                        
                        try:
                            self.driver.get(post['url'])
                            time.sleep(2)
                            
                            # 1. 读取帖子内容
                            post_content = ""
                            try:
                                content_selectors = [".t_f", ".pcb", "#postmessage_", ".message"]
                                for selector in content_selectors:
                                    try:
                                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                        if elements:
                                            post_content = elements[0].text[:500]
                                            logging.info(f"✅ [测试] 成功读取帖子内容")
                                            break
                                    except:
                                        continue
                                if not post_content:
                                    logging.warning(f"⚠️ [测试] 未能读取帖子内容")
                            except Exception as e:
                                logging.warning(f"⚠️ [测试] 读取内容失败: {e}")
                            
                            # 2. 生成智能回复（基于标题+内容）
                            reply_content = self.get_smart_reply(post['title'], post_content)
                            
                            # 3. 查找回复框
                            reply_box = None
                            reply_selectors = [
                                "textarea[name='message']",
                                "#fastpostmessage",
                                "textarea#e_textarea",
                                "textarea.pt",
                                ".reply_textarea",
                                "textarea"
                            ]
                            
                            for selector in reply_selectors:
                                try:
                                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                                    for elem in elements:
                                        if elem.is_displayed() and elem.is_enabled():
                                            reply_box = elem
                                            logging.info(f"✅ [测试] 找到回复框: {selector}")
                                            break
                                    if reply_box:
                                        break
                                except:
                                    continue
                            
                            if not reply_box:
                                logging.error(f"❌ [测试] 未找到回复框")
                            else:
                                # 4. 输入回复内容（测试用）
                                try:
                                    reply_box.clear()
                                    reply_box.send_keys(reply_content)
                                    logging.info(f"✅ [测试] 已输入回复内容到文本框")
                                except Exception as e:
                                    logging.error(f"❌ [测试] 输入回复失败: {e}")
                                
                                # 5. 查找提交按钮（但不点击）
                                submit_button = None
                                submit_selectors = [
                                    "input[type='submit'][value*='回复']",
                                    "input[type='submit'][value*='发表']",
                                    "button[type='submit']",
                                    ".btn_submit"
                                ]
                                
                                for selector in submit_selectors:
                                    try:
                                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                        if submit_button.is_displayed():
                                            logging.info(f"✅ [测试] 找到提交按钮: {selector}")
                                            logging.info(f"🚫 [测试] 测试模式 - 不点击提交按钮")
                                            break
                                    except:
                                        continue
                                
                                if not submit_button:
                                    logging.error(f"❌ [测试] 未找到提交按钮")
                            
                            # 显示测试结果
                            logging.info(f"")
                            logging.info(f"🧪 标题: {post['title']}")
                            logging.info(f"🧪 链接: {post['url']}")
                            if post_content:
                                preview = post_content[:80].replace('\n', ' ')
                                logging.info(f"📄 内容: {preview}...")
                            else:
                                logging.info(f"📄 内容: (无法读取)")
                            logging.info(f"💬 回复: {reply_content}")
                            logging.info(f"")
                            
                        except Exception as e:
                            logging.warning(f"⚠️ 打开帖子失败: {e}")
                            # 失败时使用仅基于标题的回复
                            reply_content = self.get_smart_reply(post['title'], "")
                            logging.info(f"🧪 标题: {post['title']}")
                            logging.info(f"🧪 链接: {post['url']}")
                            logging.info(f"💬 回复(仅标题): {reply_content}")
                else:
                    logging.info(f"🧪 [测试模式] ⚠️ 没有找到符合条件的帖子")
                
            logging.info(f"")
            logging.info(f"🧪 [测试模式] =====================================")
            logging.info(f"🧪 [测试模式] 测试完成，未执行任何实际回复操作")
            logging.info(f"🧪 [测试模式] 如需调整过滤规则，请修改 skip_keywords")
            
        except Exception as e:
            logging.error(f"❌ 测试模式执行失败: {e}")
    
    def run_auto_tasks(self):
        """运行自动化任务"""
        try:
            logging.info("🚀 开始自动化任务...")
            
            # 测试模式：分别测试签到和回复
            if self.enable_test_mode or self.enable_test_checkin or self.enable_test_reply:
                test_items = []
                if self.enable_test_checkin:
                    test_items.append("签到")
                if self.enable_test_reply:
                    test_items.append("回复")
                if self.enable_test_mode and not (self.enable_test_checkin or self.enable_test_reply):
                    test_items = ["签到", "回复"]  # 全部测试模式
                
                logging.info("🧪 ============ 测试模式已启用 ============")
                logging.info(f"🧪 测试项目: {', '.join(test_items)}")
                logging.info("🧪 会打开浏览器，但不实际提交")
                logging.info("🧪 用于验证所有功能是否正常")
                logging.info("🧪 无视签到/自动回复等所有开关设置")
                logging.info("🧪 =====================================")
                logging.info("💡 注意：按照论坛规则，先回复后签到")
                logging.info("")
                
                # 1. 先测试回复流程（如果启用）- 论坛要求先回复
                if self.enable_test_mode or self.enable_test_reply:
                    logging.info("🧪 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    logging.info("🧪 ========== 开始测试回复功能 ==========")
                    logging.info("🧪 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    self._run_test_mode()
                    logging.info("🧪 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    logging.info("🧪 ========== 回复测试完成 ==========")
                    logging.info("🧪 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    logging.info("")
                
                # 2. 回复测试完成后测试签到（如果启用）- 论坛规则
                if self.enable_test_mode or self.enable_test_checkin:
                    logging.info("📋 回复测试完成，现在测试签到功能...")
                    logging.info("🧪 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    logging.info("🧪 ========== 开始测试签到功能 ==========")
                    logging.info("🧪 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    self.daily_checkin(test_mode=True)
                    logging.info("🧪 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    logging.info("🧪 ========== 签到测试完成 ==========")
                    logging.info("🧪 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                return  # 测试模式完成后直接返回
            
            # 正常模式：按照配置执行
            # 注意：论坛要求先回复一条才能签到，所以先回复后签到
            
            # 1. 检查是否启用自动回复
            if not self.enable_auto_reply:
                logging.info("ℹ️ 自动回复功能已禁用")
                # 如果不回复，也不能签到（论坛规则）
                if self.enable_daily_checkin:
                    logging.warning("⚠️ 论坛要求回复后才能签到，跳过签到")
                return
            
            # 2. 先执行自动回帖（论坛要求）
            reply_count = 0
            for forum_id in self.target_forums:
                # 检查停止标志
                if self.stop_flag():
                    logging.info("🛑 检测到停止信号，停止自动回帖")
                    return
                
                if reply_count >= self.daily_reply_limit:
                    break
                
                posts = self.get_forum_posts(forum_id)
                
                for post in posts:
                    # 检查停止标志
                    if self.stop_flag():
                        logging.info("🛑 检测到停止信号，停止自动回帖")
                        return
                    
                    if reply_count >= self.daily_reply_limit:
                        break
                    
                    # 检查是否应该跳过该帖子（包括已回复检查）
                    if self.should_skip_post(post['title'], post['url']):
                        continue
                    
                    # 回复帖子（传递标题用于智能回复）
                    if self.reply_to_post(post['url'], post_title=post['title']):
                        reply_count += 1
                        logging.info(f"✅ 已回复 {reply_count}/{self.daily_reply_limit} 个帖子")
                        
                        # 等待间隔（期间也检查停止标志）
                        wait_time = random.randint(self.reply_interval_min, self.reply_interval_max)
                        logging.info(f"⏰ 等待 {wait_time} 秒...")
                        
                        # 分段等待，便于响应停止信号
                        for i in range(wait_time):
                            if self.stop_flag():
                                logging.info("🛑 检测到停止信号，中断等待")
                                return
                            time.sleep(1)
                    else:
                        logging.warning("⚠️ 回复失败，跳过此帖")
            
            logging.info(f"✅ 自动回帖完成！共回复 {reply_count} 个帖子")
            
            # 3. 回复完成后执行签到（论坛要求先回复才能签到）
            if self.enable_daily_checkin:
                if reply_count > 0:
                    logging.info("📋 已完成回复，现在开始签到...")
                    self.daily_checkin()
                else:
                    logging.warning("⚠️ 未成功回复任何帖子，跳过签到（论坛要求回复后才能签到）")
            else:
                logging.info("ℹ️ 签到功能已禁用")
            
            logging.info(f"🎉 所有自动化任务完成！")
            
        except Exception as e:
            logging.error(f"❌ 自动化任务失败: {e}")
    
    def run(self):
        """运行主程序"""
        try:
            # 设置浏览器
            if not self.setup_driver():
                return False
            
            # 尝试使用已保存的登录状态
            logged_in = False
            if os.path.exists(self.cookies_file):
                logging.info("=" * 60)
                logging.info("🔍 发现已保存的登录状态文件！")
                logging.info(f"📂 文件位置: {self.cookies_file}")
                logging.info("🔄 尝试恢复登录状态...")
                logging.info("=" * 60)
                
                if self.load_cookies():
                    logging.info("📝 Cookies已加载，正在验证登录状态...")
                    if self.check_login_status():
                        logging.info("=" * 60)
                        logging.info("🎉 登录状态验证成功！")
                        logging.info("✅ 无需重新登录，直接使用已保存的登录状态")
                        logging.info("=" * 60)
                        logged_in = True
                    else:
                        logging.info("=" * 60)
                        logging.warning("⚠️ 登录状态已过期或失效")
                        logging.info("🗑️ 正在删除过期的登录状态文件...")
                        # 删除过期的cookies文件
                        try:
                            os.remove(self.cookies_file)
                            logging.info("✅ 已删除过期文件，准备重新登录")
                        except Exception as e:
                            logging.warning(f"删除文件失败: {e}")
                        logging.info("=" * 60)
                else:
                    logging.warning("⚠️ 加载Cookies失败，将尝试重新登录")
            else:
                logging.info("ℹ️ 未找到已保存的登录状态，将执行首次登录")
            
            # 如果没有登录成功，执行正常登录流程
            if not logged_in:
                logging.info("=" * 60)
                logging.info("🔐 开始账号密码登录流程...")
                logging.info("=" * 60)
                if not self.login():
                    return False
            
            # 运行自动化任务
            self.run_auto_tasks()
            
            return True
            
        except Exception as e:
            logging.error(f"❌ 程序运行失败: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
                logging.info("🔚 浏览器已关闭")

def main():
    """主函数"""
    print("=" * 50)
    print("🌸 色花堂智能助手 Pro")
    print("=" * 50)
    print("🚀 机器人启动中...")
    print("=" * 50)
    
    bot = SeleniumAutoBot()
    success = bot.run()
    
    if success:
        print("=" * 50)
        print("🎉 所有任务完成！")
        print("=" * 50)
    else:
        print("=" * 50)
        print("❌ 任务失败，请查看 logs/selenium_bot.log")
        print("=" * 50)

if __name__ == "__main__":
    main()
