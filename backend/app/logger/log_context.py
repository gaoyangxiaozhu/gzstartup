import threading
import uuid

from typing import Any

class LogContext:
    _log_context_local = threading.local()
    _log_context_global: dict[str, Any] = {}

    @classmethod
    def set_global_context(cls, key: str, value: Any) -> None:
        cls._log_context_global[key] = value

    @classmethod
    def get_global_context(cls) -> Any:
        return cls._log_context_global

    @classmethod
    def set(cls, key: str, value: Any, else_value: str = '') -> None:
        if value is None:
            value = else_value
        setattr(cls._log_context_local, key, value)

    @classmethod
    def set_dict(cls, data_dict: dict[str, Any]) -> None:
        for key, value in data_dict.items():
            cls.set(key, value)

    @classmethod
    def get_or_else(cls, key: str, value: Any) -> Any:
        if hasattr(cls._log_context_local, key):
            return getattr(cls._log_context_local, key)
        return value

    @classmethod
    def get_or_create_trace_id(cls) -> str:
        trace_id = str(uuid.uuid4())
        ret = cls.get_or_else('trace_id', trace_id)
        if isinstance(ret, str):
            LogContext.set('trace_id', ret)
            return ret
        return ''