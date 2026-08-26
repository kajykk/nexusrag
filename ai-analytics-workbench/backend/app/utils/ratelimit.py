"""轻量内存限流器：滑动窗口计数，按客户端 IP 限制请求频率。

适用单进程部署（uvicorn 单 worker / Celery 场景下的 API 进程）。
多副本部署应改用 Redis 或网关级限流。
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.logging_config import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """固定容量滑动窗口：每 `seconds` 秒内最多 `times` 次/键。"""

    def __init__(self, times: int, seconds: int) -> None:
        self.times = times
        self.seconds = seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> None:
        window = self._hits[key]
        while window and now - window[0] > self.seconds:
            window.popleft()

    def check(self, request: Request) -> None:
        """超限抛 429；否则记录本次命中。"""
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self._lock:
            self._prune(client_ip, now)
            window = self._hits[client_ip]
            if len(window) >= self.times:
                logger.warning("ratelimit.exceeded", extra={"client_ip": client_ip})
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="请求过于频繁，请稍后再试",
                )
            window.append(now)

    def reset(self) -> None:
        """清空全部计数（测试/运维用途）。"""
        with self._lock:
            self._hits.clear()


# 认证端点共用实例：每 IP 每分钟最多 10 次（登录爆破 / 注册滥用的基本防线）
auth_limiter = RateLimiter(times=10, seconds=60)
