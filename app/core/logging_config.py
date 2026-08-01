"""
Centralized logging configuration for the application.

Uses Loguru for structured logging with different formats for
development and production environments.
"""

import sys
from pathlib import Path
from loguru import logger
from app.config import settings


def setup_logging():
    """Configure logging for the application."""
    
    # Remove default logger
    logger.remove()
    
    # Log format for development
    if settings.APP_ENV == "development":
        logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            level=settings.LOG_LEVEL,
            colorize=True
        )
    else:
        # JSON format for production
        logger.add(
            sys.stdout,
            format="{time} | {level} | {name}:{function}:{line} | {message}",
            level=settings.LOG_LEVEL,
            serialize=True
        )
    
    # File logging for errors
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "error.log",
        rotation="1 day",
        retention="30 days",
        level="ERROR",
        format="{time} | {level} | {name}:{function}:{line} | {message}"
    )
    
    # File logging for all logs (rotated)
    logger.add(
        log_dir / "app.log",
        rotation="100 MB",
        retention="7 days",
        level=settings.LOG_LEVEL,
        format="{time} | {level} | {name}:{function}:{line} | {message}"
    )
    
    logger.info(f"Logging configured for {settings.APP_ENV} environment")
    return logger


# Export a logger instance
logger = setup_logging()