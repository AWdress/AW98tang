# Git 认证问题解决指南

## 问题描述

容器启动时遇到以下错误：
```
❌ 获取远程更新失败！
错误信息: remote: Invalid username or token. Password authentication is not supported for Git operations.
fatal: Authentication failed for 'https://github.com/AWdress/AW98tamg.git/'
```

## 原因分析

1. **仓库可能是私有的** - 需要身份认证
2. **未提供 GitHub Token** - Docker 容器无法访问私有仓库
3. **GitHub Token 无效或过期** - 需要更新 Token

## 解决方案

### 方案1：跳过自动更新（推荐）⭐

如果你不需要自动更新功能，直接跳过 Git 操作：

**修改 `docker-compose.yml`：**
```yaml
environment:
  - SKIP_GIT=true  # 添加这一行
```

或者删除/注释掉 `AUTO_UPDATE` 配置：
```yaml
environment:
  # - AUTO_UPDATE=true  # 注释掉这一行
```

**重启容器：**
```bash
docker-compose down
docker-compose up -d
```

### 方案2：使用 GitHub Token

如果你需要自动更新功能，需要配置 GitHub Token。

#### 步骤1：创建 GitHub Token

1. 访问 GitHub：https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 设置 Token 名称（如：AW98tang-docker）
4. 勾选权限：
   - ✅ `repo` (完整仓库访问权限)
5. 点击 "Generate token"
6. **复制生成的 Token**（只显示一次！）

#### 步骤2：配置 Token

**方法A：使用环境变量文件（推荐）**

创建 `.env` 文件：
```env
GITHUB_TOKEN=ghp_your_token_here_xxxxxxxxxxxx
AUTO_UPDATE=true
```

**方法B：直接写在 docker-compose.yml**
```yaml
environment:
  - AUTO_UPDATE=true
  - GITHUB_TOKEN=ghp_your_token_here_xxxxxxxxxxxx
```

**重启容器：**
```bash
docker-compose down
docker-compose up -d
```

### 方案3：公开仓库访问

如果仓库是公开的，但仍然出现认证错误：

1. 检查网络连接
2. 检查 GitHub 服务状态
3. 尝试手动拉取测试：
   ```bash
   docker-compose exec AW98tang git fetch origin main
   ```

## 配置说明

### docker-compose.yml 中的相关配置

```yaml
environment:
  # 自动更新开关
  - AUTO_UPDATE=true          # true=启用自动更新, false=禁用（默认）
  
  # GitHub Token（私有仓库必需）
  - GITHUB_TOKEN=ghp_xxx      # 你的GitHub Token
  
  # 跳过 Git 操作（优先级最高）
  - SKIP_GIT=true             # true=跳过所有Git操作
```

### 配置优先级

1. `SKIP_GIT=true` - 最高优先级，直接跳过所有 Git 操作
2. `AUTO_UPDATE=false` - 禁用自动更新
3. `AUTO_UPDATE=true` + `GITHUB_TOKEN` - 启用自动更新并认证

## 验证配置

### 查看容器日志

```bash
docker-compose logs -f AW98tang
```

**成功的日志输出：**
```
🔄 检查代码更新...
📦 检测到 Git 仓库
🔑 配置 GitHub Token 认证...
✅ GitHub Token 配置成功
📌 当前版本: d7f2907b
⬇️ 正在从远程仓库同步代码...
✅ 远程更新获取成功
✅ 代码已是最新版本
```

**跳过更新的日志输出：**
```
ℹ️ SKIP_GIT=true，跳过所有 Git 操作
ℹ️ 自动更新已禁用
```

## 安全提示

### ⚠️ Token 安全

1. **不要将 Token 提交到 Git 仓库**
   - 使用 `.env` 文件（已在 `.gitignore` 中）
   - 或使用环境变量

2. **Token 权限最小化**
   - 只授予必要的 `repo` 权限
   - 不要授予 `delete_repo` 等危险权限

3. **定期更新 Token**
   - 建议每3-6个月更换一次
   - 如果 Token 泄露，立即在 GitHub 删除

### 🔒 .env 文件示例

```env
# Web 控制面板登录
WEB_USERNAME=admin
WEB_PASSWORD=your_secure_password

# GitHub 自动更新
AUTO_UPDATE=true
GITHUB_TOKEN=ghp_your_token_here

# 或者跳过自动更新
# SKIP_GIT=true
```

## 常见问题

### Q1: Token 无效？
**A:** 检查 Token 是否：
- 已过期
- 有 `repo` 权限
- 格式正确（ghp_开头）

### Q2: 仍然提示认证失败？
**A:** 尝试：
```bash
# 停止容器
docker-compose down

# 删除容器和镜像
docker-compose down --volumes

# 重新构建
docker-compose up -d --build
```

### Q3: 不想自动更新？
**A:** 最简单的方法：
```yaml
environment:
  - SKIP_GIT=true
```

### Q4: 如何手动更新？
**A:** 进入容器执行：
```bash
docker-compose exec AW98tang git pull origin main
docker-compose restart
```

## 推荐配置

### 场景1：不需要自动更新（推荐）
```yaml
environment:
  - SKIP_GIT=true
  # 或者不配置 AUTO_UPDATE
```

### 场景2：需要自动更新（私有仓库）
```yaml
environment:
  - AUTO_UPDATE=true
  - GITHUB_TOKEN=ghp_your_token
```

### 场景3：需要自动更新（公开仓库）
```yaml
environment:
  - AUTO_UPDATE=true
  # 不需要 GITHUB_TOKEN
```

## 总结

- 🎯 **最简单**: 设置 `SKIP_GIT=true`，跳过自动更新
- 🔐 **最安全**: 使用 `.env` 文件存储 `GITHUB_TOKEN`
- 🚀 **最灵活**: 根据需要选择是否启用自动更新

如有其他问题，请查看容器日志：
```bash
docker-compose logs -f AW98tang
```

