import time
import threading
from functools import wraps


def ttl_cache(ttl_seconds: float):
    """
    Thread-safe TTL cache.

    Prevents multiple simultaneous requests for the same key from
    executing the wrapped function at the same time.
    """

    def decorator(func):
        store = {}

        # One lock per cache key so duplicate requests for the same
        # ticker wait for the first request to finish.
        key_locks = {}
        locks_guard = threading.Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()

            # Return immediately if we already have a valid cached value.
            cached = store.get(key)
            if cached is not None:
                value, expires_at = cached
                if now < expires_at:
                    return value

            # Get/create a lock specifically for this cache key.
            with locks_guard:
                key_lock = key_locks.setdefault(key, threading.Lock())

            # Only one request for this key can enter here at a time.
            with key_lock:
                # Check cache again because another request may have
                # populated it while this request was waiting.
                now = time.monotonic()
                cached = store.get(key)

                if cached is not None:
                    value, expires_at = cached
                    if now < expires_at:
                        return value

                # Only this request now performs the expensive fetch.
                value = func(*args, **kwargs)

                store[key] = (
                    value,
                    time.monotonic() + ttl_seconds,
                )

                return value

        def cache_clear():
            store.clear()
            with locks_guard:
                key_locks.clear()

        wrapper.cache_clear = cache_clear
        return wrapper

    return decorator