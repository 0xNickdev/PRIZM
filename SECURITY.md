# PULSΞ Security Features

## Authentication & Authorization

### ✅ SQL Injection Prevention
- **SQLAlchemy ORM** - все запросы к базе данных параметризованы через ORM
- **Pydantic validators** - валидация и санитизация всех входных данных
- **Нет прямых SQL запросов** - все операции через типобезопасный ORM

```python
# ❌ УЯЗВИМО к SQL инъекции:
query = f"SELECT * FROM users WHERE email = '{email}'"

# ✅ БЕЗОПАСНО (используется в проекте):
result = await db.execute(select(User).where(User.email == email))
```

### ✅ Password Security
- **Bcrypt hashing** - криптографически стойкое хеширование паролей (passlib)
- **Salt per password** - уникальная соль для каждого пароля автоматически
- **Timing-safe comparison** - защита от timing attacks при проверке пароля
- **Минимальная длина** - минимум 4 символа (настраивается)
- **Максимальная длина** - максимум 128 символов (защита от DoS)

```python
# Хеширование при регистрации
password_hash = get_password_hash(request.password)  # bcrypt с солью

# Безопасная проверка при логине
verify_password(request.password, user.password_hash)  # timing-safe
```

### ✅ Input Validation & Sanitization

**Backend (Pydantic):**
```python
class RegisterRequest(BaseModel):
    email: EmailStr  # автоматическая валидация email
    password: str
    
    @field_validator('email')
    def validate_email(cls, v):
        # Regex валидация email
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        # Ограничение длины
        if len(v) > 255:
            raise ValueError('Email too long')
        # Нормализация
        return v.lower().strip()
    
    @field_validator('password')
    def validate_password(cls, v):
        # Минимальная длина
        if len(v) < 4:
            raise ValueError('Password must be at least 4 characters')
        # Максимальная длина (защита от DoS)
        if len(v) > 128:
            raise ValueError('Password too long')
        # Блокировка опасных символов
        if '<' in v or '>' in v or '"' in v or "'" in v:
            raise ValueError('Password contains invalid characters')
        return v
```

**Frontend (JavaScript):**
```javascript
function sanitizeInput(input) {
    return input.trim().replace(/[<>]/g, '');
}

function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}
```

### ✅ JWT Token Security
- **HS256 algorithm** - HMAC SHA-256 подпись
- **Secret key** - 32+ символов (настраивается через env)
- **Expiration** - 7 дней по умолчанию
- **Stored in localStorage** - автоматическое добавление к запросам

### ✅ XSS Prevention
- **Input sanitization** - удаление опасных символов `<>` на фронтенде
- **Content-Type headers** - правильные заголовки для JSON
- **No eval()** - не используется eval или эквиваленты
- **HTML escaping** - все пользовательские данные экранируются

### ✅ CSRF Protection
- **JWT tokens** - stateless authentication
- **SameSite cookies** - если используются cookies
- **Origin validation** - проверка источника запросов

### ✅ Additional Security Measures

**Backend:**
- Activity logging (audit trail)
- User enumeration prevention (generic error messages)
- Account locking on inactive status
- Rate limiting (рекомендуется добавить middleware)
- HTTPS enforcement (в production)

**Frontend:**
- Password visibility toggle
- Client-side validation before API calls
- Error message sanitization
- Secure token storage
- Auto-logout on token expiration

## Recommended Additions

### Rate Limiting
```python
# Рекомендуется добавить slowapi или fastapi-limiter
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")  # 5 попыток в минуту
async def login(...):
    ...
```

### CORS Configuration
```python
# main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # конкретные домены
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Environment Variables
```bash
# .env (никогда не коммитить в git!)
JWT_SECRET=your_very_long_random_secret_key_min_32_chars
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/pulse
```

## Security Checklist

- [x] SQL injection prevention (SQLAlchemy ORM)
- [x] Password hashing (bcrypt)
- [x] Input validation (Pydantic)
- [x] Input sanitization (frontend & backend)
- [x] XSS prevention
- [x] JWT authentication
- [x] Activity logging
- [x] User enumeration prevention
- [ ] Rate limiting (рекомендуется)
- [ ] HTTPS enforcement (production)
- [ ] Security headers (production)
- [ ] CORS whitelist (production)

## Testing

```bash
# Тестирование SQL injection
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com OR 1=1--","password":"test"}'
# ✅ Должен вернуть ошибку валидации email

# Тестирование XSS
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"<script>alert(1)</script>@test.com","password":"test"}'
# ✅ Должен вернуть ошибку валидации email
```

## Production Deployment

1. **Используйте HTTPS** - обязательно для production
2. **Настройте JWT_SECRET** - минимум 32 случайных символа
3. **Добавьте rate limiting** - защита от brute force
4. **Настройте CORS** - только доверенные домены
5. **Регулярно обновляйте зависимости** - `pip list --outdated`
6. **Мониторинг логов** - отслеживайте подозрительную активность

---

**Контакт:** security@pulse.app (если используется в production)
