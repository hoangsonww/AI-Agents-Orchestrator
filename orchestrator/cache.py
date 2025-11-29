"""Caching utilities for performance optimization."""

import hashlib
import json
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Union

T = TypeVar("T")


class CacheEntry:
    """Cache entry with expiration."""

    def __init__(self, value: Any, ttl: Optional[int] = None) -> None:
        """
        Initialize cache entry.

        Args:
            value: Cached value
            ttl: Time to live in seconds (None = no expiration)
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl

    def get_age(self) -> float:
        """Get age of entry in seconds."""
        return time.time() - self.created_at


class InMemoryCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 3600) -> None:
        """
        Initialize cache.

        Args:
            default_ttl: Default time to live in seconds
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        entry = self.cache.get(key)

        if entry is None:
            self.misses += 1
            return None

        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None

        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live (overrides default)
        """
        if ttl is None:
            ttl = self.default_ttl

        self.cache[key] = CacheEntry(value, ttl)

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def cleanup_expired(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]

        for key in expired_keys:
            del self.cache[key]

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests,
        }


class FileCache:
    """Persistent file-based cache."""

    def __init__(self, cache_dir: Union[str, Path], default_ttl: int = 3600) -> None:
        """
        Initialize file cache.

        Args:
            cache_dir: Directory for cache files
            default_ttl: Default time to live in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path) as f:
                data = json.load(f)

            entry = CacheEntry(data["value"], data.get("ttl"))
            entry.created_at = data["created_at"]

            if entry.is_expired():
                cache_path.unlink()
                return None

            return entry.value
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        if ttl is None:
            ttl = self.default_ttl

        cache_path = self._get_cache_path(key)

        data = {
            "value": value,
            "ttl": ttl,
            "created_at": time.time(),
        }

        try:
            with open(cache_path, "w") as f:
                json.dump(data, f)
        except (TypeError, OSError):
            # Value not JSON serializable or IO error
            pass

    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        cache_path = self._get_cache_path(key)

        if cache_path.exists():
            cache_path.unlink()
            return True
        return False

    def clear(self) -> None:
        """Clear all cache files."""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()


# Global cache instance
_cache: Optional[InMemoryCache] = None


def get_cache() -> InMemoryCache:
    """Get or create global cache instance."""
    global _cache
    if _cache is None:
        _cache = InMemoryCache()
    return _cache


def cache_result(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    use_args: bool = True,
    use_kwargs: bool = True,
) -> Callable:
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key
        use_args: Include positional args in cache key
        use_kwargs: Include keyword args in cache key

    Returns:
        Decorated function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            cache = get_cache()

            # Generate cache key
            key_parts = [key_prefix or func.__name__]

            if use_args:
                key_parts.extend(str(arg) for arg in args)

            if use_kwargs:
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)

            return result

        # Add cache management methods
        wrapper.cache_clear = lambda: get_cache().clear()  # type: ignore
        wrapper.cache_info = lambda: get_cache().get_stats()  # type: ignore

        return wrapper

    return decorator


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """
    Simple memoization decorator (no expiration).

    Args:
        func: Function to memoize

    Returns:
        Memoized function
    """
    return cache_result(ttl=None)(func)
