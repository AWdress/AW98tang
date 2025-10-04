#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统检查脚本 - 检查所有依赖和配置
"""

import sys
import os

def check_python_version():
    """检查Python版本"""
    print("=" * 60)
    print("🐍 检查Python版本")
    print("=" * 60)
    print(f"Python版本: {sys.version}")
    version_info = sys.version_info
    if version_info.major >= 3 and version_info.minor >= 8:
        print("✅ Python版本满足要求 (>= 3.8)")
        return True
    else:
        print("❌ Python版本过低，需要 >= 3.8")
        return False

def check_dependencies():
    """检查所有依赖"""
    print("\n" + "=" * 60)
    print("📦 检查依赖包")
    print("=" * 60)
    
    dependencies = {
        'requests': 'HTTP请求库（AI接口需要）',
        'selenium': 'Selenium自动化',
        'flask': 'Web控制面板',
        'beautifulsoup4': 'HTML解析',
        'lxml': 'XML解析',
        'schedule': '定时任务',
    }
    
    all_ok = True
    for package, desc in dependencies.items():
        try:
            if package == 'beautifulsoup4':
                __import__('bs4')
            else:
                __import__(package)
            print(f"✅ {package:20s} - {desc}")
        except ImportError:
            print(f"❌ {package:20s} - {desc} [未安装]")
            all_ok = False
    
    return all_ok

def check_files():
    """检查关键文件"""
    print("\n" + "=" * 60)
    print("📁 检查关键文件")
    print("=" * 60)
    
    files = {
        'selenium_auto_bot.py': '主程序',
        'web_app.py': 'Web控制面板',
        'stats_manager.py': '统计管理器',
        'ai_reply_service.py': 'AI服务（新增）',
        'config.json.example': '配置示例',
        'requirements.txt': '依赖列表',
        'docker-compose.yml': 'Docker配置',
        'docker-entrypoint.sh': 'Docker启动脚本',
    }
    
    all_ok = True
    for filename, desc in files.items():
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"✅ {filename:30s} - {desc} ({size} bytes)")
        else:
            print(f"❌ {filename:30s} - {desc} [不存在]")
            all_ok = False
    
    return all_ok

def check_config():
    """检查配置文件"""
    print("\n" + "=" * 60)
    print("⚙️ 检查配置文件")
    print("=" * 60)
    
    if not os.path.exists('config.json'):
        print("❌ config.json 不存在")
        print("💡 提示: 复制 config.json.example 并修改")
        return False
    
    try:
        import json
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("✅ config.json 格式正确")
        
        # 检查关键配置
        required_keys = ['username', 'password', 'base_url']
        missing_keys = [k for k in required_keys if k not in config]
        
        if missing_keys:
            print(f"⚠️ 缺少配置项: {', '.join(missing_keys)}")
            return False
        
        # 检查AI配置
        if config.get('enable_ai_reply'):
            if not config.get('ai_api_key'):
                print("⚠️ AI回复已启用但未配置API Key")
            else:
                print(f"✅ AI回复已启用 (类型: {config.get('ai_api_type', 'openai')})")
        else:
            print("ℹ️ AI回复未启用")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ config.json 格式错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 读取配置失败: {e}")
        return False

def check_directories():
    """检查必需的目录"""
    print("\n" + "=" * 60)
    print("📂 检查目录结构")
    print("=" * 60)
    
    directories = {
        'logs': '日志目录',
        'data': '数据目录（登录状态、统计数据）',
        'debug': '调试目录',
        'docs': '文档目录',
        'templates': '模板目录',
    }
    
    all_ok = True
    for dirname, desc in directories.items():
        if os.path.exists(dirname) and os.path.isdir(dirname):
            files_count = len(os.listdir(dirname))
            print(f"✅ {dirname:15s} - {desc} ({files_count} 个文件)")
        else:
            print(f"⚠️ {dirname:15s} - {desc} [不存在，将自动创建]")
            try:
                os.makedirs(dirname, exist_ok=True)
                print(f"   ✅ 已创建目录: {dirname}")
            except Exception as e:
                print(f"   ❌ 创建失败: {e}")
                all_ok = False
    
    return all_ok

def check_imports():
    """检查关键模块是否能导入"""
    print("\n" + "=" * 60)
    print("🔌 检查模块导入")
    print("=" * 60)
    
    modules = [
        ('selenium_auto_bot', '主程序'),
        ('web_app', 'Web应用'),
        ('stats_manager', '统计管理'),
        ('ai_reply_service', 'AI服务'),
    ]
    
    all_ok = True
    for module_name, desc in modules:
        try:
            __import__(module_name)
            print(f"✅ {module_name:25s} - {desc}")
        except Exception as e:
            print(f"❌ {module_name:25s} - {desc} [导入失败: {e}]")
            all_ok = False
    
    return all_ok

def main():
    """主检查流程"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "AW98tang 系统检查工具" + " " * 21 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    checks = [
        ("Python版本", check_python_version),
        ("依赖包", check_dependencies),
        ("关键文件", check_files),
        ("目录结构", check_directories),
        ("配置文件", check_config),
        ("模块导入", check_imports),
    ]
    
    results = {}
    for name, check_func in checks:
        results[name] = check_func()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 检查总结")
    print("=" * 60)
    
    all_passed = True
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name:15s}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有检查通过！系统运行正常")
        print("\n💡 下一步:")
        print("   1. 编辑 config.json 配置文件")
        print("   2. 运行: python selenium_auto_bot.py")
        print("   3. 或启动Web: python web_app.py")
    else:
        print("⚠️ 发现问题，请根据上述提示修复")
        print("\n💡 常见解决方案:")
        print("   1. 安装依赖: pip install -r requirements.txt")
        print("   2. 复制配置: cp config.json.example config.json")
        print("   3. 创建目录: mkdir logs data debug")
    
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

