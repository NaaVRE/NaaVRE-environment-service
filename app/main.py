import logging

from app import config
from app.routes.build import router as build_router
from fastapi import FastAPI

if config.DEBUG:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

app = FastAPI(
    root_path=config.ROOT_PATH
    )

app.include_router(build_router)
