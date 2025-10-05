#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动更新管理模块
"""
import os
import subprocess
import json
import requests
import logging
from datetime import datetime
import shutil

class UpdateManager:
    def __init__(self):
        self.current_version = self.get_current_version_from_readme()
        self.repo_owner = "AWdress"
        self.repo_name = "AW98tamg"
        self.github_api = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        self.branch = "main"
        
    def get_current_version_from_readme(self):
        """从README.md读取当前版本"""
        try:
            with open('README.md', 'r', encoding='utf-8') as f:
                content = f.read()
                # 查找版本信息行：**版本**：v3.3
                import re
                match = re.search(r'\*\*版本\*\*[：:]\s*(v[\d.]+)', content)
                if match:
                    return match.group(1)
        except Exception as e:
            logging.warning(f"无法从README读取版本: {e}")
        return "v3.3"  # 默认版本
    
    def get_current_version(self):
        """获取当前版本"""
        return self.current_version
    
    def get_local_commit_hash(self):
        """获取本地commit hash"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                capture_output=True,
                text=True,
                cwd='.'
            )
            if result.returncode == 0:
                return result.stdout.strip()[:7]
        except Exception as e:
            logging.error(f"获取本地commit失败: {e}")
        return None
    
    def get_latest_commit_info(self):
        """从GitHub获取最新commit信息"""
        try:
            headers = {}
            github_token = os.getenv('GITHUB_TOKEN')
            if github_token:
                headers['Authorization'] = f'token {github_token}'
            
            url = f"{self.github_api}/commits/{self.branch}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'sha': data['sha'][:7],
                    'message': data['commit']['message'].split('\n')[0],
                    'date': data['commit']['author']['date'],
                    'author': data['commit']['author']['name']
                }
        except Exception as e:
            logging.error(f"获取远程版本失败: {e}")
        return None
    
    def get_latest_release(self):
        """从GitHub获取最新Release版本"""
        try:
            headers = {}
            github_token = os.getenv('GITHUB_TOKEN')
            if github_token:
                headers['Authorization'] = f'token {github_token}'
            
            url = f"{self.github_api}/releases/latest"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'version': data['tag_name'],
                    'name': data['name'],
                    'body': data['body'],
                    'published_at': data['published_at']
                }
        except Exception as e:
            logging.warning(f"获取Release信息失败: {e}")
        return None
    
    def check_update(self):
        """检查是否有更新"""
        try:
            local_hash = self.get_local_commit_hash()
            remote_info = self.get_latest_commit_info()
            release_info = self.get_latest_release()
            
            if not remote_info:
                return {
                    'success': False,
                    'message': '无法连接到GitHub，请检查网络'
                }
            
            has_update = local_hash != remote_info['sha'] if local_hash else True
            
            return {
                'success': True,
                'has_update': has_update,
                'current_version': self.current_version,
                'current_commit': local_hash or '未知',
                'latest_commit': remote_info['sha'],
                'latest_message': remote_info['message'],
                'latest_date': remote_info['date'],
                'latest_release': release_info
            }
        except Exception as e:
            logging.error(f"检查更新失败: {e}")
            return {
                'success': False,
                'message': f'检查更新失败: {str(e)}'
            }
    
    def backup_config(self):
        """备份配置文件"""
        try:
            if os.path.exists('config.json'):
                shutil.copy2('config.json', 'config.json.backup')
                logging.info("配置文件已备份")
                return True
        except Exception as e:
            logging.error(f"备份配置失败: {e}")
        return False
    
    def restore_config(self):
        """恢复配置文件"""
        try:
            if os.path.exists('config.json.backup'):
                shutil.copy2('config.json.backup', 'config.json')
                logging.info("配置文件已恢复")
                return True
        except Exception as e:
            logging.error(f"恢复配置失败: {e}")
        return False
    
    def is_git_repo(self):
        """检查是否为Git仓库"""
        return os.path.exists('.git')
    
    def init_git_repo(self):
        """初始化Git仓库"""
        try:
            if not self.is_git_repo():
                logging.info("初始化Git仓库...")
                subprocess.run(['git', 'init'], check=True)
                
                # 添加远程仓库
                github_token = os.getenv('GITHUB_TOKEN', '')
                if github_token:
                    remote_url = f"https://{github_token}@github.com/{self.repo_owner}/{self.repo_name}.git"
                else:
                    remote_url = f"https://github.com/{self.repo_owner}/{self.repo_name}.git"
                
                subprocess.run(['git', 'remote', 'add', 'origin', remote_url], check=True)
                subprocess.run(['git', 'fetch', 'origin'], check=True)
                subprocess.run(['git', 'checkout', '-b', self.branch, f'origin/{self.branch}'], check=True)
                
                logging.info("Git仓库初始化完成")
                return True
        except Exception as e:
            logging.error(f"初始化Git仓库失败: {e}")
        return False
    
    def do_update(self):
        """执行更新"""
        try:
            # 1. 检查是否为Git仓库
            if not self.is_git_repo():
                if not self.init_git_repo():
                    return {
                        'success': False,
                        'message': '初始化Git仓库失败，请检查网络或GitHub访问权限'
                    }
            
            # 2. 备份配置文件
            if not self.backup_config():
                return {
                    'success': False,
                    'message': '备份配置文件失败'
                }
            
            # 3. 保存当前分支
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True
            )
            current_branch = result.stdout.strip() if result.returncode == 0 else self.branch
            
            # 4. 配置Git
            subprocess.run(['git', 'config', '--global', 'user.email', 'bot@aw98tang.local'])
            subprocess.run(['git', 'config', '--global', 'user.name', 'AW98tang Bot'])
            
            # 5. 暂存本地修改
            subprocess.run(['git', 'stash', 'save', 'auto-update-backup'])
            
            # 6. 拉取最新代码
            logging.info("正在拉取最新代码...")
            result = subprocess.run(
                ['git', 'pull', 'origin', current_branch],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # 尝试恢复
                subprocess.run(['git', 'stash', 'pop'])
                self.restore_config()
                return {
                    'success': False,
                    'message': f'Git拉取失败: {result.stderr}'
                }
            
            # 7. 恢复配置文件（防止被覆盖）
            self.restore_config()
            
            # 8. 恢复本地修改
            subprocess.run(['git', 'stash', 'pop'], capture_output=True)
            
            # 9. 获取更新信息
            new_version = self.get_current_version_from_readme()
            new_commit = self.get_local_commit_hash()
            
            logging.info(f"更新成功！新版本: {new_version}, Commit: {new_commit}")
            
            return {
                'success': True,
                'message': '更新成功！请重启服务以应用更新',
                'new_version': new_version,
                'new_commit': new_commit,
                'need_restart': True
            }
            
        except Exception as e:
            logging.error(f"更新失败: {e}")
            # 尝试恢复
            try:
                subprocess.run(['git', 'stash', 'pop'], capture_output=True)
                self.restore_config()
            except:
                pass
            
            return {
                'success': False,
                'message': f'更新失败: {str(e)}'
            }
    
    def get_update_log(self, limit=10):
        """获取更新日志"""
        try:
            result = subprocess.run(
                ['git', 'log', f'-{limit}', '--pretty=format:%h|%s|%an|%ar'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logs = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('|')
                        if len(parts) == 4:
                            logs.append({
                                'hash': parts[0],
                                'message': parts[1],
                                'author': parts[2],
                                'date': parts[3]
                            })
                return {'success': True, 'logs': logs}
        except Exception as e:
            logging.error(f"获取更新日志失败: {e}")
        
        return {'success': False, 'logs': []}


