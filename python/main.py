"""
═══════════════════════════════════════════════════════════════
PRIZM Backend - Full Python FastAPI Server
Auth, Market Data, AI Agent, Whale Tracking, Sentiment, Derivatives
═══════════════════════════════════════════════════════════════
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from services.whale_tracker import WhaleTrackerService
from services.sentiment import SentimentService
from services.derivatives import DerivativesService
from database import get_db, init_db

# Import signals cache
try:
    import signals_cache
except ImportError:
    signals_cache = None
    print("⚠️  signals_cache module not available")

# Import routes
from routes import market_router, agent_router, auth_router, radar_router
from routes.dexscreener_routes import router as dex_router
from routes.blockchair_routes import router as chain_whale_router

load_dotenv()

# Initialize services
whale_service = None
sentiment_service = None
derivatives_service = None
cleanup_task = None


async def periodic_cleanup():
    """
    Background task to periodically clean up old signals
    Runs every 6 hours, deletes signals older than 7 days
    """
    while True:
        try:
            await asyncio.sleep(6 * 3600)  # Wait 6 hours
            
            if signals_cache:
                deleted = signals_cache.cleanup_old_signals(hours=168)  # 7 days
                if deleted > 0:
                    print(f"🧹 Periodic cleanup: removed {deleted} old signals")
        except asyncio.CancelledError:
            print("🛑 Cleanup task cancelled")
            break
        except Exception as e:
            print(f"⚠️  Cleanup task error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    global whale_service, sentiment_service, derivatives_service, cleanup_task
    
    # Initialize database
    await init_db()
    
    # Initialize services
    whale_service = WhaleTrackerService()
    sentiment_service = SentimentService()
    derivatives_service = DerivativesService()

    # Expose services via app.state for routers
    app.state.whale_service = whale_service
    app.state.sentiment_service = sentiment_service
    app.state.derivatives_service = derivatives_service
    
    # Start background cleanup task
    if signals_cache:
        cleanup_task = asyncio.create_task(periodic_cleanup())
        print("🚀 Started periodic signals cleanup task (every 6h)")
    
    yield
    
    # Cleanup
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    
    if whale_service:
        await whale_service.close()
    if sentiment_service:
        await sentiment_service.close()
    if derivatives_service:
        await derivatives_service.close()

    # Clear state
    app.state.whale_service = None
    app.state.sentiment_service = None
    app.state.derivatives_service = None


app = FastAPI(
    title="PRIZM Backend",
    description="Full crypto market intelligence platform with AI agent",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
allowed_origins_env = os.getenv("PULSE_ALLOWED_ORIGINS", "").strip()
if allowed_origins_env:
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
frontend_path = Path("/frontend")
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory="/frontend"), name="static")

# Mount images directory for favicons
images_path = Path("/images")
if images_path.exists():
    app.mount("/images", StaticFiles(directory="/images"), name="images")

# Include all routers
app.include_router(market_router)
app.include_router(agent_router)
app.include_router(auth_router)
app.include_router(radar_router)
app.include_router(dex_router)
app.include_router(chain_whale_router)


# ══════════════════════════════════════════════════════════
# FRONTEND ROUTES
# ══════════════════════════════════════════════════════════
@app.get("/style.css")
async def serve_css():
    return FileResponse("/frontend/style.css", media_type="text/css")

@app.get("/utils.js")
async def serve_utils():
    return FileResponse("/frontend/utils.js", media_type="application/javascript")

@app.get("/api.js")
async def serve_api():
    return FileResponse("/frontend/api.js", media_type="application/javascript")

@app.get("/config.js")
async def serve_config():
    return FileResponse("/frontend/config.js", media_type="application/javascript")

@app.get("/")
async def root():
    return FileResponse("/frontend/index.html")

@app.get("/dashboard")
async def dashboard():
    return FileResponse("/frontend/dashboard.html")

@app.get("/dashboard.html")
async def dashboard_html():
    return FileResponse("/frontend/dashboard.html")

@app.get("/agents")
async def agents():
    return FileResponse("/frontend/agents.html")

@app.get("/agents.html")
async def agents_html():
    return FileResponse("/frontend/agents.html")

@app.get("/test_env_debug")
async def test_env_debug():
    return FileResponse("/frontend/test_env_debug.html")

@app.get("/test_env_debug.html")
async def test_env_debug_html():
    return FileResponse("/frontend/test_env_debug.html")

@app.get("/radar")
async def radar():
    return FileResponse("/frontend/radar.html")

@app.get("/radar.html")
async def radar_html():
    return FileResponse("/frontend/radar.html")


# ══════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "services": {
            "whale_tracker": whale_service is not None,
            "sentiment": sentiment_service is not None,
            "derivatives": derivatives_service is not None
        }
    }


@app.get("/api/debug/env")
async def debug_env():
    import os
    
    twitter_bearer = os.getenv("TWITTER_BEARER_TOKEN")
    twitter_key = os.getenv("TWITTER_API_KEY")
    twitter_secret = os.getenv("TWITTER_API_SECRET")
    whale_key = os.getenv("WHALE_ALERT_API_KEY")
    binance_key = os.getenv("BINANCE_API_KEY")
    
    return {
        "env_check": {
            "TWITTER_BEARER_TOKEN": {
                "exists": twitter_bearer is not None,
                "length": len(twitter_bearer) if twitter_bearer else 0,
                "preview": twitter_bearer[:20] + "..." if twitter_bearer and len(twitter_bearer) > 20 else twitter_bearer
            },
            "TWITTER_API_KEY": {
                "exists": twitter_key is not None,
                "length": len(twitter_key) if twitter_key else 0,
                "preview": twitter_key[:10] + "..." if twitter_key and len(twitter_key) > 10 else twitter_key
            },
            "TWITTER_API_SECRET": {
                "exists": twitter_secret is not None,
                "length": len(twitter_secret) if twitter_secret else 0
            },
            "WHALE_ALERT_API_KEY": {
                "exists": whale_key is not None,
                "length": len(whale_key) if whale_key else 0
            },
            "BINANCE_API_KEY": {
                "exists": binance_key is not None,
                "length": len(binance_key) if binance_key else 0
            }
        }
    }


# ══════════════════════════════════════════════════════════
# WHALE TRACKING
# ══════════════════════════════════════════════════════════
@app.get("/api/whales/{symbol}")
async def get_whale_transactions(
    symbol: str,
    limit: int = 20,
    min_amount_usd: float = 1000000.0
):
    if not whale_service:
        raise HTTPException(status_code=503, detail="Whale service not available")
    
    try:
        transactions = await whale_service.get_recent_transactions(
            symbol=symbol.upper(),
            limit=limit,
            min_amount_usd=min_amount_usd
        )
        return {"transactions": transactions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/whales/fetch")
async def fetch_whale_transactions(symbols: list[str] = None):
    if not whale_service:
        raise HTTPException(status_code=503, detail="Whale service not available")
    
    try:
        if symbols is None:
            symbols = ["BTC", "ETH", "SOL", "XRP"]
        
        result = await whale_service.fetch_and_cache(symbols)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════
# SENTIMENT ANALYSIS
# ══════════════════════════════════════════════════════════
@app.get("/api/sentiment/{symbol}")
async def get_sentiment(
    symbol: str,
    hours: int = 24
):
    if not sentiment_service:
        raise HTTPException(status_code=503, detail="Sentiment service not available")
    
    try:
        data = await sentiment_service.get_sentiment_data(
            symbol=symbol.upper(),
            hours=hours
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sentiment/analyze")
async def analyze_sentiment(symbols: list[str] = None):
    if not sentiment_service:
        raise HTTPException(status_code=503, detail="Sentiment service not available")
    
    try:
        if symbols is None:
            symbols = ["BTC", "ETH", "SOL", "DOGE"]
        
        result = await sentiment_service.analyze_and_cache(symbols)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════
# DERIVATIVES (FUNDING RATES, OPEN INTEREST)
# ══════════════════════════════════════════════════════════
@app.get("/api/derivatives/{symbol}")
async def get_derivatives_data(symbol: str):
    if not derivatives_service:
        raise HTTPException(status_code=503, detail="Derivatives service not available")
    
    try:
        data = await derivatives_service.get_derivatives_data(symbol.upper())
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/derivatives/fetch")
async def fetch_derivatives_data(symbols: list[str] = None):
    if not derivatives_service:
        raise HTTPException(status_code=503, detail="Derivatives service not available")
    
    try:
        if symbols is None:
            symbols = ["BTC", "ETH", "SOL"]
        
        result = await derivatives_service.fetch_and_cache(symbols)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════
# MARKET ANALYSIS
# ══════════════════════════════════════════════════════════
@app.get("/api/analysis/{symbol}")
async def get_comprehensive_analysis(symbol: str):
    try:
        symbol = symbol.upper()
        
        whales = await get_whale_transactions(symbol, limit=10, min_amount_usd=500000)
        sentiment = await get_sentiment(symbol, hours=24)
        derivatives = await get_derivatives_data(symbol)
        
        return {
            "symbol": symbol,
            "whale_activity": whales.get("transactions", []),
            "sentiment": sentiment,
            "derivatives": derivatives,
            "timestamp": "now"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
