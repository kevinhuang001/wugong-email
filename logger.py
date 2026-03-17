import logging
import sys
import os
from pathlib import Path
from typing import Optional, Union
from rich.console import Console
from rich.logging import RichHandler

# Global console instance used across the application to ensure UI coordination
# (e.g., preventing logs from overlapping with progress bars)
console = Console(stderr=True)

def setup_logger(
    name: str = "wugong", 
    console_level: Union[int, str] = logging.WARNING,
    file_level: Union[int, str] = logging.DEBUG,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """Sets up a logger with both console and file handlers."""
    # Ensure name starts with wugong to maintain hierarchy
    if name != "wugong" and not name.startswith("wugong."):
        name = f"wugong.{name}"
        
    logger = logging.getLogger(name)
    
    # Always use the root 'wugong' logger to hold handlers for consistent propagation
    target_logger = logging.getLogger("wugong")
    
    # Force the lowest level on the target logger so handlers can filter
    target_logger.setLevel(logging.DEBUG)
    
    if target_logger.handlers:
        # Update existing handlers if needed
        for handler in target_logger.handlers:
            if isinstance(handler, RichHandler):
                handler.setLevel(console_level)
            elif isinstance(handler, logging.FileHandler):
                handler.setLevel(file_level)
        return logging.getLogger(name)

    formatter = logging.Formatter(
        "%(message)s",
        datefmt="[%X]"
    )

    # Console handler using RichHandler - Default to stderr to avoid breaking JSON output
    console_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        show_time=False,
        show_path=False,
        markup=True
    )
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)
    target_logger.addHandler(console_handler)

    # File handler - Default to config directory log if not provided
    if log_file is None:
        # Check environment variable first
        env_path = os.environ.get("WUGONG_CONFIG")
        if env_path:
            log_file = Path(env_path).parent / "wugong.log"
        else:
            # Check ~/.config/wugong first
            config_dir = Path.home() / ".config" / "wugong"
            if not config_dir.exists() and (Path.home() / ".wugong").exists():
                config_dir = Path.home() / ".wugong"
            log_file = config_dir / "wugong.log"
    
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(file_level)
        target_logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not setup file logging: {e}")

    return logger

def update_console_level(level: Union[int, str]) -> None:
    """Updates the console log level for the root 'wugong' logger."""
    root_logger = logging.getLogger("wugong")
    for handler in root_logger.handlers:
        if isinstance(handler, RichHandler) or (isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)):
            handler.setLevel(level)

def disable_logging() -> None:
    """Disables all logging for the 'wugong' hierarchy."""
    root_logger = logging.getLogger("wugong")
    root_logger.setLevel(logging.CRITICAL + 1)
    for handler in root_logger.handlers:
        handler.setLevel(logging.CRITICAL + 1)
    
    # Also disable at the library level
    logging.disable(logging.CRITICAL)

def enable_logging() -> None:
    """Enables logging back to default levels."""
    logging.disable(logging.NOTSET)
    root_logger = logging.getLogger("wugong")
    root_logger.setLevel(logging.DEBUG)
    # Note: this doesn't restore original handler levels, but it's enough for tests

# Default root logger instance
logger = setup_logger("wugong")
