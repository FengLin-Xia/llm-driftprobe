# DriftProbe

*Chatbot Stress Test* 参考实现（v0）。展开下方 **中文** 或 **English** 阅读完整介绍、默认栈与上手步骤。  
Runnable reference for **Chatbot Stress Test** (v0) — expand **中文** or **English** for the full guide, stack, and setup.

🇨🇳 中文

## 项目简介

**DriftProbe** 是一个面向多轮 LLM 系统的黑盒故障探针框架。  
它不试图还原模型不可见的内部机制，而是聚焦于**可观察的对话失效模式**，例如：指令重新对齐失败、次级约束过载、上下文伪连续、独白惯性、奉承噪声，以及错误后的过度自信解释。

项目目标不是回答“模型内部究竟怎么想”，而是更稳定地回答：

- 模型在第几轮开始跑偏
- 用户纠偏后是否真正修复
- 哪类约束被错误放大
- 失败更像是理解偏差、修复失败，还是解释升级
- 不同模型、不同 case 之间的失效模式如何比较

---

## 核心思路

DriftProbe 采用三角色评测结构：

```text
Actor
  → 生成或选择 user turn，持续向目标模型施加刺激

Target
  → 被测多轮对话模型

Judge
  → 对每轮输出结构化标签

Scorer / Reporter
  → 聚合指标并生成可比较报告
```

三个角色相互分离，可独立替换。  
这种设计让框架既能支持固定脚本测试，也能支持更动态的多轮 probing。

---

## 当前关注的失败模式

DriftProbe 目前主要覆盖以下几类可观察失效：

- **Alignment failure**：用户已经明确纠偏，但模型仍未重新对齐真实意图
- **Repair failure**：模型察觉到问题后，修复动作无效或只是表面补丁
- **Structure drift**：用户要求简短、直接，但模型仍持续独白或过度展开
- **Continuity masking**：上下文已经缺失，模型却伪造连续性而不承认信息不足
- **Flattery noise**：即使被要求克制，模型仍持续输出奉承、安抚或讨好性表达
- **Constraint fixation**：某个次级约束词被错误放大，压过主语义
- **Overconfident self-explanation**：模型答错后，用未经验证的机制叙事过度解释自己

---

## 框架概览

```text
Actor (local / configurable)
    ↓ generate or select user_message
Target Model (API or local)
    ↓ generate assistant_message
Judge (local / configurable)
    ↓ output turn-level structured labels
Scorer
    ↓ aggregate run-level metrics
Reporter
    ↓ Markdown / JSONL / UI views
```

### 本仓库 v0 实现与默认栈

本仓库是 DriftProbe 的一套**可运行参考实现**（别称 *Chatbot Stress Test v0*）。下列栈与后文「运行阶段」「安装」「启动 Gradio」中的默认假设一致，便于他人 clone 后复现（三角色在代码中仍解耦，可更换模型/适配层）。

```text
Actor  (Qwen2.5-7B-Instruct，transformers 本地)
    ↓ 生成 user_message
Target (经 OpenRouter 等适配层访问的 API 目标模型)
    ↓ 生成 assistant_message
Judge  (Qwen2.5-7B-Instruct，与 Actor 共用本地推理管线)
    ↓ 逐轮结构化 / 二元标签
Scorer → 聚合指标
Reporter → Markdown / JSONL
```

- **配置**：`configs/models.yaml` 中声明 provider 与本地模型路径，默认可指向本机或 Hugging Face 缓存的 Qwen2.5-7B-Instruct 权重；目标侧在典型配置下用项目根目录 `.env` 中的 `OPENROUTER_API_KEY` 访问 OpenRouter（亦可按 `adapters` 层扩展其他 provider，视实现为准）。
- **显存（经验值）**：Phase 3/4 的本地 7B fp16 推理约需 **~16GB** 级别显存，以本机环境为准。

---

## 测试 Case


| ID  | 分类         | 测试目标                          |
| --- | ---------- | ----------------------------- |
| A01 | alignment  | 用户明确纠偏后，模型是否重新对齐主意图           |
| B01 | structure  | 被要求简短回答时，模型是否仍保留 monologue 惯性 |
| C01 | continuity | 上下文缺失后，模型是否诚实承认而非伪造连续性        |
| D01 | alignment  | 明令禁止奉承后，模型是否仍持续输出奉承噪声         |


后续可扩展的 case 方向包括：

- 次级约束劫持（如“最近”压过主语义）
- 流式输出中的关键词打转
- 用户重述后仍无法恢复主任务
- 错误后的机制幻觉升级

---

## 评估指标


