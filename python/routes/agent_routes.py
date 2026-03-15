"""
AI Agent routes (DeepSeek integration)
No authentication required
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
from openai import OpenAI
import sys
import uuid

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import signals cache
try:
    import signals_cache
except ImportError:
    signals_cache = None
    print("⚠️  signals_cache module not available")

router = APIRouter(prefix="/api/agent", tags=["agent"])

# DeepSeek client (OpenAI-compatible)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

deepseek_client = None

if DEEPSEEK_API_KEY:
    deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL
    )

# System prompt for AI agent
SYSTEM_PROMPT = """You are PRIZM — an elite AI crypto market intelligence agent. You synthesize market data, whale movements, social sentiment, funding rates, and $CASHTAG activity into actionable intelligence. Sharp, precise, no fluff. Always respond in English only.

ANALYSIS FRAMEWORK:
1. VERDICT: BULLISH / BEARISH / NEUTRAL / CAUTION
2. CONFIDENCE: 0-100%
3. CONTEXT: 2-3 sentences on what's happening now
4. KEY SIGNALS (◆ bullets): price momentum, volume, whales, social/$cashtag velocity, funding/OI, S/R levels
5. RISK: LOW / MEDIUM / HIGH / EXTREME
6. OUTLOOK: 24-72h forecast
7. ACTION: 1 sentence clear recommendation

Rules:
- Always use $CASHTAG format for tickers
- Be data-driven and precise with real numbers from the provided data
- No marketing fluff or generic advice
- Focus on actionable intelligence
- Include specific price levels, percentages, and metrics
- Respond in English only"""

# Multi-agent mission prompt
MISSION_PROMPT = """You are PRIZM's multi-agent crypto intelligence orchestrator. You coordinate 5 specialized AI agents that each analyze different dimensions of the market. Provide DEEP, COMPREHENSIVE analysis — not summaries.

For the requested asset/topic, run ALL 5 agents with detailed output:

━━━ AGENT 1: MARKET ANALYST ━━━
Analyze in detail:
- Current price action and trend (1H, 4H, 1D timeframes)
- Key support and resistance levels with exact prices
- RSI, MACD, Bollinger Bands status
- Volume analysis vs 20-day moving average
- Chart patterns forming (if any)
- ATH distance and significance

━━━ AGENT 2: WHALE TRACKER ━━━
Analyze in detail:
- Large transactions in last 24-48h (count, direction, size)
- Net exchange flow (inflow vs outflow)
- Smart money wallet behavior
- Accumulation or distribution patterns
- Exchange reserve changes

━━━ AGENT 3: $CASHTAG SCANNER ━━━
Analyze in detail:
- Mention velocity and acceleration (% change vs baseline)
- Sentiment ratio (bullish/bearish/neutral breakdown)
- KOL (Key Opinion Leader) activity — who is talking
- Organic vs bot activity assessment
- Cross-platform spread (Twitter → Telegram → Discord)
- Narrative forming around the asset

━━━ AGENT 4: RISK ASSESSOR ━━━
Analyze in detail:
- Funding rate current + trend (positive/negative, increasing/decreasing)
- Open Interest changes ($ amount and %)
- Liquidation clusters above and below current price
- Long/Short ratio
- Correlation with BTC (decorrelating = independent move possible)
- Market-wide risk indicators (Fear & Greed, DXY, yields)

━━━ AGENT 5: ON-CHAIN & DEFI ANALYST ━━━
Analyze in detail:
- TVL changes on related protocols
- DEX volume trends
- Stablecoin flows into/out of the network
- Developer activity (if relevant)
- Upcoming token unlocks or protocol upgrades
- DeFi yield environment

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL SYNTHESIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After all agents report, provide:
- VERDICT: BULLISH / BEARISH / NEUTRAL / CAUTION
- CONFIDENCE: 0-100% (weighted by agent agreement)
- TIMEFRAME: Primary analysis window
- ENTRY STRATEGY: Specific price levels for entry
- TARGETS: 2-3 take-profit levels
- STOP LOSS: Where to cut
- RISK/REWARD: Calculated ratio
- KEY RISK: The #1 thing that could invalidate this thesis

