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

# Git 拉取函数
gitpull() {
    echo "[Git] 拉取远程分支 $GIT_BRANCH..."
    git reset --hard origin/"$GIT_BRANCH"
    git pull origin "$GIT_BRANCH"
}

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
            echo "⚠️ 无法连接到远程仓库"
            echo "   可能是私有仓库或网络问题"
            echo "   跳过 Git 同步，使用当前代码"
            SKIP_GIT="true"
        fi
    else
        echo "📦 检测到 Git 仓库"
        
        # 检查当前远程仓库地址
        CURRENT_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
        
        # 判断是否需要更新远程地址
        NEED_UPDATE=false
        if [ -z "$CURRENT_REMOTE" ]; then
            echo "[Git] 未配置远程仓库，添加远程地址"
            git remote add origin "$GIT_REMOTE"
            NEED_UPDATE=false
        elif [[ "$CURRENT_REMOTE" != *"AWdress/AW98tamg"* ]]; then
            echo "⚠️ 检测到错误的远程仓库: ${CURRENT_REMOTE:0:50}..."
            echo "[Git] 重新配置为正确的仓库"
            git remote remove origin 2>/dev/null || true
            git remote add origin "$GIT_REMOTE"
            NEED_UPDATE=false
        else
            echo "📍 当前远程地址: ${CURRENT_REMOTE:0:50}..."
            
            # 如果远程地址不同，更新它（可能是因为添加了Token）
            if [ "$CURRENT_REMOTE" != "$GIT_REMOTE" ]; then
                echo "[Git] 更新远程地址以使用新的认证"
                git remote set-url origin "$GIT_REMOTE"
            fi
        fi
        
        # 保存当前版本
        CURRENT_VERSION=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
        echo "📌 当前版本: ${CURRENT_VERSION:0:8}"
    fi
    
    # 如果没有被跳过，则执行同步
    if [ "$SKIP_GIT" != "true" ]; then
        echo "[Git] 开始同步代码..."
        
        # 尝试拉取代码
        if gitpull 2>&1; then
            NEW_VERSION=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
            
            if [ "$CURRENT_VERSION" != "unknown" ] && [ "$CURRENT_VERSION" != "$NEW_VERSION" ]; then
                echo "✅ 代码已更新到最新版本"
                echo "📌 新版本: ${NEW_VERSION:0:8}"
                
                # 检查是否需要重新安装依赖
                if git diff --name-only "$CURRENT_VERSION" "$NEW_VERSION" 2>/dev/null | grep -q "requirements.txt"; then
                    echo "📦 检测到依赖变更，重新安装依赖..."
                    pip install --no-cache-dir -r requirements.txt
                    echo "✅ 依赖安装完成"
                fi
            else
                echo "✅ 代码已是最新版本"
            fi
        else
            echo "⚠️ Git 同步失败，使用当前版本继续运行"
            echo ""
            echo "💡 故障排查："
            echo "   1. 检查 GITHUB_TOKEN 是否有效（私有仓库需要）"
            echo "   2. 检查网络连接是否正常"
            echo "   3. 可以设置 SKIP_GIT=true 跳过 Git 同步"
            echo ""
        fi
    else
        echo "[Git] 跳过 Git 同步操作"
    fi
fi

echo "================================"
echo "🌐 启动 Web 控制面板..."
echo "================================"

# 执行传入的命令（默认是启动 web_app.py）
exec "$@"
