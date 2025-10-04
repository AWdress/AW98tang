# Git 配置指南

## 📖 概述

AW98tang 项目已升级为灵活的 Git 配置系统，与 AWLottery 项目保持一致。你现在可以通过环境变量轻松配置仓库地址、分支和认证信息。

---

## 🎯 新增环境变量

### 1. `GIT_REMOTE` - 仓库地址

**作用**: 指定要同步的 Git 仓库地址

**默认值**: `https://github.com/AWdress/AW98tamg.git`

**使用场景**:
- Fork 了项目，想从自己的仓库同步
- 使用镜像仓库
- 切换到其他仓库

**示例**:
```yaml
environment:
  - GIT_REMOTE=https://github.com/yourname/your-repo.git
```

---

### 2. `GIT_BRANCH` - 分支名称

**作用**: 指定要同步的分支

**默认值**: `main`

**使用场景**:
- 使用开发分支 (dev)
- 测试新功能
- 使用特定版本分支

**示例**:
```yaml
environment:
  - GIT_BRANCH=dev
```

---

### 3. `GITHUB_TOKEN` - 认证令牌

**作用**: 访问私有仓库或提高请求限制

**格式**: `ghp_` 开头的 Classic Token (推荐)

**权限要求**: 
- ✅ `repo` (完整勾选)

**示例**:
```yaml
environment:
  - GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

---

### 4. `SKIP_GIT` - 跳过 Git 操作

**作用**: 完全跳过所有 Git 同步操作

**默认值**: `false`

**使用场景**:
- 不需要自动更新
- Git 认证问题无法解决
- 使用自己的代码版本

**示例**:
```yaml
environment:
  - SKIP_GIT=true
```

---

## 🚀 使用场景示例

### 场景1: 默认配置（推荐新手）

```yaml
# docker-compose.yml
environment:
  - SKIP_GIT=true  # 不自动更新，保持稳定
```

**说明**: 最简单最稳定，不会因为代码更新导致问题。

---

### 场景2: 自动更新（公开仓库）

```yaml
# docker-compose.yml
environment:
  # 不设置任何 Git 相关变量
  # 容器启动时自动从 GitHub 拉取最新代码
```

**说明**: 适合想要始终使用最新版本的用户。

---

### 场景3: 私有仓库更新

```yaml
# docker-compose.yml
environment:
  - GITHUB_TOKEN=ghp_your_token_here
  - GIT_REMOTE=https://github.com/yourname/private-repo.git
  - GIT_BRANCH=main
```

**说明**: 适合 Fork 后使用自己私有仓库的用户。

---

### 场景4: 使用开发分支

```yaml
# docker-compose.yml
environment:
  - GIT_BRANCH=dev
  - GITHUB_TOKEN=ghp_your_token_here  # 如果是私有仓库
```

**说明**: 想要测试最新开发功能。

---

### 场景5: 多个项目部署

**项目1 (AW98tang):**
```yaml
services:
  AW98tang:
    environment:
      - GIT_REMOTE=https://github.com/AWdress/AW98tamg.git
      - GIT_BRANCH=main
      - GITHUB_TOKEN=${GITHUB_TOKEN}
```

**项目2 (AWLottery):**
```yaml
services:
  AWLottery:
    environment:
      - GIT_REMOTE=https://github.com/AWdress/AWLottery.git
      - GIT_BRANCH=dev
      - GITHUB_TOKEN=${GITHUB_TOKEN}
