import asyncio
import hashlib
import time
from typing import Dict, Any, Optional, Callable, Awaitable
from cachetools import TTLCache

# In-memory thread-safe TTL caches:
# - search_cache: up to 1,000 search queries cached for 15 minutes (900s)
# - extract_cache: up to 2,000 video extractions cached for 10 minutes (600s)
search_cache: TTLCache = TTLCache(maxsize=1000, ttl=900)
extract_cache: TTLCache = TTLCache(maxsize=2000, ttl=600)

# Lock for thread-safety during cache operations
_cache_lock = asyncio.Lock()

# In-flight request deduplication map to prevent the "thundering herd" problem
_inflight_tasks: Dict[str, asyncio.Future] = {}


def hash_key(prefix: str, key: str) -> str:
    """Generate a clean normalized hash key for caching."""
    clean = key.strip().lower()
    return f"{prefix}:{hashlib.sha256(clean.encode('utf-8')).hexdigest()}"


async def get_or_set_cached(
    cache: TTLCache,
    key_prefix: str,
    raw_key: str,
    fetch_func: Callable[[], Awaitable[Any]],
) -> Any:
    """
    High-performance single-flight cache retrieval:
    1. Checks memory cache.
    2. If missing, ensures only ONE worker fetches the data for this key,
       while all other concurrent callers await the same worker's result.
    3. Caches the result and serves all callers simultaneously.
    """
    key = hash_key(key_prefix, raw_key)

    async with _cache_lock:
        if key in cache:
            return cache[key]

        # Check if another coroutine is already fetching this exact key
        if key in _inflight_tasks:
            future = _inflight_tasks[key]
        else:
            future = asyncio.get_event_loop().create_future()
            _inflight_tasks[key] = future
            # Schedule execution
            asyncio.create_task(_run_fetch(cache, key, fetch_func, future))

    return await future


async def _run_fetch(
    cache: TTLCache,
    key: str,
    fetch_func: Callable[[], Awaitable[Any]],
    future: asyncio.Future,
):
    try:
        result = await fetch_func()
        async with _cache_lock:
            cache[key] = result
        if not future.done():
            future.set_result(result)
    except Exception as exc:
        if not future.done():
            future.set_exception(exc)
    finally:
        async with _cache_lock:
            _inflight_tasks.pop(key, None)
