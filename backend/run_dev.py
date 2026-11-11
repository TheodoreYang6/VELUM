"""PyCharm 一键启动入口。

在 PyCharm 中右键本文件 → Run 'run_dev'，然后访问 http://127.0.0.1:8000/
本脚本自行修正工作目录与模块搜索路径，无需额外配置 PYTHONPATH。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    reload_enabled = os.getenv("TAROT_RELOAD", "0") == "1"
    print("The Tarot backend starting → http://127.0.0.1:8000/")
    print(f"working dir: {BACKEND} | reload: {reload_enabled}")
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=reload_enabled,
        log_level="info",
    )
