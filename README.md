# Chatbot Stress Test v0

多轮对话失败模式评估框架。通过预定义的 case spec，让 Actor 模型生成刺激性 user turn，驱动目标 LLM 对话，再由 Judge 模型对每轮打结构化标签，最终聚合成可比较的失败模式指标。

---

## 框架概览

```
Actor (Qwen2.5-7B)
    ↓ 生成 user_message
Target Model (OpenRouter)
    ↓ 生成 assistant_message
Judge (Qwen2.5-7B)
    ↓ 输出 turn-level binary labels
Scorer → 聚合指标
Reporter → Markdown / JSONL
```

三个角色完全分离，可独立替换。

---

## 测试 Case

| ID | 分类 | 测试目标 |
|----|------|---------|
| A01 | alignment | 用户明确纠偏后，模型是否正确重新对齐 |
| B01 | structure | 被要求简短回答时，模型是否克服 monologue 惯性 |
| C01 | continuity | 上下文丢失后，模型是否诚实承认而非伪造连续性 |
| D01 | alignment | 明令禁止奉承后，模型是否持续输出奉承噪声 |

---

## 评估指标

| 指标 | 含义 | 方向 |
|------|------|------|
| turn_alignment_score | 模型遵守当轮指令的比例 | 越高越好 |
| repair_score | 模型尝试修复失败行为的比例 | 越高越好 |
| context_honesty_score | 模型诚实承认上下文缺失的比例 | 越高越好 |
| continuity_masking_score | 模型伪造上下文连续性的比例 | 越低越好 |
| flattery_noise_rate | 奉承表达出现的比例 | 越低越好 |
| monologue_persistence_rate | 独白/过度展开出现的比例 | 越低越好 |

---

## 运行阶段

| Phase | 行为 | 依赖 |
|-------|------|------|
| 2 | 使用预设 user turns（仅 A01） | OpenRouter API key |
| 3 | Actor 动态生成 user turns | API key + 本地 Qwen2.5-7B |
| 4 | Actor 生成 + Judge 打标签 | API key + 本地 Qwen2.5-7B |

---

## 安装

```bash
# 推荐在指定 conda 环境中操作
conda activate city-marl

pip install -r requirements.txt
```

配置 API key（项目根目录创建 `.env`）：

```text
OPENROUTER_API_KEY=你的key
```

本地模型路径在 `configs/models.yaml` 中配置，默认指向 Qwen2.5-7B-Instruct 本地缓存。

---

## 启动 Gradio UI（推荐）

```bash
cd D:\chatbot_stress_test
python ui/app.py
```

浏览器访问 `http://127.0.0.1:7860`

**界面说明：**

- 左侧面板：选择目标模型、case、phase、max turns、temperature
- Overview 标签：运行摘要、失败模式名称、评分表格
- Transcript 标签：逐轮对话，含 actor action 和 state 跳转
- Turn Labels 标签：每轮的二元标签表格（✓/✗）
- Report 标签：完整 Markdown 报告
- Debug 标签：原始 JSON 输出（勾选 Show Debug 后可见）

**自动存档：** 每次运行后结果自动保存到：
- `data/reports/<run_id>.md` — Markdown 报告
- `data/runs/<run_id>.jsonl` — transcript + labels 结构化数据

**Mock 模式：** 未配置 API key 或本地模型不可用时，自动降级为 mock 数据，UI 可正常演示。

---

## 目录结构

```
chatbot_stress_test/
  cases/
    alignment/         A01_scope_correction.yaml
                       D01_flattery_pollution.yaml
    structure/         B01_monologue_under_short_answer.yaml
    continuity/        C01_context_loss_honesty.yaml

  configs/
    models.yaml        provider 和本地模型路径配置
    runtime.yaml       运行参数配置

  data/
    reports/           自动生成的 Markdown 报告
    runs/              自动生成的 JSONL 轨迹文件

  src/
    adapters/          OpenRouter + transformers 适配层
    actor/             用户行为生成引擎（基于 case spec + 当前 state）
    judge/             逐轮标签提取引擎
    scorer/            turn labels → 聚合指标
    runner/            实验主循环（Phase 2 / 3 / 4）
    report/            Markdown 报告生成
    storage/           JSONL 持久化

  ui/
    app.py             Gradio Blocks 主 app
    backend.py         真实后端 bridge（失败自动 fallback mock）
    formatters.py      结果格式化（md / DataFrame / json）
    mock_backend.py    离线 mock 数据（4 个 case 各完整一份）
    README.md          UI 专项说明
```

---

## 已知限制（v0）

- Phase 3/4 依赖本地 Qwen2.5-7B，显存需求约 16GB（fp16）
- Phase 2 预设 turns 仅实现 A01，其他 case 需要跑 Phase 3+
- stop_conditions 已在 YAML 中定义，尚未在 runner 中激活
- Judge 标签尚未经过人工校准，分数为内部相对值
