#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能回复服务
支持多种AI接口（OpenAI, Claude, 国产AI等）
"""

import requests
import json
import logging
from typing import Optional

class AIReplyService:
    """AI回复服务类"""
    
    def __init__(self, config: dict):
        """
        初始化AI服务
        
        Args:
            config: AI配置字典
        """
        self.enabled = config.get('enable_ai_reply', False)
        self.api_type = config.get('ai_api_type', 'openai')  # openai, claude, custom
        self.api_url = config.get('ai_api_url', '')
        self.api_key = config.get('ai_api_key', '')
        self.model = config.get('ai_model', 'gpt-3.5-turbo')
        self.temperature = config.get('ai_temperature', 0.8)
        self.max_tokens = config.get('ai_max_tokens', 200)
        self.timeout = config.get('ai_timeout', 10)
        
        # 系统提示词
        self.system_prompt = config.get('ai_system_prompt', 
            '你是一个论坛用户，需要根据帖子标题和内容生成简短的回复。'
            '回复要自然、友好、简洁，不超过50字。'
            '不要使用敏感词汇，保持礼貌和正能量。'
        )
        
        self.logger = logging.getLogger(__name__)
    
    def is_enabled(self) -> bool:
        """检查AI回复是否启用"""
        return self.enabled and bool(self.api_key)
    
    def generate_reply(self, title: str, content: str = "") -> Optional[str]:
        """
        调用AI生成回复
        
        Args:
            title: 帖子标题
            content: 帖子内容（可选）
        
        Returns:
            生成的回复内容，失败返回None
        """
        if not self.is_enabled():
            self.logger.warning("AI回复未启用或API Key未配置")
            return None
        
        try:
            # 构建提示词
            user_prompt = f"帖子标题：{title}"
            if content:
                # 限制内容长度，避免token过多
                content_preview = content[:500] if len(content) > 500 else content
                user_prompt += f"\n帖子内容：{content_preview}"
            user_prompt += "\n\n请生成一条简短的回复（不超过50字）："
            
            # 根据API类型调用不同接口
            if self.api_type == 'openai':
                return self._call_openai_api(user_prompt)
            elif self.api_type == 'claude':
                return self._call_claude_api(user_prompt)
            elif self.api_type == 'custom':
                return self._call_custom_api(user_prompt)
            else:
                self.logger.error(f"不支持的API类型: {self.api_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"AI生成回复失败: {str(e)}")
            return None
    
    def _call_openai_api(self, prompt: str) -> Optional[str]:
        """调用OpenAI兼容接口"""
        try:
            url = self.api_url or "https://api.openai.com/v1/chat/completions"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            self.logger.info(f"🤖 调用AI接口: {url} (model: {self.model})")
            
            response = requests.post(
                url, 
                headers=headers, 
                json=data, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                reply = result['choices'][0]['message']['content'].strip()
                self.logger.info(f"✅ AI生成回复: {reply}")
                return reply
            else:
                self.logger.error(f"❌ AI接口返回错误: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error("❌ AI接口请求超时")
            return None
        except Exception as e:
            self.logger.error(f"❌ OpenAI API调用失败: {str(e)}")
            return None
    
    def _call_claude_api(self, prompt: str) -> Optional[str]:
        """调用Claude API"""
        try:
            url = self.api_url or "https://api.anthropic.com/v1/messages"
            
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": self.model or "claude-3-haiku-20240307",
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": self.system_prompt,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            
            self.logger.info(f"🤖 调用Claude接口: {url}")
            
            response = requests.post(
                url, 
                headers=headers, 
                json=data, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                reply = result['content'][0]['text'].strip()
                self.logger.info(f"✅ AI生成回复: {reply}")
                return reply
            else:
                self.logger.error(f"❌ Claude接口返回错误: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Claude API调用失败: {str(e)}")
            return None
    
    def _call_custom_api(self, prompt: str) -> Optional[str]:
        """
        调用自定义API接口
        
        自定义接口需要返回以下JSON格式：
        {
            "reply": "生成的回复内容"
        }
        或者OpenAI兼容格式
        """
        try:
            if not self.api_url:
                self.logger.error("自定义API URL未配置")
                return None
            
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            # 尝试通用格式
            data = {
                "prompt": prompt,
                "system_prompt": self.system_prompt,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }
            
            self.logger.info(f"🤖 调用自定义接口: {self.api_url}")
            
            response = requests.post(
                self.api_url, 
                headers=headers, 
                json=data, 
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 尝试多种响应格式
                reply = None
                if 'reply' in result:
                    reply = result['reply']
                elif 'response' in result:
                    reply = result['response']
                elif 'choices' in result:
                    # OpenAI格式
                    reply = result['choices'][0]['message']['content']
                elif 'content' in result:
                    # Claude格式
                    if isinstance(result['content'], list):
                        reply = result['content'][0]['text']
                    else:
                        reply = result['content']
                
                if reply:
                    reply = reply.strip()
                    self.logger.info(f"✅ AI生成回复: {reply}")
                    return reply
                else:
                    self.logger.error(f"❌ 无法解析自定义API响应: {result}")
                    return None
            else:
                self.logger.error(f"❌ 自定义接口返回错误: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 自定义API调用失败: {str(e)}")
            return None
    
    def test_connection(self) -> dict:
        """
        测试AI接口连接
        
        Returns:
            {"success": bool, "message": str}
        """
        if not self.is_enabled():
            return {
                "success": False,
                "message": "AI回复未启用或API Key未配置"
            }
        
        try:
            test_reply = self.generate_reply("测试帖子标题", "这是一个测试内容")
            
            if test_reply:
                return {
                    "success": True,
                    "message": f"连接成功！测试回复: {test_reply}"
                }
            else:
                return {
                    "success": False,
                    "message": "API调用失败，请检查配置"
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"测试失败: {str(e)}"
            }

