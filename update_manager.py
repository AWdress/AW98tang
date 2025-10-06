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
import zipfile
import tempfile

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
        """获取当前版本：优先使用 Release 版本；无 Release 再读取 README。"""
        try:
            rel = self.get_latest_release()
            if rel and rel.get('version'):
                return rel['version']
        except Exception:
            pass
        return self.get_current_version_from_readme()
    
    def get_local_commit_hash(self):
        """获取当前代码对应的commit标识。
        优先读取 data/last_update.json（ZIP更新会写入准确commit），否则回退到 .git HEAD。
        """
        # 1) 优先 last_update.json（ZIP路径会写真实commit）
        try:
            state_path = os.path.join('data', 'last_update.json')
            if os.path.exists(state_path):
                with open(state_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                    commit = info.get('commit')
                    if commit:
                        return commit[:7]
        except Exception as e:
            logging.warning(f"读取上次更新记录失败: {e}")

        # 2) 回退到git HEAD
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
        """检查是否有更新（优先使用 Release 版本对比；无 Release 再回退到 commit 对比）"""
        try:
            current_version = self.get_current_version()
            local_hash = self.get_local_commit_hash()

            # 优先获取 Release 信息
            release_info = self.get_latest_release()
            if release_info and release_info.get('version'):
                has_update = (current_version != release_info['version'])
                # 同时也返回最近一次提交信息用于参考
                remote_info = self.get_latest_commit_info() or {}
                return {
                    'success': True,
                    'has_update': has_update,
                    'current_version': current_version,
                    'current_commit': local_hash or '未知',
                    'latest_commit': remote_info.get('sha'),
                    'latest_message': remote_info.get('message'),
                    'latest_date': remote_info.get('date'),
                    'latest_release': release_info
                }

            # 无 Release 时回退到 commit 对比
            remote_info = self.get_latest_commit_info()
            if not remote_info:
                return {
                    'success': False,
                    'message': '无法连接到GitHub，请检查网络'
                }
            has_update = local_hash != remote_info['sha'] if local_hash else True
            return {
                'success': True,
                'has_update': has_update,
                'current_version': current_version,
                'current_commit': local_hash or '未知',
                'latest_commit': remote_info['sha'],
                'latest_message': remote_info['message'],
                'latest_date': remote_info['date'],
                'latest_release': None
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
                
                subprocess.run(['git', 'init'], check=True, stdin=subprocess.DEVNULL)
                
                # 配置Git禁用凭据
                subprocess.run(['git', 'config', 'credential.helper', ''], check=True)
                
                # 添加远程仓库
                github_token = os.getenv('GITHUB_TOKEN', '')
                if github_token:
                    logging.info("使用GitHub Token进行认证")
                    remote_url = f"https://{github_token}@github.com/{self.repo_owner}/{self.repo_name}.git"
                else:
                    logging.info("使用公开访问模式（无认证）")
                    remote_url = f"https://github.com/{self.repo_owner}/{self.repo_name}.git"
                
                subprocess.run(['git', 'remote', 'add', 'origin', remote_url], check=True)
                subprocess.run(['git', 'fetch', 'origin'], check=True, stdin=subprocess.DEVNULL)
                subprocess.run(['git', 'checkout', '-b', self.branch, f'origin/{self.branch}'], check=True, stdin=subprocess.DEVNULL)
                
                logging.info("Git仓库初始化完成")
                return True
        except Exception as e:
            logging.error(f"初始化Git仓库失败: {e}")
        return False
    
    def do_update(self):
        """执行更新"""
        try:
            # 备份配置文件
            if not self.backup_config():
                return {
                    'success': False,
                    'message': '备份配置文件失败'
                }
            # 直接走 ZIP 镜像/API 更新（不再使用 git）
            logging.info("正在通过ZIP方式获取最新代码...")
            fb = self._fallback_update_via_zip()
            if fb.get('success'):
                # 与前端对齐：返回通用成功信息，不暴露回退来源
                fb['message'] = '更新成功'
                fb.pop('from', None)
                return fb
            else:
                return {
                    'success': False,
                    'message': fb.get('message', '更新失败')
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
    
    def _fallback_update_via_zip(self):
        """使用ZIP下载+覆盖方式更新（支持公开镜像与私有仓库zipball）。"""
        try:
            def download_with_requests(url: str, out_path: str, headers: dict | None = None) -> bool:
                try:
                    resp = requests.get(url, timeout=60, stream=True, headers=headers or {})
                    if resp.status_code == 200:
                        with open(out_path, 'wb') as f:
                            for chunk in resp.iter_content(chunk_size=1024 * 256):
                                if chunk:
                                    f.write(chunk)
                        return True
                    logging.warning(f"requests 下载失败: {url} -> HTTP {resp.status_code}")
                except Exception as e:
                    logging.warning(f"requests 异常: {e}")
                return False

            def download_with_curl(url: str, out_path: str, headers: dict | None = None) -> bool:
                try:
                    cmd = ['curl', '-L', '-sS', '--fail', '-o', out_path]
                    if headers:
                        for k, v in headers.items():
                            cmd.extend(['-H', f"{k}: {v}"])
                    cmd.append(url)
                    r = subprocess.run(cmd, capture_output=True, text=True)
                    if r.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                        return True
                    logging.warning(f"curl 下载失败: {url} -> {r.stderr.strip()}")
                except Exception as ce:
                    logging.warning(f"curl 异常: {ce}")
                return False

            # 1) 私有仓库：优先 GitHub API zipball
            github_token = os.getenv('GITHUB_TOKEN')
            if github_token:
                api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/zipball/{self.branch}"
                headers = {'Authorization': f'token {github_token}', 'Accept': 'application/vnd.github+json'}
                with tempfile.TemporaryDirectory() as td:
                    zip_path = os.path.join(td, 'repo.zip')
                    if download_with_requests(api_url, zip_path, headers) or download_with_curl(api_url, zip_path, headers):
                        return self._extract_and_overlay(zip_path)

            # 2) 公开镜像
            mirrors = [
                f"https://mirror.ghproxy.com/https://codeload.github.com/{self.repo_owner}/{self.repo_name}/zip/refs/heads/{self.branch}",
                f"https://kgithub.com/{self.repo_owner}/{self.repo_name}/archive/refs/heads/{self.branch}.zip",
                f"https://hub.fgit.cf/{self.repo_owner}/{self.repo_name}/archive/refs/heads/{self.branch}.zip"
            ]

            last_error = None
            for url in mirrors:
                try:
                    with tempfile.TemporaryDirectory() as td:
                        zip_path = os.path.join(td, 'repo.zip')
                        ok = download_with_requests(url, zip_path) or download_with_curl(url, zip_path)
                        if not ok:
                            last_error = '下载失败'
                            continue
                        return self._extract_and_overlay(zip_path)
                except Exception as e:
                    last_error = str(e)
                    continue

            return {'success': False, 'message': f'镜像ZIP更新失败: {last_error or "未知错误"}'}
        except Exception as e:
            logging.error(f"ZIP回退更新异常: {e}")
            return {'success': False, 'message': f'ZIP回退更新异常: {str(e)}'}

    def _extract_and_overlay(self, zip_path: str) -> dict:
        with tempfile.TemporaryDirectory() as td:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(td)

            # 找到解压后的根目录
            entries = [p for p in os.listdir(td) if os.path.isdir(os.path.join(td, p))]
            src_root = None
            for p in entries:
                if p.lower().startswith(self.repo_name.lower()):
                    src_root = os.path.join(td, p)
                    break
            if not src_root and entries:
                src_root = os.path.join(td, entries[0])
            if not src_root:
                return {'success': False, 'message': 'ZIP内容解析失败'}

            # 从解压目录名尝试解析commit（zipball/codeload 通常包含短/长sha）
            parsed_commit = None
            try:
                import re
                base = os.path.basename(src_root)
                m = re.search(r'-([0-9a-fA-F]{7,40})$', base)
                if m:
                    parsed_commit = m.group(1)[:7]
            except Exception:
                pass

            keep_files = {'config.json'}
            keep_dirs = {'logs', 'debug', 'data', '.git'}

            for root, dirs, files in os.walk(src_root):
                rel = os.path.relpath(root, src_root)
                if rel == '.':
                    rel = ''
                parts = rel.split(os.sep) if rel else []
                if parts and parts[0] in keep_dirs:
                    continue

                dest_dir = os.path.join('.', rel) if rel else '.'
                os.makedirs(dest_dir, exist_ok=True)

                for filename in files:
                    if filename in keep_files:
                        continue
                    src_file = os.path.join(root, filename)
                    dst_file = os.path.join(dest_dir, filename)
                    shutil.copy2(src_file, dst_file)

            logging.info("ZIP更新完成")
            # 记录本次更新来源与时间，便于非git环境显示版本信息
            try:
                os.makedirs('data', exist_ok=True)
                with open(os.path.join('data', 'last_update.json'), 'w', encoding='utf-8') as f:
                    json.dump({
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'zip',
                        'commit': parsed_commit or 'zip'
                    }, f, ensure_ascii=False)
            except Exception:
                pass

            new_version = self.get_current_version_from_readme()
            new_commit = parsed_commit or 'zip'
            return {
                'success': True,
                'message': '更新成功',
                'new_version': new_version,
                'new_commit': new_commit,
                'need_restart': True
            }

    def get_update_log(self, limit=10):
        """获取更新日志（包含完整提交内容）"""
        try:
            # 使用不可见分隔符，避免正文换行影响解析
            record_sep = '\x1e'  # 记录分隔
            field_sep = '\x1f'   # 字段分隔
            pretty = f"%h%x1f%an%x1f%ar%x1f%B%x1e"
            result = subprocess.run(
                ['git', 'log', f'-{limit}', f'--pretty=format:{pretty}'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                raw = result.stdout
                logs = []
                for rec in raw.split(record_sep):
                    if not rec.strip():
                        continue
                    fields = rec.split(field_sep)
                    if len(fields) >= 4:
                        commit_hash, author, rel_date, message = fields[0], fields[1], fields[2], field_sep.join(fields[3:])
                        logs.append({
                            'hash': commit_hash.strip(),
                            'author': author.strip(),
                            'date': rel_date.strip(),
                            'message': message.strip()
                        })
                return {'success': True, 'logs': logs}
        except Exception as e:
            logging.error(f"获取更新日志失败: {e}")
        return {'success': False, 'logs': []}


