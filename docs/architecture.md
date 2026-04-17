# Architecture

- `model/`: 统一的 vision/audio/text/multimodal 预测接口与注册中心
- `tasks/`: 任务编排（qa / reading / movie）
- `application/`: 给 API / CLI 的服务外观层
- `interfaces/`: FastAPI 与 CLI 适配层
- `app/`: 旧入口的兼容封装，不再承载核心业务实现
- `config/settings.py`: 当前唯一 canonical runtime config，统一管理 app/model/stage/transcription/media 选项

## 当前阶段说明

- 当前处于 **QA 阶段**
- QA 已支持录音 / 录屏答案转写：Whisper 主路径，百度云 ASR 兜底
- `movie` / `reading` 保留任务骨架，但默认 **不启用文本模态**
- `MOVIE_USES_TEXT_MODALITY=false`
- `READING_USES_TEXT_MODALITY=false`
- `QA_AUDIO_TRANSCRIPTION_ENABLED=true`
- `TRANSCRIPTION_ENABLED=true`
- `ALLOW_LOCAL_AUDIO_PATH_INPUT=true`（仅本地 demo / internal compatibility，生产建议关闭）

这意味着：
- 目前只在 QA 阶段使用媒体转文本
- 看电影/朗读阶段暂不自动做媒体转文本
- 未来 movie/reading 若启用转写，可复用同一套 transcription 配置
- 对外 API 已优先支持 multipart 真上传；录屏文件会通过 ffmpeg 抽取音轨再转写。若客户端环境受限，再退回 `answer_audio_base64`，避免把服务端本地路径作为公共契约
