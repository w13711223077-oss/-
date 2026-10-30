# data-model Specification

## Purpose

定义会话数据模型的真源、审计事件状态与 Gate 1 前的生命周期门禁；让 18/19 的契约文档与代码一致，并保证审查发现的缺口可追溯、可承接，而不是被归档动作掩盖。

## Requirements

### Requirement: FR-01 会话文档为唯一真源

`Answer` 与 `CheckpointEvent` MUST 作为 Session 文档的内嵌结构（`answers`、`checkpoints`），MUST NOT 另存为独立落盘实体；查询、S8 summary 与 S9—S12 的读取 MUST 以 Session 文档为准。

#### Scenario: 读取作答与卡点只走 Session

- **GIVEN** 一个已完成 S5—S7 的会话
- **WHEN** 读取作答、卡点或 summary
- **THEN** 数据只来自 `session.answers` / `session.checkpoints` / `session.summary`
- **AND** 不存在与之并列的 `Answer` 或 `CheckpointEvent` 落盘文件

#### Scenario: ER 图中的实体标注为内嵌

- **GIVEN** 阅读 18 的 ER 图与字段表
- **WHEN** 查找 `Answer` / `CheckpointEvent`
- **THEN** 两者被标为 Session 的内嵌结构，而非独立实体

### Requirement: FR-02 审计事件状态必须真实

`session_events.jsonl` MUST 被标注为「已定义、未实现」；在实现之前，文档与 API MUST NOT 声称事件已落盘，Gate 1 的「退出位置 / 每步耗时」MUST NOT 依赖该文件。

#### Scenario: 文档不 overclaim 事件写入

- **GIVEN** 阅读 12、18 或 19 中关于审计事件的表述
- **WHEN** 对照 `app/` 代码
- **THEN** 文档明确标注「已定义未实现」，且代码中不存在 `session_events` 的写入路径

#### Scenario: Gate 1 不把事件日志当数据源

- **GIVEN** Gate 1 需要统计退出位置或每步耗时
- **WHEN** 事件日志尚未实现
- **THEN** 统计不得声称来自 `session_events.jsonl`，须另记人工记录或等实现后再用

### Requirement: FR-03 Gate 1 前的数据生命周期门禁

Gate 1（真实家庭实测）开始前，Session MUST 具备 `schema_version` 与读时迁移方案，并 MUST 具备 `expires_at` + 删除入口 + 清理机制；任一缺失时 Gate 1 MUST NOT 开始。

#### Scenario: 缺版本号时阻断 Gate 1

- **GIVEN** Session 文档没有 `schema_version`、也没有读时迁移
- **WHEN** 评审 Gate 1 是否可开始
- **THEN** 判定为阻断，先由 `session-lifecycle` 补齐

#### Scenario: 缺删除入口时阻断 Gate 1

- **GIVEN** 会话没有 `expires_at`、也没有单次/全部删除入口
- **WHEN** 家长要求删除或评审 Gate 1
- **THEN** 判定为阻断；不得以「会话短命」替代删除权

### Requirement: FR-04 数据模型缺口必须可追溯

数据模型审查结论 MUST 以编号（DM-01—DM-08）记录严重级、证据（`文件:行`）、不处理的后果、修复选项与成本、是否推翻 ADR；任何未修复的 P0/P1 MUST 指定承接变更与阻断门。

#### Scenario: 每条 finding 可回溯到代码

- **GIVEN** 打开 26 号审查报告
- **WHEN** 抽查任一条 DM finding
- **THEN** 能按证据行号在代码中复现该问题或确认其已修复

#### Scenario: 未修复项有承接变更

- **GIVEN** DM-02、DM-03 仍未实现
- **WHEN** 查看后续变更清单
- **THEN** 两者均指向 `session-lifecycle`，并写明 Gate 1 阻断

### Requirement: FR-05 数据契约文档以代码为准

当 18/19 的字段或响应描述与代码不一致时，文档 MUST 以代码为准修正，并在沿革中标注依据（25·D 编号或 26·K/DM 编号）；MUST NOT 反向要求代码照旧文档实现。

#### Scenario: 19 的响应描述与代码对齐

- **GIVEN** `/confirm`、`/answer`、`GET /sessions/{id}` 的实际返回
- **WHEN** 对照 19 的 §3.3/§3.4/§3.6
- **THEN** 文档不再描述 `prep` 外发或旧版 `session_status/progress/checkpoint` 形状
