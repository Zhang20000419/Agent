# Depression Interview Demo

这是一个独立于现有聊天 demo 的第二个 demo 项目，用于对固定 16 轮访谈回答进行抑郁相关识别与结构化分析。

## 任务定义

系统对受试者进行 16 轮固定问题访谈。每一轮都会接收一个回答，并输出该回答对应的结构化识别结果。

目标不是直接做医疗诊断，而是完成以下任务：

1. 从单轮回答中抽取抑郁相关症状线索
2. 识别症状的持续时间、频率、严重程度和极性
3. 给出判断置信度
4. 输出可解释信息，说明为什么做出该判断
5. 在 16 轮结束后，汇总整场访谈，给出整体抑郁分类结果、症状总结和可解释信息

## 方法设计

为了降低单模型误判，这个 demo 使用多代理流程：

1. `extractor agent`
负责从受试者回答中抽取结构化症状信息

2. `reviewer agent`
负责复核 extractor 的结论，检查矛盾、漏项、过度推断和无依据字段，确保输出不是幻觉

3. `summarizer agent`
负责汇总 16 轮结果，输出整体风险判断与解释

## 输入

### 单轮输入

```json
{
  "question_id": 1,
  "question_text": "过去两周，你是否经常感到情绪低落、沮丧或者绝望？",
  "answer": "是的，最近基本每天都觉得提不起劲，已经持续快一个月了。"
}
```

### 全量输入

```json
{
  "session_id": "demo-001",
  "responses": [
    {
      "question_id": 1,
      "question_text": "过去两周，你是否经常感到情绪低落、沮丧或者绝望？",
      "answer": "最近几乎每天都很难受，持续了三周以上。"
    }
  ]
}
```

## 单轮输出

```json
{
  "question_id": 1,
  "question_text": "过去两周，你是否经常感到情绪低落、沮丧或者绝望？",
  "answer": "最近几乎每天都很难受，持续了三周以上。",
  "symptom": "情绪低落",
  "duration": "2_to_4_weeks",
  "duration_text": "三周以上",
  "frequency": "almost_every_day",
  "frequency_text": "几乎每天",
  "severity": "moderate",
  "polarity": "support",
  "confidence": 0.88,
  "evidence": [
    "回答中出现“几乎每天”",
    "回答中出现“持续了三周以上”",
    "回答中出现“很难受”"
  ],
  "explanation": "回答明确支持情绪低落存在，并给出了高频和持续时间信息。",
  "review_notes": "回答中同时出现频率和持续时间，支持抑郁情绪相关症状存在。",
  "risk_flag": true
}
```

## 字段定义

- `symptom`: 当前问题对应的主要症状或线索
- `duration`: 归一化持续时间，取值只能是 `none` / `less_than_2_weeks` / `2_to_4_weeks` / `1_to_3_months` / `more_than_3_months` / `unclear`
- `duration_text`: 持续时间的可解释文本
- `frequency`: 归一化频率，取值只能是 `none` / `rare` / `sometimes` / `often` / `almost_every_day` / `unclear`
- `frequency_text`: 频率的可解释文本
- `severity`: 严重程度，取值只能是 `none` / `mild` / `moderate` / `severe`
- `polarity`: `support` 表示受试者回答支持症状存在，`deny` 表示受试者回答在否定该症状，`uncertain` 表示信息不足或含糊
- `confidence`: 0 到 1 之间的阿拉伯数字小数
- `evidence`: 支持该判断的文本依据，必须来自原始回答
- `explanation`: 对当前结构化判断的可解释说明
- `review_notes`: reviewer agent 的复核结论
- `risk_flag`: 当前轮是否提示风险

## 全量输出

```json
{
  "session_id": "demo-001",
  "turns": [],
  "overall_risk": "medium",
  "depression_classification": "moderate_depression",
  "overall_confidence": 0.81,
  "summary": "受试者在情绪低落、兴趣减退、疲劳和睡眠问题上存在多项阳性线索，频率较高且持续时间较长。",
  "symptom_summary": [
    "持续性情绪低落",
    "高频兴趣减退",
    "伴随疲劳和睡眠问题"
  ],
  "key_findings": [
    "情绪低落呈高频出现",
    "睡眠问题持续时间较长",
    "兴趣减退与精力不足同时出现"
  ],
  "missing_information": [
    "缺少对自责和无价值感的明确表述"
  ],
  "explanation": "最终分类主要基于多轮阳性症状、较高频率和较长持续时间，但仍然不是临床诊断。"
}
```

### 最终抑郁分类取值约束

- `normal`
- `mild_depression`
- `moderate_depression`
- `moderately_severe_depression`
- `severe_depression`
- `uncertain`

最终输出必须包含：

- 抑郁分类结果
- 症状总结
- 关键依据
- 可解释信息
- 缺失信息

## 固定 16 题

1. 过去两周，你是否经常感到情绪低落、沮丧或者绝望？
2. 过去两周，你是否对平时感兴趣的事情失去了兴趣或愉快感？
3. 最近你的睡眠情况怎么样，比如失眠、早醒或睡得过多？
4. 最近你的食欲或体重有没有明显变化？
5. 最近你是否常常感到疲劳、没精力或做什么都很吃力？
6. 最近你是否觉得自己很失败，或者让自己和家人失望？
7. 最近你在注意力集中、看书、工作或做决定时是否变得困难？
8. 最近你的动作或说话速度是否明显变慢，或者相反变得烦躁坐立不安？
9. 最近你是否有过“活着没意思”、伤害自己或不如死了的想法？
10. 最近这些情绪或状态对你的学习、工作或社交影响大吗？
11. 这些状态一般从什么时候开始的？
12. 在这一段时间里，这些感受是偶尔出现，还是经常出现？
13. 当这些感受出现时，通常会持续多久？
14. 你觉得这些问题的严重程度更接近轻微、中等还是严重？
15. 最近有没有什么支持因素，让你感觉稍微好一点？
16. 你是否愿意继续寻求帮助，比如和家人、朋友或专业人员沟通？

## 运行方式

### 安装

```bash
pip install -r requirements.txt
```

### 启动后端

```bash
python main.py
```

默认地址：

```text
http://127.0.0.1:8090
```

前端页面入口：

```text
http://127.0.0.1:8090/
```

### 命令行 demo

```bash
python cli.py
```

## API

- `GET /`
- `GET /health`
- `GET /api/questions`
- `POST /api/analyze-turn`
- `POST /api/analyze-session`

## 前端页面说明

页面会：

1. 按固定 16 题顺序展示问题
2. 每提交一题，就立即展示该题的结构化识别结果
3. 每完成两题，自动短暂停顿约 1.2 秒
4. 完成全部 16 题后，自动请求整场访谈汇总结果并展示抑郁分类、症状总结和可解释信息

当前实现中，前端在第 16 题分析完成后会立即调用 `POST /api/analyze-session`，不是手动触发。

页面还支持：

1. 左侧问题目录，显示当前题目和已完成题目
2. 访谈统计卡，展示已完成轮数、风险标记数和阳性轮数
3. 自动演示模式，使用预置 16 条回答一键跑完整场访谈
4. 结果时间线，逐轮展示结构化输出和最终汇总卡片

## 免责声明

这个 demo 仅用于算法原型、结构化抽取与风险识别实验，不构成临床诊断依据，也不能替代专业医生或心理健康服务。
