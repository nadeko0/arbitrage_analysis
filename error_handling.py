import logging
from functools import wraps
from typing import Callable, Any, Dict
from aiohttp import ClientError
from asyncio import TimeoutError

logger = logging.getLogger(__name__)

class APIError(Exception):
    pass

def handle_api_errors(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except ClientError as e:
            logger.error(f"Network error in {func.__name__}: {e}")
            raise APIError(f"Network error: {e}")
        except TimeoutError:
            logger.error(f"Timeout error in {func.__name__}")
            raise APIError("Request timed out")
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise APIError(f"Unexpected error: {e}")
    return wrapper

# Usage example:
# @handle_api_errors
# async def fetch_data(url: str) -> Dict[str, Any]:
#     # Fetch data from URL
#     pass

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Could not convert {value} to float, using default {default}")
        return default

def safe_dict_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    try:
        return d[key]
    except KeyError:
        logger.warning(f"Key {key} not found in dictionary, using default {default}")
        return default