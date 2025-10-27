# Cron 表达式调度指南

## 📋 概述

v3.7 版本新增了 **Cron 表达式调度**功能，让定时任务配置更加灵活强大。

## ✨ 新功能

### 1. 支持标准 Cron 表达式

使用标准的 5 字段 Cron 表达式：

```
分钟 小时 日 月 星期
 *   *   *  *  *
```

### 2. 三种调度模式

| 模式 | 配置参数 | 优先级 | 说明 |
|------|---------|--------|------|
| **Cron 表达式** | `schedule_cron` | ⭐⭐⭐ 最高 | 最灵活，支持复杂调度 |
| **固定时间点** | `schedule_times` | ⭐⭐ 中 | 简单易用，适合固定时间 |
| **单一时间** | `schedule_time` | ⭐ 低 | 兼容旧版，仅单个时间 |

## 🚀 快速开始

### 方式 1: 使用 Cron 表达式（推荐）

编辑 `config.json`：

```json
{
  "enable_scheduler": true,
  "schedule_cron": "0 3,9,15,21 * * *"
}
```

这表示：每天的 3点、9点、15点、21点 运行

### 方式 2: 使用固定时间点

```json
{
  "enable_scheduler": true,
  "schedule_times": ["03:00", "09:00", "15:00", "21:00"]
}
```

### 方式 3: 使用单一时间（旧版兼容）

```json
{
  "enable_scheduler": true,
  "schedule_time": "03:00"
}
```

## 📚 Cron 表达式语法

### 基本格式

```
┌───────────── 分钟 (0 - 59)
│ ┌───────────── 小时 (0 - 23)
│ │ ┌───────────── 日 (1 - 31)
│ │ │ ┌───────────── 月 (1 - 12)
│ │ │ │ ┌───────────── 星期 (0 - 6) (0=周日)
│ │ │ │ │
* * * * *
```

### 特殊字符

| 字符 | 说明 | 示例 |
|------|------|------|
| `*` | 任何值 | `* * * * *` = 每分钟 |
| `,` | 列举多个值 | `0 3,9,15,21 * * *` = 每天3,9,15,21点 |
| `-` | 范围 | `0 9-17 * * *` = 每天9-17点 |
| `/` | 间隔 | `*/30 * * * *` = 每30分钟 |

## 💡 常用示例

### 每天固定时间

```json
{
  "schedule_cron": "0 3 * * *",
  "说明": "每天凌晨3点"
}
```

```json
{
  "schedule_cron": "0 3,9,15,21 * * *",
  "说明": "每天3点、9点、15点、21点"
}
```

### 每隔N小时

```json
{
  "schedule_cron": "0 */6 * * *",
  "说明": "每6小时（0点、6点、12点、18点）"
}
```

```json
{
  "schedule_cron": "0 */4 * * *",
  "说明": "每4小时"
}
```

### 每隔N分钟

```json
{
  "schedule_cron": "*/30 * * * *",
  "说明": "每30分钟"
}
```

```json
{
  "schedule_cron": "0,30 * * * *",
  "说明": "每小时的0分和30分"
}
```

### 工作日/周末

```json
{
  "schedule_cron": "0 9 * * 1-5",
  "说明": "工作日（周一到周五）早上9点"
}
```

```json
{
  "schedule_cron": "0 10 * * 0,6",
  "说明": "周末（周六、周日）早上10点"
}
```

### 特定日期

```json
{
  "schedule_cron": "0 3 1 * *",
  "说明": "每月1号凌晨3点"
}
```

```json
{
  "schedule_cron": "0 3 1,15 * *",
  "说明": "每月1号和15号凌晨3点"
}
```

## 🎯 推荐配置

### 高成功率配置（推荐）

```json
{
  "enable_scheduler": true,
  "schedule_cron": "0 3,9,15,21 * * *"
}
```

**说明**：每天4个时间点，配合自动重试，成功率 >99%

### 低频率配置

```json
{
  "enable_scheduler": true,
  "schedule_cron": "0 3 * * *"
}
```

**说明**：每天只运行一次，适合网络稳定环境

### 高频率配置

```json
{
  "enable_scheduler": true,
  "schedule_cron": "0 */2 * * *"
}
```

**说明**：每2小时运行一次，适合网络不稳定环境

### 工作时间配置

```json
{
  "enable_scheduler": true,
  "schedule_cron": "0 9,12,15,18 * * 1-5"
}
```

**说明**：工作日的9点、12点、15点、18点运行

## 🔍 验证 Cron 表达式

### 方法 1: 在线验证

访问：https://crontab.guru/

输入你的 cron 表达式，查看执行时间

### 方法 2: Python 验证

```bash
python -c "from croniter import croniter; from datetime import datetime; cron = croniter('你的cron表达式', datetime.now()); print('下次运行:', cron.get_next(datetime))"
```