| 指标                           | 含义             | 方向   |
| ---------------------------- | -------------- | ---- |
| `turn_alignment_score`       | 模型遵守当轮核心指令的比例  | 越高越好 |
| `repair_score`               | 模型尝试修复失败行为的比例  | 越高越好 |
| `context_honesty_score`      | 模型诚实承认上下文缺失的比例 | 越高越好 |
| `continuity_masking_score`   | 模型伪造上下文连续性的比例  | 越低越好 |
| `flattery_noise_rate`        | 奉承表达出现的比例      | 越低越好 |
| `monologue_persistence_rate` | 独白 / 过度展开出现的比例 | 越低越好 |


后续还可加入：

- `constraint_fixation_rate`
- `repair_after_reframing_score`
- `mechanism_overclaim_rate`

---

## 运行阶段


| Phase | 行为                                                              | 依赖                                             |
| ----- | --------------------------------------------------------------- | ---------------------------------------------- |
| 2     | 使用**预设** user turns（当前代码仅完整实现 **A01**；其它 case 需 Phase 3+ 或自补脚本） | 目标模型 API key（如 OpenRouter）                     |
| 3     | Actor 按 case spec 动态生成 user turns                               | 目标 API + **本地** Actor 模型（默认 Qwen2.5-7B）        |
| 4     | Actor 生成 + Judge 逐轮打标签                                          | 目标 API + 本地 Actor + 本地 Judge（可与 Actor 同权重或分配置） |


---

## 安装

```bash
# 推荐在指定 conda 环境中操作
conda activate city-marl

pip install -r requirements.txt
```

在项目根目录创建 `.env`：

```text
OPENROUTER_API_KEY=your_key
```

本地模型路径在 `configs/models.yaml` 中配置；默认可指向本机或缓存中的 **Qwen2.5-7B-Instruct** 权重，与上节「本仓库 v0 实现与默认栈」一致。

---

## 启动 Gradio UI（推荐）

在**仓库根目录**（含 `requirements.txt` 的目录）执行，例如：

```bash
cd /path/to/chatbot_stress_test
python ui/app.py
```

Windows 示例（路径按你本机实际为准）：

```bash
cd D:\chatbot_stress_test
python ui/app.py
```

默认浏览器访问：

```text
http://127.0.0.1:7860
```

### UI 说明

- **左侧面板**：选择目标模型、case、phase、max turns、temperature
- **Overview**：运行摘要、失败模式名称、评分表格
- **Transcript**：逐轮对话，含 actor action 和 state 跳转
- **Turn Labels**：每轮**二元/结构化**标签表（如 ✓/✗ 展示，视 case 与 judge 输出而定）
- **Report**：完整 Markdown 报告
- **Debug**：原始 JSON 输出；界面中**勾选「Show Debug」**后通常更完整

### 自动存档

每次运行后结果自动保存到：

- `data/reports/<run_id>.md`
- `data/runs/<run_id>.jsonl`

### Mock 模式

当 API key 未配置或本地模型不可用时，系统会自动回退到 mock 数据，便于演示 UI 流程。

---

## 目录结构

以下以**仓库根目录**名为 `chatbot_stress_test` 为例（clone 时目录名可不同）：

```text
chatbot_stress_test/
  cases/
    alignment/         A01_scope_correction.yaml
                       D01_flattery_pollution.yaml
    structure/         B01_monologue_under_short_answer.yaml
    continuity/        C01_context_loss_honesty.yaml

  configs/
    models.yaml        provider 与本地模型路径
    runtime.yaml       运行期参数

  data/
    reports/           运行生成的 Markdown 报告
    runs/              运行生成的 JSONL 轨迹
    ...                其它如规划类 md 可按需自增

  src/
    adapters/          OpenRouter、transformers 等适配
    actor/             用户 turn 生成（case spec + state）
    judge/             逐轮标签
    scorer/            标签 → 聚合指标
    runner/            Phase 2 / 3 / 4 主循环
    report/            报告
    storage/           JSONL 等持久化

  ui/
    app.py
    backend.py
    formatters.py
    mock_backend.py
    README.md
```

---

## 项目边界

DriftProbe 的定位是**黑盒行为探针**，不是白盒机制诊断器。

它适合回答：

- 哪个 case 失败了
- 失败发生在哪一轮
- 用户纠偏后是否修复
- 哪类外显行为模式最常见
- 开关某个条件后，行为是否稳定变化

它不直接回答：

- 模型真实内部 prompt 是什么
- 某个 reranker 的权重是多少
- attention / DPO / tool policy 哪个是唯一根因

