from fastapi import FastAPI

from orderops_api import __version__
from orderops_api.core.config import get_settings
from orderops_api.routers.agent import router as agent_router
from orderops_api.routers.evals import router as evals_router
from orderops_api.routers.health import router as health_router
from orderops_api.routers.tools import router as tools_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
    )
    app.include_router(health_router)
    app.include_router(agent_router)
    app.include_router(evals_router)
    app.include_router(tools_router)
    return app


app = create_app()
