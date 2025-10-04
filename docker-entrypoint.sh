#!/bin/bash
# 注意：不使用 set -e，因为我们需要处理 git pull 可能的失败

echo "================================"
echo "🚀 AW98tang 容器启动中..."
echo "================================"

# 调试信息
echo "[Debug] 当前目录: $(pwd)"
echo "[Debug] AUTO_UPDATE=$AUTO_UPDATE"
echo "[Debug] SKIP_GIT=$SKIP_GIT"
echo "[Debug] GITHUB_TOKEN=$([ -n "$GITHUB_TOKEN" ] && echo '已设置' || echo '未设置')"

# Git 拉取函数
gitpull() {
    echo "[Git] 拉取远程分支..."
    git reset --hard origin/main
    git pull origin main
}

# 检查是否跳过 Git 操作
if [ "${SKIP_GIT}" = "true" ]; then
    echo "ℹ️ SKIP_GIT=true，跳过所有 Git 操作"
    AUTO_UPDATE="false"
fi

# 检查是否启用自动更新
if [ "${AUTO_UPDATE}" = "true" ]; then
    echo "🔄 检查代码更新..."
    
    # 检查是否在 git 仓库中
    if [ ! -d ".git" ]; then
        echo "ℹ️ 未检测到 Git 仓库，跳过更新检查"
    else
        echo "📦 检测到 Git 仓库"
        
        # 配置 Git 安全目录
        git config --global --add safe.directory /app
        
        # 配置 Git 用户信息
        git config --global user.email "bot@aw98tang.local"
        git config --global user.name "AW98tang Bot"
        
        # 禁用 Git 密码提示
        export GIT_TERMINAL_PROMPT=0
        export GIT_ASKPASS=/bin/echo
        git config --global credential.helper ''
        
        # 获取当前远程仓库 URL
        CURRENT_REMOTE=$(git config --get remote.origin.url 2>/dev/null || echo "")
        
        # 如果没有配置远程仓库
        if [ -z "$CURRENT_REMOTE" ]; then
            echo "[Git] 初始化远程仓库..."
            if [ -n "${GITHUB_TOKEN}" ]; then
                git remote add origin "https://x-access-token:${GITHUB_TOKEN}@github.com/AWdress/AW98tamg.git"
                echo "[Git] 使用 GitHub Token 进行认证"
            else
                git remote add origin "https://github.com/AWdress/AW98tamg.git"
                echo "[Git] 未设置 GITHUB_TOKEN，使用公开访问"
            fi
        else
            echo "📍 当前远程 URL: ${CURRENT_REMOTE:0:50}..."
            
        # 如果提供了 GITHUB_TOKEN，更新远程 URL
        if [ -n "${GITHUB_TOKEN}" ]; then
            echo "🔑 配置 GitHub Token 认证..."
            
            # 去除 Token 中可能存在的空格和换行符
            CLEAN_TOKEN=$(echo "$GITHUB_TOKEN" | tr -d '[:space:]')
            
            # 清理 URL 中的旧认证信息
            CLEAN_URL=$(echo "$CURRENT_REMOTE" | sed 's|https://[^@]*@|https://|g')
            
            # 提取仓库路径
            if [[ "$CLEAN_URL" == https://github.com/* ]]; then
                REPO_PATH=${CLEAN_URL#https://github.com/}
                REPO_PATH=${REPO_PATH%.git}
                
                # 尝试多种认证格式
                # 格式1: x-access-token (推荐)
                NEW_URL="https://x-access-token:${CLEAN_TOKEN}@github.com/${REPO_PATH}.git"
                git remote set-url origin "$NEW_URL"
                echo "✅ GitHub Token 配置成功 (格式: x-access-token)"
                
                # 备用格式2: 直接使用token作为用户名
                # NEW_URL="https://${CLEAN_TOKEN}@github.com/${REPO_PATH}.git"
                
            elif [[ "$CLEAN_URL" == git@github.com:* ]]; then
                REPO_PATH=${CLEAN_URL#git@github.com:}
                REPO_PATH=${REPO_PATH%.git}
                NEW_URL="https://x-access-token:${CLEAN_TOKEN}@github.com/${REPO_PATH}.git"
                git remote set-url origin "$NEW_URL"
                echo "✅ 已转换为 HTTPS 并配置 Token"
            fi
        fi
        
        # 保存当前版本
        CURRENT_VERSION=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
        echo "📌 当前版本: ${CURRENT_VERSION:0:8}"
        
        # 尝试获取远程更新
        echo "⬇️ 正在从远程仓库同步代码..."
        
        # 使用 2>&1 捕获所有输出
        FETCH_OUTPUT=$(git fetch origin main 2>&1)
        FETCH_STATUS=$?
        
        if [ $FETCH_STATUS -ne 0 ]; then
            echo "❌ 获取远程更新失败！"
            echo "错误信息: $FETCH_OUTPUT"
            
            # 检查是否是认证问题
            if echo "$FETCH_OUTPUT" | grep -q "Authentication failed\|Invalid username or token\|Permission denied"; then
                echo "⚠️ 认证失败，可能原因："
                echo "   1. 仓库是私有的，需要设置 GITHUB_TOKEN 环境变量"
                echo "   2. GITHUB_TOKEN 已过期或无效"
                echo "   3. Token 没有足够的权限"
                echo ""
                echo "💡 解决方案："
                echo "   - 在 docker-compose.yml 中设置 GITHUB_TOKEN 环境变量"
                echo "   - 或者设置 SKIP_GIT=true 跳过自动更新"
                echo "   - 或者设置 AUTO_UPDATE=false 禁用自动更新"
            fi
            
            echo "⚠️ 使用当前版本继续运行"
            echo ""
        else
            echo "✅ 远程更新获取成功"
            
            # 强制同步到远程版本
            echo "🔄 强制同步到远程版本..."
            RESET_OUTPUT=$(git reset --hard origin/main 2>&1)
            RESET_STATUS=$?
            
            if [ $RESET_STATUS -ne 0 ]; then
                echo "❌ 代码同步失败！"
                echo "错误信息: $RESET_OUTPUT"
                echo "⚠️ 使用当前版本继续运行"
            else
                NEW_VERSION=$(git rev-parse HEAD)
                
                if [ "$CURRENT_VERSION" != "$NEW_VERSION" ]; then
                    echo "✅ 代码已同步到最新版本!"
                    echo "📌 新版本: ${NEW_VERSION:0:8}"
                    
                    # 检查是否需要重新安装依赖
                    if git diff --name-only $CURRENT_VERSION $NEW_VERSION 2>/dev/null | grep -q "requirements.txt"; then
                        echo "📦 检测到依赖变更，重新安装依赖..."
                        pip install --no-cache-dir -r requirements.txt
                        echo "✅ 依赖安装完成"
                    fi
                else
                    echo "✅ 代码已是最新版本"
                fi
            fi
        fi
    fi
else
    echo "ℹ️ 自动更新已禁用"
    echo "   - 设置 AUTO_UPDATE=true 启用自动更新"
    echo "   - 设置 GITHUB_TOKEN=你的token 进行认证（私有仓库）"
    echo "   - 设置 SKIP_GIT=true 完全跳过 Git 操作"
fi

echo "================================"
echo "🌐 启动 Web 控制面板..."
echo "================================"

# 执行传入的命令（默认是启动 web_app.py）
exec "$@"