因此，DriftProbe 更像是对多轮 LLM 系统做**症状学分析、诱发试验和故障切片**，而不是直接恢复不可见的底层因果结构。

---

## 已知限制（v0）

- Phase 3/4 依赖本地 Qwen2.5-7B 级模型与显存（约 **16GB fp16** 为经验值，以本机为准）
- Phase 2 预设 user turns 仅**完整实现 A01**；其他 case 需走 Phase 3+ 等路径
- `stop_conditions` 等已在部分 YAML 中定义，**尚未在 runner 中完全激活**
- Judge 标签与分数**尚未**充分人工校准，更适合作内部相对比较
- 本框架**适合行为级/症状级**诊断，不适合作为白盒根因的唯一定论



🇬🇧 English

## Overview

**DriftProbe** is a black-box probing framework for failure modes in multi-turn LLM systems.  
Rather than claiming access to hidden internal mechanisms, it focuses on **observable conversational breakdowns** such as repair failure, over-fixation on secondary constraints, false continuity, monologue inertia, flattery noise, and overconfident self-explanations after failure.

Its goal is not to answer “what exactly happened inside the model,” but to answer more operational questions:

- At which turn does the interaction start to drift?
- Does the model genuinely recover after user correction?
- Which constraint is being overweighted?
- Is the failure mainly misalignment, failed repair, or post-hoc explanation escalation?
- How do these patterns compare across models and cases?

---

## Core Idea

DriftProbe uses a three-role evaluation loop:

```text
Actor
  → generates or selects user turns to probe the target model

Target
  → the multi-turn LLM system under evaluation

Judge
  → assigns structured turn-level labels

Scorer / Reporter
  → aggregates run-level metrics and produces reports
```

The three roles are decoupled and independently replaceable.  
This makes the framework suitable for both fixed scripted tests and more dynamic multi-turn probing.

---

## Failure Modes of Interest

DriftProbe currently focuses on several observable classes of failure:

- **Alignment failure**: the user has explicitly corrected the model, but the model still fails to realign with the actual intent
- **Repair failure**: the model attempts recovery, but the repair is ineffective or merely cosmetic
- **Structure drift**: the user requests a short or direct answer, yet the model continues with monologue-like expansion
- **Continuity masking**: the context has already been lost, but the model pretends continuity instead of admitting uncertainty
- **Flattery noise**: the model keeps producing praise, reassurance, or performative niceness even when explicitly discouraged
- **Constraint fixation**: a secondary cue is overweighted and starts dominating the main semantic objective
- **Overconfident self-explanation**: after going wrong, the model escalates into speculative mechanistic explanations stated with undue confidence

---

## Framework Snapshot

```text
Actor (local / configurable)
    ↓ generate or select user_message
Target Model (API or local)
    ↓ generate assistant_message
Judge (local / configurable)
    ↓ output turn-level structured labels
Scorer
    ↓ aggregate run-level metrics
Reporter
    ↓ Markdown / JSONL / UI views
```

### This repository: v0 implementation and default stack

This repository is a **runnable reference implementation** of DriftProbe (also referred to as *Chatbot Stress Test v0*). The stack below matches the defaults assumed in “Run Phases”, “Installation”, and “Launch the Gradio UI”, so others can reproduce runs after cloning (roles remain decoupled in code and can be swapped).

```text
Actor  (Qwen2.5-7B-Instruct, local transformers)
    ↓ generate user_message
Target (API target model via adapters, typically OpenRouter)
    ↓ generate assistant_message
Judge  (Qwen2.5-7B-Instruct, same local inference path as Actor)
    ↓ turn-level structured / binary labels
Scorer → aggregate metrics
Reporter → Markdown / JSONL
```

- **Configuration**: `configs/models.yaml` lists providers and local model paths (default: Qwen2.5-7B-Instruct on disk or HF cache). Target access usually uses `OPENROUTER_API_KEY` in a root `.env` file; other providers are possible depending on `adapters`.
- **VRAM (rule of thumb)**: local 7B fp16 for Phases 3/4 is often on the order of **~16GB**; verify on your machine.

---

## Test Cases


| ID  | Category   | Goal                                                                          |
| --- | ---------- | ----------------------------------------------------------------------------- |
| A01 | alignment  | Can the model realign after explicit user correction?                         |
| B01 | structure  | Can the model avoid monologue inertia when asked to be brief?                 |
| C01 | continuity | Does the model honestly admit context loss instead of fabricating continuity? |
| D01 | alignment  | Can the model suppress flattery when explicitly instructed not to?            |


Natural future case directions include:

- secondary-constraint hijack (for example, “recent” overriding the main intent)
- keyword looping during streaming generation
- persistent failure after user reframing
- mechanistic self-explanation escalation after an earlier mistake

