"""Logging configuration using loguru."""
import sys
from typing import Dict

from flask import Flask, g, has_request_context, request
from loguru import logger as loguru_logger


def setup_logging(app: Flask) -> None:
    """Configure loguru for structured logging."""
    log = loguru_logger
    # Remove default logger
    log.remove()

    def add_timestamp(record: Dict):
        """Ensure a 'timestamp' field exists for any custom formats."""
        record["timestamp"] = record["time"].isoformat()

    log = log.patch(add_timestamp)

    # Determine log format based on config
    log_format = app.config.get("LOG_FORMAT", "json")
    log_level = app.config.get("LOG_LEVEL", "INFO")

    if log_format == "json":
        # Structured JSON logging for production
        def format_record(record: Dict) -> str:
            """Format log record as JSON."""
            import json
            
            base = {
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "message": record["message"],
                "module": record["name"],
                "function": record["function"],
                "line": record["line"],
            }

            # Add request context if available
            if has_request_context():
                base.update(
                    {
                        "request_id": g.get("request_id"),
                        "tenant_id": g.get("tenant_id"),
                        "user_id": g.get("user_id"),
                        "method": request.method,
                        "path": request.path,
                        "ip": request.remote_addr,
                    }
                )

            # Add extra fields
            if record["extra"]:
                base.update(record["extra"])

            return json.dumps(base) + "\n"

        log.add(
            sys.stdout,
            format=format_record,
            level=log_level,
            serialize=False,
        )
    else:
        # Human-readable format for development
        log_format_str = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        log.add(sys.stdout, format=log_format_str, level=log_level, colorize=True)

    # Log to file in production (only if not in production, to avoid scope issues)
    if not app.debug and log_format == "json":
        log.add(
            "logs/tracktok_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="30 days",
            compression="zip",
            level=log_level,
            format=format_record,
        )
    elif not app.debug:
        log.add(
            "logs/tracktok_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="30 days",
            compression="zip",
            level=log_level,
            format=log_format_str,
        )

    # Intercept standard logging
    import logging

    class InterceptHandler(logging.Handler):
        """Intercept standard logging and redirect to loguru."""

        def emit(self, record):
            try:
                level = log.level(record.levelname).name
            except ValueError:
                level = record.levelno

            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            log.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # Replace Flask's logger
    app.logger.handlers = [InterceptHandler()]
    app.logger.setLevel(log_level)

    # Intercept werkzeug logger
    logging.getLogger("werkzeug").handlers = [InterceptHandler()]
    logging.getLogger("werkzeug").setLevel(log_level)

    # Intercept sqlalchemy logger (only if echo is enabled)
    if app.config.get("SQLALCHEMY_ECHO"):
        logging.getLogger("sqlalchemy.engine").handlers = [InterceptHandler()]
        logging.getLogger("sqlalchemy.engine").setLevel("INFO")

    log.info("Logging configured", log_format=log_format, log_level=log_level)
