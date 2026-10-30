# Spec Delta

## Purpose

记录 v1「无认证」的真实边界、隔离强度与上线前最小认证门禁；防止把 `session_id` 隔离误当成身份认证，也防止文档再次作出代码不支持的隔离承诺。

## ADDED Requirements

### Requirement: FR-01 v1 无认证的边界必须写实

v1 MUST NOT 声称具备账号、登录或身份认证；文档 MUST 明确 `session_id` 是 bearer 凭证、持有即可读写；该现状 MUST 在 14/19/21/26 中一致。

#### Scenario: 文档一致声明无鉴权

- **GIVEN** 阅读 14·§四、19·§一/§六、21·ADR-007、26·§四
- **WHEN** 查找认证状态
- **THEN** 四处一致写明「v1 无账号/无鉴权，`session_id` 是唯一凭证，上线前必须补」

#### Scenario: 代码中不存在鉴权检查

- **GIVEN** 审查 `app/main.py` 与 `app/api/sessions.py`
- **WHEN** 查找 token、签名或 owner 校验
- **THEN** 不存在任何鉴权路径；任意合法 `session_id` 可直接读写

### Requirement: FR-02 隔离表述不得超出实现

在 `owner_ref` 与客户端绑定实现之前，文档与 API MUST NOT 声称「会话只能被创建它的客户端读写」；隔离强度 MUST 表述为「持有 `session_id` 即可读写」。

#### Scenario: 14 的隔离表述与字段一致

- **GIVEN** Session 字段表没有 `owner_ref`
- **WHEN** 阅读 14·§四
- **THEN** 不再出现客户端绑定承诺，且保留指向 26·K4/AU-02 的修正注

#### Scenario: 不提供列表接口

- **GIVEN** v1 的端点矩阵
- **WHEN** 查找会话列表
- **THEN** 不存在列表端点；跨会话访问仍只靠猜中 `session_id`

### Requirement: FR-03 学生投影不得包含备课与答案

`/confirm`、`/answer`、`GET /sessions/{id}` 的学生响应 MUST NOT 返回 `prep`、`type`、`level`、`implicit_set`、`note`、`target_ref`、`answer`、`solution`；MUST 只返回 `{verdict, session}` 等学生投影字段。

#### Scenario: 三个端点都不外发 prep

- **GIVEN** 一个 `locked=true` 的会话
- **WHEN** 调用 `/confirm`、`/answer`、`GET /sessions/{id}`
- **THEN** 响应中不出现 `prep` 及其内部分句/级别/隐含集合

#### Scenario: summary 走白名单

- **GIVEN** 会话 `summary` 新增了一个字段
- **WHEN** 生成学生投影
- **THEN** 只有 `headline/did/note/duration_seconds` 被输出，未知字段不外发

### Requirement: FR-04 公开分发前的最小认证门禁

在公开分发前，系统 MUST 同时具备：独立 opaque token（≥128 bit，≠ `session_id`）、`expires_at`、`revoked_at` + 删除入口、Origin 白名单/同源、最小速率限制，以及（若公开分发）监护人告知/同意留痕；缺任一项 MUST NOT 公开分发。

#### Scenario: 缺 Origin 白名单时阻断上线

- **GIVEN** CORS 仍为 `Access-Control-Allow-Origin: *` 且无 Origin 校验
- **WHEN** 评审是否可公开分发
- **THEN** 判定为阻断，先由 `session-auth-hardening` 补齐

#### Scenario: 缺过期/吊销时阻断上线

- **GIVEN** 会话没有 `expires_at`/`revoked_at`，也没有删除入口
- **WHEN** 家长要求删除或评审上线
- **THEN** 判定为阻断；不得以「v1 受控使用」跳过

### Requirement: FR-05 受控实测的条件

Gate 1（3—5 个真实家庭）MUST 同时满足：本机/受控网络、操作者在场、数据用后删除、家长书面告知留痕；任一缺失 MUST NOT 开始真实家庭实测。

#### Scenario: 条件不齐时不开 Gate 1

- **GIVEN** 计划在真实家庭设备上做 Gate 1
- **WHEN** 缺少家长书面告知或数据用后删除方案
- **THEN** 判定为阻断，改为本机/受控环境或补齐条件后再开

#### Scenario: Gate 0 离线实测不受影响

- **GIVEN** 认证与生命周期缺口尚未修复
- **WHEN** 执行 Gate 0 的离线 P0 实测
- **THEN** 允许进行；样本与脚本不经过 session API、不写产品库

### Requirement: FR-06 认证缺口必须分派

AU-01—AU-05 MUST 以编号记录严重级、证据与修复选项；P0 项（AU-01/02/03）MUST 在 Gate 1 真实家庭前承接，P1 项（AU-04/05）MUST 在公开分发前承接；承接变更 MUST 为 `session-auth-hardening`。

#### Scenario: 每个 P0 认证项有承接

- **GIVEN** 打开 26 的认证 findings
- **WHEN** 查看 AU-01、AU-02、AU-03
- **THEN** 每条都指向 `session-auth-hardening`，并标注 Gate 1 前完成
