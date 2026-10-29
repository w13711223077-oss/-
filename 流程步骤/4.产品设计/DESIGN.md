# DESIGN.md — 数学审题逐题陪练 · AI 可执行设计规格

> **合成来源**：[20-前端页面规格]（8 个状态屏的布局/组件/状态/交互）+ [13-信息架构与页面流程]（单页 8 状态）+ [24-合规与安全设计]（禁止项）
> **使用方式**：AI 生成或修改任何本产品界面代码前，必须先读本文件。四段结构：① 设计参数结构化数据块 → ② 跨页面可复用组件模式 → ③ 设计理念的可执行约束规则 → ④ 整体约束与已知缺口。参数冲突时以第一段数据块为准；数据块未覆盖的，查第四段缺口表，**禁止自行发明设计参数**。

---

## 第一段：设计参数结构化数据块（源自 20 号页面规格 + 当前 v1 实现）

```yaml
# ================================================================
# 数学审题逐题陪练 设计系统参数块 · 唯一事实来源：20-前端页面规格 + v1/index.html
# null 值 = 源文档未定义 → 对应第四段缺口编号，使用前需产品方确认
# ================================================================

meta:
  design_philosophy: "一张干净的作业纸"
  metaphor: "页面是纸，AI 是坐在旁边的教练——不抢戏、不发光、不制造紧张"
  pillars:
    - 纸感           # -> 暖纸底 + 白卡面 + 细边框，不用纯白/纯黑
    - 一次一件事     # -> 一屏一个主操作，没有仪表盘、没有多栏
    - 克制           # -> 一个强调色、两套字体、只为卡片和 Toast 加阴影
  principles:
    - 像作业纸，不像 App 商店   # 留白、细线、纸色；不堆装饰
    - 像教练，不像评分器         # 只夸动作、不排名、不打分
    - 像对话，不像表单墙         # 一次一句、一次一个动作

color:
  primary:                      # 【三种声音】定义产品气质
    accent: "#2f6b5f"           # 【教练的声音】主按钮 / 聚焦环 / 反馈左边框 / 品牌
    accent_dark: "#275a50"      # 主按钮 hover
    warm: "#b27a2c"             # 【纸的温度】仅品牌小圆点 / 极少量点缀
  palette:
    paper: "#f6f2e9"            # 页面主背景（暖纸）
    card: "#fffdf8"             # 卡片 / 输入框 / 按钮底
    ink: "#202824"              # 标题 / 正文 / Toast 底
    muted: "#6f776f"            # 说明 / 提示 / 步骤条
    line: "#ddd5c6"             # 1px 边框 / 分隔
    soft: "#f4faf7"             # 反馈底 / 选项 hover 底
    sentence: "#f8f4ea"         # 句子原话块底
    danger: "#a24b3b"           # 错误文字 / 错误边框（只在真实系统错误）
  background_layers:            # 页面背景只允许这三层，不许加别的渐变
    - "radial-gradient(circle at 12% 0%, rgba(178,122,44,.07), transparent 42%)"
    - "radial-gradient(circle at 92% 18%, rgba(47,107,95,.06), transparent 46%)"
    - "var(--paper)"
  semantic:                     # 语义状态：只做文字/细边框，不大面积填充
    info:    { bg: "#f4faf7", text: "#2f6b5f" }   # 反馈 / 提示
    error:   { bg: "#fdf2ef", text: "#a24b3b" }   # 系统错误（不是“答错”）
  chart_palette: null           # v1 没有图表 -> GAP-02

typography:
  heading:
    family: "Songti SC / Noto Serif CJK SC / SimSun, serif"
    size: "clamp(24px, 5vw, 32px)"
    weight: 600
    lineheight: 1.35
  display:                      # 大字 / 收束句
    family: 同上
    size: "clamp(20px, 4.5vw, 26px)"
    weight: 400
    lineheight: 1.75
  sentence:                     # 句子原话
    family: 同上
    size: 19px
    weight: 400
    lineheight: 1.95
  body:
    family: "PingFang SC / Microsoft YaHei / Noto Sans CJK SC, sans-serif"
    size: "15—16px"
    weight: 400
    lineheight: 1.8
    note: "本地系统字体，无 Web 字体依赖"
  small:
    size: "13—14px"
    lineheight: 1.8
  micro:
    size: "12px"
    lineheight: 1.4
  letter_spacing:
    brand_step: ".14em"

radius:
  button: 12
  input: 14
  option: 14
  sentence: 14
  preview: 14
  card: 20            # ≤560px 为 16
  card_mobile: 16
  toast: 999
  dot: "50%"

shadow:
  card: "0 10px 30px rgba(32, 40, 36, .08)"
  toast: "0 8px 24px rgba(32, 40, 36, .18)"
  levels: [card, toast]   # 只有这两处允许阴影

spacing:
  scale: [4, 8, 12, 16, 20, 24, 28, 30, 40, 64]
  page_padding: 20
  card_padding_desktop: "30px 28px"
  card_padding_mobile: "24px 20px"
  max_width: 720
  title_gap: 12
  action_gap: 22
  button_gap: 12
  footer_gap: 22

responsive:
  mobile: "≤560px  单列；卡片 24px 20px / 16px 圆角；S6 选项改一列"
  tablet: "561—720px  单列；卡片 30px 28px；S5 两列 / S6 三列"
  desktop: ">720px  内容仍 720px 居中；不放大字号、不加第二列"
  touch_target: "≥44×44px"
  viewport: "移动优先，430×900 为基准视口"

states:
  loading: "全屏纸色遮罩 + spinner + 一句具体的话（如「我在看题…」）"
  empty: "不显示空表格/空列表；只显示下一步动作"
  error: "错误屏：标题 + 原因 + 「再试一次」+「回到开头」"
  reduced_motion: "prefers-reduced-motion 下关闭所有动画"
```

