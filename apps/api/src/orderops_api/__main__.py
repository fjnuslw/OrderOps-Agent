import uvicorn

from orderops_api.core.config import get_settings


def main() -> None:
    settings = get_settings()

    uvicorn.run(
        "orderops_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )


if __name__ == "__main__":
    main()
