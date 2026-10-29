# 17. Agent 与工具契约 — 数学审题逐题陪练

> 上游：15、16。下游：18、19。
> 样板 29 号文的 Agent 是「LLM 在工具集里自由选择」；我们的 v1 **不是**。
> 我们是 **确定性流程编排器 + LLM 工具**：流程由状态机决定，LLM 只在「备课 / 判定 / 追问」这几个点上工作。

---

## 一、为什么不是自由 Agent

| 维度 | 自由 ReAct Agent（样板） | 我们 v1 |
|---|---|---|
| 谁决定下一步 | LLM 选工具 | **状态机 + 守卫** |
| 可复现性 | 低（同输入可能不同路径） | 高 |
| 风险 | LLM 可能跳过步骤、提前给结论 | 流程门禁，跳不过去 |
| 适用 | 开放任务、多工具、多意图 | 单流程、短会话、强顺序 |
| LLM 角色 | 编排者 | **工具内部的判断器** |

> 15·§9·决策 6：单流程产品要可测、可复现；流程由状态机守卫，不靠 prompt 自觉。

---

## 二、角色（Persona）

v1 只有 1 个：

| Persona | 定位 | 可见工具 | 禁止 |
|---|---|---|---|
| **Student / 审题教练** | 陪学生把题读懂 | read_problem / prep_problem / judge_answer / probe_implicit / close_session / save_record | 不给答案、不给解法、不点名、不排名 |

v2 预留（只读）：

| Persona | 能看 | 不能看 |
|---|---|---|
| Parent | 一条周摘要（时间维度、类型级） | 逐题明细、排名、其他孩子 |
| Teacher | 匿名班级聚合 | 学生姓名、单个学生详情 |

---

## 三、工具契约（6 个）

每个工具必须写清四件事：**何时用 / 会发生什么 / 下一步 / NOT for**。

### 3.1 `read_problem`

| 项 | 内容 |
|---|---|
| 何时用 | S1 收到图片或文本 |
| 会发生什么 | 图片走模型原生读题（只抄题，不解题）；文本走 F13 兜底不经模型 |
| 下一步 | 返回候选文本 → S2 学生确认 |
| **NOT for** | 不读解答、不批改、不做题库匹配、不猜看不清的字 |
| 返回 | `{text, mode, stub}` |

### 3.2 `prep_problem`

| 项 | 内容 |
|---|---|
| 何时用 | S2 学生确认文本后 |
| 会发生什么 | 把题解剖成分句/类型/级别/隐含条件集合/不确定项；成功即锁定 |
| 下一步 | 返回 `prep` → S4 开场 |
| **NOT for** | 不生成解法、不写讲稿、不在之后重新读题 |
| 返回 | `{prep, stub}` |

### 3.3 `judge_answer`

| 项 | 内容 |
|---|---|
| 何时用 | S5/S6 学生点选后 |
| 会发生什么 | 拿锁定的 `prep` 比对；输出一致/不一致/不判定 |
| 下一步 | 一致→肯定；不一致→线索；不判定→提问 |
| **NOT for** | 不在 P0 未通过时判对错；不点名答案；不跨步骤判 |
| 返回 | `{结果, 依据, 来源}` |

### 3.4 `probe_implicit`

| 项 | 内容 |
|---|---|
| 何时用 | S7 学生提交隐含条件文本，或点「我说不出来」 |
| 会发生什么 | 判断是否命中 `prep.隐含条件集合`；未命中追问一次；仍不行标记 |
| 下一步 | 命中→确认；未命中→追问；说不出→标记继续 |
| **NOT for** | 不直接告诉学生隐含条件是什么；不追问超过一次 |
| 返回 | `{结果, 依据, 可追问}` |

### 3.5 `close_session`

| 项 | 内容 |
|---|---|
| 何时用 | S7 结束 |
| 会发生什么 | 汇总本次做到的具体动作；给出 S8 收束 |
| 下一步 | 结束首体验；邀请写解答（v2） |
| **NOT for** | 不打分、不排名、不说“你没做到” |
| 返回 | `summary` |

### 3.6 `save_record`（v2/S12）

| 项 | 内容 |
|---|---|
| 何时用 | 会话结束且判定可用 |
| 会发生什么 | 写练习记录 + 卡点 + 错题（追加式） |
| 下一步 | 更新「待再看的题」 |
| **NOT for** | 不在 Gate 0 前写 `fail`；不写点名证据到学生可见层 |
| 返回 | `{练习ID, 已写入}` |

---

## 四、TOOL_META 与 Guard

### 4.1 TOOL_META

