#!/bin/bash
# 注意：不使用 set -e，因为我们需要处理 git pull 可能的失败

echo "================================"
echo "🚀 AW98tang 容器启动中..."
echo "================================"

# 检查是否启用自动更新
if [ "${AUTO_UPDATE}" = "true" ]; then
    echo "🔄 检查代码更新..."
    
    # 检查是否在 git 仓库中
    if [ -d ".git" ]; then
        echo "📦 检测到 Git 仓库"
        
        # 配置 Git 使用 GitHub Token（用于私有仓库）
        if [ -n "${GITHUB_TOKEN}" ]; then
            echo "🔑 配置 GitHub Token 认证..."
            
            # 配置 Git 安全目录（避免 dubious ownership 错误）
            git config --global --add safe.directory /app
            
            # 禁用 Git 密码提示（关键：避免在非交互环境中要求密码）
            export GIT_TERMINAL_PROMPT=0
            export GIT_ASKPASS=/bin/echo
            
            # 配置 Git 不使用 credential helper
            git config --global credential.helper ''
            
            # 获取远程仓库 URL
            REPO_URL=$(git config --get remote.origin.url 2>/dev/null)
            
            if [ -z "$REPO_URL" ]; then
                echo "⚠️ 未检测到远程仓库，初始化远程仓库..."
                # 假设仓库是 AWdress/AW98tamg
                git remote add origin "https://${GITHUB_TOKEN}@github.com/AWdress/AW98tamg.git"
                echo "✅ 远程仓库已配置"
            else
                echo "📍 当前远程 URL: ${REPO_URL:0:50}..."  # 只显示前50个字符，避免暴露token
                
                # 检查 URL 中是否已经包含 token
                if [[ "$REPO_URL" == *"${GITHUB_TOKEN}"* ]]; then
                    echo "✅ GitHub Token 已配置，跳过"
                else
                    # 清理 URL 中可能存在的旧 token
                    CLEAN_URL="$REPO_URL"
                    # 移除 URL 中的所有认证信息
                    CLEAN_URL=$(echo "$CLEAN_URL" | sed 's|https://[^@]*@|https://|g')
                    
                    # 提取仓库路径
                    if [[ "$CLEAN_URL" == https://github.com/* ]]; then
                        REPO_PATH=${CLEAN_URL#https://github.com/}
                        REPO_PATH=${REPO_PATH%.git}
                        
                        # 配置带 token 的 URL
                        NEW_URL="https://${GITHUB_TOKEN}@github.com/${REPO_PATH}.git"
                        git remote set-url origin "$NEW_URL"
                        echo "✅ GitHub Token 配置成功"
                    elif [[ "$CLEAN_URL" == git@github.com:* ]]; then
                        # SSH URL 转换为 HTTPS
                        REPO_PATH=${CLEAN_URL#git@github.com:}
                        REPO_PATH=${REPO_PATH%.git}
                        NEW_URL="https://${GITHUB_TOKEN}@github.com/${REPO_PATH}.git"
                        git remote set-url origin "$NEW_URL"
                        echo "✅ 已转换为 HTTPS 并配置 Token"
                    else
                        echo "⚠️ 未知的 URL 格式，跳过配置"
                    fi
                fi
            fi
        fi
        
        # 保存当前版本
        CURRENT_VERSION=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
        echo "📌 当前版本: ${CURRENT_VERSION:0:8}"
        
        # 配置 Git 用户信息（避免拉取时的警告）
        git config --global user.email "bot@aw98tang.local"
        git config --global user.name "AW98tang Bot"
        
        # 尝试拉取更新
        echo "⬇️ 正在从远程仓库拉取更新..."
        ERROR_MSG=$(git pull origin main 2>&1)
        if [ $? -eq 0 ]; then
            NEW_VERSION=$(git rev-parse HEAD)
            
            if [ "$CURRENT_VERSION" != "$NEW_VERSION" ]; then
                echo "✅ 代码已更新!"
                echo "📌 新版本: ${NEW_VERSION:0:8}"
                
                # 检查是否需要重新安装依赖
                if git diff --name-only $CURRENT_VERSION $NEW_VERSION | grep -q "requirements.txt"; then
                    echo "📦 检测到依赖变更，重新安装依赖..."
                    pip install --no-cache-dir -r requirements.txt
                    echo "✅ 依赖安装完成"
                fi
            else
                echo "✅ 代码已是最新版本"
            fi
        else
            echo "❌ 拉取更新失败！"
            echo "错误信息: $ERROR_MSG"
            echo "⚠️ 使用当前版本继续运行"
        fi
    else
        echo "ℹ️ 未检测到 Git 仓库，跳过更新检查"
    fi
else
    echo "ℹ️ 自动更新已禁用 (设置 AUTO_UPDATE=true 启用)"
fi

echo "================================"
echo "🌐 启动 Web 控制面板..."
echo "================================"

# 执行传入的命令（默认是启动 web_app.py）
exec "$@"

