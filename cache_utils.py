"""Framework-agnostic TTL cache, standing in for `st.cache_data` in modules
that need to be importable outside a running Streamlit script (the FastAPI
backend, or a plain Python shell) without pulling in Streamlit or printing
its "missing ScriptRunContext" warnings.

Behaviorally equivalent to `st.cache_data(ttl=..., show_spinner=False)` for
every function it replaces in this app: all of them are called with plain,
hashable string/int/float/None arguments, so a dict keyed on (args, kwargs)
with a stored expiry time is a faithful substitute — same TTL semantics,
same "call it again after expiry, get fresh data" behavior.
"""

import time
from functools import wraps


def ttl_cache(ttl_seconds: float):
    """Decorator: cache a function's return value per distinct call
    signature for `ttl_seconds`, after which the next call recomputes and
    re-caches."""

    def decorator(func):
        store = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            cached = store.get(key)
            if cached is not None:
                value, expires_at = cached
                if now < expires_at:
                    return value
            value = func(*args, **kwargs)
            store[key] = (value, now + ttl_seconds)
            return value

        wrapper.cache_clear = store.clear
        return wrapper

    return decorator
