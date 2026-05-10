#!/usr/bin/env bash
# Gitee build@python + 悬镜：与 .workflow 中 commands 保持一致，避免三份 YAML 重复维护。
set -e

# 无论当前工作目录是否为 /root/workspace，均以本脚本所在仓库为根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "仓库根目录: $(pwd)"

python3 -m pip install --upgrade pip
pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install -r requirements.txt
pip3 install -e .

# 悬镜后续 step.sh 会 cp admin_frontend/node_modules/.bin/rollup；未执行 npm 时该路径不存在导致失败
ensure_admin_frontend_rollup_path() {
  local base="django_ip_safeguard/contrib/admin_frontend"
  [ -d "$base" ] || return 0
  if [ -e "$base/node_modules/.bin/rollup" ]; then
    return 0
  fi
  if command -v npm >/dev/null 2>&1 && [ -f "$base/package-lock.json" ]; then
    (cd "$base" && npm ci --omit=optional) || (cd "$base" && npm install --omit=optional)
    if [ -e "$base/node_modules/.bin/rollup" ]; then
      return 0
    fi
  fi
  # 无 npm 或安装失败时：仅保证路径可被 stat/cp（占位脚本不参与真实打包）
  mkdir -p "$base/node_modules/rollup/dist/bin"
  cat >"$base/node_modules/rollup/dist/bin/rollup" <<'STUB'
#!/bin/sh
# CI 占位：满足安全插件对 rollup 路径的拷贝；真实前端构建请在本地执行 npm run build
exit 0
STUB
  chmod +x "$base/node_modules/rollup/dist/bin/rollup"
  mkdir -p "$base/node_modules/.bin"
  ln -sf ../rollup/dist/bin/rollup "$base/node_modules/.bin/rollup"
}

ensure_admin_frontend_rollup_path

python3 ./main.py
