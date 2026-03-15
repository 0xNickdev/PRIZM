import os
import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/api/dex", tags=["dexscreener"])
BASE = os.getenv("DEXSCREENER_BASE_URL", "https://api.dexscreener.com")

@router.get("/new-tokens")
async def get_new_tokens():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/token-profiles/latest/v1", timeout=10)
        return r.json()

@router.get("/boosted")
async def get_boosted():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/token-boosts/top/v1", timeout=10)
        return r.json()

@router.get("/search/{query}")
async def search_token(query: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/latest/dex/search", params={"q": query}, timeout=10)
        return r.json()

@router.get("/token/{chain}/{address}")
async def get_token(chain: str, address: str):
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{BASE}/tokens/v1/{chain}/{address}", timeout=10)
        return r.json()
