# Nginx 反向代理配置指南（PWA 优化版）

## 📋 完整 Nginx 配置

### 基础配置（支持 PWA）

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # HTTP 自动重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL 证书配置（Let's Encrypt）
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL 优化配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全头部
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    
    # 客户端最大上传大小
    client_max_body_size 50M;
    
    # 反向代理到 Flask 应用
    location / {
        proxy_pass http://127.0.0.1:5000;
        
        # 必需的代理头部
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时配置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # ============ PWA 关键配置 ============
    
    # Service Worker - 禁用缓存，确保及时更新
    location = /static/sw.js {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        
        # 重要：禁用 Service Worker 缓存
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
        
        # Service Worker 必需的 MIME 类型
        add_header Content-Type "application/javascript; charset=utf-8";
    }
    
    # PWA Manifest - 短期缓存
    location = /static/manifest.json {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        
        # 短期缓存 manifest
        add_header Cache-Control "public, max-age=3600";
        add_header Content-Type "application/manifest+json; charset=utf-8";
    }
    
    # PWA 图标 - 长期缓存
    location ~* ^/static/icons/.*\.(png|jpg|jpeg|ico)$ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        
        # 长期缓存图标（1年）
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
    
    # 其他静态资源 - 中期缓存
    location ~* ^/static/.*\.(css|js|jpg|jpeg|png|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        
        # 缓存静态资源（7天）
        add_header Cache-Control "public, max-age=604800";
    }
    
    # API 请求 - 禁用缓存
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # API 不缓存
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
    
    # 离线页面
    location = /offline.html {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        add_header Cache-Control "public, max-age=86400";
    }
    
    # 访问日志（可选）
    access_log /var/log/nginx/aw98tang_access.log;
    error_log /var/log/nginx/aw98tang_error.log;
}
```

---

## 🔧 配置步骤

### 1. 创建配置文件

```bash
sudo nano /etc/nginx/sites-available/aw98tang
```

粘贴上面的配置，修改 `your-domain.com` 为你的域名。

### 2. 启用站点

```bash
sudo ln -s /etc/nginx/sites-available/aw98tang /etc/nginx/sites-enabled/
```

### 3. 测试配置

```bash
sudo nginx -t
```

应该看到：
```
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 4. 重载 Nginx

```bash
sudo systemctl reload nginx
```

### 5. 获取 SSL 证书（如果还没有）

```bash
sudo certbot --nginx -d your-domain.com
```

---

## ✅ 验证 PWA 功能

### 1. 检查关键文件是否可访问

在浏览器打开以下地址：

```
https://your-domain.com/static/manifest.json
https://your-domain.com/static/sw.js
https://your-domain.com/static/icons/icon-192x192.png
https://your-domain.com/offline.html
```

所有文件都应该**正常显示，不能是 404**。

### 2. 检查响应头

按 `F12` → **Network** 标签页 → 访问 `/static/sw.js`：

**Response Headers 应该包含：**
```
Content-Type: application/javascript; charset=utf-8
Cache-Control: no-cache, no-store, must-revalidate
```

### 3. 查看控制台

**Console 标签页应该显示：**
```
🔍 PWA支持检测结果：
├─ Service Worker支持: ✅
├─ HTTPS/Localhost: ✅
├─ 通知支持: ✅
└─ 推送支持: ✅

✅ Service Worker 注册成功: https://your-domain.com/
```

---

## 🐛 常见问题排查

### 问题 1: Service Worker 注册失败

**症状：**
```
❌ Service Worker 注册失败: SecurityError
```

**原因：** Mixed Content（混合内容）

**解决：**
```nginx
# 确保所有请求都通过 HTTPS
proxy_set_header X-Forwarded-Proto $scheme;
```

### 问题 2: manifest.json 404

**症状：** 控制台显示 `Failed to load manifest`

