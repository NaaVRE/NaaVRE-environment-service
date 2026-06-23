import logging
import os

from fastapi import FastAPI

app = FastAPI(
    root_path=os.getenv(
        'ROOT_PATH',
        '/NaaVRE-workflow-service'
        )
    )

if os.getenv('DEBUG', 'false').lower() == 'true':
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)


@app.get("/")
def main():
    return {"message": "Hello World"}