Use REAL data from the market context provided. Be specific with numbers.
Every section should have 4-8 bullet points minimum.
Total response should be comprehensive — this is a full intelligence briefing, not a summary.
English only."""

# Signal generation prompt
SIGNAL_PROMPT = """You are an elite crypto trading signal generator for PRIZM. Analyze market data and generate 5-7 ACTIONABLE trading signals with entry/exit strategies.

For each signal, provide:
- action: BUY / SELL / HOLD / CLOSE
- ticker: Symbol only (e.g., BTC, not $BTC)
- confidence: 0-100 (numerical confidence level)
- entry: Entry price point (use current price if immediate)
- target: Take-profit target price
- stop: Stop-loss price
- timeframe: Position timeframe (e.g., "1-3 days", "Immediate", "4-7 days")
- reason: 1-2 sentences with SPECIFIC data (price %, volume change, Fear&Greed, momentum)

Trade Logic:
- BUY: Strong uptrend, high volume, positive sentiment → open long
- SELL: Downtrend, distribution signs, negative sentiment → open short or exit longs
- CLOSE: Take profit or cut losses on existing position
- HOLD: Consolidation, wait for clearer signals

Use REAL numbers from provided data. Calculate entry/target/stop based on:
- Support/resistance levels (±2-5% from current)
- ATH distances
- Volume patterns
- Fear & Greed extremes

Format as JSON array:
[{"action": "BUY", "ticker": "SOL", "confidence": 78, "entry": 142.50, "target": 165.00, "stop": 135.00, "timeframe": "2-4 days", "reason": "Volume surge +240% with RSI at 58. Breaking $140 resistance. F&G at 72 (Greed) suggests momentum. Target previous local high."}]

Return 5-7 signals. Mix actions (BUY/SELL/HOLD). Prioritize high-confidence setups. English only."""


class ChatRequest(BaseModel):
    message: str
    context: str = ""


class ChatResponse(BaseModel):
    reply: str | None
    error: str | None = None


class MissionRequest(BaseModel):
    task: str
    market_data: str = ""
    context: str = ""


class MissionResponse(BaseModel):
    synthesis: str | None


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Chat with AI agent (DeepSeek)
    Analyze market data, answer crypto questions
    """
    
    if not request.message:
        raise HTTPException(status_code=400, detail="No message provided")
    
    if not deepseek_client:
        return ChatResponse(
            reply=None,
            error="Set DEEPSEEK_API_KEY env var"
        )
    
    try:
        full_message = request.message
        if request.context:
            full_message += f"\n\nMarket Data:\n{request.context}"
        
        response = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_message}
            ],
            max_tokens=2048,
            temperature=0.7
        )
        
        reply = response.choices[0].message.content
        return ChatResponse(reply=reply, error=None)
    
    except Exception as e:
        return ChatResponse(reply=None, error=str(e))


