# Spec Delta

## Purpose

定义 Gate 0 判定可靠性的实测能力：用固定样本、标注、运行、指标与门禁，证明「模型判学生标得对不对」的误判正例率为 0，并约束判定开关的开启条件与开启后的行为边界。

## ADDED Requirements

### Requirement: FR-01 样本契约

P0 样本 MUST 为 50—100 道真实七年级应用题，覆盖背景/条件/问题/指令与条件三级；题源只用教材、练习册或教师提供，禁止学生身份信息。样本存放在 `流程步骤/3.验证与商业/p0_判定可靠性测试/samples/`，以 `P001…` 命名，并附 `manifest.json`（题号/来源/年级/结构/是否含隐含条件/授权状态）。

#### Scenario: 合格样本集被接受

- **GIVEN** `samples/` 下有 50—100 道题、每题已标注、`manifest.json` 字段齐全
- **WHEN** 运行 P0 前置检查
- **THEN** 检查通过，并输出题量与覆盖统计

#### Scenario: 样本不足或超量被拒绝

- **GIVEN** `samples/` 下少于 50 道或多于 100 道题
- **WHEN** 运行 P0 前置检查
- **THEN** 检查失败，提示题量不在 50—100 区间

### Requirement: FR-02 标注契约

每题的标注 MUST 包含 `sentences`（i/text/type/level）、`implicit`（集合）、`adjudication_cases`（student_says/truth/why），且至少 4 条「集合外但成立」用例。单人标注；≥20% 题目由**教师**复核；不一致由第三人裁决并记录 `resolution`。

#### Scenario: 集合外但成立的用例存在

- **GIVEN** 某题有学生说法不在标准措辞内但语义成立
- **WHEN** 标注该题的 `adjudication_cases`
- **THEN** 该用例标为 `truth=correct`，并在 `why` 写明「集合外但成立」

#### Scenario: 复核比例达标

- **GIVEN** 样本 80 题、教师复核 16 题
- **WHEN** 检查标注覆盖率
- **THEN** 复核比例 ≥20%，检查通过；低于 20% 则失败

### Requirement: FR-03 运行契约

`p0_judge.py` MUST 读取 `sample_annotation.json` 并输出 `out/model_output.json`；`p0_compare.py` MUST 读取标注与模型输出，输出 `out/P0_报告.txt` 与 `out/P0_摘要.json`。`--baseline` MUST 不联网、可 30 秒内跑完；同一输入、模型版本与提示词版本 MUST 产生同一份指标。

#### Scenario: 基线运行不联网

- **GIVEN** 未配置 `DEEPSEEK_API_KEY`
- **WHEN** 运行 `python p0_judge.py --baseline`
- **THEN** 命令成功退出并写出基线输出，不发起网络请求

#### Scenario: 对照脚本发现故意做错的输出

- **GIVEN** `out/_broken_output.json` 存在
- **WHEN** 运行 `python p0_compare.py --model out/_broken_output.json`
- **THEN** 报告显示误判正例率 >0、红线已破，退出码为 1

### Requirement: FR-04 指标口径

四个指标 MUST 按固定分母计算：句子类型准确率 = 判对的句子数 / 全部句子数；三级准确率 = 判对级别的条件句数 / 全部条件句数；误判正例率 = 被判错的 correct 用例数 / 全部 correct 用例数；说不准率 = 不判定数 / 全部判定请求数。

#### Scenario: 误判正例率按 correct 用例计算

- **GIVEN** 共 20 条 `truth=correct` 的判定用例，其中 1 条被判错
- **WHEN** 计算误判正例率
- **THEN** 结果为 1/20 = 5%，并标记红线已破

#### Scenario: 说不准率按全部判定请求计算

- **GIVEN** 共 100 条判定请求，其中 8 条返回「不判定」
- **WHEN** 计算说不准率
- **THEN** 结果为 8/100 = 8%

### Requirement: FR-05 通过判据

`P0_已通过` 仅当误判正例率 = 0、句子类型准确率 ≥90%、三级准确率 ≥90%、说不准率 ≤10% 时才可置为 True；否则 MUST 保持 False。22·§二只写「不过高」，10% 为 2026-10-30 拍板值（估算，待 P0 实测校准）。

#### Scenario: 四条同时满足才通过

- **GIVEN** 误判正例率 = 0、两类准确率均 ≥90%、说不准率 ≤10%
- **WHEN** 评估 Gate 0
- **THEN** Gate 0 判定为通过，允许进入开关治理流程

