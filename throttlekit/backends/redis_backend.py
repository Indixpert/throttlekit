import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any, Coroutine, Protocol, Union


class RedisClient(Protocol):
    """A protocol for redis-py's sync and async clients."""

    def evalsha(self, sha: str, numkeys: int, *keys_and_args: Any) -> Any:
        ...

    def script_load(self, script: str) -> Any:
        ...


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: float  # in seconds
    reset_after: float  # in seconds


# Lua Scripts

TOKEN_BUCKET_LUA = """
-- KEYS[1]: bucket_key
-- ARGV[1]: limit (capacity)
-- ARGV[2]: window (in seconds)
-- ARGV[3]: now (float timestamp)

local bucket_key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local rate = limit / window

local bucket_data = redis.call('GET', bucket_key)
local bucket

if bucket_data == false then
    bucket = {
        tokens = limit,
        last_refill = now
    }
else
    -- cjson is part of Redis's Lua environment
    bucket = cjson.decode(bucket_data)
end

local time_passed = now - bucket.last_refill
if time_passed > 0 then
    local tokens_to_add = time_passed * rate
    bucket.tokens = math.min(limit, bucket.tokens + tokens_to_add)
    bucket.last_refill = now
end

local allowed = 0
local remaining = bucket.tokens
local retry_after_ms = 0

if bucket.tokens >= 1 then
    allowed = 1
    bucket.tokens = bucket.tokens - 1
    remaining = bucket.tokens
else
    -- Not enough tokens, calculate time to wait for one token
    local time_to_one_token = (1 - bucket.tokens) / rate
    retry_after_ms = math.ceil(time_to_one_token * 1000)
end

redis.call('SET', bucket_key, cjson.encode(bucket))
-- Set a TTL that is twice the window to avoid losing the bucket state
-- in case of inactivity, but also prevent it from living forever.
redis.call('PEXPIRE', bucket_key, window * 2 * 1000)

return {allowed, math.floor(remaining), retry_after_ms}
"""

SLIDING_WINDOW_LUA = """
-- KEYS[1]: sorted_set_key
-- ARGV[1]: limit
-- ARGV[2]: window (in seconds)
-- ARGV[3]: now (float timestamp)
-- ARGV[4]: request_id

local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local request_id = ARGV[4]

-- Remove entries older than the window
local window_start = now - window
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

-- Get current count
local count = redis.call('ZCARD', key)

local allowed = 0
local remaining = 0
local retry_after_ms = 0

if count < limit then
    allowed = 1
    redis.call('ZADD', key, 'NX', now, request_id)
    -- Set expiration to clean up the key if it becomes inactive
    redis.call('PEXPIRE', key, window * 1000)
    remaining = limit - (count + 1)
else
    -- Find when the oldest request will expire to suggest a retry time
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    if #oldest > 0 then
        local oldest_ts = tonumber(oldest[2])
        local time_to_wait = (oldest_ts + window) - now
        retry_after_ms = math.max(0, math.ceil(time_to_wait * 1000))
    else
        -- This case should ideally not be hit if count >= limit, but as a fallback
        retry_after_ms = math.ceil(window * 1000)
    end
end

return {allowed, remaining, retry_after_ms}
"""

FIXED_WINDOW_LUA = """
-- KEYS[1]: counter_key (includes bucket id)
-- ARGV[1]: limit
-- ARGV[2]: window (in seconds)
-- ARGV[3]: now (float timestamp)

local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local count = redis.call('INCR', key)

if count == 1 then
    redis.call('PEXPIRE', key, window * 1000)
end

local allowed = 0
local remaining = 0
local reset_after_ms = 0

if count <= limit then
    allowed = 1
    remaining = limit - count
else
    remaining = 0
end

-- Time until the current fixed window expires
local time_in_window = now % window
local reset_after = window - time_in_window
reset_after_ms = math.ceil(reset_after * 1000)

return {allowed, remaining, reset_after_ms}
"""


class RedisBackend:
    def __init__(self, client: RedisClient, key_prefix: str = "throttle"):
        self.client = client
        self.key_prefix = key_prefix
        self._scripts_loaded = False
        self._token_bucket_sha: Union[str, None] = None
        self._sliding_window_sha: Union[str, None] = None
        self._fixed_window_sha: Union[str, None] = None

    async def _load_scripts(self) -> None:
        if self._scripts_loaded:
            return

        results = await asyncio.gather(
            self._script_load(TOKEN_BUCKET_LUA),
            self._script_load(SLIDING_WINDOW_LUA),
            self._script_load(FIXED_WINDOW_LUA),
        )
        self._token_bucket_sha = results[0]
        self._sliding_window_sha = results[1]
        self._fixed_window_sha = results[2]
        self._scripts_loaded = True

    async def _script_load(self, script: str) -> str:
        res = self.client.script_load(script)
        if asyncio.iscoroutine(res):
            res = await res
        return res

    async def _evalsha(self, sha: str, numkeys: int, *args: Any) -> Any:
        res = self.client.evalsha(sha, numkeys, *args)
        if asyncio.iscoroutine(res):
            res = await res
        return res

    async def is_allowed_token_bucket(
        self, key: str, limit: int, window: float
    ) -> RateLimitResult:
        await self._load_scripts()
        now = time.time()
        redis_key = f"{self.key_prefix}:{key}:tb"

        result = await self._evalsha(
            self._token_bucket_sha, 1, redis_key, limit, window, now
        )

        allowed, remaining, retry_after_ms = result

        rate = limit / window
        reset_after = (limit - remaining) / rate if rate > 0 else float("inf")

        return RateLimitResult(
            allowed=bool(allowed),
            remaining=int(remaining),
            retry_after=float(retry_after_ms / 1000),
            reset_after=reset_after,
        )

    async def is_allowed_sliding_window(
        self, key: str, limit: int, window: float
    ) -> RateLimitResult:
        await self._load_scripts()
        now = time.time()
        request_id = uuid.uuid4().hex
        redis_key = f"{self.key_prefix}:{key}:sw"

        result = await self._evalsha(
            self._sliding_window_sha, 1, redis_key, limit, window, now, request_id
        )

        allowed, remaining, retry_after_ms = result

        reset_after = float(retry_after_ms / 1000) if not allowed else 0.0

        return RateLimitResult(
            allowed=bool(allowed),
            remaining=int(remaining),
            retry_after=float(retry_after_ms / 1000),
            reset_after=reset_after,
        )

    async def is_allowed_fixed_window(
        self, key: str, limit: int, window: float
    ) -> RateLimitResult:
        await self._load_scripts()
        now = time.time()

        window_bucket = int(now // window)
        redis_key = f"{self.key_prefix}:{key}:{window_bucket}:fw"

        result = await self._evalsha(
            self._fixed_window_sha, 1, redis_key, limit, window, now
        )

        allowed, remaining, reset_after_ms = result

        return RateLimitResult(
            allowed=bool(allowed),
            remaining=int(remaining),
            retry_after=float(reset_after_ms / 1000),
            reset_after=float(reset_after_ms / 1000),
        )
