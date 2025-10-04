# 🌐 代理配置指南

## 📖 功能说明

本系统支持完整的代理配置功能，可以通过 **Web 界面** 直接配置，无需修改 Docker 配置或重新构建镜像。

### ✨ 特性

- ✅ Web界面可视化配置
- ✅ 支持 HTTP/HTTPS 代理
- ✅ 支持 SOCKS5 代理
- ✅ 独立控制 Git 和 Selenium 的代理
- ✅ 配置即时生效（重启容器后）
- ✅ 解决 GitHub 访问问题

---

## 🎯 解决的问题

### 问题现象
```
fatal: unable to access 'https://github.com/...': 
GnuTLS recv error (-110): The TLS connection was non-properly terminated
```

### 问题原因
- 需要通过代理访问 GitHub
- Git 操作未配置代理
- TLS 连接被中断

### 解决方案
✅ 通过 Web 界面配置代理，自动应用到 Git 操作

---

## 📝 配置步骤

### 方法 1: 通过 Web 界面配置（推荐）⭐⭐⭐⭐⭐

#### 步骤 1: 访问 Web 界面
```
http://你的IP:15000
```

登录账号：
- 用户名：`Awhitedress`
- 密码：`qw5561255`

#### 步骤 2: 进入系统配置
1. 点击左侧菜单 **⚙️ 系统配置**
2. 找到 **🌐 网络代理配置** 区域

#### 步骤 3: 填写代理信息
```
启用代理：            是
HTTP 代理地址：       http://192.168.50.113:7890
HTTPS 代理地址：      http://192.168.50.113:7890
不使用代理的地址：     localhost,127.0.0.1
Git 更新使用代理：     是（推荐）✅
Selenium 使用代理：    否（推荐）❌
```

#### 步骤 4: 保存并重启
1. 点击 **💾 保存配置**
2. 重启容器：
```bash
docker restart AW98tang
```

---

### 方法 2: 直接修改 config.json

如果你偏好手动编辑配置文件：

```json
{
  ...其他配置...
  "proxy": {
    "enabled": true,
    "http_proxy": "http://192.168.50.113:7890",
    "https_proxy": "http://192.168.50.113:7890",
    "no_proxy": "localhost,127.0.0.1",
    "use_for_git": true,
    "use_for_selenium": false
  }
}
```

保存后重启容器：
```bash
docker restart AW98tang
```

---

## 🔧 代理格式说明

### HTTP 代理
```
http://代理IP:端口
示例: http://192.168.1.100:7890
```

### HTTPS 代理
```
http://代理IP:端口 或 https://代理IP:端口
示例: http://192.168.1.100:7890
```

### SOCKS5 代理
```
socks5://代理IP:端口
示例: socks5://127.0.0.1:1080
```

### 带认证的代理
```
http://用户名:密码@代理IP:端口
示例: http://user:pass@192.168.1.100:7890
```

---

## 🎯 使用场景

### 场景 1: GitHub 需要代理访问（最常见）✅

**配置：**
```
启用代理：            是
HTTP 代理地址：       http://你的代理IP:端口
HTTPS 代理地址：      http://你的代理IP:端口
Git 更新使用代理：     是 ✅
Selenium 使用代理：    否 ❌
```

**说明：**
- Git 操作通过代理访问 GitHub
- 网站访问直连（不走代理）
- 适用于国内网络环境

---

### 场景 2: 全局代理

**配置：**
```
启用代理：            是
HTTP 代理地址：       http://你的代理IP:端口
HTTPS 代理地址：      http://你的代理IP:端口
Git 更新使用代理：     是 ✅
Selenium 使用代理：    是 ✅
```

**说明：**
- 所有网络请求都走代理
- 适用于需要全局代理的环境

---

### 场景 3: 不使用代理

**配置：**
```
启用代理：            否
```

**说明：**
- 所有连接直连
- 适用于无需代理的环境

---

## 🔍 验证配置

### 检查日志

启动容器后，查看日志：

```bash
docker logs AW98tang
```

成功配置代理的日志：
```
🌐 配置网络代理...
[Proxy] 从 config.json 读取代理配置...
[Proxy] ✅ 代理已启用
[Proxy] HTTP代理: http://192.168.50.113:7890
[Proxy] HTTPS代理: http://192.168.50.113:7890
[Proxy] 🔧 配置 Git 使用代理
[Proxy] Git HTTP代理已设置
[Proxy] Git HTTPS代理已设置
```

Git 更新成功的日志：
```
[Git] 尝试获取远程代码...
✅ 成功连接到远程仓库
✅ 代码更新成功
```

---

## ❌ 常见问题

### Q1: 配置代理后仍然无法连接 GitHub

**解决：**
1. 检查代理地址和端口是否正确
2. 确认代理服务正在运行
3. 检查防火墙是否允许容器访问代理
4. 查看容器日志确认代理已启用

### Q2: 代理配置不生效

**解决：**
1. 确保已点击"保存配置"
2. **重启容器**（必须！）
3. 检查 config.json 是否正确保存

### Q3: 启用 Selenium 代理后网站无法访问

**解决：**
- 如果目标网站不需要代理，设置 `Selenium 使用代理` 为 `否`
- 大多数情况下，只需要 Git 使用代理

### Q4: 代理需要认证怎么办？

**配置：**
```
HTTP 代理地址：http://用户名:密码@192.168.50.113:7890
```

---

## 🚀 快速测试

### 测试 1: 容器内测试代理

```bash
# 进入容器
docker exec -it AW98tang bash

# 测试 HTTP 代理
curl -v --proxy http://192.168.50.113:7890 https://www.google.com

# 测试 Git
git ls-remote https://github.com/AWdress/AW98tamg.git

# 退出
exit
```

### 测试 2: Web 界面测试

1. 登录 Web 界面
2. 配置代理
3. 保存配置
4. 重启容器
5. 查看"运行日志"确认代理已启用

---

## 📊 推荐配置

### 国内用户（推荐）⭐⭐⭐⭐⭐

```json
{
  "proxy": {
    "enabled": true,
    "http_proxy": "http://你的代理IP:端口",
    "https_proxy": "http://你的代理IP:端口",
    "no_proxy": "localhost,127.0.0.1",
    "use_for_git": true,      ← GitHub 需要代理
    "use_for_selenium": false ← 网站直连
  }
}
```

### 海外用户

```json
{
  "proxy": {
    "enabled": false  ← 不需要代理
  }
}
```

---

## 🎉 完成！

配置完成后：

1. ✅ GitHub 自动更新正常工作
2. ✅ 不再出现 `GnuTLS recv error` 错误
3. ✅ 可以通过 Web 界面随时调整代理配置
4. ✅ 无需修改 Docker 配置或重新构建镜像

---

## 🆘 需要帮助？

如果遇到问题：

1. 查看容器日志：`docker logs AW98tang`
2. 检查代理服务是否正常运行
3. 确认防火墙设置
4. 在 Web 界面的"运行日志"中查找错误信息

---

**更新时间：** 2024-10-04  
**适用版本：** AW98tang v2.0+


