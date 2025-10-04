# 论坛名称映射配置指南

## 功能说明

将论坛ID（如 `fid=141`）映射为友好的名称（如 `网友原创区`），方便在Web界面查看。

## 使用方法

### 1. 编辑配置文件

打开 `config.json`，添加 `forum_names` 配置项：

```json
{
  "target_forums": [
    "fid=141",
    "fid=2"
  ],
  
  "forum_names": {
    "fid=141": "网友原创区",
    "fid=2": "亚洲无码原创区",
    "fid=36": "亚洲有码原创区"
  }
}
```

### 2. 显示效果

**配置前：**
```
论坛: fid=141, fid=2
```

**配置后：**
```
论坛: 网友原创区, 亚洲无码原创区
```

## 常用论坛ID对照表

### 色花堂论坛版块

| 论坛ID | 版块名称 | 说明 |
|--------|---------|------|
| fid=2 | 亚洲无码原创区 | 原创无码内容 |
| fid=36 | 亚洲有码原创区 | 原创有码内容 |
| fid=141 | 网友原创区 | 网友自拍、原创 |
| fid=37 | 中字原创区 | 中文字幕原创 |
| fid=103 | 国产原创区 | 国产原创内容 |
| fid=38 | 转帖交流区 | 转帖分享 |
| fid=230 | 欧美原创区 | 欧美原创内容 |

## 完整配置示例

```json
{
  "base_url": "https://sehuatang.org/",
  "username": "你的用户名",
  "password": "你的密码",
  
  "target_forums": [
    "fid=141",
    "fid=2",
    "fid=36"
  ],
  
  "forum_names": {
    "fid=141": "网友原创区",
    "fid=2": "亚洲无码原创区",
    "fid=36": "亚洲有码原创区",
    "fid=37": "中字原创区",
    "fid=103": "国产原创区",
    "fid=38": "转帖交流区",
    "fid=230": "欧美原创区"
  },
  
  "max_replies_per_day": 30,
  "reply_interval": [3600, 7200],
  "enable_daily_checkin": true
}
```

## 注意事项

### 1. 向后兼容
- 如果不配置 `forum_names`，Web界面会显示原始ID
- 不会影响机器人的正常运行

### 2. 只影响显示
- `forum_names` 只用于Web界面显示
- 不会改变机器人访问的实际论坛ID
- `target_forums` 仍然使用原始ID

### 3. 添加新论坛
```json
{
  "target_forums": [
    "fid=141",
    "fid=新论坛ID"
  ],
  
  "forum_names": {
    "fid=141": "网友原创区",
    "fid=新论坛ID": "新论坛的友好名称"
  }
}
```

## 查找论坛ID

### 方法1：从URL查找
访问论坛版块，查看URL：
```
https://sehuatang.org/forum.php?mod=forumdisplay&fid=141
                                                      ^^^
                                                    论坛ID
```

### 方法2：查看页面源代码
在论坛列表页面，右键查看源代码，搜索版块名称。

## 故障排除

### Q1: Web界面仍显示fid=141？
**A:** 检查：
1. `config.json` 中是否正确添加了 `forum_names`
2. JSON格式是否正确（注意逗号）
3. 刷新浏览器（Ctrl+F5）
4. 重启Web服务

### Q2: 配置后机器人无法运行？
**A:** 检查JSON格式：
```bash
python -c "import json; json.load(open('config.json'))"
```
如果有语法错误会显示具体位置。

### Q3: 显示的名称不对？
**A:** 确保：
- ID完全匹配（包括 `fid=` 前缀）
- 没有多余的空格
- 使用双引号不是单引号

## 配置验证

### 验证配置是否正确
```bash
python -c "
import json
config = json.load(open('config.json'))
print('目标论坛:', config.get('target_forums', []))
print('论坛名称映射:', config.get('forum_names', {}))
for fid in config.get('target_forums', []):
    name = config.get('forum_names', {}).get(fid, fid)
    print(f'  {fid} -> {name}')
"
```

### 预期输出
```
目标论坛: ['fid=141', 'fid=2']
论坛名称映射: {'fid=141': '网友原创区', 'fid=2': '亚洲无码原创区'}
  fid=141 -> 网友原创区
  fid=2 -> 亚洲无码原创区
```

## 高级用法

### 多个论坛批量配置
```json
{
  "target_forums": [
    "fid=141",
    "fid=2",
    "fid=36",
    "fid=37",
    "fid=103"
  ],
  
  "forum_names": {
    "fid=141": "网友原创区",
    "fid=2": "亚洲无码原创区",
    "fid=36": "亚洲有码原创区",
    "fid=37": "中字原创区",
    "fid=103": "国产原创区"
  },
  
  "max_replies_per_day": 50,
  "reply_interval": [7200, 14400]
}
```

### 使用注释（仅示例，实际JSON不支持注释）
实际配置时删除注释：
```json
{
  "target_forums": [
    "fid=141"  // 这是注释，实际配置要删除
  ]
}
```

应该写成：
```json
{
  "target_forums": [
    "fid=141"
  ],
  "_comment": "fid=141 是网友原创区"
}
```

## 总结

- ✅ 简单配置即可使用
- ✅ 不影响机器人功能
- ✅ 支持多个论坛
- ✅ 向后兼容
- ✅ 随时可以添加新映射

添加 `forum_names` 后，Web界面会更加友好和直观！

