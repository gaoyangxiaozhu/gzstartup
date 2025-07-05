import logging
import sys
import os
import inspect
import traceback
import threading

from typing import Any

def init_root_logger() -> logging.Logger:
    root_logger = logging.getLogger()
    root_logger.setLevel('INFO')
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(threadName)s - %(message)s")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    return root_logger

# config root logger.
logger = init_root_logger()

def init_monitor_logger() -> logging.Logger:
    # config monitor logger.
    monitoring_logger = logging.getLogger('monitor')
    monitoring_logger.setLevel('INFO')
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(threadName)s - %(message)s")
    monitor_handler.setFormatter(formatter)
    monitoring_logger.addHandler(monitor_handler)
    monitoring_logger.propagate = False

    return monitoring_logger


def init_userqa_logger() -> logging.Logger:
    # config userqa logger.
    userqa_logger = logging.getLogger('userqa')
    userqa_logger.setLevel('INFO')
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(threadName)s - %(message)s")
    userqa_handler.setFormatter(formatter)
    userqa_logger.addHandler(userqa_handler)
    userqa_logger.propagate = False

    return userqa_logger

# Log lock to avoid deadlock
log_lock = threading.Lock()


# config monitor logger.
monitor_handler = logging.FileHandler('/var/log/gzpearl_backend_monitor.log') \
    if 'IS_TEST' not in os.environ else logging.StreamHandler(sys.stdout)
monitor_logger = init_monitor_logger()

# config userqa logger.
userqa_handler = logging.FileHandler('/var/log/gzpearl_backend_userqa.log') \
    if 'IS_TEST' not in os.environ else logging.StreamHandler(sys.stdout)
userqa_logger = init_userqa_logger()

def init_fast_api_logger() -> None:
    # fastapi & uvicorn
    fast_logger = logging.getLogger("fastapi")
    fast_logger.setLevel(logging.INFO)
    for hdl in fast_logger.handlers:
        fast_logger.removeHandler(hdl)
    fast_logger.addHandler(monitor_handler)
    fast_logger.propagate = False

    # Disable uvicorn default log.
    uvicorn_logger = logging.getLogger("uvicorn.access")
    for hdl in uvicorn_logger.handlers:
        uvicorn_logger.removeHandler(hdl)
    uvicorn_logger.propagate = False

def _log_template(message: Any, log_level: int) -> str:
    frame = inspect.currentframe()
    if frame is not None and frame.f_back is not None and frame.f_back.f_back is not None:
        caller = inspect.getframeinfo(frame.f_back.f_back)
        lineno = caller.lineno
        caller_filename = os.path.basename(caller.filename)
        # There is a memory leak issue which caused ZMQ thread not being released.
        # Explicitly remove it
        del frame
    else:
        lineno = 0
        caller_filename = 'unknown'
    sys_log_tag = os.getenv('SYS_LOG_TAG', '')
    return f"{caller_filename}({lineno}) - {message}"

def log_error(message: Any, e: Any = None, gz_log: logging.Logger = logger) -> None:
    if logging.ERROR < gz_log.getEffectiveLevel():
        return

    log_message = _log_template(message, logging.ERROR)
    throwable_str = '' if e is None else traceback.format_exc()
    with log_lock:
        gz_log.error(log_message, exc_info=True)

def log_warn(message: Any, gz_log: logging.Logger = logger) -> None:
    if logging.WARN < gz_log.getEffectiveLevel():
        return

    with log_lock:
        gz_log.warning(_log_template(message, logging.WARN))

def log_info(message: Any, gz_log: logging.Logger = logger) -> None:
    if logging.INFO < gz_log.getEffectiveLevel():
        return

    with log_lock:
        gz_log.info(_log_template(message, logging.INFO))