# 开工前决策清单

> 本节是对 v2 重构计划的前置约束补充，用于避免在 E01 案例材料尚未整理完成前，把实现范围摊得过大。

## A. 开工前必须确定

1. **E01 的原始现象材料**
   - 真实 badcase transcript 是什么。
   - 用户在哪一轮给出纠偏。
   - 模型在哪一轮没有吸收纠偏。
   - 我们认为“失败 / 修复”的可见证据是什么。

2. **新版 case spec 的最小 schema**
   - 第一版建议只锁定：
     - `case_id`
     - `name`
     - `suite`
     - `max_turns`
     - `phenomenon`
     - `seed_scenario`
     - `interaction_script`
     - `observation_focus`
     - `transition_windows`
     - `required_labels`
     - `extension_metrics`
   - 其中最关键的是 `interaction_script` 和 `transition_windows`，它们决定 runner 与 judge 如何跑。

3. **E01 第一版使用固定脚本，而不是 actor 生成用户轮次**
   - 第一版建议 E01 使用固定 `interaction_script`。
   - 不让 actor 参与生成用户轮次，避免同时验证 case schema、target、judge、actor 多层能力。

4. **judge 输出格式**
   - 第一版建议使用统一 observations 结构：

```yaml
observations:
  - unit: turn
    turn_index: 1
    labels: {...}
  - unit: transition
    from_turn: 1
    to_turn: 2
    labels: {...}
```

   - 这样比同时维护 `turn_labels` / `transition_labels` 更容易扩展。

5. **两个 extension metric 的精确定义**
   - `correction_uptake_score`：用户纠偏后，模型是否显式吸收新约束并调整回答策略。
   - `prior_frame_persistence_rate`：用户纠偏后，模型仍沿旧错误线索展开的比例。

6. **第一批 target 组合**
   - 本地：继续使用 `local/transformers`，或明确改为 Ollama。
   - API：继续使用 `openrouter` 的 OpenAI-compatible 通道。
   - 第一阶段不接 Anthropic / Gemini / Responses API 等更多 provider。

7. **验收标准**
   - 能加载 E01 YAML。
   - 能按固定多轮脚本跑一个 local target 和一个 API target。
   - judge 能产出 turn + transition observations。
   - scorer 能计算两个 extension metrics。
   - markdown report 能展示 before / after correction 和 cross-model 对比。

## B. 可以边做边商议

- 完整 taxonomy / family 命名体系。
- 所有旧 case 的迁移策略。
- UI 如何展示异常复盘。
- provider 能力字段如 `supports_tools` / `supports_search` / `supports_reasoning_summary` 的完整设计。
- streaming 接口。
- extension metric 注册系统是否插件化。
- actor 是否参与自动生成 follow-up。
- report 的长期格式和可视化样式。

## C. 建议第一刀

第一刀只做：**E01 fixed-script vertical slice**。

也就是：

1. 新增 E01 case spec。
2. runner 支持 `interaction_script`。
3. judge 支持 transition observation。
4. scorer 支持两个 extension metric。
5. markdown report 展示异常复盘。

这样改动面小，但能验证这份计划最核心的命题：DriftProbe 是否真的能从一个真实异常长出可复现 case。

---

# DriftProbe 重构计划 v2
## 面向真实异常现象复现的黑盒多轮 Probe 框架

## 1. 背景

当前 DriftProbe 更接近一个以固定 failure label 为中心的多轮评测原型：  
它已经能对一些典型失效模式做 case 化处理，例如对齐失败、独白惯性、上下文伪连续、奉承噪声等。

但随着真实使用增多，一个新需求变得更明确：

**我们更需要一个“活”的框架。**  
也就是，当在真实使用某个 chatbot / LLM / API 时遇到一个很怪的现象，能够快速把这个现象抽象成 case，再拿去测试其他模型或接口是否也会复现类似问题。

这意味着框架的中心不应只是“已有标签”，而应逐步转向：

**真实异常现象 → case 抽象 → 跨模型复现 → family 归纳**

