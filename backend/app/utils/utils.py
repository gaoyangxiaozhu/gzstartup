import time

MILLI_TO_SECOND = 1000

def current_sec() -> int:
    return int(time.time())

def current_ms() -> int:
    return int(time.time() * MILLI_TO_SECOND)

class Watch:
    def __init__(self) -> None:
        self.start_time = time.time() * MILLI_TO_SECOND

    def stop(self) -> float:
        end_time = time.time() * MILLI_TO_SECOND
        return end_time - self.start_time

    def stop_s(self) -> float:
        end_time = time.time() * MILLI_TO_SECOND
        return (end_time - self.start_time) / MILLI_TO_SECOND

    def reset(self) -> None:
        self.start_time = time.time() * MILLI_TO_SECOND
