"""One place to configure logging so every module just does `logging.getLogger(__name__)`."""

import logging
import os


def configure_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    # Quiet down noisy third-party loggers unless we're explicitly debugging.
    if level != "DEBUG":
        for noisy in ("httpx", "httpcore", "urllib3", "chromadb"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
