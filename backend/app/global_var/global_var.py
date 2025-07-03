import os

from concurrent.futures import ThreadPoolExecutor
from math import ceil

# For two vCores, it will create 6 threads.
_THREAD_IO_RATIO = 0.65
_CPU_COUNT = os.cpu_count() or 1
_THREAD_COUNT = ceil(_CPU_COUNT / (1 - _THREAD_IO_RATIO))
_global_executor = ThreadPoolExecutor(_THREAD_COUNT)


def global_executor() -> ThreadPoolExecutor:
    return _global_executor
