import os

import uvicorn


def main() -> None:
    host = os.getenv("ORDEROPS_API_HOST", "127.0.0.1")
    port = int(os.getenv("ORDEROPS_API_PORT", "8000"))
    reload = os.getenv("ORDEROPS_API_RELOAD", "1") != "0"

    uvicorn.run(
        "orderops_api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    main()
