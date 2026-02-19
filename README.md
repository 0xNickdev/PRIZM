# ══════════════════════════════════════════════════════════
# PULSΞ - Crypto Market Intelligence Platform
# ══════════════════════════════════════════════════════════

![PULSE Logo](https://via.placeholder.com/800x200/000000/00ffa3?text=PULS%CE%9E)

## 🚀 Features

- **Real-time Market Data** - Live crypto prices from CoinGecko
- **AI Agent** - Claude AI powered market analysis 
- **Whale Tracking** - Monitor large crypto transactions
- **Sentiment Analysis** - Twitter/X social sentiment tracking
- **Funding Rates** - Derivatives data from Binance/Bybit
- **Portfolio Management** - Track your crypto holdings
- **Price Alerts** - Get notified on price targets

## 🛠️ Tech Stack

**Frontend:**
- HTML5, CSS3 (Minimal framework)
- Vanilla JavaScript

**Backend:**
- Python 3.11 + FastAPI (single backend)
- PostgreSQL (database)
- Redis (caching)
- SQLAlchemy 2.0 (async ORM)
- JWT authentication (python-jose)

**Python Services:**
- Whale Alert API integration
- Twitter API v2 (sentiment analysis)
- Binance/Bybit APIs (derivatives)
- TextBlob (sentiment analysis)
- Anthropic Claude (AI agent)

**DevOps:**
- Docker + Docker Compose
- Multi-container architecture

## 📋 Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development without Docker)

## 🔑 Required API Keys

You'll need these API keys (add to `.env` file):

### Essential (Core Features):
- **CoinGecko API** (free tier works) - [Get Key](https://www.coingecko.com/en/api/pricing)
- **Anthropic API** (Claude AI) - [Get Key](https://console.anthropic.com/)

### Optional (Advanced Features):
- **Whale Alert API** - [Get Key](https://whale-alert.io/)
- **Twitter/X API v2** - [Apply Here](https://developer.twitter.com/en/portal/dashboard)
- **Binance API** - [Create Key](https://www.binance.com/en/my/settings/api-management)

## 🚀 Quick Start

### 1. Clone & Configure

```bash
cd pulse
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start with Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services will be available at:
- **Frontend**: Open `index.html` in browser
- **Backend API**: http://localhost:3001
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **pgAdmin** (optional): http://localhost:5050

### 3. Or Run Locally (Development)

**Backend:**
```bash
cd python
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 3001 --reload
```

**PostgreSQL:**
```bash
# Install PostgreSQL locally or use Docker:
docker run -d \
  --name pulse_postgres \
  -e POSTGRES_DB=pulse_db \
  -e POSTGRES_USER=pulse_user \
  -e POSTGRES_PASSWORD=pulse_dev_password \
  -p 5432:5432 \
  postgres:16-alpine
```

## 📁 Project Structure

```
pulse/
├── index.html              # Landing page
├── dashboard.html          # Main dashboard
├── agents.html             # Multi-agent lab
├── style.css               # Global styles
├── api.js                  # API client
├── utils.js                # Utilities
├── config.js               # Configuration
├── docker-compose.yml      # Multi-container setup
├── .env                    # Environment variables
├── database/
│   └── init.sql           # PostgreSQL schema
└── python/                # Python Backend
    ├── main.py            # FastAPI main app
    ├── Dockerfile         # Python container
    ├── requirements.txt   # Dependencies
    ├── database.py        # DB connection
    ├── models.py          # SQLAlchemy models
    ├── auth.py            # JWT authentication
    ├── routes/
    │   ├── auth_routes.py      # Auth endpoints
    │   ├── market_routes.py    # Market data
    │   └── agent_routes.py     # AI agent
    └── services/
        ├── whale_tracker.py    # Whale Alert
        ├── sentiment.py        # Twitter sentiment
        └── derivatives.py      # Exchange data
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Core
PORT=3001
JWT_SECRET=your_secret_here
SECRET_KEY=your_jwt_secret_key_here

# Database
POSTGRES_HOST=localhost
POSTGRES_DB=pulse_db
POSTGRES_USER=pulse_user
POSTGRES_PASSWORD=your_password

# APIs
ANTHROPIC_API_KEY=sk-ant-...
COINGECKO_API_KEY=CG-...
WHALE_ALERT_API_KEY=...
TWITTER_BEARER_TOKEN=...
BINANCE_API_KEY=...
```

## 📡 API Endpoints

### Backend (Python FastAPI)

**Auth:**
- `POST /api/auth/register` - Register user
- `POST /api/auth/login` - Login
- `POST /api/auth/twitter` - Twitter OAuth
- `GET /api/auth/me` - Get current user

**Market Data:**
- `GET /api/market` - All coins
- `GET /api/market/:id` - Single coin
- `GET /api/fng` - Fear & Greed Index

**AI Agent:**
- `POST /api/agent/chat` - Chat with AI
- `POST /api/agent/mission` - Multi-agent mission

**User Data:**
- `GET /api/logs` - Activity logs

### Python Service

**Whale Tracking:**
- `GET /api/whales/:symbol` - Recent whale transactions
- `POST /api/whales/fetch` - Fetch latest data

**Sentiment:**
- `GET /api/sentiment/:symbol` - Sentiment data
- `POST /api/sentiment/analyze` - Analyze tweets

**Derivatives:**
- `GET /api/derivatives/:symbol` - Funding rates & OI
- `POST /api/derivatives/fetch` - Fetch latest data

**Analysis:**
- `GET /api/analysis/:symbol` - Comprehensive analysis

## 🐳 Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Restart a service
docker-compose restart backend

# Rebuild after code changes
docker-compose up -d --build

# Stop everything
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v

# Access PostgreSQL
docker exec -it pulse_postgres psql -U pulse_user -d pulse_db

# Access Redis
docker exec -it pulse_redis redis-cli
```

## 🔒 Security Notes

- Change all default passwords in production
- Use strong JWT secrets (min 32 chars)
- Enable HTTPS in production
- Rate limiting is enabled (100 req/15min)
- API keys should never be committed to git

## 🐛 Troubleshooting

**Port already in use:**
```bash
# Change ports in docker-compose.yml or .env
```

**Database connection failed:**
```bash
# Check if PostgreSQL is running
docker-compose ps
docker-compose logs postgres
```

**Python service won't start:**
```bash
# Check logs
docker-compose logs backend

# Rebuild
docker-compose up -d --build backend
```

## 📈 Performance Tips

1. **Redis caching** - Market data cached for 30s
2. **Database indexes** - Optimized queries
3. **Connection pooling** - Reused connections
4. **Rate limiting** - Prevents API abuse
5. **Lightweight UI** - 3D background optional

## 🤝 Contributing

Pull requests welcome! Please:
1. Fork the repo
2. Create a feature branch
3. Commit your changes
4. Push and create a PR

## 📄 License

MIT License - see LICENSE file

## 🙏 Credits

- **CoinGecko** - Market data
- **Anthropic** - Claude AI
- **Whale Alert** - Transaction tracking
- **Twitter** - Social sentiment

---

**Made with ⚡ by the PULSΞ team**
