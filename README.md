# LangChain Agent Backend

这是一个最基本的 LangChain 后端项目，使用 FastAPI 暴露 HTTP 接口，并把模型连接配置抽到了独立模块里，方便你后面接前端页面。

## 环境要求

- Python 3.10+
- 根据你选择的 provider 配置对应 API Key

## 安装

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置

默认 provider 是 `gemini`。如果你要用智谱，请显式设置 `LLM_PROVIDER=zhipu`。

### Gemini

```bash
export LLM_PROVIDER="gemini"
export GEMINI_API_KEY="your_api_key"
export GEMINI_MODEL="gemini-2.5-flash-lite"
```

也兼容：

```bash
export GOOGLE_API_KEY="your_api_key"
```

对免费版 API，更稳妥的默认选择是 `gemini-2.5-flash-lite`。

### 智谱

```bash
export LLM_PROVIDER="zhipu"
export ZHIPUAI_API_KEY="your_api_key"
export ZHIPU_MODEL="glm-4-flash"
```

可选：

```bash
export ZHIPU_TEMPERATURE="0.1"
```

## 项目结构

```text
app/
  main.py            # FastAPI 入口
  agent_service.py   # agent 与工具封装
  llm_config.py      # Gemini / 智谱模型配置
  schemas.py         # 请求响应模型
main.py              # 后端启动脚本
cli.py               # 命令行调试入口
```

## 启动后端

```bash
python main.py
```

启动后默认监听：

```text
http://127.0.0.1:8080
```

可用接口：

```text
GET  /health
POST /api/chat
```

请求示例：

```bash
curl -X POST http://127.0.0.1:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is the weather in beijing? Also tell me 2 + 2."}'
```

## 命令行调试

如果你还想保留终端聊天方式，可以运行：

```bash
python cli.py
```

你可以直接输入问题，例如：

```text
北京天气怎么样？
2 + 2 等于几？
上海天气如何，顺便总结一下今天适不适合出门？
```

输入 `exit` 或 `quit` 退出。
