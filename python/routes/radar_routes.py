from __future__ import annotations

import os
import random
import time
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore

try:
    import redis.asyncio as redis  # type: ignore
except Exception:
    redis = None  # type: ignore

from auth import get_current_user
from models import User

router = APIRouter(prefix="/api/radar", tags=["radar"])

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY")

STABLE_SYMBOLS = {
    "USDT",
    "USDC",
    "DAI",
    "TUSD",
    "BUSD",
    "USDP",
    "FDUSD",
    "USDE",
    "FRAX",
    "PYUSD",
    "GUSD",
    "LUSD",
}

STABLE_IDS = {
    "tether",
    "usd-coin",
    "dai",
    "true-usd",
    "binance-usd",
    "paxos-standard",
    "first-digital-usd",
    "ethena-usde",
    "frax",
    "paypal-usd",
    "gemini-dollar",
    "liquity-usd",
    "usd1-wlfi",
}

_cache: dict[str, Any] = {"ts": 0.0, "data": None}
_breakdown_cache: dict[str, Any] = {"ts": {}, "data": {}}

_rl_mem: dict[str, Any] = {"buckets": {}}

REDIS_URL = os.getenv("REDIS_URL", "")
_redis_client = None

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

_deepseek_client = None
if DEEPSEEK_API_KEY and OpenAI:
    _deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _client_key(request: Request, user: User) -> str:
    xf = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    ip = xf or (request.client.host if request.client else "") or "unknown"
    return f"u:{getattr(user, 'id', '')}:{ip}"


async def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not REDIS_URL or not redis:
        _redis_client = None
        return None
    try:
        _redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        return _redis_client
    except Exception:
        _redis_client = None
        return None


async def _rate_limit(request: Request, user: User, scope: str, limit: int, window_sec: int) -> None:
    """Simple fixed-window rate limit. Enforced per user+IP.

    Uses Redis when available, otherwise in-memory.
    """
    key = f"rl:{scope}:{_client_key(request, user)}:{int(time.time()) // window_sec}"

    r = await _get_redis()
    if r is not None:
        try:
            n = await r.incr(key)
            if n == 1:
                await r.expire(key, window_sec)
            if n > limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            return
        except HTTPException:
            raise
        except Exception:
            pass

    # In-memory fallback
    buckets: dict[str, Any] = _rl_mem["buckets"]
    now = int(time.time())
    if key not in buckets:
        buckets[key] = {"n": 0, "exp": now + window_sec}
    b = buckets[key]
    if b["exp"] <= now:
        b["n"] = 0
        b["exp"] = now + window_sec
    b["n"] += 1
    if b["n"] > limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


def _safe_symbol(s: str | None) -> str:
    return (s or "").strip().upper()


def _is_stable(coin: dict[str, Any]) -> bool:
    sym = _safe_symbol(coin.get("symbol"))
    cid = (coin.get("id") or "").strip().lower()
    name = (coin.get("name") or "").strip().lower()
    if sym in STABLE_SYMBOLS:
        return True
    if cid in STABLE_IDS:
        return True
    if sym.endswith("USD") and sym in {"USDD", "USDP", "TUSD", "FDUSD", "PYUSD"}:
        return True
    # Catch newer/unknown USD-pegged tickers like USD1/USDX/etc
    if sym.startswith("USD"):
        return True
    if " usd" in f" {name} ":
        price = coin.get("current_price")
        if isinstance(price, (int, float)) and 0.97 <= float(price) <= 1.03:
            return True
    return False


def _clamp(x: float, a: float, b: float) -> float:
    return max(a, min(b, x))


def _score_coin(coin: dict[str, Any], social_velocity: float | None = None) -> tuple[int, list[str]]:
    ch24 = float(coin.get("price_change_percentage_24h_in_currency") or 0.0)
    ch1h = float(coin.get("price_change_percentage_1h_in_currency") or 0.0)
    mcap = float(coin.get("market_cap") or 0.0)
    vol = float(coin.get("total_volume") or 0.0)

    vol_ratio = (vol / mcap) if mcap > 0 else 0.0

    momentum = _clamp(abs(ch24) / 12.0, 0.0, 1.0)
    accel = _clamp(abs(ch1h) / 3.0, 0.0, 1.0)
    volume = _clamp(vol_ratio / 0.25, 0.0, 1.0)

    social = 0.0
    if social_velocity is not None:
        social = _clamp(social_velocity / 500.0, 0.0, 1.0)

    raw = 45.0 + 30.0 * momentum + 15.0 * volume + 10.0 * accel + 20.0 * social
    raw += random.uniform(-4.0, 4.0)
    score = int(_clamp(raw, 50.0, 100.0))

    tags: list[str] = []
    if volume >= 0.65:
        tags.append("volume")
    if social >= 0.5:
        tags.append("social")
    if accel >= 0.6:
        tags.append("kol")
    if momentum >= 0.8:
        tags.append("whale")
    if not tags:
        tags.append("volume" if volume > 0.25 else "social")

    tags = list(dict.fromkeys(tags))
    return score, tags


async def _fetch_top_coins(limit: int) -> list[dict[str, Any]]:
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params: dict[str, Any] = {
        "vs_currency": "usd",
        "order": "volume_desc",
        "per_page": min(limit, 250),
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "1h,24h,7d",
    }
    if COINGECKO_API_KEY:
        params["x_cg_demo_api_key"] = COINGECKO_API_KEY

    async with httpx.AsyncClient(timeout=15.0, proxies={}) as client:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="CoinGecko unavailable")
        return r.json()