---

## 第二段：跨页面可复用组件模式（源自 20 号页面规格）

> 从 8 个状态屏中扫描出的重复组件。每个模式 = 基础结构 + 变体 + 使用条件。新页面遇到同类需求，MUST 复用以下模式，禁止另起炉灶。

### P-01 顶栏 `top-bar`

品牌名（衬线、15px、`--accent`、字距 .14em）在左；语音开关（ghost 按钮）在右；最大宽度 720px，左右 20px，顶部 22px。出现页面：全部 8 屏。

### P-02 步骤条 `step-label`

卡片上方一行 12px `--muted` 小字，格式 `S5 · 逐句标注`，字距 .14em。只显示当前步骤与名称；**禁止**进度条、百分比、步骤圆点。

### P-03 屏幕卡片 `screen-card`

`--card` 底、1px `--line` 边、20px 圆角、`30px 28px` 内边距、`--shadow` 阴影；≤560px 改 16px 圆角 + `24px 20px`。一屏只有一个卡片。

### P-04 按钮 `button`

| 变体 | 视觉 | 使用条件 |
|---|---|---|
| `btn-primary` | `--accent` 底、白字、12px 圆角、`12px 18px` | 一屏唯一主操作（拍照/确认/开始/说说看/继续） |
| `btn-secondary` | 白底、`--line` 边框 | 次操作（粘贴题目、重新拍） |
| `btn-ghost` | 透明底、无边框、`--muted` 文字、`8px 10px` | 低权重（重新开始、先记下来、我说不出来） |

### P-05 选项网格 `option-grid`

| 变体 | 结构 | 使用条件 |
|---|---|---|
| `options-four` | 2×2 网格，4 项，每项 `<b>主词</b><span>一句话解释</span>` | S5 逐句标注（背景/条件/问题/指令） |
| `options-three` | 3 列，3 项，同样结构 | S6 条件定级（直接/间接/隐含）；≤560px 改一列 |

