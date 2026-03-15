import logging
import sys
import os
from pathlib import Path
from typing import Optional, Union

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
    
    # Force the lowest level on the logger itself so handlers can filter
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers on the root 'wugong' logger
    root_logger = logging.getLogger("wugong")
    if root_logger.handlers and name != "wugong":
        return logger
    
    if logger.handlers:
        # Update existing handlers if needed
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(console_level)
            elif isinstance(handler, logging.FileHandler):
                handler.setLevel(file_level)
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)
    logger.addHandler(console_handler)

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
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not setup file logging: {e}")

    return logger

def update_console_level(level: Union[int, str]) -> None:
    """Updates the console log level for the root 'wugong' logger."""
    root_logger = logging.getLogger("wugong")
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handler.setLevel(level)

# Default root logger instance
logger = setup_logger("wugong")
