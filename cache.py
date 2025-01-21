import time
from typing import Any, Callable, Dict
from config import CACHE_EXPIRATION

class Cache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Any:
        if key in self._cache:
            if time.time() - self._cache[key]['timestamp'] < CACHE_EXPIRATION:
                return self._cache[key]['data']
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = {
            'data': value,
            'timestamp': time.time()
        }

    def clear(self) -> None:
        self._cache.clear()

cache = Cache()

def cached(func: Callable) -> Callable:
    async def wrapper(*args, **kwargs):
        key = f"{func.__name__}:{args}:{kwargs}"
        result = cache.get(key)
        if result is None:
            result = await func(*args, **kwargs)
            cache.set(key, result)
        return result
    return wrapper

# Usage example:
# @cached
# async def fetch_data(url: str) -> Dict[str, Any]:
#     # Fetch data from URL
#     pass