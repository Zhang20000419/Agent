# API Contracts

## Compatibility API
- `GET /health`
- `GET /api/questions`
- `POST /api/analyze-turn`
- `POST /api/analyze-session`

## V1 API
- `GET /api/v1/health`
- `GET /api/v1/qa/questions`
- `POST /api/v1/qa/turns:predict`
- `POST /api/v1/qa/sessions:predict`
- `POST /api/v1/reading:predict`
- `POST /api/v1/movie:predict`
- `POST /api/v1/text:predict`
- `POST /api/v1/audio:predict`
- `POST /api/v1/vision:predict`
- `POST /api/v1/multimodal:predict`

## Current Phase Notes
- 当前阶段是 **QA**
- QA 路由支持：
  - `multipart/form-data` 真正媒体上传（字段：`question_id` + `answer_audio` 文件，可选 `answer`；可上传录音或录屏）
  - 直接文本输入 `answer`
  - JSON 兼容媒体直传 `answer_audio_base64`
  - 本地 demo / internal 兼容媒体路径 `answer_audio_path`
- 当 `answer` 为空且提供上传文件、`answer_audio_base64`（或在 local-only 模式下提供 `answer_audio_path`）时，后端会执行：
  - ffmpeg 媒体规范化与音轨抽取
  - Whisper 转写
  - 百度云 ASR 兜底
  - 文本抑郁识别
- `answer_audio_path` 仅适合单机 demo / 内部任务；远程客户端应优先使用 multipart 真上传，其次再使用 `answer_audio_base64`
- 可以通过 `ALLOW_LOCAL_AUDIO_PATH_INPUT=false` 禁用本地路径输入，避免把服务端文件路径暴露为公共 API 语义
- `reading` 与 `movie` 路由仍保留，但默认不启用文本模态预处理
- 即使请求里携带 transcript，默认也不会把它作为当前阶段的有效模态输入，除非配置显式开启：
  - `READING_USES_TEXT_MODALITY=true`
  - `MOVIE_USES_TEXT_MODALITY=true`