本次重构的目标不是把 DriftProbe 收窄成某一种 failure 的专用评测器，而是增强它对**新异常现象的承接、表达、复现和比较能力**。

---

## 2. 重构目标

本次重构的总体目标是：

**将 DriftProbe 重构为一个面向真实异常现象复现的黑盒多轮 probe 框架，支持本地模型与 API 模型并行接入，并允许 score 维度随新问题不断扩展。**

具体来说，重构后框架应具备以下能力：

### 2.1 现象驱动建 case
当遇到一个真实怪问题时，可以较低成本地把它写成可复现 case，而不必先等待完整 taxonomy 成熟。

### 2.2 支持“过程型异常”表达
case 不再只是单轮 prompt，而应能表达：
- 初始场景
- 风险点
- 用户后续动作
- 观察模型后续是否变化

### 2.3 Judge 既能看单轮状态，也能看前后变化
很多真实异常不是某一轮看出来的，而是要看：
- 用户说完某句话后
- 模型下一轮有没有变化

### 2.4 Target 接口从“本地优先”扩展到“本地 + API”
框架应支持：
- 本地模型后端
- 标准 API 模型后端
- 后续跨 provider 扩展

### 2.5 Score 体系支持持续扩维
除了保留核心通用指标外，应允许随着新异常被发现，逐步增加新的观测维度和评分维度。

---

## 3. 不做什么

为了避免重构失控，本次明确**不做**以下事情：

### 3.1 不做白盒机制分析
不尝试恢复：
- system prompt
- attention 细节
- reranker 权重
- 内部 CoT 真相
- 某个 provider 的真实实现机制

框架继续坚持**黑盒行为探针**定位。

### 3.2 不一次性定死完整 failure ontology
taxonomy 可以继续存在，但不应成为接新 case 的门槛。  
新的 family 允许后验归纳，而不是先验穷举。

### 3.3 不推翻现有 actor / target / judge / scorer / reporter 主骨架
本次是**抽象层升级**，不是全项目推倒重来。

### 3.4 不要求所有旧 case 一次性迁移完成
允许新旧 case 暂时并存，先让新结构在 E01 上跑通。

---

## 4. 核心设计变化

## 4.1 从“按固定标签测问题”改为“按真实异常做复现”

### 旧工作流
固定 failure family  
→ 设计 case  
→ 跑模型  
→ 输出标签

### 新工作流
真实异常现象  
→ 抽象为 case  
→ 在不同模型 / API 上复现  
→ 观察行为模式  
→ 再决定是否归纳成 family

这意味着 case 不再只是 benchmark item，而更像一个**异常复现脚本**。

---

## 4.2 Case 的表达能力升级：从 prompt 到异常过程

### 旧 case 更像
- 一个 user prompt
- 一个失败模式预期

### 新 case 应表达
- 真实异常背景
- 初始 query
- 风险线索
- 用户纠偏 / 追问 / 强化动作
- 目标观察点
- judge 边界
- 可选的 case-specific labels

### 结果
case 会更像一段“事故脚本”，而不是一道题。

---

## 4.3 Judge 升级：从单轮状态观察到状态 + 转移双视角

### 旧 judge
主要看：
- 这一轮 assistant output 是否像某种 failure

### 新 judge
同时支持：

#### A. State-level observation
看单轮状态：
- 是否啰嗦
- 是否奉承
- 是否伪连续
- 是否诚实承认不确定
- 是否符合用户当前要求

#### B. Transition-level observation
看前后变化：
- 用户是否发出了新信号
- 模型下一轮是否吸收了新信号
- 是否仍沿旧框架作答
- 是否调整了策略

### 为什么必要
因为很多真实异常不是“这一轮输出烂”，而是：
**“用户都提醒了，它为什么还没变。”**

---

## 4.4 Score 升级：从固定指标集变成 Core + Extension

### Core metrics
长期保留、跨 case 通用的稳定指标，例如：
- `turn_alignment_score`
- `repair_score`
- `context_honesty_score`
- `monologue_persistence_rate`
- `flattery_noise_rate`

