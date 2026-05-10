# -*- coding: utf-8 -*-
"""
Gitee build@python 步骤入口脚本。

悬镜等安全插件随模板调用本文件；此前缺失会导致「can't open file './main.py'」。
依赖安装与可编辑安装请在流水线 YAML 中先于本脚本执行；此处仅做源码语法编译校验。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    """返回仓库根目录（本文件所在目录）。"""
    return Path(__file__).resolve().parent


def main() -> int:
    root = _repo_root()
    pkg = root / "django_ip_safeguard"
    if not pkg.is_dir():
        print("错误: 未找到 django_ip_safeguard 源码目录", file=sys.stderr)
        return 1

    # 无需 Django 运行时即可暴露语法错误，供构建/安全扫描阶段快速失败
    subprocess.check_call(
        [sys.executable, "-m", "compileall", "-q", str(pkg)],
        cwd=str(root),
    )
    print("流水线入口: compileall 校验通过")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as e:
        print(f"子进程失败: exit {e.returncode}", file=sys.stderr)
        raise SystemExit(e.returncode)
