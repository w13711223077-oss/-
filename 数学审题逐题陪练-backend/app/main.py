#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP 服务与路由 —— 极薄，零框架
================================================================================

【为什么不引框架】
  这个服务只有四个端点、两个股存储、一次转发。
  FastAPI/Flask 装进来是几十个包，而 §8.2 要的是「极薄」。
  更重要的是：**用户机器上不用装任何东西**，跟 setup_env.py 和 P0 工具的零依赖取向一致。

【它解决的三个问题，都在 §8.1 那张表里】
  1. 无后端 → 有了（存储层）
  2. key 暴露在网页源码里 → 有了（转发层，key 只在服务端）
  3. 本地文件直调接口被跨域拦 → 有了（本服务带 CORS 头，也能顺手把静态网页同源发出去）

启动：python run.py      （或 python -m app.main）
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from .api import forward, records, session, sessions
from .domain import schema

# ─────────────────────────────────────────────────────────────
# 路由表
# ─────────────────────────────────────────────────────────────

def _健康(_请求体, _查询):
    return 200, {
        "服务": "数学审题逐题陪练-backend",
        "状态": "ok",
        "桩模式": forward._桩模式(),
        "有模型key": bool(forward._key()),
        "端点": ["%s %s" % (m, p) for m, p, _ in 路由],
        "会话端点": [
            "POST /api/v1/sessions",
            "POST /api/v1/sessions/{id}/problem",
            "POST /api/v1/sessions/{id}/confirm",
            "POST /api/v1/sessions/{id}/start",
            "POST /api/v1/sessions/{id}/answer",
            "POST /api/v1/sessions/{id}/close",
            "GET  /api/v1/sessions/{id}",
            "POST /api/v1/sessions/{id}/discard",
        ],
    }


def _契约(_请求体, _查询):
    return 200, schema.口径()


路由 = [
    ("GET",  "/api/v1/health", _健康),
    ("GET",  "/api/v1/schema", _契约),
] + forward.路由 + records.路由 + session.路由 + sessions.路由

_路由索引 = {(方法, 路径): 处理 for 方法, 路径, 处理 in 路由}


def _动态处理(方法, 路径):
    """把 /api/v1/sessions/{id}/... 解析成带 sid 的调用。"""
    前缀 = "/api/v1/sessions/"
    if not 路径.startswith(前缀):
        return None
    余 = 路径[len(前缀):].strip("/")
    if not 余:
        return None
    段 = 余.split("/")
    if len(段) == 1 and 方法 == "GET":
        sid = 段[0]
        return lambda 体, 查: sessions.读取(体, 查, sid)
    if len(段) == 2:
        sid, 动作 = 段
        处理 = sessions.动态路由.get((方法, 动作))
        if 处理:
            return lambda 体, 查: 处理(体, 查, sid)
    return None


# ─────────────────────────────────────────────────────────────
# 可选：把 v1 网页同源发出去（这样前端不用改就能不踩跨域）
# ─────────────────────────────────────────────────────────────

_静态目录 = None       # 由 run.py 或 main() 设置


def _发静态(路径):
    """返回 (状态码, content_type, bytes) 或 None。"""
    if not _静态目录:
        return None
    根 = os.path.realpath(_静态目录)
    相对 = (路径 or "/").lstrip("/") or "index.html"
    全 = os.path.realpath(os.path.join(根, 相对))
    # 防目录穿越：必须比 startswith(根) 严——否则同级的 "site-秘密/" 会被当成 "site/" 的子路径
    if not (全 == 根 or 全.startswith(根 + os.sep)) or not os.path.isfile(全):
        return None
    类型 = {".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8"}.get(
                os.path.splitext(全)[1].lower(), "application/octet-stream")
    with open(全, "rb") as f:
        return 200, 类型, f.read()


# ─────────────────────────────────────────────────────────────
# 请求处理
# ─────────────────────────────────────────────────────────────