@router.post("/mission", response_model=MissionResponse)
async def run_mission(request: MissionRequest):
    """
    Multi-agent mission — full comprehensive analysis
    """
    
    if not request.task:
        raise HTTPException(status_code=400, detail="No task provided")
    
    if not deepseek_client:
        return MissionResponse(synthesis=None)
    
    try:
        # Build full context with market data
        full_task = request.task
        
        # Add market data if provided
        if request.market_data:
            try:
                import json
                coins = json.loads(request.market_data)
                
                market_context = "\n\n━━━ LIVE MARKET DATA ━━━\n"
                
                total_mcap = sum(c.get('market_cap', 0) for c in coins)
                total_volume = sum(c.get('total_volume', 0) for c in coins)
                avg_24h = sum(c.get('price_change_percentage_24h_in_currency', 0) for c in coins) / max(len(coins), 1)
                
                market_context += f"Total Market Cap: ${total_mcap/1e9:.1f}B\n"
                market_context += f"24h Volume: ${total_volume/1e9:.1f}B\n"
                market_context += f"Average 24h Change: {avg_24h:+.2f}%\n\n"
                
                market_context += "Asset Details:\n"
                for c in coins[:15]:
                    sym = c.get('symbol', '').upper()
                    price = c.get('current_price', 0)
                    ch_1h = c.get('price_change_percentage_1h_in_currency', 0)
                    ch_24h = c.get('price_change_percentage_24h_in_currency', 0)
                    ch_7d = c.get('price_change_percentage_7d_in_currency', 0)
                    vol = c.get('total_volume', 0) / 1e9
                    mcap = c.get('market_cap', 0) / 1e9
                    ath = c.get('ath', 0)
                    ath_dist = c.get('ath_change_percentage', 0)
                    high = c.get('high_24h', 0)
                    low = c.get('low_24h', 0)
                    market_context += f"${sym}: ${price:,.4f} | 1h: {ch_1h:+.2f}% | 24h: {ch_24h:+.2f}% | 7d: {ch_7d:+.2f}% | Vol: ${vol:.2f}B | MCap: ${mcap:.1f}B | ATH: ${ath:,.2f} ({ath_dist:.1f}%) | 24h Range: ${low:,.2f}-${high:,.2f}\n"
                
                full_task += market_context
            except:
                if request.market_data:
                    full_task += f"\n\nMarket Data:\n{request.market_data[:2000]}"
        
        # Add additional context
        if request.context:
            full_task += f"\n\nAdditional Context:\n{request.context}"
        
        # Try to get Fear & Greed Index
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                fng_resp = await client.get('https://api.alternative.me/fng/')
                if fng_resp.status_code == 200:
                    fng_data = fng_resp.json()
                    fng_value = fng_data['data'][0]['value']
                    fng_class = fng_data['data'][0]['value_classification']
                    full_task += f"\n\nFear & Greed Index: {fng_value}/100 ({fng_class})"
        except:
            pass
        
        # Call DeepSeek API with extended tokens
        response = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": MISSION_PROMPT},
                {"role": "user", "content": full_task}
            ],
            max_tokens=4096,
            temperature=0.8
        )
        
        synthesis = response.choices[0].message.content
        return MissionResponse(synthesis=synthesis)
    
    except Exception as e:
        return MissionResponse(synthesis=None)


class Signal(BaseModel):
    action: str
    ticker: str
    confidence: int
    entry: float
    target: float
    stop: float
    timeframe: str
    reason: str


class SignalsRequest(BaseModel):
    market_data: str = ""


class SignalsResponse(BaseModel):
    signals: list[Signal] | None
    error: str | None = None


