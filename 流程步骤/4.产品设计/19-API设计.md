# 19. API 设计 — 数学审题逐题陪练

> 上游：15、16、17、18。下游：20。
> 样板 34 号文有 50+ 端点 + SSE + JWT；我们 v1 只有 **1 组会话端点 + 1 组记录端点 + 2 个兼容端点**，没有账号、没有 SSE、没有 JWT。

---

## 一、约定

| 项 | 约定 |
|---|---|
| Base | `http://127.0.0.1:8787` |
| 内容类型 | `application/json; charset=utf-8` |
| 命名 | 字段用中文（与 11/18 一致）；路径用英文 |
| 认证 | v1 无账号；只有 `session_id` 做隔离；上线前必须补鉴权 |
| 幂等 | `answer` 对同一 `target_ref` 只接受一次；重复返回 409/`E_LIMIT`（`E_DEDUP` 为 v2 预留） |
| 错误 | `{错误, 码, 提示?}`；HTTP 状态码 + 业务码 |
| 时间 | ISO 8601，带时区 |

---

## 二、端点矩阵

### 2.1 会话（S1—S8）

| 方法 | 路径 | 干什么 | 状态变化 |
|---|---|---|---|
| POST | `/api/v1/sessions` | 创建会话 | → `CREATED` |
| POST | `/api/v1/sessions/{id}/problem` | 上传图片/文本，读题 | `CREATED` → `READING` → `CONFIRMING` |
| POST | `/api/v1/sessions/{id}/confirm` | 确认文本 + F2 备课 | `CONFIRMING` → `PREPARING` → `READY` |
| POST | `/api/v1/sessions/{id}/start` | S4 开场完成 | `READY` → `ANNOTATING` |
| POST | `/api/v1/sessions/{id}/answer` | S5/S6/S7 作答 | 见下 |
| POST | `/api/v1/sessions/{id}/close` | S8 收束 | `CLOSING` → `CLOSED` |
| GET | `/api/v1/sessions/{id}` | 读会话状态 | — |
| POST | `/api/v1/sessions/{id}/discard` | 丢弃 | 任意非终态 → `DISCARDED` |

### 2.2 兼容/底层

| 方法 | 路径 | 干什么 |
|---|---|---|
| POST | `/api/v1/model/read` | F1 读图/文本（无状态） |
| POST | `/api/v1/model/forward` | 通用转发（藏 key） |
| POST | `/api/v1/prep` | F2 备课（无状态，供脚本/测试） |
| POST | `/api/v1/judge` | F3 判定（无状态，Gate 0 前不判定） |

### 2.3 记录

| 方法 | 路径 | 干什么 |
|---|---|---|
| POST | `/api/v1/exercises` | S12 写练习记录（两个库） |
| GET | `/api/v1/exercises` | 读练习记录 |
| GET | `/api/v1/pending` | 未清账目 |
| POST | `/api/v1/wrong-items/done` | 标记错题已重做 |

### 2.4 元信息

| 方法 | 路径 | 干什么 |
|---|---|---|
| GET | `/api/v1/health` | 状态、桩模式、key 是否配置、端点列表 |
| GET | `/api/v1/schema` | 数据契约（枚举 + 规格） |

---

## 三、会话端点契约

### 3.1 `POST /api/v1/sessions`

请求：`{}`（可选 `{"first_experience": true}`）
响应 `201`：

```json
{
  "session_id": "S-3f8a1c2d9e04",
  "status": "CREATED",
  "first_experience": true,
  "created_at": "2026-10-29T19:30:00+08:00"
}
```

### 3.2 `POST /api/v1/sessions/{id}/problem`

请求二选一：

```json
{"mode": "image", "image_data_url": "data:image/jpeg;base64,..."}
{"mode": "text", "text": "七年七班计划组织学生去植物园研学……"}
```

响应 `200`：

```json
{
  "session_id": "S-...",
  "status": "CONFIRMING",
  "text": "七年七班计划组织学生去植物园研学……",
  "mode": "image",
  "stub": false
}
```

错误：`E_STATE`（不是 CREATED）、`E_MODEL`、`E_TEXT_EMPTY`。

### 3.3 `POST /api/v1/sessions/{id}/confirm`

请求：`{"text": "学生确认后的题目文本"}`
响应 `200`：

```json
{
  "session": {
    "session_id": "S-...",
    "status": "READY",
    "problem": {"confirmed_text": "..."},
    "progress": {"step": null, "answered": 0, "total": 0, "next": null},
    "checkpoints": {}
  },
  "桩": false
}
```

> ⚠️ **prep 不得出现在任何对外响应中**（14·§三）。`/confirm` 只返回学生投影；备课解剖（分句 / type / level / 隐含条件集合 / note）只留在服务端，供 S5/S6/S7 使用。

错误：`E_STATE`、`E_PREP`（备课失败/不合契约）、`E_TEXT_EMPTY`。

### 3.4 `POST /api/v1/sessions/{id}/answer`

请求：

```json
{"step": "S5", "target_ref": "sentence:0", "input": "背景"}
{"step": "S6", "target_ref": "condition:0", "input": "直接"}
{"step": "S7", "target_ref": "implicit", "input": "总人数不变"}
{"step": "S7", "target_ref": "implicit", "input": "我说不出来", "can_not_say": true}
```

