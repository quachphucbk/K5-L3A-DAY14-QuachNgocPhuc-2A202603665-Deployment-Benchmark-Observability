"""Daily budget in Redis, using integer nano-USD and atomic reservations."""
import hashlib
import math
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from app.config import settings
from app.redis_client import r

PRICE_INPUT_PER_1K = settings.price_input_per_1k
PRICE_OUTPUT_PER_1K = settings.price_output_per_1k
SCALE = 1_000_000_000
RESERVE_SCRIPT = """
local used = tonumber(redis.call('GET', KEYS[1]) or '0')
if used + tonumber(ARGV[1]) > tonumber(ARGV[2]) then return 0 end
redis.call('INCRBY', KEYS[1], ARGV[1])
redis.call('EXPIREAT', KEYS[1], ARGV[3])
return 1
"""

def token_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K) / 1000

def check_budget(estimated_cost: float) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expiry = int((now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).timestamp())
    identity = hashlib.sha256(settings.agent_api_key.encode()).hexdigest()
    key = f"budget:{identity}:{now:%Y-%m-%d}"
    reserved = math.ceil(estimated_cost * SCALE)
    allowed = r.eval(RESERVE_SCRIPT, 1, key, reserved,
        math.floor(settings.daily_budget_usd * SCALE), expiry)
    if not allowed:
        raise HTTPException(status_code=402, detail="Daily budget exceeded")
    return key, reserved

def record_cost(input_tokens: int, output_tokens: int, reservation: tuple[str, int]) -> float:
    cost = token_cost(input_tokens, output_tokens)
    key, reserved = reservation
    r.incrby(key, math.ceil(cost * SCALE) - reserved)
    return cost

def release_reservation(reservation: tuple[str, int]) -> None:
    key, reserved = reservation
    r.incrby(key, -reserved)
