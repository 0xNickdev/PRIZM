"""
Derivatives Service - Funding rates, open interest from exchanges
"""
import os
import httpx
import asyncio
from datetime import datetime
import ccxt.async_support as ccxt


class DerivativesService:
    """Get derivatives data from crypto exchanges"""
    
    def __init__(self):
        self.binance_key = os.getenv("BINANCE_API_KEY")
        self.binance_secret = os.getenv("BINANCE_API_SECRET")
        self.client = httpx.AsyncClient(timeout=30.0)
        
        # Initialize exchange clients
        self.binance = None
        if self.binance_key and self.binance_secret:
            self.binance = ccxt.binance({
                'apiKey': self.binance_key,
                'secret': self.binance_secret,
                'options': {'defaultType': 'future'}
            })
    
    async def close(self):
        await self.client.aclose()
        if self.binance:
            await self.binance.close()
    
    async def get_derivatives_data(self, symbol: str):
        """
        Get funding rates and open interest for a symbol
        """
        if not self.binance:
            return {"status": "error", "message": "Binance API not configured"}
        
        try:
            # Get funding rate
            funding = await self._get_funding_rate(symbol)
            
            # Get open interest
            open_interest = await self._get_open_interest(symbol)
            
            return {
                "symbol": symbol,
                "exchange": "binance",
                "funding_rate": funding,
                "open_interest": open_interest,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def fetch_and_cache(self, symbols: list[str]):
        """
        Fetch and cache derivatives data for multiple symbols
        """
        if not self.binance:
            return {"status": "error", "message": "Exchange API not configured"}
        
        try:
            results = {}
            
            for symbol in symbols:
                data = await self.get_derivatives_data(symbol)
                results[symbol] = data
                
                # TODO: Save to database
            
            return {
                "status": "ok",
                "fetched": len(results),
                "symbols": list(results.keys())
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def _get_funding_rate(self, symbol: str):
        """Get current funding rate from Binance"""
        try:
            # Convert symbol format (BTC -> BTCUSDT)
            pair = f"{symbol}USDT"
            
            url = "https://fapi.binance.com/fapi/v1/premiumIndex"
            params = {"symbol": pair}
            
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "current_rate": float(data.get("lastFundingRate", 0)) * 100,  # Convert to percentage
                    "next_funding_time": data.get("nextFundingTime"),
                    "mark_price": float(data.get("markPrice", 0))
                }
            else:
                return None
                
        except Exception:
            return None
    
    async def _get_open_interest(self, symbol: str):
        """Get open interest from Binance"""
        try:
            pair = f"{symbol}USDT"
            
            url = "https://fapi.binance.com/fapi/v1/openInterest"
            params = {"symbol": pair}
            
            response = await self.client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "open_interest": float(data.get("openInterest", 0)),
                    "symbol": symbol,
                    "timestamp": data.get("time")
                }
            else:
                return None
                
        except Exception:
            return None
