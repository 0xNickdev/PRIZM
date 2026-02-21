# 🔐 Система авторизации PULSΞ

## ✅ Что реализовано

### Frontend (Landing Page - index.html)

**Модальные окна:**
- ✅ **Login Modal** - красивое модальное окно для входа
- ✅ **Register Modal** - модальное окно регистрации с подтверждением пароля
- ✅ Плавная анимация открытия/закрытия
- ✅ Закрытие по Escape или клику на фон
- ✅ Переключение между Login и Register

**Валидация на фронтенде:**
- ✅ Email формат проверка (regex)
- ✅ Минимальная длина пароля (4 символа)
- ✅ Совпадение паролей при регистрации
- ✅ Санитизация input (удаление `<>`)
- ✅ Показ ошибок пользователю

**Дизайн:**
- ✅ Модальное окно в стиле PULSΞ
- ✅ Темный фон с blur эффектом
- ✅ Зеленая кнопка подтверждения
- ✅ Мобильная адаптация
- ✅ Кнопки Login и Register на главной

### Frontend (Dashboard - dashboard.html)

- ✅ **Проверка авторизации** - редирект на главную если нет токена
- ✅ **Отображение email** - показ email залогиненного пользователя
- ✅ **Кнопка Logout** - красная кнопка выхода в topbar
- ✅ **Автоматический logout** - при истечении токена (401)

### Backend (Python FastAPI)

**Security Features:**
- ✅ **SQL Injection Prevention** - SQLAlchemy ORM с параметризованными запросами
- ✅ **Bcrypt Password Hashing** - криптографически стойкое хеширование
- ✅ **JWT Tokens** - stateless authentication (7 дней)
- ✅ **Input Validation** - Pydantic validators с regex
- ✅ **Input Sanitization** - проверка длины и опасных символов
- ✅ **Activity Logging** - audit trail всех действий
- ✅ **User Enumeration Prevention** - generic error messages
- ✅ **Timing-Safe Password Comparison** - защита от timing attacks

**API Endpoints:**
- `POST /api/auth/register` - регистрация нового пользователя
- `POST /api/auth/login` - вход существующего пользователя
- Все endpoints защищены от SQL инъекций

### Database (PostgreSQL)

- ✅ Таблица `users` с полями: email, password_hash, auth_method
- ✅ Таблица `activity_logs` для аудита
- ✅ UUID primary keys (безопаснее integer)
- ✅ Indexes для быстрого поиска

## 🚀 Как использовать

### Для пользователей:

1. **Открыть главную страницу** → `http://localhost:8000/`
2. **Нажать "Register"** → откроется модальное окно
3. **Ввести email и пароль** (минимум 4 символа)
4. **Нажать "Create Account"** → автоматический вход и редирект на dashboard
5. **На dashboard** → видно email и кнопку Logout

### Для разработчиков:

**Запуск проекта:**
```bash
# 1. Запустить Docker контейнеры (PostgreSQL)
docker-compose up -d

# 2. Проверить что база данных работает
# PostgreSQL будет на localhost:5432

# 3. Открыть в браузере
http://localhost:8000/
```

**Тестирование:**
```bash
# Регистрация через API
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test1234"}'

# Login через API  
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test1234"}'
```

## 📝 Технические детали

### Формат токена (localStorage):
```javascript
localStorage.getItem('pulse_token')  // JWT token
localStorage.getItem('pulse_email')  // user@example.com
```

### API Client (api.js):
- Автоматически добавляет `Authorization: Bearer <token>` к запросам
- Автоматически логаутит при 401 ошибке
- Редиректит на главную если токен истек

### Password Requirements:
- Минимум: 4 символа
- Максимум: 128 символов
- Нельзя: `<`, `>`, `"`, `'` (защита от XSS)

### Email Requirements:
- Валидный email формат (regex)
- Максимум 255 символов
- Автоматическая нормализация (lowercase, trim)

## 🔒 Безопасность

### Защита от атак:

**SQL Injection:**
```python
# ❌ УЯЗВИМО:
query = f"SELECT * FROM users WHERE email = '{email}'"

# ✅ БЕЗОПАСНО (используется):
result = await db.execute(select(User).where(User.email == email))
```

**XSS (Cross-Site Scripting):**
```javascript
// Санитизация input
function sanitizeInput(input) {
  return input.trim().replace(/[<>]/g, '');
}
```

**Password Hashing:**
```python
# Bcrypt с автоматической солью
password_hash = get_password_hash(password)
verify_password(plain, hashed)  # timing-safe
```

**JWT Tokens:**
- HS256 алгоритм
- 7 дней expiration
- Хранится в localStorage
- Автоматическая проверка на backend

## 📊 User Flow

```
Landing Page (/)
    ↓
[Register Button] → Modal with Form
    ↓
Validation (frontend)
    ↓
POST /api/auth/register
    ↓
Validation (backend + Pydantic)
    ↓
Bcrypt hashing
    ↓
Save to PostgreSQL (via ORM)
    ↓
Generate JWT token
    ↓
Return token to frontend
    ↓
Save token to localStorage
    ↓
Redirect to /dashboard
    ↓
Dashboard checks token
    ↓
Show user interface
```

## 🐛 Troubleshooting

**Проблема:** Не могу зарегистрироваться
- Проверьте формат email
- Пароль минимум 4 символа
- Проверьте консоль браузера (F12)

**Проблема:** Токен истекает слишком быстро
- Измените `ACCESS_TOKEN_EXPIRE_DAYS` в `auth.py`
- По умолчанию: 7 дней

**Проблема:** 401 Unauthorized
- Токен истек → нужен re-login
- Проверьте `JWT_SECRET` в env переменных

**Проблема:** SQL ошибки
- Проверьте что PostgreSQL запущен: `docker ps`
- Проверьте DATABASE_URL в config

## 🎨 Стилизация модальных окон

**CSS классы:**
- `.modal` - контейнер модального окна
- `.modal-content` - само окно
- `.modal-header` - заголовок с кнопкой закрытия
- `.modal-body` - форма с input полями
- `.inp-group` - группа input + label
- `.btn-submit` - зеленая кнопка подтверждения

**Анимация:**
```css
@keyframes slideUp {
  from { transform: translateY(30px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
```

## 🔧 Настройка Production

1. **Измените JWT_SECRET** в `.env`:
```bash
JWT_SECRET=your_very_long_random_secret_key_min_32_chars
```

2. **Добавьте HTTPS** (обязательно!)
3. **Настройте CORS whitelist**
4. **Добавьте rate limiting** (рекомендуется)
5. **Включите мониторинг логов**

## 📚 Дополнительно

- **SECURITY.md** - детальное описание всех мер безопасности
- **README.md** - общая документация проекта
- **auth.py** - backend authentication логика
- **auth_routes.py** - API endpoints для auth

---

**Готово!** Теперь у вас полноценная система авторизации с защитой от SQL инъекций и красивым UI! 🎉
