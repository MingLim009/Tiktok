"""Logging con formato legible y redacción de secretos."""

from __future__ import annotations

import logging
import re
import sys

# Patrones que jamás deben aparecer en un log ni en una captura de pantalla.
_SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"),
    re.compile(r"(?i)(password|contrase[nñ]a|clave)\s*[:=]\s*\S+"),
    re.compile(r"(?i)(sessionid|sid_tt|msToken)\s*[:=]\s*\S+"),
]


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for pattern in _SECRET_PATTERNS:
            msg = pattern.sub("[REDACTADO]", msg)
        return msg


def setup(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        RedactingFormatter(
            fmt="%(asctime)s  %(levelname)-7s %(name)-22s  %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))

    # Estas librerías son muy ruidosas en DEBUG.
    for noisy in ("httpx", "httpcore", "urllib3", "websockets", "TikTokLive"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