class 处理器(BaseHTTPRequestHandler):
    server_version = "PeilianBackend/0.1"
    protocol_version = "HTTP/1.1"

    # 别把每个请求都打到 stderr 上，太吵
    def log_message(self, fmt, *args):
        if os.environ.get("PEILIAN_VERBOSE"):
            super().log_message(fmt, *args)

    # ── CORS（§8.1 第三条风险的解法）─────────────────────────
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        self._走("GET")

    def do_POST(self):
        self._走("POST")

    # ── 主流程 ────────────────────────────────────────────────
    def _走(self, 方法):
        u = urlparse(self.path)
        路径 = u.path.rstrip("/") or "/"
        查询 = {k: v[0] for k, v in parse_qs(u.query).items()}

        # 静态文件（只在配了 --static 时；/api/ 一律走接口）
        if 方法 == "GET" and not 路径.startswith("/api/"):
            try:
                静 = _发静态(路径)
            except OSError:
                静 = None
            if 静:
                self._回(*静)
                return

        处理 = _路由索引.get((方法, 路径))
        if 处理 is None:
            处理 = _动态处理(方法, 路径)
        if 处理 is None:
            self._回(404, "application/json; charset=utf-8",
                     json.dumps({
                         "错误": "没有这个端点：%s %s" % (方法, 路径),
                         "有的是": ["%s %s" % (m, p) for m, p, _ in 路由],
                     }, ensure_ascii=False).encode("utf-8"))
            return

        请求体 = {}
        if 方法 == "POST":
            # 别用 int() 硬转——收到非数字的 Content-Length 会抛异常，
            # 异常冒出 socketserver 就是「连接被掐断」，客户端连个 400 都拿不到。
            原长 = (self.headers.get("Content-Length") or "0").strip()
            if not 原长.isdigit():
                self._回(400, "application/json; charset=utf-8",
                         json.dumps({"错误": "Content-Length 不是数字：%r" % 原长},
                                    ensure_ascii=False).encode("utf-8"))
                return
            长 = int(原长)
            原 = self.rfile.read(长) if 长 else b""
            if 原:
                try:
                    请求体 = json.loads(原.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    self._回(400, "application/json; charset=utf-8",
                             json.dumps({"错误": "请求体不是合法 JSON：%s" % e},
                                        ensure_ascii=False).encode("utf-8"))
                    return
                if not isinstance(请求体, dict):
                    self._回(400, "application/json; charset=utf-8",
                             json.dumps({"错误": "请求体应为 JSON 对象"},
                                        ensure_ascii=False).encode("utf-8"))
                    return

        try:
            状态, 数据 = 处理(请求体, 查询)
        except Exception as e:                             # noqa: BLE001
            import traceback
            traceback.print_exc()
            self._回(500, "application/json; charset=utf-8",
                     json.dumps({"错误": "服务端炸了：%s" % e},
                                ensure_ascii=False).encode("utf-8"))
            return

        self._回(状态, "application/json; charset=utf-8",
                 json.dumps(数据, ensure_ascii=False, indent=2).encode("utf-8"))

    def _回(self, 状态, 类型, 内容: bytes):
        self.send_response(状态)
        self._cors()
        self.send_header("Content-Type", 类型)
        self.send_header("Content-Length", str(len(内容)))
        self.end_headers()
        self.wfile.write(内容)


# ─────────────────────────────────────────────────────────────
# 启动
# ─────────────────────────────────────────────────────────────

def 起(端口=8787, 静态目录=None):
    global _静态目录
    if 静态目录:
        全 = os.path.abspath(静态目录)
        if not os.path.isdir(全):
            sys.exit("找不到静态目录：%s" % 全)
        _静态目录 = 全

    服 = ThreadingHTTPServer(("127.0.0.1", 端口), 处理器)
    服.daemon_threads = True

    print("数学审题逐题陪练-backend 已启动")
    print("  地址      http://127.0.0.1:%d" % 端口)
    print("  桩模式    %s" % ("开" if forward._桩模式() else "关"))
    print("  模型 key  %s" % ("已配置" if forward._key() else "未配置"))
    if _静态目录:
        print("  静态目录  %s" % _静态目录)
    print("  端点")
    for 方法, 路径, _ in 路由:
        print("    %-5s %s" % (方法, 路径))
    print("\nCtrl+C 停。")
    try:
        服.serve_forever()
    except KeyboardInterrupt:
        print("\n停了。")
    finally:
        服.server_close()


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="数学审题逐题陪练-backend")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PEILIAN_PORT", 8787)))
    ap.add_argument("--static", default=os.environ.get("PEILIAN_STATIC"),
                    help="可选：把 v1 的网页同源发出去（避开跨域）")
    args = ap.parse_args(argv)
    起(args.port, args.static)


if __name__ == "__main__":
    main()
