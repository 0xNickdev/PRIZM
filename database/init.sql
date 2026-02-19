-- ══════════════════════════════════════════════════════════
-- PULSΞ Database Schema - PostgreSQL
-- ══════════════════════════════════════════════════════════

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ══════════════════════════════════════════════════════════
-- USERS
-- ══════════════════════════════════════════════════════════
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT,
    auth_method VARCHAR(50) NOT NULL DEFAULT 'email', -- 'email', 'twitter', 'google'
    twitter_id VARCHAR(255),
    display_name VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    extra_data JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_twitter_id ON users(twitter_id);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- ══════════════════════════════════════════════════════════
-- PORTFOLIOS
-- ══════════════════════════════════════════════════════════
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_portfolios_user_id ON portfolios(user_id);

-- ══════════════════════════════════════════════════════════
-- HOLDINGS
-- ══════════════════════════════════════════════════════════
CREATE TABLE holdings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    coin_id VARCHAR(100) NOT NULL, -- coingecko id (bitcoin, ethereum, etc)
    symbol VARCHAR(20) NOT NULL,
    amount DECIMAL(30, 10) NOT NULL,
    avg_buy_price DECIMAL(20, 8),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, coin_id)
);

CREATE INDEX idx_holdings_portfolio_id ON holdings(portfolio_id);
CREATE INDEX idx_holdings_coin_id ON holdings(coin_id);

-- ══════════════════════════════════════════════════════════
-- WATCHLISTS
-- ══════════════════════════════════════════════════════════
CREATE TABLE watchlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    coin_id VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, coin_id)
);

CREATE INDEX idx_watchlists_user_id ON watchlists(user_id);
CREATE INDEX idx_watchlists_coin_id ON watchlists(coin_id);

-- ══════════════════════════════════════════════════════════
-- PRICE ALERTS
-- ══════════════════════════════════════════════════════════
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    coin_id VARCHAR(100) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- 'price_above', 'price_below', 'percent_change'
    target_value DECIMAL(20, 8) NOT NULL,
    current_value DECIMAL(20, 8),
    is_triggered BOOLEAN DEFAULT false,
    triggered_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    notification_sent BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_alerts_user_id ON alerts(user_id);
CREATE INDEX idx_alerts_coin_id ON alerts(coin_id);
CREATE INDEX idx_alerts_is_active ON alerts(is_active) WHERE is_active = true;

-- ══════════════════════════════════════════════════════════
-- WHALE TRANSACTIONS (cached from Whale Alert API)
-- ══════════════════════════════════════════════════════════
CREATE TABLE whale_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_hash VARCHAR(255) UNIQUE NOT NULL,
    blockchain VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    amount DECIMAL(30, 10) NOT NULL,
    amount_usd DECIMAL(20, 2) NOT NULL,
    from_address TEXT,
    from_owner VARCHAR(255),
    to_address TEXT,
    to_owner VARCHAR(255),
    transaction_type VARCHAR(50), -- 'transfer', 'exchange_deposit', 'exchange_withdrawal'
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_whale_transactions_symbol ON whale_transactions(symbol);
CREATE INDEX idx_whale_transactions_timestamp ON whale_transactions(timestamp DESC);
CREATE INDEX idx_whale_transactions_amount_usd ON whale_transactions(amount_usd DESC);

-- ══════════════════════════════════════════════════════════
-- SENTIMENT DATA (from Twitter/X analysis)
-- ══════════════════════════════════════════════════════════
CREATE TABLE sentiment_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour < 24),
    mentions_count INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    sentiment_score DECIMAL(5, 2), -- -100 to +100
    engagement_score INTEGER DEFAULT 0,
    top_keywords JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date, hour)
);

CREATE INDEX idx_sentiment_symbol_date ON sentiment_data(symbol, date DESC);
CREATE INDEX idx_sentiment_score ON sentiment_data(sentiment_score);

-- ══════════════════════════════════════════════════════════
-- FUNDING RATES (from exchanges)
-- ══════════════════════════════════════════════════════════
CREATE TABLE funding_rates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    exchange VARCHAR(50) NOT NULL, -- 'binance', 'bybit', etc
    symbol VARCHAR(20) NOT NULL,
    funding_rate DECIMAL(10, 6) NOT NULL,
    mark_price DECIMAL(20, 8),
    open_interest DECIMAL(30, 2),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(exchange, symbol, timestamp)
);

CREATE INDEX idx_funding_rates_symbol ON funding_rates(symbol, timestamp DESC);
CREATE INDEX idx_funding_rates_exchange ON funding_rates(exchange);

-- ══════════════════════════════════════════════════════════
-- ACTIVITY LOGS
-- ══════════════════════════════════════════════════════════
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    email VARCHAR(255),
    action_type VARCHAR(100) NOT NULL, -- 'login', 'register', 'chat', 'mission', etc
    ip_address INET,
    user_agent TEXT,
    extra_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_created_at ON activity_logs(created_at DESC);
CREATE INDEX idx_activity_logs_action_type ON activity_logs(action_type);

-- ══════════════════════════════════════════════════════════
-- AI CHAT HISTORY
-- ══════════════════════════════════════════════════════════
CREATE TABLE chat_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant'
    message TEXT NOT NULL,
    context JSONB,
    token_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_history_user_id ON chat_history(user_id);
CREATE INDEX idx_chat_history_session_id ON chat_history(session_id, created_at);

-- ══════════════════════════════════════════════════════════
-- FUNCTIONS & TRIGGERS
-- ══════════════════════════════════════════════════════════

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_portfolios_updated_at BEFORE UPDATE ON portfolios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_holdings_updated_at BEFORE UPDATE ON holdings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ══════════════════════════════════════════════════════════
-- INITIAL DATA
-- ══════════════════════════════════════════════════════════

-- Create demo user (password: demo1234)
INSERT INTO users (email, password_hash, auth_method, display_name)
VALUES (
    'demo@pulse.app',
    '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi',
    'email',
    'Demo User'
) ON CONFLICT (email) DO NOTHING;