@router.get("/signals")
async def radar_signals(
    request: Request,
    limit: int = 80,
    current_user: User = Depends(get_current_user),
):
    if limit < 1 or limit > 120:
        raise HTTPException(status_code=400, detail="limit must be 1..120")
    await _rate_limit(request, current_user, scope="radar_signals", limit=30, window_sec=60)

    ts = time.time()
    if _cache["data"] is not None and (ts - float(_cache["ts"])) < 20:
        return _cache["data"]

    coins = await _fetch_top_coins(limit=limit)
    coins = [c for c in coins if not _is_stable(c)]

    symbol_list = [_safe_symbol(c.get("symbol")) for c in coins]
    symbol_list = [s for s in symbol_list if s]

    social_velocity_map: dict[str, float] = {}
    sentiment_service = getattr(request.app.state, "sentiment_service", None)
    if sentiment_service:
        try:
            sample = symbol_list[:25]
            result = await sentiment_service.get_cashtag_metrics(sample)
            if result and result.get("status") == "ok":
                for item in result.get("data", []):
                    sym = _safe_symbol(item.get("symbol"))
                    v = item.get("velocity")
                    if sym and isinstance(v, (int, float)):
                        social_velocity_map[sym] = float(v)
        except Exception:
            social_velocity_map = {}

    whale_service = getattr(request.app.state, "whale_service", None)
    whale_hot: set[str] = set()
    if whale_service:
        try:
            for sym in symbol_list[:12]:
                txs = await whale_service.get_recent_transactions(sym, limit=3, min_amount_usd=750000.0)
                if txs:
                    whale_hot.add(sym)
        except Exception:
            whale_hot = set()

    out = []
    for c in coins[:limit]:
        sym = _safe_symbol(c.get("symbol"))
        score, tags = _score_coin(c, social_velocity_map.get(sym))
        if sym in whale_hot and "whale" not in tags:
            tags = ["whale", *tags]
            tags = list(dict.fromkeys(tags))
            score = min(100, score + 6)

        heat = "hot" if score >= 85 else "warm" if score >= 70 else "cold"
        primary = tags[0]

        out.append(
            {
                "coin_id": c.get("id"),
                "symbol": sym,
                "name": c.get("name"),
                "type": primary,
                "types": tags,
                "score": score,
                "heat": heat,
                "price": c.get("current_price"),
                "change": c.get("price_change_percentage_24h_in_currency"),
                "mcap": c.get("market_cap"),
                "volume": c.get("total_volume"),
                "time": "live",
                "meta": {
                    "social_velocity": social_velocity_map.get(sym, 0.0),
                    "whale_tx": sym in whale_hot,
                },
            }
        )

    out.sort(key=lambda x: x.get("score", 0), reverse=True)

    payload = {"ts": _now_iso(), "signals": out}
    _cache["ts"] = ts
    _cache["data"] = payload
    return payload


@router.get("/breakdown/{symbol}")
async def radar_breakdown(
    request: Request,
    symbol: str,
    include_ai: int = 0,
    current_user: User = Depends(get_current_user),
):
    sym = _safe_symbol(symbol)
    if not sym:
        raise HTTPException(status_code=400, detail="symbol required")
    if len(sym) > 10 or not sym.replace("$", "").isalnum():
        raise HTTPException(status_code=400, detail="invalid symbol")

    await _rate_limit(request, current_user, scope="radar_breakdown", limit=20, window_sec=60)
    if include_ai:
        await _rate_limit(request, current_user, scope="radar_breakdown_ai", limit=5, window_sec=300)

    # Cache breakdown for 60s per symbol (+ include_ai flag)
    ck = f"{sym}:{1 if include_ai else 0}"
    now = time.time()
    prev_ts = _breakdown_cache["ts"].get(ck)
    if prev_ts and (now - float(prev_ts)) < 60 and ck in _breakdown_cache["data"]:
        return _breakdown_cache["data"][ck]

    whale_service = getattr(request.app.state, "whale_service", None)
    sentiment_service = getattr(request.app.state, "sentiment_service", None)
    derivatives_service = getattr(request.app.state, "derivatives_service", None)

    whales = []
    if whale_service:
        try:
            whales = await whale_service.get_recent_transactions(sym, limit=10, min_amount_usd=500000.0)
        except Exception:
            whales = []

    sentiment = None
    if sentiment_service:
        try:
            sentiment = await sentiment_service.get_sentiment_data(sym, hours=24)
        except Exception:
            sentiment = None

    cashtags = None
    if sentiment_service:
        try:
            cashtags = await sentiment_service.get_cashtag_metrics([sym])
        except Exception:
            cashtags = None

    derivatives = None
    if derivatives_service:
        try:
            derivatives = await derivatives_service.get_derivatives_data(sym)
        except Exception:
            derivatives = None

    breakdown = {
        "symbol": sym,
        "ts": _now_iso(),
        "whales": whales,
        "sentiment": sentiment,
        "cashtags": cashtags,
        "derivatives": derivatives,
        "dev": None,
    }

    summary = None
    if include_ai and _deepseek_client:
        try:
            prompt = (
                f"You are Pulse Radar. Provide a concise breakdown for ${sym}. "
                "Return 4-7 bullet points with numbers if available. "
                "Focus on: whale activity, mention velocity/sentiment, volume/derivatives. "
                "No hype, just facts and interpretation."
            )
            response = _deepseek_client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": str(breakdown)[:12000]},
                ],
                temperature=0.2,
            )
            summary = response.choices[0].message.content
        except Exception:
            summary = None

    payload = {"breakdown": breakdown, "summary": summary}
    _breakdown_cache["ts"][ck] = now
    _breakdown_cache["data"][ck] = payload
    return payload
