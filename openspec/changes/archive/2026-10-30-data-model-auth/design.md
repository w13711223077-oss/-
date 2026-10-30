# Design

## Context

审查对象是 18（数据模型）、14（可见性）、19（API）、21（ADR-001/003/006/007）、24（未成年人条款）与 `app/main.py`、`app/api/sessions.py`、`app/engine/flow.py`、`app/store/`。

已核实事实（26·§二）：

- **K1** 全仓无鉴权；`session_id` 是唯一 bearer 凭证。
- **K2** `session_id` = 前缀 + `uuid4().hex[:12]`（48 bit）。
- **K3** CORS `*`，无 Origin 校验、无速率限制。
- **K4** 14·§四 声称「只能被创建它的客户端读写」，但 Session 无 `owner_ref`/客户端绑定。
- **K5** 并发只靠进程内锁 + 原子 rename；多进程/多 worker 会丢写。

审查时点：2026-10-30 20:02。复核时点：HEAD `90e24e0`（20:52）。期间 `90e24e0` 把 `summary` 改为白名单，DM-07 已修复；该事实写入 26·§七 补记。

约束：零依赖；不新增端点；不改 S1—S8、session 存储与可见性投影；不采集学生身份（CLAUDE.md §4/§7）。

## Goals / Non-Goals

**Goals**

- 给数据模型与认证体系一份有证据、有严重级、有成本、有 ADR 影响的审查基线。
- 把 18/19/14 中与代码不符的表述改到「以代码为准」，避免后续变更照旧文档实现。
- 明确 Gate 1 与公开分发前的阻断门，并把 P0 实施项分派到后续变更。

**Non-Goals**

- 不实现认证（token/过期/吊销/Origin/限速/监护人告知）。
- 不做 `schema_version`、迁移、`expires_at`、删除入口、清理任务。
- 不补 EventLog 写入；不扩 S9—S12 的 `SolutionAsset`/`GradeResult`。
- 不修并发模型；不翻 `P0_已通过`；不归档 `p0-judge-reliability`。

## Decisions

### D-01 审查报告只读、只新增

26 号文只做审查与拍板记录，不改代码；文档修正单独落在 18/19/14，并以「沿革/修正注」标注来源（25·D 编号、26·K/AU 编号）。理由：审查与实现分开，避免审查结论被实现细节稀释。

### D-02 Session 文档为唯一真源（Q4=A）

`Answer`/`CheckpointEvent` 在 ER 中保留为「内嵌」，不独立落盘；查询、summary、S9—S12 读 `session.answers`/`session.checkpoints`。理由：改文档 0.5 人日，不动代码；拆实体等 S9—S12 再评估。

### D-03 认证路线（Q1=A）

v1 用标准库补独立 opaque token（≥128 bit，≠ `session_id`）+ 过期/吊销 + 同源/Origin 白名单 + 最小限速；不引账号/登录。理由：不推翻 ADR-001/003；账号留 v2。

### D-04 会话生命周期（Q2=A）

`expires_at` + 单次/全部删除入口 + 定期清理；与 AU-02/DM-03 共用字段。理由：24:67-68 要求删除入口，手动清理无法满足家长自助。

### D-05 S9—S12 数据模型（Q3=A）

Gate 2 前另开变更补 `SolutionAsset`/`GradeResult`；当前不扩 18。理由：提前扩会锁死未验证的批改形态。

### D-06 上线门禁（Q5=A）

公开分发前必须具备：token + 过期 + 删除 + Origin + 最小限速 + 监护人告知（若公开分发），全部前置。理由：24 对未成年人条款从严；AU-03 的跨站读取不能留到上线后。

### D-07 受控实测的边界

Gate 1（3—5 个真实家庭）只在「本机/受控网络 + 操作者在场 + 数据用后删除 + 家长书面告知」下**有条件可接受**；任一条不满足即阻断。Gate 0 离线实测不受认证问题影响。

## Findings 摘要与状态

| 类别 | P0 | P1 | 已处理 |
|---|---|---|---|
| 数据模型 | DM-02（无 `schema_version`）、DM-03（无保留期/删除） | DM-01/04/05/06/07/08 | DM-07（`90e24e0` 已改白名单） |
| 认证 | AU-01（无鉴权）、AU-02（无过期/吊销/owner）、AU-03（CORS `*`） | AU-04（无限速）、AU-05（48 bit ID） | 无 |

> DM-07 的修复只关闭「summary 可能漏答案字段」这一条；不代表其他 P1 已完成。

## Follow-ups（不属于本变更）

| 变更 | 范围 | 阻断门 |
|---|---|---|
| `session-auth-hardening` | AU-01/02/03/04/05：token、`owner_ref`、`expires_at`/`revoked_at`、revoke 端点、Origin 白名单、最小限速、监护人告知 | Gate 1 真实家庭实测前；公开分发前必须全部完成 |
| `session-lifecycle` | DM-02/03：`schema_version` + 读时迁移、`expires_at` + 删除入口 + 清理 | Gate 1 前 |
| `s9-s12-data-model` | Q3：补 `SolutionAsset`/`GradeResult` | Gate 2 前 |
| 文档小修 | 12·D5 测试数 60→63 | 不阻断；下一次文档修正处理 |

## Risks / Trade-offs

- **审查快照会过期** → 26·§七 记录复核时点与差异；后续变更必须重新核对 HEAD。
- **把「已记录」误当「已修复」** → 本变更明确区分 findings 状态与实现状态；归档摘要必须原样保留 P0 未实施清单。
- **文档修正引起契约误读** → 18/19 的修正以代码为准，并留沿革；不改实际端点。
- **认证实施拖延** → 用 Gate 1/公开分发两道阻断门卡住；未完成不得进入真实家庭。
- **14 的隔离表述被再次写成承诺** → 保留修正注与 26·K4 证据，新增能力规格 FR-02 约束。

## Migration Plan

1. 文档修正与审查报告落地（已完成）。
2. 归档本变更，主规格写入 `openspec/specs/data-model/` 与 `openspec/specs/session-auth/`。
3. 按 Follow-ups 另开变更；在每个变更的 proposal 中引用 26 的 finding 编号与阻断门。
4. 回滚：本变更无代码，回滚即恢复 14/18/19/26 的文档改动；不影响运行时。

## Resolved Decisions (2026-10-30)

| # | 问题 | 拍板结论 |
|---|---|---|
| Q1 | v1 认证路线 | A：独立 opaque token + 过期/吊销 + 同源/Origin 白名单（最小版） |
| Q2 | 会话生命周期 | A：`expires_at` + 单次/全部删除入口 + 定期清理 |
| Q3 | S9—S12 数据模型 | A：Gate 2 前另开变更补 `SolutionAsset`/`GradeResult` |
| Q4 | Answer/Checkpoint 真源 | A：Session 文档为唯一真源，ER 标为内嵌 |
| Q5 | 上线门禁范围 | A：token + 过期 + 删除 + Origin + 最小限速 + 监护人告知，全部前置 |
| Q6 | 归档前复核差异 | DM-07 标记已修复；测试数 63 与文档 60 的差异转 12·D5 文档小修 |
