import uvicorn


def main() -> None:
    from depression_detection.config.settings import get_runtime_settings

    settings = get_runtime_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    main()
