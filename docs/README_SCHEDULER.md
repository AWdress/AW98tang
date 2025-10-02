# ⏰ 定时任务使用指南

## 功能说明

定时任务功能可以让机器人每天在指定时间自动运行，无需手动启动。

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置定时时间

#### 方式1：Web界面（推荐）
1. 访问 http://localhost:5000
2. 登录控制面板
3. 点击 "⚙️ 配置设置"
4. 找到 "⏰ 启用定时任务" 设置为 "是"
5. 设置 "⏰ 定时运行时间"（如：03:00 = 凌晨3点）
6. 点击 "💾 保存配置"

#### 方式2：配置文件
编辑 `config.json`：
```json
{
  "enable_scheduler": true,
  "schedule_time": "03:00",
  ...
}
```

### 3. 启动定时任务调度器

**Windows用户：**
双击运行 `start_scheduler.bat`

**Linux/Mac用户：**
```bash
python scheduler.py
```

## 📋 执行流程

```
定时任务启动
    ↓
等待到设定时间（如凌晨3点）
    ↓
自动启动机器人
    ↓
1. 登录论坛
2. 执行自动回复
3. 完成回复后签到
    ↓
任务完成
    ↓
等待下一天的定时时间
```

## ⚙️ 配置说明

### enable_scheduler
- `true`: 启用定时任务
- `false`: 禁用定时任务

### schedule_time
- 格式：`"HH:MM"`（24小时制）
- 示例：
  - `"03:00"` - 凌晨3点
  - `"14:30"` - 下午2点30分
  - `"23:00"` - 晚上11点

## 🔄 执行顺序（论坛规则）

**重要：论坛要求先回复后才能签到**

正确顺序：
1. ✅ 先执行自动回复（至少1条）
2. ✅ 回复成功后再签到

如果没有回复成功，签到会被跳过。

## 💡 使用建议

### 推荐时间设置
- **凌晨3:00-5:00** - 服务器压力小，不易被检测
- **中午12:00-14:00** - 活跃时段，更像真人
- **晚上21:00-23:00** - 高峰期，容易混在人群中

### 保守型（推荐）
```json
{
  "enable_scheduler": true,
  "schedule_time": "03:00",
  "max_replies_per_day": 3,
  "reply_interval": [3600, 7200]
}
```
- 凌晨3点运行
- 每天回复3个帖子
- 间隔1-2小时

### 积极型
```json
{
  "enable_scheduler": true,
  "schedule_time": "14:00",
  "max_replies_per_day": 10,
  "reply_interval": [600, 1200]
}
```
- 下午2点运行
- 每天回复10个帖子
- 间隔10-20分钟

## 🖥️ 后台运行

### Windows
使用任务计划程序：
1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每天
4. 操作：启动程序 → `python scheduler.py`
5. 设置为开机自动启动

### Linux
使用 cron：
```bash
crontab -e
# 添加：
0 3 * * * cd /path/to/98 && python3 scheduler.py
```

### Docker
使用 docker-compose：
```yaml
services:
  scheduler:
    build: .
    command: python scheduler.py
    restart: always
```

## 📊 日志查看

定时任务日志保存在 `scheduler.log`：
```bash
# 实时查看日志
tail -f scheduler.log

# Windows
Get-Content scheduler.log -Wait
```

## 🛑 停止定时任务

- 在运行窗口按 `Ctrl+C`
- 或者关闭终端窗口
- 任务计划程序中禁用任务

## ⚠️ 注意事项

1. **保持调度器运行**
   - 定时任务需要 scheduler.py 持续运行
   - 建议设置为开机自动启动

2. **时间设置**
   - 使用24小时制
   - 建议避开高峰期（论坛维护时间）

3. **资源占用**
   - 调度器本身几乎不占资源
   - 只在执行任务时启动浏览器

4. **执行顺序**
   - 必须先回复才能签到（论坛规则）
   - 如果回复失败，签到会被跳过

## 🔧 故障排除

### Q: 定时任务没有执行
A: 检查 scheduler.py 是否在运行，查看 scheduler.log

### Q: 时间设置不生效
A: 确保格式正确（HH:MM），重启 scheduler.py

### Q: 签到失败
A: 确保至少成功回复了1个帖子，否则无法签到

---

**祝您使用愉快！** 🚀



