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

# 使用ZIP回退更新（支持公开/私有仓库）
zip_fallback_update() {
    echo "[Zip] 尝试使用ZIP回退方式更新代码..."

    # 解析 owner/repo
    OWNER="AWdress"
    REPO="AW98tamg"
    if [ -n "$GIT_REMOTE" ]; then
        # 提取像 https://github.com/owner/repo.git 的 owner 与 repo
        OWNER_TMP=$(echo "$GIT_REMOTE" | sed -E 's#.*github.com/([^/]+)/([^/.]+).*#\1#')
        REPO_TMP=$(echo "$GIT_REMOTE" | sed -E 's#.*github.com/([^/]+)/([^/.]+).*#\2#')
        if [ -n "$OWNER_TMP" ] && [ -n "$REPO_TMP" ]; then
            OWNER="$OWNER_TMP"; REPO="$REPO_TMP"
        fi
    fi

    [ -z "$GIT_BRANCH" ] && GIT_BRANCH="main"

    TMP_DIR="/tmp/zip_update"
    rm -rf "$TMP_DIR" && mkdir -p "$TMP_DIR"
    ZIP_PATH="$TMP_DIR/repo.zip"

    DOWNLOAD_OK=false

    if [ -n "$GITHUB_TOKEN" ]; then
        echo "[Zip] 使用 GitHub API（私有仓库支持）下载 zipball..."
        curl -L -H "Authorization: token $GITHUB_TOKEN" \
             -H "Accept: application/vnd.github+json" \
             -o "$ZIP_PATH" \
             "https://api.github.com/repos/$OWNER/$REPO/zipball/$GIT_BRANCH" && DOWNLOAD_OK=true
    else
        echo "[Zip] 使用公开镜像下载 zip..."
        for URL in \
            "https://mirror.ghproxy.com/https://codeload.github.com/$OWNER/$REPO/zip/refs/heads/$GIT_BRANCH" \
            "https://codeload.github.com/$OWNER/$REPO/zip/refs/heads/$GIT_BRANCH" \
            "https://kgithub.com/$OWNER/$REPO/archive/refs/heads/$GIT_BRANCH.zip" \
            "https://hub.fgit.cf/$OWNER/$REPO/archive/refs/heads/$GIT_BRANCH.zip"; do
            echo "[Zip] 尝试: $URL"
            curl -L -o "$ZIP_PATH" "$URL" && DOWNLOAD_OK=true && break
        done
    fi

    if [ "$DOWNLOAD_OK" != true ]; then
        echo "[Zip] ZIP下载失败，回退更新无法完成"
        return 1
    fi

    unzip -q "$ZIP_PATH" -d "$TMP_DIR" || { echo "[Zip] 解压失败"; return 1; }
    SRC_ROOT=$(find "$TMP_DIR" -maxdepth 1 -type d -name "$REPO-*" | head -n1)
    if [ -z "$SRC_ROOT" ]; then
        SRC_ROOT=$(find "$TMP_DIR" -maxdepth 1 -type d ! -path "$TMP_DIR" | head -n1)
    fi
    if [ -z "$SRC_ROOT" ]; then
        echo "[Zip] 未找到解压目录"
        return 1
    fi

    echo "[Zip] 覆盖更新代码（保留 config.json / logs / debug / data / .git）..."
    # 同步文件（尽量不依赖rsync）
    (cd "$SRC_ROOT" && \
        find . -mindepth 1 -maxdepth 1 \
          ! -name 'config.json' \
          ! -name 'logs' \
          ! -name 'debug' \
          ! -name 'data' \
          ! -name '.git' \
          -print0 | xargs -0 -I {} bash -c 'SRC="{}"; DST="/app/${SRC#./}"; \
              if [ -d "$SRC" ]; then mkdir -p "$DST" && cp -r "$SRC"/* "$DST" 2>/dev/null || true; \
              else mkdir -p "$(dirname "$DST")" && cp -f "$SRC" "$DST"; fi')

    echo "[Zip] 回退更新完成"
    return 0
}

# 设置代理配置
echo "🌐 配置网络代理..."
setup_proxy
echo "================================"

# 检查是否跳过 Git 操作
if [ "$SKIP_GIT" = "true" ]; then
    echo "ℹ️ SKIP_GIT=true，跳过所有 Git 操作"
else
    echo "🔄 开始启动时自动更新检查..."

    # 新增总开关：STARTUP_AUTO_UPDATE=true 才会在启动时尝试更新
    if [ "$STARTUP_AUTO_UPDATE" != "true" ]; then
        echo "ℹ️ 跳过启动时更新（设置 STARTUP_AUTO_UPDATE=true 可启用）"
        echo "📌 当前版本:"
        git log -1 --oneline 2>/dev/null || echo "  (无法获取版本信息)"
        # 直接跳出更新逻辑，继续启动服务
    else
        echo "🔄 开始 Git/ZIP 代码同步流程（ZIP优先）..."
    
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
        
        # 先尝试ZIP更新（更稳健，无需交互）
        if zip_fallback_update; then
            echo "✅ ZIP回退优先更新成功"
        else
            echo "⚠️ ZIP回退失败，尝试Git同步..."
            if git fetch origin "$GIT_BRANCH" 2>/dev/null; then
                echo "✅ 成功获取远程更新"
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
                echo "❌ Git 同步失败，使用当前版本继续运行"
            fi
        fi
    fi
    fi
fi

echo "================================"
echo "🚀 启动应用程序..."
echo "================================"

# 启动Web应用
exec python web_app.py