#### Scenario: 任意一条不满足即不通过

- **GIVEN** 误判正例率 = 0，但三级准确率为 88%
- **WHEN** 评估 Gate 0
- **THEN** Gate 0 判定为不通过，`P0_已通过` MUST 保持 False

### Requirement: FR-06 开关治理

翻开关 MUST 由项目维护者执行，且执行前 MUST 存在 `out/P0_摘要.json`（含 `passed=true`、模型/提示词/样本版本）；改动 MUST 在 `judge.py` 顶部注释与变更记录中留痕（日期/操作者/依据报告）。无摘要或摘要未通过时 MUST NOT 改 `P0_已通过`。

#### Scenario: 有通过摘要才允许改开关

- **GIVEN** `out/P0_摘要.json` 的 `passed=true`，且记录了三类版本
- **WHEN** 维护者把 `P0_已通过` 改为 True
- **THEN** 变更记录中能追溯到该摘要与日期

#### Scenario: 无通过摘要时拒绝改开关

- **GIVEN** `out/P0_摘要.json` 不存在或 `passed=false`
- **WHEN** 有人尝试把 `P0_已通过` 改为 True
- **THEN** 代码审查 MUST 拒绝该改动

### Requirement: FR-07 可复现

报告 MUST 记录模型 ID 与版本、提示词版本/哈希、样本集版本/哈希、运行时间、执行命令；同一输入与版本 MUST 可复现同一指标。模型非确定性导致的差异 MUST 在报告中标注为「模型波动」，不得静默重跑取最好结果。

#### Scenario: 报告包含可复现五要素

- **GIVEN** 一次 P0 运行完成
- **WHEN** 打开 `out/P0_报告.txt`
- **THEN** 能找到模型版本、提示词版本、样本版本、运行时间、执行命令

#### Scenario: 重跑差异被标注

- **GIVEN** 同一输入与版本连续运行两次，指标不同
- **WHEN** 生成第二次报告
- **THEN** 报告标注「模型波动」及两次差异，不覆盖第一次结果

### Requirement: FR-08 产出与验收

产出 MUST 包含 `P0_报告.txt` 与 `P0_摘要.json`，并满足 25·§6.2 五项：50—100 题已标注、四数字齐全、误判正例率 = 0、可复现、可挂门禁。报告 MUST 逐条列出破红线的用例及模型理由。

#### Scenario: 五项验收齐全

- **GIVEN** P0 运行完成
- **WHEN** 对照 25·§6.2 逐项检查
- **THEN** 五项均有对应证据；缺任一项则验收不通过

#### Scenario: 破红线用例可定位

- **GIVEN** 报告显示误判正例率 >0
- **WHEN** 查看报告明细
- **THEN** 能定位到具体用例、模型输出与理由

### Requirement: FR-09 开关生效后的三态反馈

`P0_已通过=True` 后，S5/S6 的 `/answer` MUST 按 15·§6.1 返回「一致 / 不一致 / 不判定」三态；`不一致` MUST 只给线索、不点名；`不判定` MUST 转为提问。开关未通过时 MUST 继续只返回「不判定」。

#### Scenario: 通过后一致反馈生效

- **GIVEN** `P0_已通过=True`，学生答案与备课一致
- **WHEN** 调用 `/answer`
- **THEN** 返回 `{结果:"一致"}`，并附具体依据

#### Scenario: 未通过时仍不判定

- **GIVEN** `P0_已通过=False`
- **WHEN** 调用 `/answer`
- **THEN** 返回 `{结果:"不判定", 来源:"未上线"}`，不判对错

### Requirement: FR-10 开关生效后的记录与契约边界

开关生效后，S8 的「判定还没上线」提示 MUST 消失；卡点 MUST 仅在判定为 `不一致` 且 `P0_已通过` 为真时写入（15·§7.4、25·D8）；`/answer` 响应形状、session 存储、19 的端点 MUST 不变，且 MUST NOT 返回 `prep/answer/solution`。

#### Scenario: 卡点只在判定为不一致时写入

- **GIVEN** `P0_已通过=True`，S5 判定为不一致
- **WHEN** 提交答案
- **THEN** 写入一条「标注错」卡点；判定为一致时不写 fail

#### Scenario: 对外契约不变

- **GIVEN** 开关从 False 变为 True
- **WHEN** 对比 `/answer` 响应字段
- **THEN** 仍为 `{verdict, session}`，不新增 `prep/answer/solution`
