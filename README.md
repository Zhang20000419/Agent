# Mental Interview Demo

一个用于演示“电影观看 + 朗读文字 + 回答问题”三阶段访谈与多模态分析的原型项目。

完整业务流程是：

1. 受试者观看正性 / 中性 / 负性的三段电影，采集受试者视频，诊断时仅使用**视觉数据**
2. 受试者朗读正性 / 中性 / 负性的三段文字，诊断时使用**视觉 + 音频数据**
3. 受试者回答固定的 **16 个问题**，诊断时使用**视觉 + 音频 + 文本数据**；其中文本不是手工输入，而是由音频转录得到

它的目标是把受试者在整个访谈过程中的多模态行为数据转换成稳定的结构化结果，便于前端展示、接口联调、流程验证和后续模型落地。项目输出的是风险分层和症状线索总结，不是临床诊断结果。

> 说明：当前仓库仍保留一个以静态资源题库驱动的 QA 兼容页面，用于验证现有 API 和后端分析链路；README 同时记录**完整目标流程**与**当前 demo 实现状态**。

## 项目能做什么

- 用 `movie / reading / qa` 三个任务层表达完整访谈协议
- 对单题 / 单阶段输入输出结构化分析结果
- 用“抽取 -> 复核 -> 裁决”的多阶段流程降低幻觉和过度推断
- 在全部回答结束后，输出整场访谈的综合总结
- 提供 Web 页面和 CLI 两种演示入口

## 完整业务流程（目标访谈协议）

### 阶段 1：观看电影（Movie）

- 受试者依次观看 **正性 / 中性 / 负性** 三段电影
- 前端通过**摄像头 + 麦克风**持续采集受试者视频并传回后端
- 这个阶段建模时**仅使用视觉模态**
- 音频即使被一并采集，也只作为采集载体或归档内容，不作为该阶段的诊断输入

### 阶段 2：朗读文字（Reading）

- 受试者依次朗读 **正性 / 中性 / 负性** 三段文字
- 前端继续通过**摄像头 + 麦克风**采集受试者视频和音频并传回后端
- 这个阶段建模时使用**视觉 + 音频**
- 是否保留文本稿件属于任务素材管理问题，不影响该阶段的核心输入模态定义

### 阶段 3：回答问题（QA）

- 受试者依次回答固定的 **16 个问题**
- 前端继续通过**摄像头 + 麦克风**采集受试者视频和音频并传回后端
- 这个阶段建模时使用**视觉 + 音频 + 文本**
- 其中“文本”不是前端直接输入，而是由该题音频经转录后得到，作为 QA 阶段的文本模态输入

### 前端采集约定

- 前端统一使用**摄像头和麦克风**采集受试者视频数据，再上传到后端
- 页面需要像文本版一样持续展示：
  - 当前阶段
  - 当前题目 / 当前刺激材料
  - 已完成进度
  - 历史回看
- 对于 QA 阶段，前端需要像之前的文本版一样展示问题本身，但回答来源改为受试者的真实音视频采集

### 后端归档与存储约定

后端应将每次访谈的原始媒体、派生音频、转录文本和诊断结果统一存放到一个**可配置的访谈归档根目录**中。配置入口应放在统一配置层（当前仓库配置集中在 `src/depression_detection/config/settings.py`）。

建议的归档原则：

- 访谈归档根目录下，每次访谈创建一个新的子文件夹
- 每个子文件夹对应一次完整访谈，例如：
  - `session-20260417-130501-abcd1234/`
  - `interview-<timestamp>-<uuid>/`
- 该子文件夹下分别存放：
  - 观看电影阶段的视频
  - 朗读文字阶段的视频
  - 回答问题阶段的视频
  - 如有需要，从视频中分离出的音频
  - 如有需要，转录生成的文本
  - 诊断结果与元数据

推荐目录结构示例：

```text
interview_archive_root/
└── session-20260417-130501-abcd1234/
    ├── session.json
    ├── movie/
    │   ├── positive/
    │   │   ├── capture.webm
    │   │   └── diagnosis.json
    │   ├── neutral/
    │   │   ├── capture.webm
    │   │   └── diagnosis.json
    │   └── negative/
    │       ├── capture.webm
    │       └── diagnosis.json
    ├── reading/
    │   ├── positive/
    │   │   ├── capture.webm
    │   │   ├── audio.wav
    │   │   └── diagnosis.json
    │   ├── neutral/
    │   └── negative/
    └── qa/
        ├── q01/
        │   ├── capture.webm
        │   ├── audio.wav
        │   ├── transcript.json
        │   └── diagnosis.json
        ├── q02/
        └── ...
```