每项：白底、1px `--line`、14px 圆角、`14px 16px`；hover 边框 `--accent`、底 `--soft`；禁用 `opacity:.45`。

### P-06 文本域 `textarea`

白底、1px `--line`、14px 圆角、`14px 16px`、15px/1.85；focus 3px `rgba(47,107,95,.16)` 外环 + `--accent` 边框。用于 S2 确认题目、S7 隐含条件。

### P-07 句子原话 `sentence-block`

`--sentence` 底、14px 圆角、`18px 20px`、衬线 19px/1.95。只显示原句；**禁止**在句子上标类型/级别/高亮。

### P-08 反馈区 `feedback`

`margin-top:20px`、`16px 18px`、左边框 3px `--accent`、`--soft` 底、`0 14px 14px 0` 圆角；主句 16px/600，补充 14px `--muted`，下方一个「继续」主按钮。出现于 S5/S6/S7。

### P-09 Toast `toast`

底部居中、`--ink` 底、白字、14px、`10px 16px`、999px 圆角、底部 28px、2.8 秒消失、不阻断操作。

### P-10 加载层 `busy-overlay`

全屏 `rgba(246,242,233,.82)` + `backdrop-filter: blur(2px)`；spinner 18px、2px、`--line` 底 + `--accent` 顶；一句具体的话（「我在看题…」「我在把这道题拆开…」）。**禁止**骨架屏闪光/彩带/弹窗式 loading。

### P-11 图片预览 `image-preview`

`width:100%; max-height:320px; object-fit:contain;` 1px `--line`、14px 圆角、白底。**禁止**裁切题目、滤镜、放大镜。

### P-12 家长说明 `parent-note`

页脚一行 12px `--muted` 居中：「给家长：它不给答案，只教孩子把题读懂。」只在页面底部出现一次；**禁止**放进学生主流程。

---

## 第三段：设计理念的可执行约束规则（源自 20 号页面规格 + 24 号合规）

> 每条规则 = MUST / MUST NOT / SHOULD + 正例反例。AI 生成界面时逐条自查，违反任意 MUST 即视为不合格输出。

### Color Rules

- **R-C1 · 主操作按钮** MUST 使用 `--accent #2f6b5f` 实心背景 + 白色文字。
  正例：S1「拍照 / 选图」、S4「开始读题」、S5/S6「继续」。
  反例：用 `--warm` 做「开始读题」按钮——暖金是纸的温度，不是系统命令。
- **R-C2 · `--warm #b27a2c` 只用于品牌小圆点和极少量点缀**，NEVER 用于主按钮、正文、大面积背景。
- **R-C3 · 页面背景** MUST 为 `--paper #f6f2e9` + 第一段规定的两层极淡径向渐变；卡片/输入 MUST `--card #fffdf8`；句子块 MUST `--sentence #f8f4ea`。
- **R-C4 · 文字层级**：标题/正文 MUST `--ink #202824`；说明/提示/步骤 MUST `--muted #6f776f`；边框 MUST `--line #ddd5c6`。
- **R-C5 · `--danger #a24b3b` 只用于真实系统错误**（服务端/网络/契约），NEVER 用于「答错」——本产品不说「你错了」。
- **R-C6 · 语义状态** MUST 用「浅底 + 深字」或文字说明，NEVER 用整块纯色表达状态。
- **R-C7 · NEVER 自行发明新颜色**。色板之外的颜色一律不许出现；确需新增，先更新本文件第一段。

### Typography Rules

- **R-T1 · 衬线字体只用于 h1、大字、句子原话**；正文/按钮/输入/说明 MUST 用无衬线系统字体栈。NEVER 用衬线排正文。
- **R-T2 · 正文最小 13px；按钮/输入 15px；h1 最小 24px**。NEVER 用 12px 以下排正文。
- **R-T3 · 中文正文行高 MUST ≥1.8；句子原话 ≥1.9；标题 1.35**。
- **R-T4 · 禁止引入 Web 字体依赖**；只用本地系统字体（PingFang / Microsoft YaHei / Noto Sans / Songti / SimSun）。
- **R-T5 · 品牌名/步骤条** MUST `letter-spacing:.14em`；正文 NEVER 加字距。

