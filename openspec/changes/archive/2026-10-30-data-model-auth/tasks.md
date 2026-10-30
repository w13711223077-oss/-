# Tasks

> **完成定义**：本变更的「完成」= 审查报告、文档契约对齐、后续变更与阻断门分派三类产物齐全；**不是**认证实现、数据迁移或 S9—S12 建模完成。后三项在下方「后续（不属于本变更）」单列，不计入本变更完成度。
>
> 粒度：0.5—1 人日/项；合计约 **3 人日·估算**（审查 1、文档对齐 1、分派与复核 1）。

## 1. 审查

- [x] 1.1 核实 K1—K5（无鉴权、48 bit ID、CORS `*`、无 owner 绑定、进程内锁）并逐条给出证据行号；验证 5 条全部确认
- [x] 1.2 产出数据模型 findings DM-01—DM-08（严重级/证据/后果/选项/成本/是否推翻 ADR）；验证每条都有 `文件:行`
- [x] 1.3 产出认证 findings AU-01—AU-05；验证覆盖越权、过期/吊销、CORS、限速、凭证强度
- [x] 1.4 给出 J1—J3 判定与 Q1—Q5 拍板建议；验证 J3 明确「P0 实测工程可开工，但不得翻开关/进家庭」

## 2. 文档契约对齐

- [x] 2.1 修正 18·§2.9/§四：`session_events.jsonl` 标「已定义未实现」，存储表同步（25·D7）；验证与 `flow.py` 无事件写入一致
- [x] 2.2 修正 19·§一/§3.3/§3.4/§3.6/§六：`/confirm` 不含 `prep`、`/answer` 为 `{verdict, session}`、`GET` 不含 `prep`、`E_DEDUP` 为 v2 预留（25·D1—D4）；验证与 `audit.公开会话`、`flow.作答` 一致
- [x] 2.3 修正 14·§四：删除「只能被创建它的客户端读写」的无支撑承诺，改为「持有 `session_id` 即可读写」，并留修正注（26·K4/AU-02）；验证 Session 字段无 `owner_ref`
- [x] 2.4 新增 26 审查报告并记录沿革；验证 K/DM/AU/J/Q 编号可互相引用
- [x] 2.5 增加 26·§七 归档前复核补记：DM-07 已由 `90e24e0` 修复；测试数 63 与文档 60 的差异转 12·D5；14 修正已落地；验证补记不改变 Q1—Q5

## 3. 门禁与分派

- [x] 3.1 在 design 中登记 `session-auth-hardening`、`session-lifecycle`、`s9-s12-data-model` 三个后续变更与阻断门；验证每个 P0 finding 都有承接变更
- [x] 3.2 归档前核查：本变更范围内无未处理项；P0 实施项全部明示为「未实施、不得误读为已修复」；验证归档摘要保留该清单

## 4. 验证

- [x] 4.1 后端测试：`python -m unittest discover -s tests` → **63 tests OK**
- [x] 4.2 P0 测试：`python -m unittest discover -s tests`（`p0_判定可靠性测试/`）→ **37 tests OK**
- [x] 4.3 代码事实抽查：`main.py` 无鉴权/CORS `*`；`flow.py` 48 bit ID、无 `owner_ref`；`session_store.py` 无 `schema_version`/`expires_at`；`registry.py` 只有 L1；无 `session_events` 写入；`audit.py` summary 已是白名单

## 后续（不属于本变更，未完成）

| 变更 | 内容 | 阻断门 |
|---|---|---|
| `session-auth-hardening` | AU-01/02/03/04/05：token、`owner_ref`、`expires_at`/`revoked_at`、revoke 端点、Origin 白名单、最小限速、监护人告知 | Gate 1 真实家庭前 / 公开分发前 |
| `session-lifecycle` | DM-02/03：`schema_version` + 读时迁移、`expires_at` + 删除入口 + 清理 | Gate 1 前 |
| `s9-s12-data-model` | Q3：补 `SolutionAsset`/`GradeResult` | Gate 2 前 |
| 文档小修 | 12·D5：测试数 60→63 | 不阻断 |
