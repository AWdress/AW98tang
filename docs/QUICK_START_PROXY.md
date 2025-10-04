# 🚀 快速开始 - 代理配置版

## 📌 问题：Git 更新失败

```
fatal: unable to access 'https://github.com/...': 
GnuTLS recv error (-110): The TLS connection was non-properly terminated
```

## ✅ 解决方案（3分钟搞定）

---

### 步骤 1: 访问 Web 界面

```
http://你的IP:15000
```

**登录信息：**
- 用户名：`Awhitedress`
- 密码：`qw5561255`

---

### 步骤 2: 配置代理

1. 点击左侧 **⚙️ 系统配置**
2. 找到 **🌐 网络代理配置**
3. 填写以下信息：

```
启用代理：          是
HTTP 代理地址：     http://192.168.50.113:7890
HTTPS 代理地址：    http://192.168.50.113:7890
Git 更新使用代理：   是 ✅
```

4. 点击 **💾 保存配置**

---

### 步骤 3: 重启容器

```bash
docker restart AW98tang
```

---

### 步骤 4: 验证

查看日志：

```bash
docker logs AW98tang
```

应该看到：

```
🌐 配置网络代理...
[Proxy] ✅ 代理已启用
[Proxy] 🔧 配置 Git 使用代理
✅ 成功连接到远程仓库
✅ 代码更新成功
```

---

## 🎉 完成！

现在 GitHub 自动更新可以正常工作了！

---

## 📝 配置文件位置

所有配置保存在：
```
/mnt/cache/docker/AW98tang/config.json
```

可以在 Web 界面随时修改，无需编辑文件！

---

## ❓ 如果还是不行？

### 检查 1: 代理是否可用

```bash
# 测试代理
curl -v --proxy http://192.168.50.113:7890 https://www.google.com
```

### 检查 2: 防火墙设置

确保容器可以访问代理服务器（192.168.50.113:7890）

### 检查 3: 配置是否保存

```bash
# 查看配置文件
cat /mnt/cache/docker/AW98tang/config.json | grep -A 8 "proxy"
```

应该看到：
```json
"proxy": {
  "enabled": true,
  "http_proxy": "http://192.168.50.113:7890",
  ...
}
```

---

## 🔄 临时禁用代理

如果需要暂时禁用代理：

1. 进入 Web 界面
2. 系统配置 → 网络代理配置
3. 设置 **启用代理** 为 **否**
4. 保存并重启容器

---

## 🆘 获取帮助

详细文档：
- 📖 `PROXY_SETUP_GUIDE.md` - 完整代理配置指南

查看日志：
- 容器日志：`docker logs -f AW98tang`
- Web 日志：登录 Web 界面 → 📋 运行日志

---

**就是这么简单！** 🎯


