import logging

from fastapi import FastAPI

from app import env
from app.routes.build import router as build_router
from app.routes.image_puller import router as image_puller_router
from app.routes.me import router as me_router

if env.DEBUG:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

app = FastAPI(
    root_path=env.ROOT_PATH
    )

app.include_router(build_router)
app.include_router(image_puller_router)
app.include_router(me_router)
