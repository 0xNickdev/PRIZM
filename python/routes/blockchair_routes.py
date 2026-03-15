import os
import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/api/whales", tags=["whales"])
BASE = os.getenv("BLOCKCHAIR_BASE_URL", "https://api.blockchair.com")

@router.get("/{chain}")
async def get_whale_txs(chain: str = "bitcoin", min_usd: int = 500000):
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{BASE}/{chain}/transactions",
            params={"limit": 10, "s": "value(desc)"},
            timeout=10
        )
        return r.json()

@router.get("/multi/latest")
async def get_all_chains():
    chains = ["bitcoin", "ethereum", "solana", "bnb"]
    results = {}
    async with httpx.AsyncClient() as c:
        for chain in chains:
            try:
                r = await c.get(
                    f"{BASE}/{chain}/transactions",
                    params={"limit": 5, "s": "value(desc)"},
                    timeout=10
                )
                results[chain] = r.json()
            except:
                results[chain] = {"error": "timeout"}
    return results
