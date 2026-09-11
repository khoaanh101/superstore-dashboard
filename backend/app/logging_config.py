"""
logging_config.py — Centralized logging setup for Superstore Dashboard.

Two loggers are produced:
  • "system"  — Application events: startup, auth, CRUD, errors.
  • "access"  — One line per HTTP request: method, path, status, duration, IP.

Log files rotate at 10 MB and keep 5 backups so the disk never fills up.

Usage in any module:
    import logging
    logger = logging.getLogger("system")   # or "access"
    logger.info("something happened")
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Logs land next to the 'backend/' directory: project root / logs /
_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_FMT_SYSTEM = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_FMT_ACCESS = "%(asctime)s | %(message)s"
_DATE_FMT   = "%Y-%m-%d %H:%M:%S"

# Rotate at 10 MB, keep 5 compressed backups
_MAX_BYTES   = 10 * 1024 * 1024
_BACKUP_COUNT = 5


def _make_file_handler(filename: str, fmt: str) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        _LOG_DIR / filename,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(fmt, datefmt=_DATE_FMT))
    return handler


def _make_console_handler(fmt: str) -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt=_DATE_FMT))
    return handler


def setup_logging(debug: bool = False) -> None:
    """
    Call once at application startup (in main.py).

    Parameters
    ----------
    debug : bool
        When True, sets system logger to DEBUG level and also prints access
        logs to stdout. In production (False) system is INFO and access logs
        go only to the file.
    """
    root_level = logging.DEBUG if debug else logging.INFO

    # ── System logger ──────────────────────────────────────────────────────────
    sys_logger = logging.getLogger("system")
    sys_logger.setLevel(root_level)
    sys_logger.propagate = False  # don't bubble up to root logger

    sys_logger.addHandler(_make_file_handler("system.log", _FMT_SYSTEM))
    sys_logger.addHandler(_make_console_handler(_FMT_SYSTEM))

    # ── Access logger ──────────────────────────────────────────────────────────
    acc_logger = logging.getLogger("access")
    acc_logger.setLevel(logging.INFO)
    acc_logger.propagate = False

    acc_logger.addHandler(_make_file_handler("access.log", _FMT_ACCESS))
    if debug:
        acc_logger.addHandler(_make_console_handler(_FMT_ACCESS))

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if debug else logging.WARNING
    )