响应 `200`：

```json
{
  "verdict": {"结果": "不判定", "依据": "判定可靠性还没测（P0 未通过）。这一步改为提问，不判对错。", "来源": "未上线"},
  "session": {
    "session_id": "S-...",
    "status": "ANNOTATING",
    "progress": {
      "step": "S5", "answered": 1, "total": 5,
      "next": {"step": "S5", "target_ref": "sentence:1", "text": "..."}
    },
    "checkpoints": {}
  }
}
```

- `S5` 全部完成 → `GRADING_CONDITIONS`；`S6` 全部完成 → `PROBING_IMPLICIT`；`S7` 结束 → `CLOSING`。
- `S7` 最多两次（首次 + 追问一次）；第二次或 `can_not_say` 后 `done=true`。
- **学生响应里不返回 `target_ref` 证据以外的内部字段**；`session.checkpoints` 只给 `{type: count}` 聚合，不给具体句子/条件。

错误：`E_STATE`（步骤不对）、`E_LIMIT`（同一目标已答）、`E_MODEL`。

> `E_DEDUP` 是 v2 预留；当前没有去重，重复答同一目标返回 `E_LIMIT`（25·D4）。

### 3.5 `POST /api/v1/sessions/{id}/close`

请求：`{}`
响应 `200`：

```json
{
  "session_id": "S-...",
  "status": "CLOSED",
  "summary": {
    "headline": "这道题你已经读明白了。",
    "did": ["你一句一句看了 5 句", "亲手标了 5 句", "给 2 条条件定了级"],
    "note": "这次判定还没上线，所以我只提问、没有判对错；没有写入卡点库。",
    "duration_seconds": 720
  }
}
```

错误：`E_STATE`（不是 CLOSING）。

### 3.6 `GET /api/v1/sessions/{id}`

返回会话的**学生投影**：状态、题目确认文本、`progress`（当前步 / 下一步）、卡点聚合、summary。
**不返回 `prep`**（分句 / 类型 / 级别 / 隐含条件集合），也不返回原始图片、内部证据、`answer/solution`（14·§三）。

### 3.7 `POST /api/v1/sessions/{id}/discard`

响应 `200`：`{"session_id": "...", "status": "DISCARDED"}`。终态不可再答。

---

## 四、无状态端点

### 4.1 `POST /api/v1/prep`

请求：`{"题目原文": "..."}` → 响应 `{"备课": {...}, "桩": false}`。
与 `confirm` 内部调用同一 `engine/prep.py`；保留它是为了 P0/脚本/测试可以直接打。

### 4.2 `POST /api/v1/judge`

请求：`{"备课解剖": {...}, "学生输入": "...", "步骤": "S5"}` → 响应 `{"结果":"不判定","依据":"...","来源":"未上线"}`。
Gate 0 前固定不判定；P0 通过后只换引擎实现，契约不变。

### 4.3 `POST /api/v1/model/read`

请求：`{"mode":"image","image_data_url":"..."}` 或 `{"mode":"text","text":"..."}` → `{"text":"...","mode":"...","桩":false}`。
**只抄题，不解题**；文本模式不经模型（F13 兜底）。

---

## 五、错误码与状态码

| HTTP | 业务码 | 含义 | 前端动作 |
|---|---|---|---|
| 400 | `E_STATE` | 当前状态不允许 | 回到正确步骤 / 重开会话 |
| 400 | `E_TEXT_EMPTY` | 文本为空 | 提示补全 |
| 404 | `E_NOT_FOUND` | 会话不存在 | 回开头 |
| 409 | `E_LIMIT` | 同一目标已答 | 忽略，显示已记录 |
| 422 | `E_CONTRACT` | 备课/记录不合契约 | 显示明细，重试 |
| 502 | `E_MODEL` | 模型/网络错误 | 重试 / 桩模式 |
| 503 | `E_NO_KEY` | 服务端无 key | 提示设 key 或开桩模式 |

---

## 六、安全与限制

| 项 | v1 |
|---|---|
| API key | 只在服务端环境变量；响应中永不出现 |
| CORS | `Access-Control-Allow-Origin: *`（v1 受控使用；上线前收紧） |
| 鉴权 | 无；**上线前必须补**（11·§8） |
| 限流 | 无；单机自用 |
| 原图 | 不落盘；请求结束丢弃 |
| 会话 ID | 随机 12 位；不可枚举 |
| 日志 | 不记录题目全文到 stdout；事件日志脱敏 |

---

## 七、与样板 34 的差异

| 样板 | 我们 |
|---|---|
| 50+ 端点、JWT、SSE | 11 个会话/记录端点 + 4 个兼容端点 |
| 多角色登录 | 无账号 |
| SSE 13 类事件 | JSON 响应 + 事件 JSONL |
| 统一错误码体系 | 7 个业务码 |
| OpenAPI 自动生成 | 零框架，`GET /schema` 手写契约 |

---

> **下一份**：[20-前端页面规格](./20-前端页面规格.md)

---

## 沿革

- **2026-10-30**：按 25·§2.2 修正 D1—D4（/confirm 不再返回 prep；/answer 改为 `{verdict, session}`；GET 不含 prep；`E_DEDUP` 标为 v2 预留）。
