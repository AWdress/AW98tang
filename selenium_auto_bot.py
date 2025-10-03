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
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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
        
        # 配置信息
        self.base_url = self.config.get('base_url', 'https://sehuatang.org/')
        self.username = self.config.get('username', '')
        self.password = self.config.get('password', '')
        self.security_question_id = self.config.get('security_question_id', '')
        self.security_answer = self.config.get('security_answer', '')
        
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
            self.driver.set_page_load_timeout(30)
            logging.info("⏱️ 设置页面加载超时: 30秒")
            
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
            logging.info(f"📋 获取论坛帖子: {forum_id}")
            
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
    
    def should_skip_post(self, title):
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
        
        return False
    
    def get_smart_reply(self, title, content=""):
        """根据帖子标题和内容生成纯色情风格回复"""
        if not self.enable_smart_reply:
            return random.choice(self.reply_templates)
        
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
        
        # 紧致特征（50个回复）
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
                "狭小蜜穴，抽插起来肯定摩擦感十足"
            ]
            reply_sentences.append(random.choice(tight_phrases))
        
        # 巨乳特征（50个回复）
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
                "大胸美女最骚了，想抓着奶子后入"
            ]
            reply_sentences.append(random.choice(breast_phrases))
        
        # 美腿特征（50个回复）
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
                "美腿控福利，看着就想射在腿上"
            ]
            reply_sentences.append(random.choice(leg_phrases))
        
        # 嫩/粉嫩特征（50个回复）
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
                "粉嫩美屄，想好好玩弄"
            ]
            reply_sentences.append(random.choice(tender_phrases))
        
        # 湿润/潮吹特征
        if has_湿润:
            wet_phrases = [
                "淫水泛滥的样子太骚了，想舔干净",
                "潮吹喷得到处都是的景象光想就硬了",
                "那湿润的蜜穴肯定水声很大",
                "屄水流得满床都是，太淫荡了"
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
        
        # 无码特征（50个回复）
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
                "就要看无码的，有码太不过瘾了"
            ]
            reply_sentences.append(random.choice(uncensored_phrases))
        
        # 中出特征（50个回复）
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
                "中出结束，看着精液慢慢流出来绝了"
            ]
            reply_sentences.append(random.choice(creampie_phrases))
        
        # 多P特征（50个回复）
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
                "多根鸡巴同时伺候，骚屄享福了"
            ]
            reply_sentences.append(random.choice(group_phrases))
        
        # AI换脸/明星特征（50个回复）
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
                "AI换脸圆梦，终于能撸女神了"
            ]
            reply_sentences.append(random.choice(ai_phrases))
        
        # 如果没有明显特征，添加通用描述（100个回复）
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
                "这么浪的屄，想插个够本"
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
                    if self.should_skip_post(post['title']):
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
                    
                    # 检查是否应该跳过该帖子
                    if self.should_skip_post(post['title']):
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
            
            # 登录
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