### Spacing Rules

- **R-S1 · 所有间距 MUST 落在 4 的倍数上**（允许 2 的倍数做微调）；NEVER 用「差不多」的间距。
- **R-S2 · 页面左右 padding MUST 20px；内容最大宽度 MUST 720px 居中**。
- **R-S3 · 卡片内边距 MUST 桌面 `30px 28px`、≤560px `24px 20px`**。
- **R-S4 · 标题与副标题 12px；副标题与操作区 22px；按钮组 gap 12px；卡片与页脚 22px**。
- **R-S5 · NEVER 用 margin 堆出超过 64px 的空白**（除页面底部安全区）。

### Radius & Shadow Rules

- **R-R1 · 圆角五档**：按钮 12px · 输入/选项/句子/图片 14px · 卡片 20px（移动 16px）· Toast 999px · 圆点 50%。NEVER 混用其他圆角。
- **R-R2 · 阴影只允许两处**：卡片 `0 10px 30px rgba(32,40,36,.08)`、Toast `0 8px 24px rgba(32,40,36,.18)`。NEVER 给按钮/选项/输入加阴影。
- **R-R3 · NEVER 用内阴影、彩色阴影、多层阴影、玻璃拟态**。

### Layout Rules

- **R-L1 · 单列布局**：MUST 最大宽度 720px；NEVER 做侧边栏、三栏、仪表盘。
- **R-L2 · 一屏一个主操作**：MUST 每屏只有一个 primary 按钮；NEVER 出现两个同权重主按钮。
- **R-L3 · 顶栏** MUST 品牌在左、语音开关在右；**步骤条** MUST 在卡片上方一行。
- **R-L4 · 没有首页/菜单/导航条/进度条**；打开就是 S1。
- **R-L5 · 图片预览** MUST 完整显示题目，不裁切。

### Component Rules

- **R-P1 · 选项** MUST 是「主词 + 一句话解释」的卡片按钮；NEVER 做成纯色块、图标卡片、带勾选动画。
- **R-P2 · 选项数量**：S5 MUST 4 个（2×2）；S6 MUST 3 个（3 列）；NEVER 增加第 5 个选项。
- **R-P3 · 句子块** MUST 只显示原句；NEVER 提前标类型/级别/关键词。
- **R-P4 · 反馈区** MUST 用 `--accent` 左边框 + `--soft` 底；NEVER 用红色“错误”反馈。
- **R-P5 · 文本域** NEVER 自动聚焦（移动端会弹键盘）；用户主动点才聚焦。
- **R-P6 · Toast** MUST 2.8 秒消失、不阻断操作；NEVER 用弹窗替代轻提示。
- **R-P7 · 加载层** MUST 全屏覆盖 + 一句具体的话；NEVER 只转圈不写字。

### State Rules

- **R-ST1 · 每个屏 MUST 覆盖三态**：加载（P-10）· 空（只显示下一步动作）· 错误（错误屏 + 重试）。
- **R-ST2 · S1/S2** MUST 允许重拍/重贴；识别错是客观风险。
- **R-ST3 · S3 备课失败** MUST 停在错误屏，给「再试一次」；NEVER 带着失败硬走。
- **R-ST4 · 40 秒记卡住** MUST 显示「这一步先记下来，我们继续」；NEVER 弹出惩罚性提示。
- **R-ST5 · 空态** MUST 告诉用户「可以做什么」，NEVER 只写「暂无数据」。

### Interaction Rules