目录规则上：

- `movie` 和 `reading` 阶段可以按 `positive / neutral / negative` 分文件夹
- `qa` 阶段可以按 `q01 ~ q16` 分文件夹
- 也可以统一为更抽象的层级，例如都使用 `item-01 / item-02 / ...`
- **关键要求不是具体命名，而是三阶段采用统一、稳定、可追溯的目录规则**

### 转录来源标记约定

由于转录可能来自两个来源，因此转录文件必须显式标注文本来源，至少应保存以下信息：

- `provider`: `whisper` 或 `baidu`
- `used_fallback`: 是否发生兜底
- `language`: 转录语言
- `confidence`: 可用时保存置信度
- `metadata.primary_error`: 如果本地 Whisper 失败后回退百度云，可记录主路径错误

推荐把转录结果单独保存为 `transcript.json`，例如：

```json
{
  "text": "最近两周心情不太稳定，有时候会低落。",
  "provider": "whisper",
  "used_fallback": false,
  "language": "zh",
  "confidence": 0.91,
  "metadata": {
    "prepared_audio_path": "qa/q03/audio.wav"
  }
}
```

如果是百度云兜底得到的文本，则应明确表现为：

```json
{
  "text": "最近两周心情不太稳定，有时候会低落。",
  "provider": "baidu",
  "used_fallback": true,
  "language": "zh",
  "metadata": {
    "primary_error": "whisper timeout"
  }
}
```

## 项目结构

当前仓库已经从单体 demo 结构演进为“**兼容层 + 标准 src 分层结构**”：

```text
depression_interview_demo/
├── main.py                 # 启动 FastAPI 服务（兼容入口）
├── cli.py                  # 命令行演示入口（兼容入口）
├── pyproject.toml
├── requirements.txt
├── app/                    # 旧 API / 旧 CLI 的兼容封装
│   ├── main.py
│   ├── pipeline.py
│   └── static/index.html
├── src/
│   └── depression_detection/
│       ├── bootstrap/      # 容器与服务组装
│       ├── config/         # 模型/环境配置
│       ├── domain/         # 稳定领域契约
│       ├── model/          # vision/audio/text/multimodal 模型层
│       ├── tasks/          # qa / reading / movie 任务编排
│       ├── application/    # 对外服务外观层
│       ├── interfaces/     # FastAPI / CLI 适配层
│       └── shared/
├── tests/
│   ├── unit/
│   ├── contract/
│   └── integration/
├── docs/
└── scripts/
```

### 模型层说明

`src/depression_detection/model/` 现在提供统一的抑郁预测接口：

- `text`
- `audio`
- `vision`
- `multimodal`

其中：
- `text` 已提供可落地的 LLM predictor 接口封装；
- `audio / vision / multimodal` 已提供标准接口与占位实现，后续可直接替换为本地训练模型。

### 任务层说明

- `qa`：当前已落地的回答问题抑郁识别主链路
- `reading`：朗读文字任务骨架
- `movie`：看电影任务骨架

前端兼容页已补上 QA 真上传能力；旧接口继续可用；新代码优先写入 `src/depression_detection/`。

### 当前代码实现状态

当前兼容 demo 实际处于**问答阶段（QA）**：

- QA 阶段继续使用文本抑郁识别主链路
- QA 阶段已支持：`录音/录屏 multipart 上传 / answer_audio_base64 -> Whisper 转写 -> 百度云 ASR 兜底 -> 文本抑郁识别`
- `movie` 和 `reading` 当前**不使用文本模态数据**
- 因此当前版本**仅在 QA 阶段落地媒体转文本**
- 但 Whisper / 百度云 ASR / ffmpeg / fallback 等开关已经预留到统一配置中，供后续阶段启用

统一配置入口为：

```text
src/depression_detection/config/settings.py
```

`model_settings.py` 仅保留兼容导出。

### QA 媒体输入说明

`/api/analyze-turn` 与 `/api/v1/qa/turns:predict` 现在支持真正的 multipart 媒体上传，同时保留 JSON 兼容模式：

1. 真正的录音 / 录屏文件上传（推荐）：

```bash
curl -X POST http://127.0.0.1:8090/api/analyze-turn \
  -F question_id=6 \
  -F answer_audio=@answer.webm
```

2. 直接文本：

```json
{
  "question_id": 6,
  "answer": "最近两周情绪比较低落。"
}
```

