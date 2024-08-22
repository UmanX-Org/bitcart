import json
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.requests import HTTPConnection
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse
from starlette.staticfiles import StaticFiles

from api import settings as settings_module
from api import utils
from api.constants import VERSION
from api.ext import tor as tor_ext
from api.logger import get_logger
from api.settings import Settings
from api.utils.logging import log_errors
from api.views import router

logger = get_logger(__name__)


class RawContextMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        request = HTTPConnection(scope, receive)
        token = settings_module.settings_ctx.set(request.app.settings)
        try:
            await self.app(scope, receive, send)
        finally:
            settings_module.settings_ctx.reset(token)


def get_app():
    settings = Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.ctx_token = settings_module.settings_ctx.set(app.settings)  # for events context
        await settings.init()
        await settings.plugins.startup()
        yield
        await app.settings.shutdown()
        await settings.plugins.shutdown()
        settings_module.settings_ctx.reset(app.ctx_token)

    app = FastAPI(
        title=settings.api_title,
        version=VERSION,
        redoc_url="/",
        docs_url="/swagger",
        root_path=settings.root_path,
        description="Bitcart Merchants API",
        lifespan=lifespan,
    )
    app.settings = settings
    app.mount("/images", StaticFiles(directory=settings.images_dir), name="images")
    app.mount("/files/localstorage", StaticFiles(directory=settings.files_dir), name="files")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    settings.init_logging()
    settings.load_plugins()

    settings.plugins.setup_app(app)
    # include built-in routes later to allow plugins to override them
    app.include_router(router)

    @app.middleware("http")
    async def add_onion_host(request: Request, call_next):
        response = await call_next(request)
        async with utils.redis.wait_for_redis():
            host = request.headers.get("host", "").split(":")[0]
            onion_host = await tor_ext.get_data("onion_host", "")
            if onion_host and not tor_ext.is_onion(host):
                response.headers["Onion-Location"] = onion_host + request.url.path
            return response

    @app.exception_handler(500)
    async def exception_handler(request, exc):
        logger.error(traceback.format_exc())
        return PlainTextResponse("Internal Server Error", status_code=500)

    app.add_middleware(RawContextMiddleware)

    if settings.openapi_path:
        with log_errors():
            with open(settings.openapi_path) as f:
                app.openapi_schema = json.loads(f.read())
    return app


app = get_app()
