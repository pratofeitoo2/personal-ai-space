"""
Logging setup for the engine.
Creates 4 log files: system, errors, audit, performance.
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime

LOG_DIR = Path(__file__).parent / "logs"


def setup_logging(level: str = "INFO") -> None:
    LOG_DIR.mkdir(exist_ok=True)

    fmt_standard = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fmt_audit = logging.Formatter(
        "[%(asctime)s] AUDIT: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    def make_handler(filename: str, formatter=None) -> logging.handlers.TimedRotatingFileHandler:
        h = logging.handlers.TimedRotatingFileHandler(
            LOG_DIR / filename, when="midnight", backupCount=30, encoding="utf-8"
        )
        h.setFormatter(formatter or fmt_standard)
        return h

    # Root engine logger
    root = logging.getLogger("engine")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    if root.handlers:
        return  # Already configured

    # system.log – all INFO+
    sys_handler = make_handler("system.log")
    sys_handler.setLevel(logging.INFO)
    root.addHandler(sys_handler)

    # errors.log – WARNING+
    err_handler = make_handler("errors.log")
    err_handler.setLevel(logging.WARNING)
    root.addHandler(err_handler)

    # audit.log – via named logger
    audit_logger = logging.getLogger("engine.audit")
    audit_handler = make_handler("audit.log", fmt_audit)
    audit_handler.setLevel(logging.DEBUG)
    audit_logger.addHandler(audit_handler)
    audit_logger.propagate = False

    # performance.log – via named logger
    perf_logger = logging.getLogger("engine.perf")
    perf_handler = make_handler("performance.log")
    perf_handler.setLevel(logging.DEBUG)
    perf_logger.addHandler(perf_handler)
    perf_logger.propagate = False

    # Console output
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, level.upper(), logging.INFO))
    console.setFormatter(fmt_standard)
    root.addHandler(console)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"engine.{name}")


def audit(message: str) -> None:
    logging.getLogger("engine.audit").info(message)


def perf(component: str, duration_ms: float, extra: str = "") -> None:
    logging.getLogger("engine.perf").info(
        f"{component}: {duration_ms:.1f}ms {extra}"
    )
