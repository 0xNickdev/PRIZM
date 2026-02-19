"""
Whale Tracker Service - Monitor large crypto transactions
"""
import os
import httpx
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from database import AsyncSessionLocal


class WhaleTrackerService:
    """Track whale transactions using Whale Alert API"""
    
    def __init__(self):
        self.api_key = os.getenv("WHALE_ALERT_API_KEY")
        self.base_url = "https://api.whale-alert.io/v1"
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def close(self):
        await self.client.aclose()
    
    async def get_recent_transactions(
        self,
        symbol: str,
        limit: int = 20,
        min_amount_usd: float = 1000000.0
    ):
        """
        Get recent whale transactions from database
        """
        if not self.api_key:
            return {"status": "error", "message": "Whale Alert API key not configured"}
        
        async with AsyncSessionLocal() as session:
            # Query from database (would be implemented with SQLAlchemy models)
            # For now, return empty list until implemented
            return []
    
    async def fetch_and_cache(self, symbols: list[str]):
        """
        Fetch latest whale transactions from API and cache to database
        """
        if not self.api_key:
            return {"status": "error", "message": "Whale Alert API key not configured"}
        
        try:
            # Get transactions from last 10 minutes
            min_timestamp = int((datetime.utcnow() - timedelta(minutes=10)).timestamp())
            
            url = f"{self.base_url}/transactions"
            params = {
                "api_key": self.api_key,
                "min_value": 500000,  # Min $500k transactions
                "start": min_timestamp,
                "limit": 100
            }
            
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                transactions = data.get("transactions", [])
                
                # Filter by symbols and cache to database
                filtered = [
                    t for t in transactions
                    if t.get("symbol", "").upper() in [s.upper() for s in symbols]
                ]
                
                # TODO: Save to database
                
                return {
                    "status": "ok",
                    "fetched": len(filtered),
                    "symbols": symbols
                }
            else:
                return {
                    "status": "error",
                    "message": f"API returned {response.status_code}"
                }
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
