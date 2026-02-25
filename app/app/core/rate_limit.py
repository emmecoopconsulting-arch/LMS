from collections import defaultdict, deque
from datetime import datetime, timedelta, UTC


class LoginRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window = timedelta(seconds=window_seconds)
        self.attempts: dict[str, deque[datetime]] = defaultdict(deque)

    def is_limited(self, key: str) -> bool:
        now = datetime.now(UTC)
        queue = self.attempts[key]
        self._purge(queue, now)
        return len(queue) >= self.max_attempts

    def add_attempt(self, key: str) -> None:
        now = datetime.now(UTC)
        queue = self.attempts[key]
        self._purge(queue, now)
        queue.append(now)

    def reset(self, key: str) -> None:
        self.attempts.pop(key, None)

    def _purge(self, queue: deque[datetime], now: datetime) -> None:
        while queue and now - queue[0] > self.window:
            queue.popleft()