**检查：**
```bash
# 确认文件存在
ls -la static/manifest.json

# 检查 Nginx 错误日志
sudo tail -f /var/log/nginx/aw98tang_error.log
```

**解决：** 确保 manifest.json 路由配置正确。

### 问题 3: 图标不显示

**症状：** 安装后应用图标是空白或默认图标

**检查：**
```bash
# 确认图标文件存在
ls -la static/icons/

# 应该看到：
# icon-72x72.png
# icon-96x96.png
# icon-192x192.png
# icon-512x512.png
```

**解决：**
```nginx
# 确保图标路径配置正确
location ~* ^/static/icons/.*\.(png|jpg|jpeg|ico)$ {
    proxy_pass http://127.0.0.1:5000;
    # ...
}
```

### 问题 4: Service Worker 更新不及时

**症状：** 修改 sw.js 后浏览器仍使用旧版本

**解决：**
```nginx
# 确保 sw.js 完全禁用缓存
location = /static/sw.js {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
    add_header Pragma "no-cache";
    add_header Expires "0";
}
```

手动清除：
1. Chrome: `chrome://serviceworker-internals/`
2. 找到你的站点 → 点击 **Unregister**
3. 刷新页面

---

## 🚀 性能优化

### 1. 启用 Gzip 压缩

```nginx
http {
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript 
               application/x-javascript application/xml+rss 
               application/json application/javascript 
               application/manifest+json;
}
```

### 2. 启用 HTTP/2

```nginx
listen 443 ssl http2;
```

### 3. 配置浏览器缓存

```nginx
# 静态资源强缓存
add_header Cache-Control "public, max-age=31536000, immutable";

# API 不缓存
add_header Cache-Control "no-cache, no-store, must-revalidate";
```

---

## 📊 监控和日志

### 查看访问日志

```bash
sudo tail -f /var/log/nginx/aw98tang_access.log
```

### 查看错误日志

```bash
sudo tail -f /var/log/nginx/aw98tang_error.log
```

### 检查 Service Worker 状态

浏览器访问：
- Chrome: `chrome://serviceworker-internals/`
- Firefox: `about:debugging#/runtime/this-firefox`
- Edge: `edge://serviceworker-internals/`

---

## 🔒 安全加固

### 1. 限制请求速率

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}

server {
    location /api/ {
        limit_req zone=api burst=20;
    }
}
```

### 2. 禁止特定路径访问

```nginx
location ~* ^/(config\.json|\.env|\.git) {
    deny all;
    return 404;
}
```

### 3. 添加安全头部

```nginx
add_header X-XSS-Protection "1; mode=block";
add_header X-Content-Type-Options "nosniff";
add_header Referrer-Policy "strict-origin-when-cross-origin";
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()";
```

---

## ✅ 配置检查清单

- [ ] HTTPS 证书配置正确
- [ ] HTTP 自动重定向到 HTTPS
- [ ] `/static/sw.js` 可访问且禁用缓存
- [ ] `/static/manifest.json` 可访问
- [ ] `/static/icons/` 下所有图标可访问
- [ ] `/offline.html` 可访问
- [ ] 控制台显示 Service Worker 注册成功
- [ ] 浏览器显示"安装应用"提示
- [ ] 从主屏幕/桌面启动是独立窗口

---

## 🎯 完整测试

```bash
# 1. 测试 HTTPS 访问
curl -I https://your-domain.com

# 2. 测试 Service Worker
curl -I https://your-domain.com/static/sw.js

# 3. 测试 Manifest
curl https://your-domain.com/static/manifest.json

# 4. 测试图标
curl -I https://your-domain.com/static/icons/icon-192x192.png
```

所有请求都应该返回 `200 OK`。

---

## 📞 需要帮助？

如果配置后仍有问题，请检查：

1. Nginx 错误日志
2. Flask 应用日志
3. 浏览器控制台错误
4. Service Worker 注册状态

提供具体的错误信息以便排查问题。