---

## Metrics


| Metric                       | Meaning                                                                   | Direction        |
| ---------------------------- | ------------------------------------------------------------------------- | ---------------- |
| `turn_alignment_score`       | proportion of turns where the model follows the core instruction          | higher is better |
| `repair_score`               | proportion of turns showing meaningful recovery behavior                  | higher is better |
| `context_honesty_score`      | proportion of turns where the model honestly acknowledges missing context | higher is better |
| `continuity_masking_score`   | proportion of turns where the model fabricates continuity                 | lower is better  |
| `flattery_noise_rate`        | frequency of flattering / ingratiating expressions                        | lower is better  |
| `monologue_persistence_rate` | frequency of monologue-like overexpansion                                 | lower is better  |


Potential future metrics:

- `constraint_fixation_rate`
- `repair_after_reframing_score`
- `mechanism_overclaim_rate`

---

## Run Phases


| Phase | Behavior                                                                                                        | Dependencies                                                                 |
| ----- | --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 2     | **Preset** user turns (only **A01** is fully wired in code today; other cases need Phase 3+ or your own script) | Target model API key (e.g. OpenRouter)                                       |
| 3     | Actor generates user turns from the case spec                                                                   | Target API + **local** Actor (default Qwen2.5-7B)                            |
| 4     | Actor + per-turn Judge labels                                                                                   | Target API + local Actor + local Judge (same or separate weights per config) |


---

## Installation

```bash
conda activate city-marl
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```text
OPENROUTER_API_KEY=your_key
```

Local model paths are configured in `configs/models.yaml`; by default this points to **Qwen2.5-7B-Instruct** on disk or in the HF cache, consistent with “This repository: v0 implementation and default stack” above.

---

## Launch the Gradio UI (recommended)

From the **repository root** (the directory that contains `requirements.txt`), for example:

```bash
cd /path/to/chatbot_stress_test
python ui/app.py
```

Windows (adjust the path as needed):

```bash
cd D:\chatbot_stress_test
python ui/app.py
```

Default local address:

```text
http://127.0.0.1:7860
```

### UI Guide

- **Left panel**: select target model, case, phase, max turns, temperature
- **Overview**: run summary, failure-mode name, score table
- **Transcript**: full conversation with actor actions and state transitions
- **Turn Labels**: structured / binary label table per turn (e.g. ✓/✗ where applicable)
- **Report**: full Markdown report
- **Debug**: raw JSON outputs; enable **Show Debug** in the UI when available for full payloads

### Auto Save

Each run is automatically archived to:

- `data/reports/<run_id>.md`
- `data/runs/<run_id>.jsonl`

### Mock Mode

If the API key is missing or local models are unavailable, the system falls back to mock data so the UI can still be demonstrated.

---

## Project Structure

Example layout with repository root folder name `chatbot_stress_test` (your clone directory name may differ):

```text
chatbot_stress_test/
  cases/
    alignment/         A01_scope_correction.yaml
                       D01_flattery_pollution.yaml
    structure/         B01_monologue_under_short_answer.yaml
    continuity/        C01_context_loss_honesty.yaml

  configs/
    models.yaml
    runtime.yaml

  data/
    reports/
    runs/
    ...

  src/
    adapters/          OpenRouter, transformers, etc.
    actor/
    judge/
    scorer/
    runner/
    report/
    storage/

  ui/
    app.py
    backend.py
    formatters.py
    mock_backend.py
    README.md
```

---

## Scope and Boundaries

DriftProbe is a **black-box behavioral probe**, not a white-box mechanism analyzer.

It is good at answering:

- which case failed
- where in the interaction the failure emerged
- whether the model recovered after correction
- which observable failure pattern is present
- whether behavior changes systematically under controlled conditions

It does **not** directly recover:

- the true hidden system prompt
- the exact reranker or tool-policy weights
- whether one internal mechanism is the sole root cause

In that sense, DriftProbe is better understood as a framework for **symptom-level analysis, elicitation tests, and behavioral failure slicing** in multi-turn LLM systems.

---

## Known Limitations (v0)

- Phases 3/4 need a local Qwen2.5-7B-class model and enough VRAM (**~16GB fp16** is a rule of thumb; measure on your hardware)
- Phase 2 preset user turns are **fully implemented only for A01**; other cases require Phase 3+ paths
- `stop_conditions` in YAML are not fully wired into the runner yet
- Judge labels and scores are **not** fully human-calibrated; best used for internal relative comparison
- The framework is aimed at **behavioral / symptomatic** diagnosis, not a definitive white-box root-cause story

