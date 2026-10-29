# 项目目录结构 — 数学审题逐题陪练-backend

> 本文只描述**目录与职责**；每个模块为什么这样切，见 `12-总体架构与骨架`、`15-审题陪练系统设计`、`17-Agent与工具契约`、`18-数据模型设计`、`19-API设计`。
> 原则：**按设计文档里出现的模块划分来组织，不凭空造层。**

---

## 一、目录树

```
数学审题逐题陪练-backend/
├── run.py                      启动入口（零依赖）
├── README.md                   怎么跑 / 端点 / 关键决策
├── STRUCTURE.md                本文
├── app/
│   ├── __init__.py
│   ├── main.py                 HTTP 服务、路由、动态会话路由、静态文件
│   ├── api/                     HTTP 层：只做请求/响应映射
│   │   ├── __init__.py
│   │   ├── sessions.py         会话生命周期 / 答题 / 收束（S1—S8）
│   │   ├── forward.py          模型读题 / 通用转发（藏 key）
│   │   ├── records.py          练习记录 / 未清账目 / 重做
│   │   └── session.py          /prep /judge 无状态兼容端点
│   ├── domain/                  领域契约：值、枚举、状态、校验
│   │   ├── __init__.py
│   │   ├── schema.py           备课/卡点/练习记录契约（值照 11 号文）
│   │   └── session_state.py    12 个会话状态 + 转移表
│   ├── engine/                  业务引擎：流程、备课、判定、审计
│   │   ├── __init__.py
│   │   ├── flow.py             确定性流程编排 + 顺序门（S1—S8）
│   │   ├── prep.py             F2 备课（桩/真模型）
│   │   ├── judge.py            F3 判定（Gate 0 前固定「不判定」）
│   │   └── audit.py            可见性投影 / 答案字段剥离
│   ├── tools/                   工具契约：TOOL_META + Guard
│   │   ├── __init__.py
│   │   └── registry.py         6 个工具的允许状态 + 顺序门
│   └── store/                   存储：会话文档 + 追加式记录
│       ├── __init__.py
│       ├── session_store.py    会话 JSON（原子写）
│       └── jsonl_store.py      练习/卡点/错题 JSONL
├── tests/                       单元 + 流程 + HTTP
│   ├── __init__.py
│   ├── test_schema.py          契约校验
│   ├── test_store.py           追加式存储 / 未清账目
│   ├── test_api.py             HTTP 基础端点 / key 不泄漏
│   ├── test_session.py         /prep /judge / Gate 0
│   ├── test_flow.py            会话状态机 / 守卫 / 可见性
│   └── test_sessions_api.py    会话端点 / 幂等 / 错误码
└── data/                       运行时生成（已 gitignore）
    ├── sessions/<id>.json      一次会话一个文档
    ├── session_events.jsonl    审计事件
    ├── exercises.jsonl         练习记录
    ├── beads.jsonl             卡点记录库
    └── wrong_items.jsonl       错题库
```

---

## 二、模块职责与文档对应

| 目录/文件 | 只负责 | 不负责 | 依据 |
|---|---|---|---|
| `api/sessions.py` | HTTP 状态码、请求体取值、错误映射 | 业务规则、状态转移 | 19 |
| `api/forward.py` | 读题/转发、藏 key、CORS 无关 | 备课/判定的业务 | 19 |
| `api/records.py` | 练习记录 / 未清账目 / 重做 | 会话状态 | 19 |
| `api/session.py` | `/prep` `/judge` 无状态兼容 | 会话状态 | 19 |
| `domain/schema.py` | 值、字段规格、校验 | 存储、流程 | 18 |
| `domain/session_state.py` | 状态枚举、转移表、步骤检查 | 业务动作 | 15/18 |
| `engine/flow.py` | 六个动作 + 顺序门 + 落盘 | HTTP、LLM prompt | 15/17 |
| `engine/prep.py` | F2 解剖、桩模式、JSON 解析 | 判定、会话 | 15 |
| `engine/judge.py` | F3 三态判定 | 备课、会话 | 15 |
| `engine/audit.py` | 学生投影、答案字段剥离 | 业务判断 | 14/18 |
| `tools/registry.py` | 工具允许状态表 + 自检 | 流程实现 | 17 |
| `store/session_store.py` | 会话文档原子读写 | 业务规则 | 18 |
| `store/jsonl_store.py` | 追加式记录 / 合并 | 会话状态 | 18 |

---

## 三、依赖方向

```text
api/  ──→  engine/  ──→  domain/
  │           │
  │           ├──→ tools/
  │           └──→ store/
  └──────────→ domain/

engine/prep.py、engine/flow.py 目前复用 api/forward.py 的模型调用。
这是一处已知的分层妥协：[推断] 后续可抽成 engine/model.py，api/forward.py 只做 HTTP 壳。
```

**禁止**：
- `domain/` 不 import `api/`、`engine/`、`store/`
- `store/` 不 import `api/`、`engine/`
- `engine/` 不 import `api/`（当前 `prep.py`/`flow.py` 对 `api/forward.py` 的依赖是例外，需在重构时消掉）
- `api/` 不写业务规则（状态判断必须在 `engine/flow.py`）

---

## 四、不在这个目录里的

| 东西 | 在哪 | 为什么 |
|---|---|---|
| 前端单页 | `流程步骤/5.创建项目骨架/v1/index.html` | v1 形态是“HTML + 极薄后端” |
| P0 判定测试 | `流程步骤/3.验证与商业/p0_判定可靠性测试/` | 独立工具，零依赖 |
| 产品设计文档 | `流程步骤/4.产品设计/11—24` | 代码只引用，不复制 |
| 家长端 / 教师端 | 不存在 | v1 不做界面（11·决策 6） |
| 数据库 | 不存在 | v1 用 JSON/JSONL（21·ADR-003） |

---

## 五、扩展时放哪

| 要加的东西 | 放哪 | 先改哪份文档 |
|---|---|---|
| 新的流程步骤 | `domain/session_state.py` + `engine/flow.py` | 13、15、18 |
| 新的判定类型 | `domain/schema.py` + `engine/judge.py` | 15、18 |
| 新的工具 | `tools/registry.py` + `api/` | 17、19 |
| 新的存储实体 | `store/` + `domain/` | 18 |
| 变式题（v2） | `engine/variant.py`（待建）+ `store/` | 16 |
| 家长/教师投影（v2） | `api/` + `engine/audit.py` | 14、16 |

> 新增任何模块前，先在 `12-总体架构与骨架` 的骨架地图里补一行，再写代码。