### 方法 3: 启动调度器查看

```bash
python scheduler.py
```

启动后会显示：
```
📅 调度模式: Cron表达式
⏰ Cron: 0 3,9,15,21 * * *
⏰ 下次运行: 2025-10-27 15:00:00
```

## ⚙️ 配置优先级

系统按以下顺序检查配置：

1. **`schedule_cron`** - 如果存在且有效，使用 Cron 模式
2. **`schedule_times`** - 如果 cron 为空，使用时间点模式
3. **`schedule_time`** - 如果以上都没有，使用单时间模式
4. **默认值** - 使用 `['03:00', '09:00', '15:00', '21:00']`

## 🐛 故障排查

### 问题 1: Cron 表达式无效

**错误信息**：
```
❌ Cron表达式无效: 0 3 * *
将使用时间点模式...
```

**原因**：Cron 表达式必须是 5 个字段

**解决**：
```json
{
  "schedule_cron": "0 3 * * *"
}
```

### 问题 2: 模块未安装

**错误信息**：
```
ModuleNotFoundError: No module named 'croniter'
```

**解决**：
```bash
pip install croniter
# 或
pip install -r requirements.txt
```

### 问题 3: 时间不准确

**检查事项**：
- 系统时区是否正确
- Docker 容器时区设置
- Cron 表达式是否正确

**Docker 时区设置**：
```yaml
# docker-compose.yml
environment:
  - TZ=Asia/Shanghai
```

## 📊 性能建议

### 1. 合理设置频率

| 频率 | Cron 表达式 | CPU占用 | 适用场景 |
|------|------------|---------|---------|
| 每天1次 | `0 3 * * *` | 极低 | 网络稳定 |
| 每天4次 | `0 3,9,15,21 * * *` | 低 | **推荐** |
| 每6小时 | `0 */6 * * *` | 中 | 高可靠性要求 |
| 每小时 | `0 * * * *` | 高 | 不推荐 |

### 2. 避免高峰期

建议避开：
- 0点（数据库备份）
- 12点（午休高峰）
- 18点（下班高峰）

推荐时段：
- 凌晨 3点（最稳定）
- 上午 9点
- 下午 3点
- 晚上 21点

### 3. 配合智能跳过

系统会自动检测签到状态，已签到会跳过后续运行，无需担心运行次数过多。

## 🎓 高级用法

### 1. 复合条件

```json
{
  "schedule_cron": "0 3,9,15,21 * * 1-5",
  "说明": "工作日的3,9,15,21点"
}
```

### 2. 特定月份

```json
{
  "schedule_cron": "0 3 * 1,7 *",
  "说明": "每年1月和7月的每天3点"
}
```

### 3. 组合间隔

```json
{
  "schedule_cron": "0 */2 * * *",
  "说明": "每2小时"
}
```

```json
{
  "schedule_cron": "*/15 * * * *",
  "说明": "每15分钟"
}
```

## 📝 配置模板

### 模板 1: 标准配置

```json
{
  "enable_scheduler": true,
  "schedule_cron": "0 3,9,15,21 * * *",
  "max_replies_per_day": 30,
  "enable_daily_checkin": true,
  "enable_auto_reply": true
}
```

### 模板 2: 低频配置

```json
{
  "enable_scheduler": true,
  "schedule_cron": "0 3 * * *",
  "max_replies_per_day": 10,
  "enable_daily_checkin": true,
  "enable_auto_reply": true
}
```

### 模板 3: 高频配置

```json
{
  "enable_scheduler": true,
  "schedule_cron": "0 */3 * * *",
  "max_replies_per_day": 50,
  "enable_daily_checkin": true,
  "enable_auto_reply": true
}
```

## 🔄 迁移指南

### 从固定时间点迁移到 Cron

**旧配置**：
```json
{
  "schedule_times": ["03:00", "09:00", "15:00", "21:00"]
}
```

**新配置**：
```json
{
  "schedule_cron": "0 3,9,15,21 * * *"
}
```

### 从单一时间迁移到 Cron

**旧配置**：
```json
{
  "schedule_time": "03:00"
}
```

**新配置**：
```json
{
  "schedule_cron": "0 3 * * *"
}
```

## 📞 技术支持

### 参考资料

- [Crontab Guru](https://crontab.guru/) - 在线 Cron 表达式验证
- [Croniter 文档](https://github.com/kiorky/croniter) - Python Cron 库
- [Wikipedia: Cron](https://en.wikipedia.org/wiki/Cron) - Cron 详细说明

### 问题反馈

如遇到问题，请提供：
1. 配置文件（隐藏敏感信息）
2. 错误日志
3. Cron 表达式

---

**最后更新**: 2025-10-27  
**版本**: v3.7.0  
**功能**: Cron 表达式调度

