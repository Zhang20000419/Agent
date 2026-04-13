# Mental Interview Demo

一个用于演示“固定 14 题访谈 + 大模型结构化分析 + 结果复核 + 整场汇总”的原型项目。

它的目标是把受试者的自然语言回答转换成稳定的结构化结果，便于前端展示、接口联调和流程验证。项目输出的是风险分层和症状线索总结，不是临床诊断结果。

## 项目能做什么

- 按固定 14 个问题进行访谈
- 对每一题回答输出结构化分析结果
- 用“抽取 -> 复核 -> 裁决”的多阶段流程降低幻觉和过度推断
- 在全部回答结束后，输出整场访谈的综合总结
- 提供 Web 页面和 CLI 两种演示入口

## 项目结构

```text
depression_interview_demo/
├── main.py                 # 启动 FastAPI 服务
├── cli.py                  # 命令行演示入口
├── requirements.txt
└── app/
    ├── main.py             # HTTP 路由与静态页面入口
    ├── pipeline.py         # 单题分析、复核裁决、整场汇总主流程
    ├── schemas.py          # Pydantic 数据模型
    ├── interview_questions.py
    ├── prompts.py          # 各代理使用的系统提示词
    ├── llm_config.py       # 模型与环境变量配置
    └── static/index.html   # 前端演示页面
```

## 核心流程

### 1. 单题分析

前端或 CLI 提交一条回答后，后端会调用 `analyze_turn`：

1. 根据回答语言推断中文或英文输出
2. 让 extractor agent 抽取结构化字段
3. 让 reviewer agent 复核抽取结果
4. 让 review decision agent 判断当前结果是否通过
5. 如果未通过，把修正意见回灌给 extractor，最多重试 3 次
6. 输出 `TurnAnalysis`

这一步的目标不是“尽量猜全”，而是“只保留回答里有依据的内容”。

### 2. 整场汇总

`analyze_session` 不会直接拿原始问答做总结，而是先逐题调用 `analyze_turn`，再把得到的结构化 `turns` 交给 summarizer agent，生成：

- `overall_risk`
- `session_classification`
- `overall_confidence`
- `summary`
- `symptom_summary`
- `key_findings`
- `missing_information`
- `explanation`

### 3. 模型驱动汇总

项目默认按模型链路运行，单题分析和整场汇总都应由 LLM 生成。

- `analyze_turn` 负责单题抽取、复核和裁决
- `analyze_session` 在逐题分析后，再由 summarizer 生成整场分类
- 最终总结的输入是前面所有题目的结构化分析结果，不是原始问答直接拼接

## 固定 14 题

1. 你今天过得怎么样？
2. 你的家乡是哪里的？
3. 你最喜欢你家乡的哪些美食景点呐？
4. 你跟你的家人、同事、同学、朋友，关系处得怎么样，可以仔细说下吗？
5. 你觉得你的性格内向还是外向一些呐？
6. 最近2周，你的心情怎么样？
7. 你对你目前的学习或工作的兴趣如何呐？
8. 你容不容易责备自己，感到自己连累了其他人呐？有的话，请你仔细讲一下当时的状态。
9. 有没有哪段时间，你觉得自己的行动、思考或说话都比较迟钝？有的话，可以仔细说一下吗？
10. 你是否经常感到紧张、焦虑，担心，惶恐不安？如果是，可以仔细说一下吗？
11. 有没有哪段时间，你感到兴奋或亢奋、或者精力旺盛？有的话，请你仔细讲一下当时的状态。
12. 有没有哪段时间，连续几天持续地感到烦躁易怒，以至于与人争论，吵架或打架，或者对着外人大吼？有的话，请你仔细讲一下。
13. 有没有哪段时间，你总喜欢滔滔不绝地讲话，说话快得让人难以理解？有的话，请你仔细讲一下。
14. 好的。有没有哪段时间，你觉得自己思维比以往格外活跃，脑子格外聪明？有的话，请你仔细讲一下。

## 数据模型

### 单题输入

```json
{
  "question_id": 6,
  "answer": "最近两周心情不算稳定，有几天会比较低落，也有几天只是觉得累和空。"
}
```

### 单题输出

```json
{
  "question_id": 6,
  "question_text": "最近2周，你的心情怎么样？",
  "answer": "最近两周心情不算稳定，有几天会比较低落，也有几天只是觉得累和空。",
  "symptom": "近两周情绪状态",
  "duration": "less_than_2_weeks",
  "duration_text": "最近两周",
  "frequency": "sometimes",
  "frequency_text": "有几天",
  "severity": "mild",
  "polarity": "support",
  "confidence": 0.88,
  "evidence": [
    "最近两周",
    "有几天会比较低落",
    "觉得累和空"
  ],
  "explanation": "回答明确提到最近两周内存在阶段性低落情绪，因此支持当前情绪状态存在波动。",
  "review_notes": "复核后保留当前结论，未发现明显无依据字段。",
  "risk_flag": false,
  "review_passed": true,
  "retry_count": 0,
  "review_issues": []
}
```

### 全场输入

```json
{
  "session_id": "demo-001",
  "responses": [
    {
      "question_id": 6,
      "answer": "最近两周心情不算稳定，有几天会比较低落，也有几天只是觉得累和空。"
    }
  ]
}
```

