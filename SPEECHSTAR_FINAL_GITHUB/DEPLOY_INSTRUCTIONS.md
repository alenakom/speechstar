# 🚀 ИНСТРУКЦИЯ ПО ДЕПЛОЮ НА RENDER.COM

## 📋 Быстрый старт

### 1. Подготовка GitHub
- Загрузить все файлы из этого архива в GitHub репозиторий
- Убедиться что файл `app.py` присутствует в корне

### 2. Подключение к Render
1. Зайти на https://render.com
2. Нажать **"New +" → "Web Service"**
3. Подключить GitHub репозиторий `speechstar`

### 3. Настройка деплоя
**Build & Deploy Settings:**
- **Runtime:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python app.py`

### 4. Environment Variables
```
BOT_TOKEN = ваш_telegram_bot_token
SESSION_SECRET = любой_случайный_ключ
PORT = 10000
YOOKASSA_SECRET_KEY = ваш_yookassa_ключ (опционально)
YOOKASSA_SHOP_ID = ваш_shop_id (опционально)
```

### 5. Деплой
- Нажать **"Create Web Service"**
- Дождаться успешного деплоя (2-3 минуты)
- Проверить URL: `https://your-service-name.onrender.com`

## ✅ Проверка работы

### Тест 1: Главная страница
```bash
curl https://your-app.onrender.com/
```
**Ожидаемый результат:** JSON с информацией о сервисе

### Тест 2: Health check
```bash
curl https://your-app.onrender.com/health
```
**Ожидаемый результат:** `{"status": "healthy"}`

### Тест 3: Bot info
```bash
curl https://your-app.onrender.com/bot
```
**Ожидаемый результат:** JSON с информацией о боте

## 🔧 Возможные проблемы

### Проблема: 502 Bad Gateway
**Решение:** Проверить что файл `app.py` есть в GitHub и Start Command правильный

### Проблема: Build Failed
**Решение:** Проверить что `requirements.txt` корректный

### Проблема: Environment Variables
**Решение:** Убедиться что BOT_TOKEN установлен

## 📊 Мониторинг

После деплоя доступны:
- **Logs:** в Render Dashboard
- **Metrics:** в разделе Metrics
- **Health Check:** автоматический на `/health`

## 🔄 Автообновления

Render автоматически деплоит изменения из GitHub при:
- Push в main ветку
- Merge pull request
- Ручной деплой через dashboard

## 💡 Оптимизация

### Для production:
1. Использовать платный план Render
2. Настроить custom domain
3. Включить CDN
4. Настроить monitoring alerts

### Free план ограничения:
- Sleep после 15 минут неактивности
- 750 часов в месяц
- Холодный старт при пробуждении

---

**Время деплоя:** 2-3 минуты  
**Статус:** Готово к production использованию