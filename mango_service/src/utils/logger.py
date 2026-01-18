import sys
import os
from loguru import logger
from src.core.config import settings


def setup_logger():
    # Remove default handler
    logger.remove()
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Add file handler with rotation
    logger.add(
        os.path.join(log_dir, 'mango_service.log'),
        rotation='10 MB',
        retention='7 days',
        compression='zip',
        format='{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{line} | {message}',
        level='INFO'
    )
    
    # Add console handler
    logger.add(
        sys.stderr,
        format='<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level}</level> | <cyan>{name}:{line}</cyan> | <level>{message}</level>',
        level='INFO',
        colorize=True
    )
    
    return logger


# Initialize logger
app_logger = setup_logger()


def get_logger(name: str = __name__):
    """
    Get a logger instance with the given name
    """
    return app_logger.bind(module=name)


# Convenience functions
def log_info(message: str, **kwargs):
    app_logger.info(message, **kwargs)


def log_debug(message: str, **kwargs):
    app_logger.debug(message, **kwargs)


def log_warning(message: str, **kwargs):
    app_logger.warning(message, **kwargs)


def log_error(message: str, **kwargs):
    app_logger.error(message, **kwargs)


def log_critical(message: str, **kwargs):
    app_logger.critical(message, **kwargs)


def log_exception(message: str, **kwargs):
    app_logger.exception(message, **kwargs)
