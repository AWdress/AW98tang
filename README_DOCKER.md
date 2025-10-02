# 🐳 Docker部署指南 - 色花堂智能助手 Pro

## 快速开始

### 1. 前置要求
- 安装 Docker Desktop (Windows/Mac)
- 或安装 Docker Engine (Linux)

### 2. 启动服务

#### Windows用户（最简单）
```bash
# 双击运行 docker-start.bat
# 选择 1 - 启动服务
```

#### Linux/Mac用户
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down
```

### 3. 配置登录账号（可选）

#### 方式1：使用默认账号
直接访问，默认账号：`admin / admin123`

#### 方式2：自定义账号
创建 `.env` 文件：
```bash
# 复制示例文件
cp env.example .env

# 编辑 .env 文件
WEB_USERNAME=your_username
WEB_PASSWORD=your_password
SECRET_KEY=your-secret-key
```

### 4. 访问控制面板
```
http://localhost:5000
```

使用您配置的账号登录

## 📋 服务架构

### AW98tang（一体化服务）
- **容器名称**: AW98tang
- **端口**: 5000
- **功能**:
  - ✅ Web控制面板
  - ✅ 定时任务调度器（内置）
  - ✅ 实时日志查看
  - ✅ 在线配置管理
- **自动重启**: 是
- **内存限制**: 1GB

## 🎯 **内置定时任务**

定时任务已集成到Web服务中，无需单独容器！

- ✅ 和Web服务同时运行
- ✅ 在后台线程中调度
- ✅ 不影响Web控制面板使用
- ✅ 可随时启动/停止机器人

## 🔧 常用命令

### 启动服务
```bash
# 启动服务（Web + 定时任务一体化）
docker-compose up -d

# 前台运行（查看日志）
docker-compose up
```

### 停止服务
```bash
# 停止服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

### 查看日志
```bash
# 实时日志
docker-compose logs -f

# 最近100行
docker-compose logs --tail=100
```

### 重启服务
```bash
# 重启服务
docker-compose restart
```

### 更新镜像
```bash
# 重新构建
docker-compose build

# 重新构建并启动
docker-compose up -d --build
```

## 📂 数据持久化

以下目录会挂载到宿主机：

```
./config.json  →  /app/config.json（配置文件）
./logs/        →  /app/logs/（日志目录）
./debug/       →  /app/debug/（调试文件）
```

修改 `config.json` 后需要重启容器：
```bash
docker-compose restart
```

## 🎯 使用场景

### 场景1：日常使用
```bash
# 启动Web控制面板
docker-compose up -d sehuatang-web

# 访问 http://localhost:5000
# 在Web界面中启动/停止机器人
```

### 场景2：定时任务
```bash
# 1. 修改 config.json
#    "enable_scheduler": true
#    "schedule_time": "03:00"

# 2. 启动定时任务服务
docker-compose --profile scheduler up -d

# 机器人会在每天3点自动运行
```

### 场景3：测试模式
```bash
# 1. 修改 config.json
#    "enable_test_mode": true
#    或 "enable_test_checkin": true
#    或 "enable_test_reply": true

# 2. 在Web界面启动机器人
# 会执行测试但不实际提交
```

## 🔍 故障排除

### 容器无法启动
```bash
# 查看容器日志
docker-compose logs sehuatang-web

# 检查容器状态
docker-compose ps
```

### 无法访问Web界面
```bash
# 检查端口是否被占用
netstat -ano | findstr :5000

# 重启容器
docker-compose restart sehuatang-web
```

### Chrome无法启动
Docker版本已配置无头模式，如果仍有问题：
```bash
# 进入容器检查
docker exec -it sehuatang-web bash
google-chrome --version
```

## 🚀 性能优化

### 限制资源使用
编辑 `docker-compose.yml`：
```yaml
services:
  sehuatang-web:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
```

### 使用国内镜像加速
```bash
# 配置Docker镜像源
# Windows: Docker Desktop → Settings → Docker Engine
# 添加：
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn"
  ]
}
```

## 📊 监控和维护

### 查看资源使用
```bash
docker stats sehuatang-web
```

### 清理日志
```bash
# 清理超过7天的日志
find ./logs -name "*.log" -mtime +7 -delete
```

### 备份配置
```bash
# 备份配置文件
cp config.json config.json.backup
```

## 🔐 安全建议

1. **修改默认密码**
   - 编辑 `web_app.py` 中的 `TEST_USERS`
   - 或添加环境变量

2. **限制访问**
   - 使用反向代理（Nginx）
   - 配置防火墙规则

3. **HTTPS访问**
   - 使用 Nginx + Let's Encrypt
   - 或 Caddy 自动HTTPS

## 📝 完整示例

### docker-compose.yml 完整配置
```yaml
version: '3.8'

services:
  sehuatang-web:
    build: .
    container_name: sehuatang-web
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./config.json:/app/config.json
      - ./logs:/app/logs
      - ./debug:/app/debug
    environment:
      - PYTHONUNBUFFERED=1
      - TZ=Asia/Shanghai
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

---

**版本**: v3.0 Docker
**更新时间**: 2025-10-03