### Extension metrics
随着新异常不断扩维，例如：
- `secondary_constraint_overweight_rate`
- `correction_uptake_score`
- `prior_frame_persistence_rate`
- `strategy_adjustment_rate`
- `mechanism_overclaim_rate`

### 原则
不是所有 case 都必须算所有分数。  
而是：
- 通用 case 用 core metrics
- 现象 case 挂 extension metrics
- 新指标可以逐步注册进入 scorer

---

## 4.5 接口层升级：支持本地模型 + LLM API

这次是很关键的一块。

### 当前问题
如果框架默认只围绕本地模型：
- 会限制实际可测对象
- 和你真实遇到怪问题的场景割裂
- 很多典型异常本来就先出现在闭源 / 商用 API / chatbot 上

### 新目标
target / actor / judge 所依赖的模型后端都统一走 adapter interface，支持：

#### Local backend
- Ollama
- vLLM
- Transformers
- 其他本地推理方式

#### API backend
- OpenAI / OpenRouter 风格接口
- Anthropic
- Gemini
- 其他兼容 chat completion / responses 的服务

### Adapter 层建议抽象
统一接口至少包括：
- `generate()`
- `stream_generate()`
- `supports_stream`
- `supports_tools`
- `supports_search`
- `supports_reasoning_summary`
- `provider_name`
- `model_name`
- `metadata`

### 价值
以后同一个 case 可以直接比较：
- 本地开源模型
- 商用 API
- 不同 provider
- 不同能力模式（是否带 search / stream）

这才贴近真实场景。

---

## 5. 本次重构的重点：E01 作为试金石

## 5.1 为什么选 E01
E01 来自真实使用里的一个异常现象，它不是抽象话题，而是一个具体“怪问题”：

- 初始 query 中包含主线索和次级线索
- 模型可能被次级线索劫持
- 用户后续给出明确纠偏
- 观察模型是否更新
- 不依赖唯一标准答案也能评估很多东西

它非常适合检验新框架的几个关键能力：

- case 能否表达异常过程
- judge 能否看“前后变化”
- score 能否扩出新维度
- 本地模型与 API 是否都能跑相同 case

---

## 5.2 E01 的定位
E01 不应视为单纯 `alignment` case，  
更适合作为一个 **E 类现象驱动 case**：

- `E = emergent anomaly / exploratory phenomenon`

建议命名：

- `id: E01`
- `name: recency_fixation_repair`

### E01 想观察的异常
- 次级线索“最近”是否被过度抬权
- 模型是否围绕错误线索持续展开
- 用户纠偏后是否吸收新信号
- 是否仍坚持旧框架
- 是否调整回答策略

### E01 的价值
它不是“以后都测这个”，而是“新框架是否能接住真实异常”的第一块试金石。

---

## 6. 重构范围拆分

## 6.1 Case Spec 重构

### 目标
让 case spec 可以表达“异常过程”，而不只是 prompt。

### 新增建议字段
- `phenomenon`
- `seed_scenario`
- `observation_focus`
- `judge_scope`
- `interaction_script`
- `transition_windows`
- `extension_metrics`

### 结果
以后新异常更容易 onboarding。

---

## 6.2 Judge Schema 重构

### 目标
支持双层观察结果：

```yaml
turn_labels:
  ...
transition_labels:
  ...
```

或更统一的：

```yaml
observations:
  - unit: turn
    labels: ...
  - unit: transition
    labels: ...
```

### Judge 设计边界
judge 不判：
- 模型内部真实意图状态
- 唯一真因
- 不可见内部机制

judge 只判：
- 可见状态
- 可见变化
- 是否出现预期修复行为
- 是否持续旧框架

---

## 6.3 Scorer 重构

### 目标
引入“核心指标 + 扩展指标注册”的机制。

### 需要的能力
- case 可声明自己需要哪些 extension metrics
- scorer 可对未知扩展指标做注册或映射
- 报告层可自动展示 case-specific metric

### 第一阶段建议
先只实现极少数新增维度：
- `correction_uptake_score`
- `prior_frame_persistence_rate`