```python
TOOL_META = {
  "read_problem":   {"personas": ["student"], "call_limit": 3, "requires": []},
  "prep_problem":   {"personas": ["student"], "call_limit": 1, "requires": ["problem_confirmed"]},
  "judge_answer":   {"personas": ["student"], "call_limit": 1, "requires": ["prep_locked", "step_ready"]},
  "probe_implicit": {"personas": ["student"], "call_limit": 2, "requires": ["conditions_done"]},
  "close_session":  {"personas": ["student"], "call_limit": 1, "requires": ["s7_done"]},
  "save_record":    {"personas": ["student"], "call_limit": 1, "requires": ["closed"]},
}
```

- **工具函数对象为键**（样板做法）或名称字符串；启动时做**双向断言**：注册的工具都有元数据、元数据都对应已注册工具。
- `requires` 是顺序门的声明；`flow.py` 用会话状态检查。

### 4.2 Guard 三层（v1 不设审批）

| 层 | 检查 | 失败返回 |
|---|---|---|
| **L1 顺序门** | `requires` 是否满足（如备课未锁定不能 judge） | `E_STATE` |
| **L2 限次** | 同一工具在同一会话/同一目标上的调用次数 | `E_LIMIT` |
| **L3 去重** | 同一工具 + 同一参数（排序后）在短窗口内重复 | `E_DEDUP` |

**没有 L4 审批**：v1 没有破坏性操作（不发布、不扣款、不通知）；不要为了对称硬加审批卡片。

### 4.3 特殊字段剥离

工具结果进入前端/LLM 前，剥离：
- `answer` / `solution` / `final_value` / `reference_step`
- `evidence_ref` / 内部 `target_ref`
- 原始模型输出（只留结构化结果）

> 样板 29 的 §5.3 是剥离 `_component` / `_route`；我们反过来，剥离“答案类字段”。这是「不给答案」的工程级保障，不靠 prompt。

---

## 五、会话状态与上下文

### 5.1 不靠聊天记忆

样板用 checkpointer + 三层记忆；我们的会话状态是**显式 `SessionState`**：

```json
{
  "session_id": "S-...",
  "status": "ANNOTATING",
  "problem": {"confirmed_text": "..."},
  "prep": {"分句": [], "隐含条件集合": [], "不确定项": [], "locked": true},
  "answers": {"S5": {}, "S6": {}, "S7": {}},
  "checkpoints": [],
  "stuck": []
}
```

它替代“LLM 记住讲到哪了”：每步都从服务端状态读，不依赖模型上下文。
短会话（≤15 分钟、≤15 轮）**不需要上下文裁剪**；不要引入摘要把状态丢掉。

### 5.2 事件与审计

| 事件 | 内容 |
|---|---|
| `session.created` | 时间、入口 |
| `problem.read` | mode、stub、耗时 |
| `prep.locked` | 分句数、不确定项数、模型/提示词版本 |
| `answer.recorded` | step、target、result、是否卡住 |
| `checkpoint.recorded` | type、visibility |
| `session.closed` | 总时长、完成率、卡点数 |

写 `data/session_events.jsonl`，追加式；敏感字段脱敏；失败不阻塞主流程。

---

## 六、错误码

| 错误码 | 含义 | 可恢复 | 学生看到 |
|---|---|---|---|
| `E_STATE` | 当前状态不允许该操作 | 是（回原状态） | 「这一步先不能做」 |
| `E_PREP` | 备课失败/不合契约 | 是 | 「我在准备时卡住了，再试一次」 |
| `E_MODEL` | 模型/网络错误 | 是 | 「我没接上，先不判」 |
| `E_TEXT_EMPTY` | 题目文本为空 | 是 | 「题目不能是空的」 |
| `E_NOT_FOUND` | 会话不存在 | 否 | 「这次练习找不到了」 |
| `E_LIMIT` | 超过调用次数 | 否 | 「这一步已经记下了」 |
| `E_DEDUP` | 重复提交 | 否 | 静默忽略 |

---

## 七、与样板的取舍

| 样板 29 | 我们 | 原因 |
|---|---|---|
| 单 Agent + 42 工具 | 确定性编排 + 6 工具 | 单流程、强顺序 |
| Gateway | 无 | 没有“跳页 vs 干活”的意图分流 |
| Persona 4 套 | 1 套（学生） | v1 单端 |
| Guard L4 审批 | 删 | 无破坏性操作 |
| Planner | 删 | 流程固定，状态机更稳 |
| SSE 13 类事件 | JSON 响应 + 事件日志 | 单页短会话，不需要流式 |
| 三层记忆 + 裁剪 | 显式 SessionState | 短会话、强状态 |
| MCP 工具服务器 | 删 | 无外部系统 |

---

> **下一份**：[18-数据模型设计](./18-数据模型设计.md)