- **R-I1 · 点选后** MUST 禁用当前选项并显示反馈；反馈里的「继续」才推进下一步。
- **R-I2 · 15 秒无动静** MUST 给一条线索；**40 秒** MUST 记「卡住」并继续。
- **R-I3 · S7「说不出来」** MUST 延迟 15 秒出现；NEVER 一上来就把它做成默认主按钮。
- **R-I4 · 任何一步 NEVER 自动进入下一步**（除 40 秒记卡住后的继续）；必须由学生点「继续」。
- **R-I5 · 产品里 NEVER 出现答案/解析/解法入口**；不提供「查看答案」。
- **R-I6 · 语音** MUST 可开关；只读教练话术，NEVER 朗读题目正文。

### Accessibility Rules

- **R-A1 · 触控目标** MUST ≥44×44px；按钮高度 ≥44px。
- **R-A2 · 文字与背景对比度** MUST ≥4.5:1；`--muted` 只用于辅助信息。
- **R-A3 · 反馈区** MUST `aria-live="polite"`；键盘可 Tab/Enter。
- **R-A4 · `prefers-reduced-motion`** 下 MUST 关闭所有动画。
- **R-A5 · 状态不能只靠颜色**；必须有文字说明。

### Content Rules

- **R-CT1 · NEVER 说「你错了」「你又漏了」**；只说线索、提问、具体动作。
- **R-CT2 · NEVER 出现分数、排名、积分、连续打卡、排行榜、徽章**。
- **R-CT3 · S8 NEVER 出现「再来一题」大按钮**；只有小号 ghost「重新开始」。
- **R-CT4 · 对学生说「待再看的题」**，NEVER 说「错题库」「未清账目」。
- **R-CT5 · 「不给答案」只对家长说**（页脚一行）；学生侧说「它觉得你能想出来」。

---

## 第四段：整体约束与已知缺口

### 整体约束

1. AI 生成或修改任何本产品界面代码前，**必须先读本文件**。
2. 参数冲突时以第一段数据块为准；数据块未覆盖的，查本段缺口表；**禁止自行发明设计参数**。
3. 修改 20 号页面规格时，MUST 同步更新本文件第一段。
4. 8 个状态屏不是 8 个孤岛：状态由服务端会话状态驱动（见 13/15/19），前端只渲染 `progress.next`，不自己记流程。
5. 页面口径：v1 = 单页 8 状态（S1—S8）；S9—S12、家长端、教师端不在 v1 视觉范围内（见 GAP-03）。

### 已知缺口（源文档未定义 → 默认处理方式）

| 编号 | 缺口 | 默认处理方式 |
|---|---|---|
| GAP-01 | 图标体系未定义（20 号只规定文字/按钮，没有图标库） | 不引入图标库；只用文字按钮；圆点仅作品牌点缀 |
| GAP-02 | 图表配色未定义（v1 没有图表） | 不实现图表；未来图表只用 `--accent` + `--warm` + `--muted`，禁止新增色 |
| GAP-03 | S9—S12、家长端、教师端的视觉未定义 | 暂不设计；先按 13/16 的流程与 14 的可见性定结构，再补 20/DESIGN |
| GAP-04 | 深色模式未定义 | 不实现深色模式；v1 只有浅色纸感 |
| GAP-05 | 561—720px 的平板细节未单独定义 | 复用单列 + 桌面内边距；不加第二列 |
| GAP-06 | 除 spinner/Toast 外的动效未定义 | 默认只用 ≤200ms 的边框/背景过渡；不加页面切换动画 |
| GAP-07 | 间距尺度最初未定义（现已补 4px 体系） | 以第一段 `spacing.scale` 为准；不得使用表外值 |
| GAP-08 | 聚焦环除 `rgba(47,107,95,.16)` 外未定义 | 统一使用该值；不新增第二种 focus 样式 |
| GAP-09 | 字号最初未定义（现已补） | 以第一段 `typography` 为准；不新增字号档 |

---

*本文件由 AI 按四段流程从 20-前端页面规格 + 13-信息架构与页面流程 + 24-合规与安全设计 合成；生成后已人工复核（色值对照 / 组件覆盖 / 规则精确性 / 缺口完整度）。源文档更新时需重新生成并复核。*
