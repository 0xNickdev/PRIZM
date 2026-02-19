"""
Signal cache using SQLite for fast persistence
Automatic cleanup of old signals
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional
import os
from contextlib import contextmanager
import hashlib

DB_PATH = os.getenv("SIGNALS_DB_PATH", "/app/data/signals.db")

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database schema"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Signals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                ticker TEXT NOT NULL,
                confidence INTEGER NOT NULL,
                entry REAL NOT NULL,
                target REAL NOT NULL,
                stop REAL NOT NULL,
                timeframe TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                market_hash TEXT,
                generation_id TEXT
            )
        """)
        
        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_created 
            ON signals(created_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_ticker 
            ON signals(ticker)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_generation 
            ON signals(generation_id)
        """)
        
        print("✅ Signals database initialized")


def generate_market_hash(market_data: str) -> str:
    """Generate hash from market data to avoid duplicate generations"""
    return hashlib.md5(market_data.encode()).hexdigest()[:16]


def save_signals(signals: List[dict], market_hash: str = None, generation_id: str = None):
    """
    Save signals to database
    
    Args:
        signals: List of signal dictionaries
        market_hash: Optional hash of market data for deduplication
        generation_id: Unique ID for this generation batch
        
    Returns:
        Number of saved signals
    """
    if not signals:
        return 0
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        for signal in signals:
            cursor.execute("""
                INSERT INTO signals 
                (action, ticker, confidence, entry, target, stop, timeframe, reason, market_hash, generation_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.get('action'),
                signal.get('ticker'),
                signal.get('confidence'),
                signal.get('entry'),
                signal.get('target'),
                signal.get('stop'),
                signal.get('timeframe'),
                signal.get('reason'),
                market_hash,
                generation_id
            ))
        
        count = cursor.rowcount
        print(f"💾 Saved {count} signals to cache")
        return count


def get_recent_signals(hours: int = 24, limit: int = 50) -> List[dict]:
    """
    Get recent signals from database
    
    Args:
        hours: Get signals from last N hours (default: 24)
        limit: Maximum number of signals to return
        
    Returns:
        List of signal dictionaries with timestamps
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Calculate cutoff time
        cutoff = datetime.now() - timedelta(hours=hours)
        
        cursor.execute("""
            SELECT 
                action, ticker, confidence, entry, target, stop, 
                timeframe, reason, created_at, generation_id
            FROM signals
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (cutoff, limit))
        
        rows = cursor.fetchall()
        
        signals = []
        for row in rows:
            signals.append({
                'action': row['action'],
                'ticker': row['ticker'],
                'confidence': row['confidence'],
                'entry': row['entry'],
                'target': row['target'],
                'stop': row['stop'],
                'timeframe': row['timeframe'],
                'reason': row['reason'],
                'created_at': row['created_at'],
                'generation_id': row['generation_id']
            })
        
        return signals


def get_latest_generation_signals(limit: int = 20) -> List[dict]:
    """
    Get signals from the most recent generation batch
    
    Args:
        limit: Maximum number of signals to return
        
    Returns:
        List of signal dictionaries from latest generation
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get latest generation_id
        cursor.execute("""
            SELECT generation_id
            FROM signals
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        if not row or not row['generation_id']:
            return []
        
        latest_gen_id = row['generation_id']
        
        # Get all signals from this generation
        cursor.execute("""
            SELECT 
                action, ticker, confidence, entry, target, stop, 
                timeframe, reason, created_at
            FROM signals
            WHERE generation_id = ?
            ORDER BY confidence DESC
            LIMIT ?
        """, (latest_gen_id, limit))
        
        rows = cursor.fetchall()
        
        signals = []
        for row in rows:
            signals.append({
                'action': row['action'],
                'ticker': row['ticker'],
                'confidence': row['confidence'],
                'entry': row['entry'],
                'target': row['target'],
                'stop': row['stop'],
                'timeframe': row['timeframe'],
                'reason': row['reason'],
                'created_at': row['created_at']
            })
        
        return signals


def get_signals_by_ticker(ticker: str, hours: int = 24) -> List[dict]:
    """Get signals for specific ticker"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        cursor.execute("""
            SELECT 
                action, ticker, confidence, entry, target, stop, 
                timeframe, reason, created_at
            FROM signals
            WHERE ticker = ? AND created_at >= ?
            ORDER BY created_at DESC
        """, (ticker.upper(), cutoff))
        
        rows = cursor.fetchall()
        
        signals = []
        for row in rows:
            signals.append({
                'action': row['action'],
                'ticker': row['ticker'],
                'confidence': row['confidence'],
                'entry': row['entry'],
                'target': row['target'],
                'stop': row['stop'],
                'timeframe': row['timeframe'],
                'reason': row['reason'],
                'created_at': row['created_at']
            })
        
        return signals


def cleanup_old_signals(hours: int = 168):
    """
    Delete signals older than specified hours
    Default: 7 days (168 hours)
    
    Args:
        hours: Delete signals older than N hours
        
    Returns:
        Number of deleted records
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        cursor.execute("""
            DELETE FROM signals
            WHERE created_at < ?
        """, (cutoff,))
        
        deleted = cursor.rowcount
        
        if deleted > 0:
            print(f"🗑️  Cleaned up {deleted} old signals (older than {hours}h)")
        
        return deleted


def get_db_stats() -> dict:
    """Get database statistics"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total signals
        cursor.execute("SELECT COUNT(*) as total FROM signals")
        total = cursor.fetchone()['total']
        
        # Signals in last 24h
        cutoff_24h = datetime.now() - timedelta(hours=24)
        cursor.execute("""
            SELECT COUNT(*) as recent 
            FROM signals 
            WHERE created_at >= ?
        """, (cutoff_24h,))
        recent = cursor.fetchone()['recent']
        
        # Oldest signal
        cursor.execute("""
            SELECT MIN(created_at) as oldest 
            FROM signals
        """)
        oldest = cursor.fetchone()['oldest']
        
        # Most active tickers
        cursor.execute("""
            SELECT ticker, COUNT(*) as count
            FROM signals
            WHERE created_at >= ?
            GROUP BY ticker
            ORDER BY count DESC
            LIMIT 5
        """, (cutoff_24h,))
        
        top_tickers = [
            {'ticker': row['ticker'], 'count': row['count']}
            for row in cursor.fetchall()
        ]
        
        # Number of unique generations
        cursor.execute("""
            SELECT COUNT(DISTINCT generation_id) as count
            FROM signals
            WHERE created_at >= ? AND generation_id IS NOT NULL
        """, (cutoff_24h,))
        generations = cursor.fetchone()['count']
        
        return {
            'total_signals': total,
            'recent_24h': recent,
            'oldest_signal': oldest,
            'top_tickers': top_tickers,
            'generations_24h': generations,
            'db_path': DB_PATH
        }


# Initialize database on module import
try:
    init_db()
except Exception as e:
    print(f"⚠️  Signals database initialization failed: {e}")
