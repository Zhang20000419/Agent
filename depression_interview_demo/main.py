def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8090, reload=False)


if __name__ == "__main__":
    main()
