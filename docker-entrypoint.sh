#!/bin/bash

echo "================================"
echo "🚀 AW98tang 容器启动中..."
echo "================================"
echo "当前 Python 版本: $(python --version)"
echo "================================"

# 调试信息
echo "[Debug] 当前目录: $(pwd)"
echo "[Debug] GIT_REMOTE=$GIT_REMOTE"
echo "[Debug] GIT_BRANCH=$GIT_BRANCH"
echo "[Debug] SKIP_GIT=$SKIP_GIT"
echo "[Debug] GITHUB_TOKEN=$([ -n "$GITHUB_TOKEN" ] && echo '已设置' || echo '未设置')"

# 读取config.json中的代理配置
read_proxy_config() {
    if [ -f "config.json" ]; then
        echo "[Proxy] 从 config.json 读取代理配置..."
        
        # 使用Python读取JSON配置
        PROXY_CONFIG=$(python3 -c "
import json
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        proxy = config.get('proxy', {})
        print(f\"{proxy.get('enabled', False)}|{proxy.get('http_proxy', '')}|{proxy.get('https_proxy', '')}|{proxy.get('no_proxy', '')}|{proxy.get('use_for_git', False)}\")
except Exception as e:
    print('false|||||')
" 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            IFS='|' read -r PROXY_ENABLED HTTP_PROXY HTTPS_PROXY NO_PROXY USE_FOR_GIT <<< "$PROXY_CONFIG"
            echo "[Proxy] 配置读取成功"
            echo "[Proxy] 启用: $PROXY_ENABLED"
            echo "[Proxy] HTTP代理: $HTTP_PROXY"
            echo "[Proxy] HTTPS代理: $HTTPS_PROXY"
            echo "[Proxy] Git使用代理: $USE_FOR_GIT"
        else
            echo "[Proxy] 读取配置失败，使用默认值"
            PROXY_ENABLED="false"
        fi
    else
        echo "[Proxy] config.json 不存在"
        PROXY_ENABLED="false"
    fi
}

# 配置代理环境变量
setup_proxy() {
    read_proxy_config
    
    if [ "$PROXY_ENABLED" = "True" ] || [ "$PROXY_ENABLED" = "true" ]; then
        echo "[Proxy] ✅ 代理已启用"
        
        if [ -n "$HTTP_PROXY" ]; then
            export http_proxy="$HTTP_PROXY"
            echo "[Proxy] HTTP代理: $http_proxy"
        fi
        
        if [ -n "$HTTPS_PROXY" ]; then
            export https_proxy="$HTTPS_PROXY"
            echo "[Proxy] HTTPS代理: $https_proxy"
        fi
        
        if [ -n "$NO_PROXY" ]; then
            export no_proxy="$NO_PROXY"
            echo "[Proxy] 不使用代理: $no_proxy"
        fi
        
        # 如果Git使用代理
        if [ "$USE_FOR_GIT" = "True" ] || [ "$USE_FOR_GIT" = "true" ]; then
            echo "[Proxy] 🔧 配置 Git 使用代理"
            
            if [ -n "$HTTP_PROXY" ]; then
                git config --global http.proxy "$HTTP_PROXY"
                echo "[Proxy] Git HTTP代理已设置"
            fi
            
            if [ -n "$HTTPS_PROXY" ]; then
                git config --global https.proxy "$HTTPS_PROXY"
                echo "[Proxy] Git HTTPS代理已设置"
            fi
            
            # 设置Git SSL验证（代理环境可能需要）
            git config --global http.sslVerify false
            echo "[Proxy] Git SSL验证已禁用（代理环境）"
        fi
    else
        echo "[Proxy] ❌ 代理未启用"
        # 清除可能存在的代理配置
        unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy NO_PROXY
        git config --global --unset http.proxy 2>/dev/null
        git config --global --unset https.proxy 2>/dev/null
    fi
}

# Git 拉取函数
gitpull() {
    echo "[Git] 拉取远程分支 $GIT_BRANCH..."
    git reset --hard origin/"$GIT_BRANCH"
    git pull origin "$GIT_BRANCH"
}

# 设置代理配置
echo "🌐 配置网络代理..."
setup_proxy
echo "================================"

# 检查是否跳过 Git 操作
if [ "$SKIP_GIT" = "true" ]; then
    echo "ℹ️ SKIP_GIT=true，跳过所有 Git 操作"
else
    echo "🔄 开始 Git 代码同步流程..."
    
    # 设置默认分支
    if [ -z "$GIT_BRANCH" ]; then
        echo "[Git] GIT_BRANCH 未设置，使用默认值 main"
        GIT_BRANCH="main"
    fi
    
    # 设置默认仓库地址
    if [ -z "$GIT_REMOTE" ]; then
        echo "[Git] GIT_REMOTE 未设置，使用默认仓库 AW98tamg"
        if [ -n "$GITHUB_TOKEN" ]; then
            # 去除 Token 中可能的空格和换行符
            CLEAN_TOKEN=$(echo "$GITHUB_TOKEN" | tr -d '[:space:]')
            GIT_REMOTE="https://${CLEAN_TOKEN}@github.com/AWdress/AW98tamg.git"
            echo "[Git] 使用 GitHub Token 进行认证"
        else
            GIT_REMOTE="https://github.com/AWdress/AW98tamg.git"
            echo "[Git] 未设置 GITHUB_TOKEN，使用公开访问"
        fi
    fi
    
    echo "[Git] 目标仓库: ${GIT_REMOTE:0:50}..."
    echo "[Git] 目标分支: $GIT_BRANCH"
    
    # 配置 Git 环境
    git config --global --add safe.directory /app
    git config --global user.email "bot@aw98tang.local"
    git config --global user.name "AW98tang Bot"
    
    # 禁用 Git 交互式提示
    export GIT_TERMINAL_PROMPT=0
    export GIT_ASKPASS=/bin/echo
    git config --global credential.helper ''
    
    # 检查是否为 Git 仓库
    if [ ! -d ".git" ]; then
        echo "[Git] 初始化本地仓库..."
        git init
        git remote add origin "$GIT_REMOTE"
        
        echo "[Git] 尝试获取远程代码..."
        if git fetch origin 2>/dev/null; then
            echo "✅ 成功连接到远程仓库"
            
            # 检查分支是否存在
            if git ls-remote --heads origin "$GIT_BRANCH" | grep -q "$GIT_BRANCH"; then
                echo "[Git] 切换到分支 $GIT_BRANCH"
                git checkout -b "$GIT_BRANCH" origin/"$GIT_BRANCH"
            else
                echo "⚠️ 分支 $GIT_BRANCH 不存在，使用当前代码"
                SKIP_GIT="true"
            fi
        else
            echo "❌ 无法连接到远程仓库"
            echo "⚠️ Git 初始化失败，使用当前版本继续运行"
            SKIP_GIT="true"
        fi
    else
        echo "[Git] 检测到现有 Git 仓库"
        
        # 更新远程仓库地址（如果有变化）
        CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
        if [ "$CURRENT_REMOTE" != "$GIT_REMOTE" ]; then
            echo "[Git] 更新远程仓库地址..."
            git remote set-url origin "$GIT_REMOTE"
        fi
        
        # 显示当前版本
        echo "📌 当前版本:"
        git log -1 --oneline 2>/dev/null || echo "  (无法获取版本信息)"
        
        # 尝试同步代码
        echo "[Git] 尝试同步最新代码..."
        
        # 清理工作目录
        git reset --hard HEAD 2>/dev/null
        
        if git fetch origin "$GIT_BRANCH" 2>/dev/null; then
            echo "✅ 成功获取远程更新"
            
            # 检查本地与远程的差异
            LOCAL_HASH=$(git rev-parse HEAD 2>/dev/null || echo "local")
            REMOTE_HASH=$(git rev-parse origin/"$GIT_BRANCH" 2>/dev/null || echo "remote")
            
            if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
                echo "[Git] 发现新版本，准备更新..."
                if gitpull; then
                    echo "✅ 代码更新成功"
                    echo "📌 更新后版本:"
                    git log -1 --oneline
                else
                    echo "⚠️ 更新失败，使用当前版本继续"
                fi
            else
                echo "✅ 已是最新版本"
            fi
        else
            echo "❌ 无法连接到远程仓库"
            echo "⚠️ Git 同步失败，使用当前版本继续运行"
        fi
    fi
fi

echo "================================"
echo "🚀 启动应用程序..."
echo "================================"

# 启动Web应用
exec python web_app.py


