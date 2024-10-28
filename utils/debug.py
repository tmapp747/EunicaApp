import functools
import time
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def debug_timer(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = f(*args, **kwargs)
        end = time.time()
        logger.debug(f"{f.__name__} took {end-start:.2f} seconds to execute")
        return result
    return wrapper

def debug_memory_usage(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        import psutil
        process = psutil.Process()
        before_mem = process.memory_info().rss
        result = f(*args, **kwargs)
        after_mem = process.memory_info().rss
        diff = after_mem - before_mem
        logger.debug(f"{f.__name__} memory usage: {diff/1024/1024:.2f} MB")
        return result
    return wrapper