@router.post("/signals", response_model=SignalsResponse)
async def generate_signals(request: SignalsRequest):
    """
    Generate AI trading signals with entry/exit strategies
    """
    
    if not deepseek_client:
        return SignalsResponse(
            signals=None,
            error="Set DEEPSEEK_API_KEY env var"
        )
    
    try:
        import json
        
        market_context = "Current crypto market overview:\n\n"
        
        if request.market_data:
            try:
                coins = json.loads(request.market_data)
                
                total_mcap = sum(c.get('market_cap', 0) for c in coins)
                total_volume = sum(c.get('total_volume', 0) for c in coins)
                avg_24h = sum(c.get('price_change_percentage_24h_in_currency', 0) for c in coins) / len(coins)
                
                top_gainers = sorted(coins, key=lambda x: x.get('price_change_percentage_24h_in_currency', 0), reverse=True)[:3]
                top_losers = sorted(coins, key=lambda x: x.get('price_change_percentage_24h_in_currency', 0))[:3]
                
                market_context += f"Total Market Cap: ${total_mcap/1e9:.1f}B\n"
                market_context += f"24h Volume: ${total_volume/1e9:.1f}B\n"
                market_context += f"Average 24h Change: {avg_24h:+.2f}%\n\n"
                
                market_context += "Top Gainers (24h):\n"
                for c in top_gainers:
                    market_context += f"- {c.get('symbol', '').upper()}: ${c.get('current_price', 0):.4f} ({c.get('price_change_percentage_24h_in_currency', 0):+.2f}%), Vol: ${c.get('total_volume', 0)/1e9:.2f}B\n"
                
                market_context += "\nTop Losers (24h):\n"
                for c in top_losers:
                    market_context += f"- {c.get('symbol', '').upper()}: ${c.get('current_price', 0):.4f} ({c.get('price_change_percentage_24h_in_currency', 0):+.2f}%), Vol: ${c.get('total_volume', 0)/1e9:.2f}B\n"
                
                market_context += "\n\nTop 8 Assets (detailed):\n"
                for c in coins[:8]:
                    sym = c.get('symbol', '').upper()
                    price = c.get('current_price', 0)
                    ch_1h = c.get('price_change_percentage_1h_in_currency', 0)
                    ch_24h = c.get('price_change_percentage_24h_in_currency', 0)
                    ch_7d = c.get('price_change_percentage_7d_in_currency', 0)
                    vol = c.get('total_volume', 0) / 1e9
                    mcap = c.get('market_cap', 0) / 1e9
                    ath_dist = c.get('ath_change_percentage', 0)
                    market_context += f"{sym}: ${price:.4f} | 1h: {ch_1h:+.2f}% | 24h: {ch_24h:+.2f}% | 7d: {ch_7d:+.2f}% | Vol: ${vol:.2f}B | MCap: ${mcap:.1f}B | ATH Δ: {ath_dist:.1f}%\n"
                
            except:
                market_context += request.market_data[:1000]
        
        # Try to get Fear & Greed Index
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                fng_resp = await client.get('https://api.alternative.me/fng/')
                if fng_resp.status_code == 200:
                    fng_data = fng_resp.json()
                    fng_value = fng_data['data'][0]['value']
                    fng_class = fng_data['data'][0]['value_classification']
                    market_context += f"\nFear & Greed Index: {fng_value}/100 ({fng_class})\n"
        except:
            pass
        
        prompt = f"{market_context}\n\nGenerate 5-7 trading signals with entry/exit strategies based on this data."
        
        response = deepseek_client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SIGNAL_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        
        try:
            start = content.find('[')
            end = content.rfind(']') + 1
            if start >= 0 and end > start:
                signals_data = json.loads(content[start:end])
                signals = [Signal(**sig) for sig in signals_data]
                
                if signals_cache and signals:
                    try:
                        generation_id = str(uuid.uuid4())
                        market_hash = signals_cache.generate_market_hash(market_context[:500])
                        signals_dict = [sig.dict() for sig in signals]
                        signals_cache.save_signals(signals_dict, market_hash, generation_id)
                    except Exception as cache_err:
                        print(f"Cache save error: {cache_err}")
                
                return SignalsResponse(signals=signals, error=None)
        except Exception as parse_err:
            print(f"Signal parsing error: {parse_err}")
            print(f"AI Response: {content[:500]}")
        
        return SignalsResponse(signals=[], error=None)
    
    except Exception as e:
        return SignalsResponse(signals=None, error=str(e))


@router.get("/signals/cached")
async def get_cached_signals(hours: int = 24, limit: int = 50):
    if not signals_cache:
        return {"signals": [], "error": "Cache not available"}
    try:
        signals = signals_cache.get_recent_signals(hours=hours, limit=limit)
        return {"signals": signals, "count": len(signals), "hours": hours}
    except Exception as e:
        return {"signals": [], "error": str(e)}


@router.get("/signals/latest")
async def get_latest_signals(limit: int = 20):
    if not signals_cache:
        return {"signals": [], "error": "Cache not available"}
    try:
        signals = signals_cache.get_latest_generation_signals(limit=limit)
        return {"signals": signals, "count": len(signals)}
    except Exception as e:
        return {"signals": [], "error": str(e)}


@router.get("/signals/ticker/{ticker}")
async def get_ticker_signals(ticker: str, hours: int = 24):
    if not signals_cache:
        return {"signals": [], "error": "Cache not available"}
    try:
        signals = signals_cache.get_signals_by_ticker(ticker, hours=hours)
        return {"ticker": ticker.upper(), "signals": signals, "count": len(signals), "hours": hours}
    except Exception as e:
        return {"signals": [], "error": str(e)}


@router.delete("/signals/cleanup")
async def cleanup_signals(hours: int = 168):
    if not signals_cache:
        return {"deleted": 0, "error": "Cache not available"}
    try:
        deleted = signals_cache.cleanup_old_signals(hours=hours)
        return {"deleted": deleted, "hours": hours, "message": f"Deleted {deleted} signals older than {hours} hours"}
    except Exception as e:
        return {"deleted": 0, "error": str(e)}


@router.get("/signals/stats")
async def get_signals_stats():
    if not signals_cache:
        return {"error": "Cache not available"}
    try:
        stats = signals_cache.get_db_stats()
        return stats
    except Exception as e:
        return {"error": str(e)}
