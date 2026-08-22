"""
Groq API Rate Limiter & Governor Module for Zomato Recommendation Engine.
Enforces safe request & token limits (30 RPM, 12K TPM, 1K RPD, 100K TPD) for llama-3.3-70b-versatile.
"""
import time
import random
import logging
from typing import Callable, Any, Dict

logging.basicConfig(level=logging.INFO)

class GroqRateLimiter:
    """Manages Groq API rate limits, sliding window token buckets, and exponential backoffs."""

    def __init__(
        self,
        max_rpm: int = 25,
        max_tpm: int = 10000,
        max_rpd: int = 1000,
        max_tpd: int = 100000
    ):
        self.max_rpm = max_rpm
        self.max_tpm = max_tpm
        self.max_rpd = max_rpd
        self.max_tpd = max_tpd

        self.min_delay = 60.0 / self.max_rpm  # ~2.4 seconds
        self.last_request_time = 0.0

        self.request_timestamps = []
        self.minute_tokens = []
        self.daily_requests = 0
        self.daily_tokens = 0
        self.day_start = time.time()

    def _reset_daily_if_needed(self):
        now = time.time()
        if now - self.day_start > 86400.0:
            self.daily_requests = 0
            self.daily_tokens = 0
            self.day_start = now

    def _clean_windows(self):
        now = time.time()
        self.request_timestamps = [t for t in self.request_timestamps if now - t < 60.0]
        self.minute_tokens = [(t, c) for (t, c) in self.minute_tokens if now - t < 60.0]

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def wait_for_slot(self, estimated_tokens: int = 300):
        self._reset_daily_if_needed()
        self._clean_windows()

        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed + random.uniform(0.05, 0.15))

        current_tpm = sum(c for _, c in self.minute_tokens)
        if current_tpm + estimated_tokens > self.max_tpm:
            logging.warning("Groq TPM limit reached. Pausing 10s...")
            time.sleep(10.0)

        now = time.time()
        self.last_request_time = now
        self.request_timestamps.append(now)
        self.minute_tokens.append((now, estimated_tokens))
        self.daily_requests += 1
        self.daily_tokens += estimated_tokens

    def execute_with_retry(
        self,
        api_func: Callable[[], Any],
        max_retries: int = 3,
        estimated_tokens: int = 300
    ) -> Any:
        self.wait_for_slot(estimated_tokens)
        delay = 2.0
        for attempt in range(1, max_retries + 1):
            try:
                return api_func()
            except Exception as e:
                err = str(e).lower()
                if "429" in err or "rate_limit" in err:
                    backoff = delay + random.uniform(0.1, 0.5)
                    logging.warning(f"Groq HTTP 429 RateLimit. Retrying in {backoff:.2f}s (Attempt {attempt}/{max_retries})...")
                    time.sleep(backoff)
                    delay *= 2.0
                else:
                    logging.error(f"Groq API Error: {e}")
                    raise e
        raise RuntimeError("Groq API failed after max retries due to rate limits.")