```

**说明**: 使用 `.env` 文件统一管理 Token，不同项目配置不同仓库。

---

## 🔐 Token 格式说明

### ✅ 推荐格式（更简洁）

```bash
https://${GITHUB_TOKEN}@github.com/AWdress/AW98tamg.git
```

**优势**:
- 格式简洁
- 与 AWLottery 保持一致
- 更易维护

### ⚠️ 旧格式（仍然支持）

```bash
https://x-access-token:${GITHUB_TOKEN}@github.com/AWdress/AW98tamg.git
```

**说明**: 如果你已经在使用旧格式，不需要修改，新版本会自动处理。

---

## 📋 环境变量优先级

1. **SKIP_GIT=true** - 最高优先级，直接跳过所有 Git 操作
2. **GIT_REMOTE** - 自定义仓库地址（覆盖默认值）
3. **GIT_BRANCH** - 自定义分支（覆盖默认值）
4. **GITHUB_TOKEN** - 提供认证（自动添加到 GIT_REMOTE）

---

## 🛠️ 调试信息

容器启动时会输出以下调试信息：

```bash
[Debug] 当前目录: /app
[Debug] GIT_REMOTE=https://github.com/AWdress/AW98tamg.git
[Debug] GIT_BRANCH=main
[Debug] SKIP_GIT=false
[Debug] GITHUB_TOKEN=已设置
```

根据这些信息可以判断配置是否生效。

---

## ❓ 常见问题

### Q1: 如何彻底禁用 Git 更新？

```yaml
environment:
  - SKIP_GIT=true
```

### Q2: 如何切换到开发分支？

```yaml
environment:
  - GIT_BRANCH=dev
```

### Q3: Token 认证失败怎么办？

1. 检查 Token 格式是否正确（`ghp_` 开头）
2. 检查 Token 权限（必须有 `repo` 权限）
3. 检查 Token 是否过期
4. 最后的方案：设置 `SKIP_GIT=true`

### Q4: 如何使用自己 Fork 的仓库？

```yaml
environment:
  - GIT_REMOTE=https://github.com/yourname/your-fork.git
  - GITHUB_TOKEN=ghp_your_token
```

### Q5: 能否同时运行多个项目？

可以！使用不同的环境变量配置：

```yaml
# docker-compose.yml
services:
  project1:
    environment:
      - GIT_REMOTE=https://github.com/user/project1.git
  
  project2:
    environment:
      - GIT_REMOTE=https://github.com/user/project2.git
```

---

## 🎓 最佳实践

### 1. 生产环境

```yaml
environment:
  - SKIP_GIT=true  # 稳定优先
```

### 2. 开发环境

```yaml
environment:
  - GIT_BRANCH=dev
  - GITHUB_TOKEN=${GITHUB_TOKEN}  # 使用 .env 文件
```

### 3. 使用 .env 文件

**创建 `.env` 文件:**
```env
GITHUB_TOKEN=ghp_your_token_here
WEB_USERNAME=admin
WEB_PASSWORD=your_secure_password
```

**在 docker-compose.yml 中引用:**
```yaml
environment:
  - GITHUB_TOKEN=${GITHUB_TOKEN}
  - WEB_USERNAME=${WEB_USERNAME}
  - WEB_PASSWORD=${WEB_PASSWORD}
```

---

## 📚 相关文档

- [GitHub Token 创建指南](./GITHUB_TOKEN_SOLUTION.md)
- [Git 认证问题排查](./GIT_AUTH_GUIDE.md)
- [Docker 部署指南](../README_DOCKER.md)

---

## 🆚 与旧版本的区别

| 特性 | 旧版本 | 新版本 (AWLottery风格) |
|------|--------|----------------------|
| 仓库地址 | 硬编码 | 环境变量 `GIT_REMOTE` ✅ |
| 分支 | 固定 `main` | 环境变量 `GIT_BRANCH` ✅ |
| Token格式 | `x-access-token:TOKEN` | `TOKEN@` 简洁格式 ✅ |
| 错误处理 | 基础 | 增强（私有仓库检测）✅ |
| 仓库检测 | 无 | 自动检测并修正 ✅ |
| 灵活性 | 低 | 高 ✅ |

---

## 🎉 总结

新版本的 Git 配置系统让你可以：

✅ 灵活切换仓库和分支  
✅ 简化 Token 配置  
✅ 更好的错误提示  
✅ 与 AWLottery 保持一致  
✅ 支持多项目部署  

推荐配置：**SKIP_GIT=true**（稳定优先）🌟

