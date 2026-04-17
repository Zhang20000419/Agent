def main() -> None:
    import uvicorn
    from depression_detection.config.settings import get_runtime_settings

    # 保持入口极简，便于本地直接 `python main.py` 启动演示服务。
    settings = get_runtime_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
