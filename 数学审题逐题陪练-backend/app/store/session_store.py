#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会话存储 —— 一次会话一个 JSON 文档
================================================================================

【为什么不进 SQLite】
  v1 是极薄版；会话是单文档读写，JSON 足够。18 号文已留好实体/字段，
  以后换 SQLite 只换这一层。

【原子写】
  先写临时文件，再 os.replace；避免写到一半留下坏 JSON。
"""

import json
import os
import threading
from pathlib import Path

_默认数据目录 = Path(__file__).resolve().parents[2] / "data"
_锁 = threading.Lock()


def _根():
    return Path(os.environ.get("PEILIAN_DATA_DIR") or _默认数据目录)


def _目录():
    p = _根() / "sessions"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _路径(session_id):
    安全 = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return _目录() / (安全 + ".json")


def 存(会话):
    with _锁:
        p = _路径(会话["session_id"])
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(会话, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, p)
    return 会话


def 读(session_id):
    p = _路径(session_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def 存在(session_id):
    return _路径(session_id).exists()
