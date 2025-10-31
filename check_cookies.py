#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cookie查看工具
用于查看保存的登录状态Cookie内容
"""

import os
import json
import pickle
from datetime import datetime

def check_cookies():
    """检查并显示Cookie内容"""
    
    cookies_pkl = 'data/cookies.pkl'
    cookies_json = 'data/cookies.json'
    
    print("=" * 80)
    print("🍪 Cookie 状态检查工具")
    print("=" * 80)
    print()
    
    # 检查pickle文件
    if os.path.exists(cookies_pkl):
        print(f"✅ 找到Cookie文件: {cookies_pkl}")
        try:
            with open(cookies_pkl, 'rb') as f:
                cookies = pickle.load(f)
            print(f"📊 Cookie数量: {len(cookies)}")
            print()
        except Exception as e:
            print(f"❌ 读取失败: {e}")
            cookies = []
    else:
        print(f"❌ 未找到Cookie文件: {cookies_pkl}")
        cookies = []
    
    # 检查JSON文件
    if os.path.exists(cookies_json):
        print(f"✅ 找到JSON格式Cookie: {cookies_json}")
        print()
    else:
        print(f"ℹ️ 未找到JSON格式Cookie（旧版本不会生成此文件）")
        print()
    
    if not cookies:
        print("💡 提示：请先运行一次机器人并成功登录，Cookie才会被保存")
        return
    
    # 显示Cookie详情
    print("-" * 80)
    print("📋 Cookie 详细内容")
    print("-" * 80)
    print()
    
    important_cookies = ['cPNj_2132_auth', 'cPNj_2132_saltkey', 'cPNj_2132_sid', 'cf_clearance']
    
    for i, cookie in enumerate(cookies, 1):
        name = cookie.get('name', 'Unknown')
        value = cookie.get('value', '')
        domain = cookie.get('domain', '')
        path = cookie.get('path', '/')
        expiry = cookie.get('expiry', None)
        
        # 标记重要Cookie
        is_important = name in important_cookies
        marker = "⭐" if is_important else "  "
        
        print(f"{marker} [{i}] {name}")
        print(f"     Domain: {domain}")
        print(f"     Path: {path}")
        
        # 显示值（敏感信息部分隐藏）
        if len(value) > 50:
            display_value = value[:20] + "..." + value[-10:]
        else:
            display_value = value
        print(f"     Value: {display_value}")
        
        # 显示过期时间
        if expiry:
            try:
                expiry_time = datetime.fromtimestamp(expiry)
                now = datetime.now()
                if expiry_time > now:
                    days_left = (expiry_time - now).days
                    print(f"     Expiry: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')} (还剩 {days_left} 天)")
                else:
                    print(f"     Expiry: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')} (已过期 ❌)")
            except:
                print(f"     Expiry: {expiry}")
        else:
            print(f"     Expiry: Session (会话)")
        
        print()
    
    print("-" * 80)
    print("🔑 重要Cookie说明")
    print("-" * 80)
    print()
    print("⭐ cPNj_2132_auth      - 认证Token，用于保持登录状态")
    print("⭐ cPNj_2132_saltkey   - 加密盐值，用于安全验证")
    print("⭐ cPNj_2132_sid       - 会话ID，当前会话标识")
    print("⭐ cf_clearance        - Cloudflare验证通过标记")
    print()
    
    # 检查关键Cookie是否存在
    cookie_names = [c.get('name', '') for c in cookies]
    print("-" * 80)
    print("✅ Cookie 有效性检查")
    print("-" * 80)
    print()
    
    if 'cPNj_2132_auth' in cookie_names:
        print("✅ 认证Cookie存在")
    else:
        print("❌ 认证Cookie缺失（可能未登录成功）")
    
    if 'cPNj_2132_saltkey' in cookie_names:
        print("✅ 加密盐值存在")
    else:
        print("⚠️ 加密盐值缺失")
    
    if 'cf_clearance' in cookie_names:
        print("✅ Cloudflare验证通过")
    else:
        print("ℹ️ 无Cloudflare验证（正常情况）")
    
    print()
    print("=" * 80)
    print("🍪 Cookie字符串格式（HTTP请求头格式）")
    print("=" * 80)
    print()
    
    # 生成Cookie字符串（浏览器/HTTP格式）
    cookie_string_parts = []
    for cookie in cookies:
        name = cookie.get('name', '')
        value = cookie.get('value', '')
        if name and value:
            cookie_string_parts.append(f"{name}={value}")
    
    cookie_string = "; ".join(cookie_string_parts)
    
    print("📋 完整Cookie字符串:")
    print("-" * 80)
    print(cookie_string)
    print()
    
    # 保存到文件
    cookie_txt_file = 'data/cookies_string.txt'
    try:
        with open(cookie_txt_file, 'w', encoding='utf-8') as f:
            f.write(cookie_string)
        print(f"✅ Cookie字符串已保存到: {cookie_txt_file}")
    except Exception as e:
        print(f"⚠️ 保存Cookie字符串失败: {e}")
    
    print()
    print("=" * 80)
    print("💡 提示：")
    print("   - JSON格式详情：data/cookies.json")
    print("   - HTTP字符串格式：data/cookies_string.txt")
    print("   - Pickle格式（程序用）：data/cookies.pkl")
    print("=" * 80)

if __name__ == '__main__':
    check_cookies()

