"""
Routes package initialization
"""
from .market_routes import router as market_router
from .agent_routes import router as agent_router

__all__ = [
    "market_router",
    "agent_router"
]
