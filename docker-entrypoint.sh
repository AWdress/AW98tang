#!/bin/bash
set -e

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
            git config --global credential.helper store
            
            # 获取远程仓库 URL
            REPO_URL=$(git config --get remote.origin.url)
            
            # 如果是 HTTPS URL，添加 token
            if [[ "$REPO_URL" == https://* ]]; then
                # 提取仓库路径（去掉 https://）
                REPO_PATH=${REPO_URL#https://}
                REPO_PATH=${REPO_PATH#github.com/}
                
                # 配置带 token 的 URL
                NEW_URL="https://${GITHUB_TOKEN}@github.com/${REPO_PATH}"
                git remote set-url origin "$NEW_URL"
                echo "✅ GitHub Token 配置成功"
            fi
        fi
        
        # 保存当前版本
        CURRENT_VERSION=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
        echo "📌 当前版本: ${CURRENT_VERSION:0:8}"
        
        # 尝试拉取更新
        echo "⬇️ 正在从远程仓库拉取更新..."
        if git pull origin main 2>/dev/null; then
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
            echo "⚠️ 拉取更新失败，使用当前版本继续运行"
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

