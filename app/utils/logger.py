"""
Structured logging for the AI Interviewer Agent System.

Provides color-coded console output and file logging with
agent-aware context for debugging multi-agent interactions.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.config import PROJECT_ROOT, settings


class ColorFormatter(logging.Formatter):
    """Custom formatter with color-coded log levels for console output."""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{self.BOLD}{record.levelname:<8}{self.RESET}"
        record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)


class AgentLogAdapter(logging.LoggerAdapter):
    """Logger adapter that includes agent name in log messages."""
    
    def process(self, msg, kwargs):
        agent_name = self.extra.get("agent_name", "System")
        return f"[{agent_name}] {msg}", kwargs


def setup_logger(
    name: str = "ai_interviewer",
    level: Optional[str] = None,
    log_to_file: bool = True,
    agent_name: Optional[str] = None,
) -> logging.Logger | AgentLogAdapter:
    """
    Set up a structured logger with console and file handlers.
    
    Args:
        name: Logger name (used for module-level loggers)
        level: Log level override (defaults to settings.LOG_LEVEL)
        log_to_file: Whether to also log to a file
        agent_name: If provided, returns an AgentLogAdapter
        
    Returns:
        Configured logger or AgentLogAdapter
    """
    log_level = getattr(logging, level or settings.LOG_LEVEL, logging.INFO)
    logger = logging.getLogger(name)
    
    # Avoid adding duplicate handlers
    if logger.handlers:
        if agent_name:
            return AgentLogAdapter(logger, {"agent_name": agent_name})
        return logger
    
    logger.setLevel(log_level)
    logger.propagate = False
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_fmt = ColorFormatter(
        "%(asctime)s │ %(levelname)s │ %(name)s │ %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)
    
    # File handler (no colors)
    if log_to_file:
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        today = datetime.now().strftime("%Y-%m-%d")
        file_handler = logging.FileHandler(
            log_dir / f"{today}.log",
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)  # Always capture everything to file
        file_fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)
    
    if agent_name:
        return AgentLogAdapter(logger, {"agent_name": agent_name})
    
    return logger


# Pre-configured loggers for common modules
def get_agent_logger(agent_name: str) -> AgentLogAdapter:
    """Get a logger configured for a specific AI agent."""
    return setup_logger(f"agent.{agent_name}", agent_name=agent_name)


def get_service_logger(service_name: str) -> logging.Logger:
    """Get a logger configured for a backend service."""
    return setup_logger(f"service.{service_name}")


def get_db_logger() -> logging.Logger:
    """Get a logger configured for database operations."""
    return setup_logger("database")


def get_rag_logger() -> logging.Logger:
    """Get a logger configured for RAG pipeline operations."""
    return setup_logger("rag")
