#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动这个后端。

    python run.py                       # 默认 127.0.0.1:8787
    python run.py --port 9000
    python run.py --static "../5.创建项目骨架/v1"   # 顺手把 v1 网页同源发出去

要真调模型，先设 key：

    set DEEPSEEK_API_KEY=sk-xxxx        （Windows cmd）
    $env:DEEPSEEK_API_KEY="sk-xxxx"     （PowerShell）
    export DEEPSEEK_API_KEY=sk-xxxx     （macOS / Linux）

不想调模型、只想验证管道：

    set PEILIAN_STUB=1                  （桩模式，照 p0_judge.py --baseline 的道理）

零依赖，不用装任何东西。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.main import main   # noqa: E402

if __name__ == "__main__":
    main()
