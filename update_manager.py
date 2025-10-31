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
        self.repo_name = "AW98tang"
        self.github_api = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        self.branch = "main"
        
    def get_current_version_from_readme(self):
        """从本地README.md读取当前版本（从 ## 🔥 最新更新 标题提取）"""
        try:
            with open('README.md', 'r', encoding='utf-8') as f:
                content = f.read()
                # 匹配格式：## 🔥 最新更新（v3.7）或 ## 🔥 最新更新（v3.7.1）
                import re
                match = re.search(r'##\s*🔥\s*最新更新[（(](v[\d.]+)[）)]', content)
                if match:
                    return match.group(1)
        except Exception as e:
            logging.warning(f"无法从README读取版本: {e}")
        return "v3.7"  # 默认版本
    
    def get_remote_version_from_readme(self):
        """从GitHub远程README.md读取最新版本号"""
        try:
            headers = {}
            github_token = os.getenv('GITHUB_TOKEN')
            if github_token:
                headers['Authorization'] = f'token {github_token}'
            
            # 使用 raw.githubusercontent.com 直接读取文件内容
            raw_url = f"https://raw.githubusercontent.com/{self.repo_owner}/{self.repo_name}/{self.branch}/README.md"
            response = requests.get(raw_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                import re
                match = re.search(r'##\s*🔥\s*最新更新[（(](v[\d.]+)[）)]', content)
                if match:
                    remote_version = match.group(1)
                    logging.info(f"从GitHub读取到最新版本: {remote_version}")
                    return remote_version
        except Exception as e:
            logging.warning(f"从GitHub读取README版本失败: {e}")
        
        # 失败时返回None，让调用方使用本地版本号作为备用
        return None
    
    def get_current_version(self):
        """获取当前版本：格式 v3.7 (commit)"""
        version = self.get_current_version_from_readme()  # v3.7 或 v3.7.1
        commit_hash = self.get_local_commit_hash()
        
        if commit_hash:
            return f"{version} ({commit_hash})"
        else:
            return version
    
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
                # 同时也返回最近一次提交信息用于参考
                remote_info = self.get_latest_commit_info() or {}
                remote_commit = remote_info.get('sha', '')
                
                # 🔧 修复：从GitHub远程读取最新版本号，而不是本地README
                remote_version = self.get_remote_version_from_readme()
                if not remote_version:
                    # 如果获取失败，降级使用本地版本号
                    remote_version = self.get_current_version_from_readme()
                    logging.warning("无法获取远程版本号，使用本地版本号作为参考")
                
                # 构建最新版本号：vX.X.X (commit)
                latest_version = f"{remote_version} ({remote_commit})" if remote_commit else remote_version
                
                has_update = (current_version != latest_version)
                return {
                    'success': True,
                    'has_update': has_update,
                    'current_version': current_version,
                    'current_commit': local_hash or '未知',
                    'latest_version': latest_version,
                    'latest_commit': remote_commit,
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
            remote_commit = remote_info['sha']
            
            # 🔧 修复：从GitHub远程读取最新版本号，而不是本地README
            remote_version = self.get_remote_version_from_readme()
            if not remote_version:
                # 如果获取失败，降级使用本地版本号
                remote_version = self.get_current_version_from_readme()
                logging.warning("无法获取远程版本号，使用本地版本号作为参考")
            
            # 构建最新版本号：vX.X.X (commit)
            latest_version = f"{remote_version} ({remote_commit})"
            
            has_update = local_hash != remote_commit if local_hash else True
            return {
                'success': True,
                'has_update': has_update,
                'current_version': current_version,
                'current_commit': local_hash or '未知',
                'latest_version': latest_version,
                'latest_commit': remote_commit,
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
            logging.info("=" * 60)
            logging.info("开始执行系统更新...")
            logging.info("=" * 60)
            
            # 备份配置文件
            logging.info("正在备份配置文件...")
            if not self.backup_config():
                logging.error("配置文件备份失败")
                return {
                    'success': False,
                    'message': '备份配置文件失败'
                }
            logging.info("配置文件备份成功")
            
            # 直接走 ZIP 镜像/API 更新（不再使用 git）
            logging.info("正在通过ZIP方式获取最新代码...")
            fb = self._fallback_update_via_zip()
            
            if fb.get('success'):
                logging.info("ZIP更新成功")
                # 恢复配置文件
                self.restore_config()
                # 与前端对齐：返回通用成功信息，不暴露回退来源
                fb['message'] = '更新成功'
                fb.pop('from', None)
                logging.info("=" * 60)
                logging.info("系统更新完成！")
                logging.info("=" * 60)
                return fb
            else:
                error_msg = fb.get('message', '更新失败')
                logging.error(f"ZIP更新失败: {error_msg}")
                # 尝试恢复配置
                self.restore_config()
                return {
                    'success': False,
                    'message': error_msg
                }
            
        except Exception as e:
            logging.error(f"更新过程发生异常: {e}", exc_info=True)
            # 尝试恢复配置
            try:
                self.restore_config()
            except Exception as restore_err:
                logging.error(f"恢复配置失败: {restore_err}")
            
            return {
                'success': False,
                'message': f'更新失败: {str(e)}'
            }
    
    def _fallback_update_via_zip(self):
        """使用ZIP下载+覆盖方式更新（支持公开镜像与私有仓库zipball）。"""
        try:
            def download_with_requests(url: str, out_path: str, headers: dict | None = None) -> bool:
                try:
                    logging.info(f"尝试使用requests下载: {url}")
                    resp = requests.get(url, timeout=60, stream=True, headers=headers or {})
                    if resp.status_code == 200:
                        total_size = 0
                        with open(out_path, 'wb') as f:
                            for chunk in resp.iter_content(chunk_size=1024 * 256):
                                if chunk:
                                    f.write(chunk)
                                    total_size += len(chunk)
                        logging.info(f"requests下载成功，文件大小: {total_size / 1024 / 1024:.2f} MB")
                        return True
                    logging.warning(f"requests 下载失败: {url} -> HTTP {resp.status_code}")
                except Exception as e:
                    logging.warning(f"requests 下载异常: {e}")
                return False

            def download_with_curl(url: str, out_path: str, headers: dict | None = None) -> bool:
                try:
                    logging.info(f"尝试使用curl下载: {url}")
                    cmd = ['curl', '-L', '-sS', '--fail', '-o', out_path]
                    if headers:
                        for k, v in headers.items():
                            cmd.extend(['-H', f"{k}: {v}"])
                    cmd.append(url)
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    if r.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                        size = os.path.getsize(out_path)
                        logging.info(f"curl下载成功，文件大小: {size / 1024 / 1024:.2f} MB")
                        return True
                    logging.warning(f"curl 下载失败: {url} -> 返回码{r.returncode}, 错误: {r.stderr.strip()}")
                except subprocess.TimeoutExpired:
                    logging.error("curl下载超时（120秒）")
                except Exception as ce:
                    logging.warning(f"curl 下载异常: {ce}")
                return False

            # 1) 私有仓库：优先 GitHub API zipball
            github_token = os.getenv('GITHUB_TOKEN')
            if github_token:
                logging.info("检测到GITHUB_TOKEN，尝试使用GitHub API下载...")
                api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/zipball/{self.branch}"
                headers = {'Authorization': f'token {github_token}', 'Accept': 'application/vnd.github+json'}
                with tempfile.TemporaryDirectory() as td:
                    zip_path = os.path.join(td, 'repo.zip')
                    if download_with_requests(api_url, zip_path, headers) or download_with_curl(api_url, zip_path, headers):
                        logging.info("GitHub API方式下载成功，开始解压...")
                        return self._extract_and_overlay(zip_path)
                logging.warning("GitHub API方式下载失败，尝试公开下载...")
            else:
                logging.info("未设置GITHUB_TOKEN，使用公开下载方式")

            # 2) GitHub官方下载地址
            official_url = f"https://github.com/{self.repo_owner}/{self.repo_name}/archive/refs/heads/{self.branch}.zip"
            
            last_error = None
            logging.info(f"尝试从GitHub官方地址下载: {official_url}")
            for url in [official_url]:
                try:
                    with tempfile.TemporaryDirectory() as td:
                        zip_path = os.path.join(td, 'repo.zip')
                        ok = download_with_requests(url, zip_path) or download_with_curl(url, zip_path)
                        if not ok:
                            last_error = '下载失败，可能是网络问题或GitHub访问受限'
                            continue
                        logging.info("下载成功，开始解压和覆盖文件...")
                        return self._extract_and_overlay(zip_path)
                except Exception as e:
                    last_error = str(e)
                    logging.error(f"下载或解压过程异常: {e}", exc_info=True)
                    continue

            return {'success': False, 'message': f'GitHub ZIP更新失败: {last_error or "未知错误"}'}
        except Exception as e:
            logging.error(f"ZIP回退更新异常: {e}", exc_info=True)
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

            # 获取完整版本号：v3.7.1 (commit)
            new_version = self.get_current_version()
            new_commit = parsed_commit or 'zip'
            return {
                'success': True,
                'message': '更新成功',
                'new_version': new_version,
                'new_commit': new_commit,
                'need_restart': True
            }

    def get_update_log(self, limit=10):
        """获取更新日志（包含完整提交内容）。
        逻辑：优先本地 git；如本地最新提交与远端不一致，改用 GitHub API；本地不可用也用 API。
        """
        def _from_github_api(n: int):
            try:
                headers = {'User-Agent': 'aw98tang-update-client'}
                github_token = os.getenv('GITHUB_TOKEN')
                if github_token:
                    headers['Authorization'] = f'token {github_token}'
                url = f"{self.github_api}/commits?sha={self.branch}&per_page={max(1,int(n))}"
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    logs = []
                    for item in resp.json():
                        logs.append({
                            'hash': item.get('sha','')[:7],
                            'author': (item.get('commit',{}).get('author',{}) or {}).get('name',''),
                            'date': (item.get('commit',{}).get('author',{}) or {}).get('date',''),
                            'message': (item.get('commit',{}) or {}).get('message','')
                        })
                    return {'success': True, 'logs': logs}
                logging.error(f"GitHub API 获取日志失败: HTTP {resp.status_code}")
            except Exception as e:
                logging.error(f"GitHub API 获取日志异常: {e}")
            return {'success': False, 'logs': []}

        # 远端最新提交SHA
        remote_info = self.get_latest_commit_info() or {}
        remote_sha = remote_info.get('sha')

        # 1) 读取本地 git 日志
        try:
            record_sep = '\x1e'
            field_sep = '\x1f'
            pretty = f"%h%x1f%an%x1f%ar%x1f%B%x1e"
            result = subprocess.run(
                ['git', 'log', f'-{limit}', f'--pretty=format:{pretty}'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
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
                # 如果本地最新与远端不同，则改用远端
                if logs and remote_sha and logs[0]['hash'] != remote_sha:
                    api_logs = _from_github_api(limit)
                    if api_logs['success']:
                        return api_logs
                if logs:
                    return {'success': True, 'logs': logs}
        except Exception as e:
            logging.warning(f"本地git日志不可用: {e}")

        # 2) 直接用远端
        return _from_github_api(limit)