### 全场输出

```json
{
  "session_id": "demo-001",
  "turns": [],
  "overall_risk": "medium",
  "session_classification": ["depression", "anxiety"],
  "overall_confidence": 0.81,
  "summary": "本次访谈呈现抑郁和焦虑相关线索并存的状态。",
  "symptom_summary": [
    "近两周存在情绪波动",
    "伴随一定自责和压力体验"
  ],
  "key_findings": [
    "近两周出现阶段性低落",
    "部分回答体现压力相关反应"
  ],
  "missing_information": [
    "缺少更稳定的时间长度和功能影响信息"
  ],
  "explanation": "最终分类基于多轮访谈中的情绪、担忧、自责和行为线索综合判断，但不构成临床诊断。"
}
```

## 关键字段说明

- `polarity`: `support` 表示回答支持症状存在，`deny` 表示回答否定症状存在，`uncertain` 表示证据不足或表达矛盾
- `duration`: 归一化持续时间，只允许 `none` / `less_than_2_weeks` / `2_to_4_weeks` / `1_to_3_months` / `more_than_3_months` / `unclear`
- `frequency`: 归一化频率，只允许 `none` / `rare` / `sometimes` / `often` / `almost_every_day` / `unclear`
- `risk_flag`: 当前题是否触发风险提示，当前题库中会更关注自责、迟滞、焦虑、兴奋、易怒和语速异常等内容
- `session_classification`: 最终分类标签列表，只允许 `depression` / `bipolar` / `anxiety` / `healthy`，并且 `healthy` 不能和其他标签同时出现
- `review_passed`: 当前单题结果是否通过最终裁决代理复核
- `retry_count`: 为通过复核而重试的次数
- `review_issues`: 复核阶段发现的问题列表

## 运行约束

- 请务必在名为 `agent` 的 conda 环境中运行本项目
- 不要直接假设裸 `python3` 就是正确解释器
- 最终总结必须由 LLM 生成

## 运行方式

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

项目默认使用 `zhipu`，也支持 `gemini`。

#### 智谱

```bash
export LLM_PROVIDER=zhipu
export ZHIPUAI_API_KEY=your_key
export ZHIPU_MODEL=glm-4-flash
```

可选：

```bash
export ZHIPU_TIMEOUT_SECONDS=180
export ZHIPU_MAX_RETRIES_429=3
export ZHIPU_RETRY_BASE_DELAY_SECONDS=6
```

#### Gemini

```bash
export LLM_PROVIDER=gemini
export GEMINI_API_KEY=your_key
export GEMINI_MODEL=gemini-2.5-flash-lite
```

也可以使用：

```bash
export GOOGLE_API_KEY=your_key
```

`llm_config.py` 会尝试从当前进程环境变量和 `~/.zshrc` 中读取这些值，因此从 IDE 启动时通常也能取到配置。

### 3. 启动 Web 服务

推荐两种方式。

先激活环境：

```bash
conda activate agent
python main.py
```

或者直接通过 conda 执行：

```bash
conda run -n agent python main.py
```

默认地址：

```text
http://127.0.0.1:8090
```

### 4. 启动 CLI 演示

```bash
conda run -n agent python cli.py
```

## API

- `GET /`：前端演示页面
- `GET /health`：健康检查
- `GET /api/questions`：固定 14 题列表
- `POST /api/analyze-turn`：单题分析
- `POST /api/analyze-session`：整场访谈汇总

### `POST /api/analyze-turn`

请求体：

```json
{
  "question_id": 6,
  "answer": "最近两周心情不算稳定，有几天会比较低落，也有几天只是觉得累和空。"
}
```

### `POST /api/analyze-session`

请求体：

```json
{
  "session_id": "demo-001",
  "responses": [
    {
      "question_id": 6,
      "answer": "最近两周心情不算稳定，有几天会比较低落，也有几天只是觉得累和空。"
    }
  ]
}
```

## 前端页面行为

前端页面会：

1. 按顺序展示 14 个固定问题
2. 每提交一题，立即调用 `POST /api/analyze-turn`
3. 不额外插入人为停顿，页面节奏直接反映模型请求的真实耗时
4. 第 14 题完成后，自动调用 `POST /api/analyze-session`
5. 展示整场分类、时间线和汇总信息

页面还包含：

- 左侧问题目录和当前进度，未到达的问题不会提前展示
- 点击左侧已完成问题，可以查看之前的回答和对应分析
- 访谈统计卡片
- 自动演示模式
- 单题结构化结果时间线
- 最终整场总结卡片

## 已知限制

- 这是演示原型，不是医疗产品
- 输出质量依赖提示词设计、模型稳定性和回答质量
- 当前题库既包含背景信息，也包含情绪、焦虑、迟滞和轻躁相关线索，不是严格的单一抑郁量表
- 当前没有持久化、鉴权、审计日志和正式评估数据集

## 免责声明

本项目仅用于原型演示、接口联调和流程验证，不提供医疗建议，不可替代专业精神科/心理评估。如回答中出现自伤、自杀或其他现实风险，请立即联系当地紧急服务、危机干预热线或专业人员。
