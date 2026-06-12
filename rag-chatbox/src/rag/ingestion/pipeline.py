from typing import Any, Optional
import sys

from fastapi import HTTPException, Request


from src.core.setup_logging import setup_logger

logger = setup_logger(__name__)



class IngestionPipeline:
    def __int__(self):
        pass