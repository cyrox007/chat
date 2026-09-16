import uvicorn

from settings import config


if __name__ == "__main__":
    app_name = "app:app"
    uvicorn.run(
        app_name,
        host="0.0.0.0",
        port=9000,
        reload=config.DEBUG,
    )
