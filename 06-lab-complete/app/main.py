"""Production agent: shared limits, health probes and structured logs."""
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from app.config import settings
from app.auth import verify_api_key
from app.redis_client import r, redis_healthy
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_budget, record_cost, release_reservation, token_cost
from utils.mock_llm import ask as llm_ask, MOCK_RESPONSES

class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {"ts": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname, "message": record.getMessage()}
        data.update(getattr(record, "fields", {}))
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=settings.log_level.upper(), handlers=[handler], force=True)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", extra={"fields": {"environment": settings.environment}})
    yield
    r.close()
    logger.info("shutdown_complete")

app = FastAPI(title="Production AI Agent", lifespan=lifespan)

@app.exception_handler(RedisError)
async def redis_error(request: Request, exc: RedisError):
    logger.warning("redis_unavailable")
    return JSONResponse(status_code=503, content={"detail": "Dependency unavailable"})

@app.middleware("http")
async def log_request(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    logger.info("request", extra={"fields": {"method": request.method,
        "path": request.url.path, "status": response.status_code,
        "ms": round((time.monotonic() - start) * 1000, 2)}})
    return response

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ready")
def ready():
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"ready": True}

# Mock token estimates are for the lab, not provider billing.
MAX_OUTPUT_TOKENS = max(len(text.split()) * 2
    for responses in MOCK_RESPONSES.values() for text in responses)

@app.post("/ask")
def ask(body: AskRequest, api_key: str = Depends(verify_api_key)):
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="Question must not be blank")
    check_rate_limit(api_key)
    input_tokens = len(body.question.split()) * 2
    reservation = check_budget(token_cost(input_tokens, MAX_OUTPUT_TOKENS))
    try:
        answer = llm_ask(body.question)
    except Exception:
        release_reservation(reservation)
        logger.exception("mock_llm_failed")
        raise HTTPException(status_code=502, detail="Model unavailable")
    cost = record_cost(input_tokens, len(answer.split()) * 2, reservation)
    return {"question": body.question, "answer": answer, "cost_usd": cost}
