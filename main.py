def main() -> None:
    import uvicorn

    # 保持入口极简，便于本地直接 `python main.py` 启动演示服务。
    uvicorn.run("app.main:app", host="127.0.0.1", port=8090, reload=False)


if __name__ == "__main__":
    main()
