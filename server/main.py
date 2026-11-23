"""ASGI entrypoint: uvicorn main:app"""

import logging

from app.api import create_app

logging.basicConfig(level=logging.INFO)

app = create_app()
