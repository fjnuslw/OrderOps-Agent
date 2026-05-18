from fastapi import FastAPI

from orderops_api import __version__
from orderops_api.routers.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="OrderOps Agent API",
        version=__version__,
    )
    app.include_router(health_router)
    return app


app = create_app()