先跑通，不要贪多。

---

## 6.4 Adapter / Provider 层重构

### 目标
把模型接入从“散落在 runner / judge 里的实现细节”收束到统一 adapter。

### 目标结构
- `local_adapter`
- `api_adapter`
- provider-specific config
- stream support
- metadata support

### 第一阶段建议
先选 1 个本地后端 + 1 个 API 后端跑通。  
例如：
- 本地：Ollama
- API：OpenAI-compatible / OpenRouter-compatible

不要一开始接满所有 provider。

---

## 6.5 Report / UI 重构

### 目标
报告不再只是 transcript + score，而是更像“异常复盘”。

### 建议新增模块
- `phenomenon summary`
- `observation focus`
- `transition window analysis`
- `before / after correction`
- `extension metrics`
- `cross-model comparison note`

### 价值
让你以后可以直接看：
“这个怪问题在别的模型上有没有复现”。

---

## 7. 推荐实施路径

## Phase 1：最小结构升级
目标：不大拆，只让框架能承接“现象驱动 case”。

### 要做
- case spec 增加现象字段
- judge 支持 transition-level labels
- scorer 支持 extension metrics
- target adapter 支持本地 + 一个 API

### 不做
- 不统一所有旧 case
- 不一次性完成 taxonomy 重写
- 不追求全 provider 支持

---

## Phase 2：用 E01 跑通端到端链路
目标：让 E01 成为新结构的第一批成功样例。

### 要跑通的链路
- case 能表达异常链
- judge 能给出 state + transition 观察
- scorer 能算 extension metrics
- local model / API model 都可运行
- report 能展示异常复盘

---

## Phase 3：建立“新异常 onboarding”流程
目标：以后遇到怪问题时，能快速塞进框架。

### 期望工作流
1. 记录真实异常 transcript / 描述
2. 提炼现象和观察重点
3. 写 interaction script
4. 挂上少量 case-specific labels
5. 选择本地 / API 模型复现
6. 比较是否跨模型出现

如果这套流程顺，框架就真正“活”了。

---

## Phase 4：将旧 case 逐步回收进新抽象
目标：避免项目分叉。

### 做法
逐步检查旧 case：
- 哪些只需 state-level judge
- 哪些也适合 transition-level judge

例如：
- A01 可受益于 correction-aware 视角
- B01 可测“被要求简短后是否收缩”
- C01 可测“被指出断链后是否承认”
- D01 可测“被要求别奉承后是否真的调整”

这样新旧结构会渐渐统一，而不是两套平行系统。

---

## 8. 产出物

这次重构应该至少产出以下东西：

### 8.1 新定位文档
重新定义 DriftProbe：
- 现象驱动
- 黑盒复现
- 跨模型比较
- 本地 + API 并行
- score 可扩展

### 8.2 新 case spec 草案
支持“异常过程型 case”。

### 8.3 统一 adapter 抽象
支持本地与 API。

### 8.4 新 judge schema
支持 state + transition。

### 8.5 scorer 扩展机制
支持 extension metrics 注册。

### 8.6 E01 作为第一批样例
验证整套思路不是空话。

---

## 9. 风险与注意点

### 9.1 风险：重构过大
应避免一上来推翻所有旧 case 和旧 scorer。

### 9.2 风险：taxonomy 再次被写死
要保留“先接住异常，再慢慢归类”的弹性。

### 9.3 风险：judge 过度解释
judge 只看可见行为，不去猜内部机制。

### 9.4 风险：API 集成过早做满
先打通一个 API 通道，再扩，不然容易被 provider 细节拖住。

### 9.5 风险：score 无限膨胀
用 `core + extension` 管理，而不是让所有 case 共享所有分数。

---

## 10. 一句话总结

**本次重构不是把 DriftProbe 改造成某一类 failure 的专用评测器，而是把它做成一个更容易从真实异常中长出 case、支持本地与 API 并行复现、并允许 score 维度持续扩展的黑盒多轮 probe 框架。**