3. JSON 兼容媒体直传：

```json
{
  "question_id": 6,
  "answer": "",
  "answer_audio_base64": "<base64-audio>",
  "answer_audio_filename": "answer.wav",
  "answer_audio_content_type": "audio/wav"
}
```

4. 本地 demo / internal 兼容媒体路径：

```json
{
  "question_id": 6,
  "answer": "",
  "answer_audio_path": "/path/to/answer.wav"
}
```

当 `answer` 为空且提供了上传文件 / `answer_audio_base64`（或仅在本地 demo 下提供 `answer_audio_path`）时，后端会：

1. 用 ffmpeg 规范化媒体并抽取音频
2. 先尝试 Whisper 转写
3. Whisper 失败时按配置回退百度云 ASR
4. 将转写文本送入现有 QA 文本抑郁识别流程

> 说明：`answer_audio_path` 是 **local-only/internal compatibility** 字段。真实前后端分离部署建议优先使用 multipart 真上传；录屏文件也可以直接上传，只要 ffmpeg 能读取其音轨即可。如果客户端环境受限，再退回 `answer_audio_base64`。生产环境建议将 `ALLOW_LOCAL_AUDIO_PATH_INPUT=false`。

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

`analyze_session` 不会直接拿原始问答做总结。默认路径下，前端会先逐题调用 `analyze_turn`，并把已经复核过的 `TurnAnalysis` 结果保存起来；整场汇总阶段直接把这些结构化 `turns` 交给 summarizer agent，生成：

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
- `analyze_session` 优先复用已有 `turns` 做整场分类；只有兼容模式下才会从 `responses` 补跑逐题分析
- 最终总结的输入是前面所有题目的结构化分析结果，不是原始问答直接拼接

## 当前 demo 题库（来自静态资源目录，当前为 16 题）

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
15. 谢谢。有没有哪段时间，你认为有人在暗中监视你、故意议论你或企图伤害你吗？有的话，请你仔细讲一下。
16. 好的。有没有哪段时间，你能听到其他人不能听到的声音，或者看到别人看不到的东西？有的话，请你仔细讲一下。

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
  "turns": [
    {
      "question_id": 6,
      "question_text": "最近2周，你的心情怎么样？",
      "answer": "最近两周心情不算稳定，有几天会比较低落，也有几天只是觉得累和空。",
      "symptom": "情绪低落",
      "duration": "less_than_2_weeks",
      "duration_text": "最近两周",
      "frequency": "sometimes",
      "frequency_text": "有几天",
      "severity": "moderate",
      "polarity": "support",
      "confidence": 0.83,
      "evidence": ["最近两周", "有几天会比较低落"],
      "explanation": "回答直接支持近两周存在低落情绪。",
      "review_notes": "复核通过。",
      "risk_flag": true,
      "review_passed": true,
      "retry_count": 0,
      "review_issues": []
    }
  ],
  "responses": [
    {
      "question_id": 6,
      "answer": "最近两周心情不算稳定，有几天会比较低落，也有几天只是觉得累和空。"
    }
  ]
}
```

说明：
- 推荐直接传 `turns`，这样整场汇总不会重新逐题调用 `analyze_turn`
- `responses` 目前仅作为兼容回退保留，便于旧调用方继续工作

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
- `GET /api/questions`：当前 demo 的题库列表（从 `app/static/interview-assets/interview/` 动态加载）
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

## 当前兼容前端页面行为

前端页面会：

1. 按顺序展示当前 demo 题库中的所有问题（当前为 16 题）
2. 每提交一题，立即调用 `POST /api/analyze-turn`
3. 不额外插入人为停顿，页面节奏直接反映模型请求的真实耗时
4. 最后一题完成后，自动调用 `POST /api/analyze-session`，并把前面收集到的 `TurnAnalysis` 一并提交
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
- README 顶部描述的“三阶段完整流程、16 题 QA、统一访谈归档目录”是系统目标流程；当前仓库已落地的兼容 demo 仍主要围绕 QA 路由展开，但题目数量已改为从静态资源目录动态读取
- 当前没有持久化、鉴权、审计日志和正式评估数据集
- 当前整场接口会信任客户端回传的 `turns`；这适用于 demo / 受信任调用方，不适合作为生产环境的最终安全方案

## 免责声明

本项目仅用于原型演示、接口联调和流程验证，不提供医疗建议，不可替代专业精神科/心理评估。如回答中出现自伤、自杀或其他现实风险，请立即联系当地紧急服务、危机干预热线或专业人员。
