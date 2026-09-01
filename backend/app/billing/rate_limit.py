"""Rate limit simples em memória (sliding window por chave)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict


class InMemoryRateLimiter:
    def __init__(self, *, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return False
            bucket.append(now)
            return True


# Checkout: 10 req / min por IP
checkout_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60.0)

# Webhook: 120 req / min por IP (Asaas pode reenviar em rajadas)
webhook_limiter = InMemoryRateLimiter(max_requests=120, window_seconds=60.0)

# Login do painel admin: 8 tentativas / min por IP
admin_login_limiter = InMemoryRateLimiter(max_requests=8, window_seconds=60.0)
