#!/usr/bin/env python3
"""
Интеграция с ЮKassa для обработки платежей
"""
import hashlib
import uuid
import requests
from datetime import datetime

class YookassaPayment:
    def __init__(self, shop_id, secret_key):
        self.shop_id = shop_id
        self.secret_key = secret_key
        self.api_url = "https://api.yookassa.ru/v3"
    
    def create_payment(self, amount, description, user_id, return_url=None):
        """Создать платеж"""
        import base64
        auth_string = f"{self.shop_id}:{self.secret_key}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json",
            "Idempotence-Key": str(uuid.uuid4())
        }
        
        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "description": description,
            "metadata": {
                "user_id": str(user_id)
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url or "https://example.com/return"
            },
            "capture": True
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/payments",
                json=payment_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Ошибка создания платежа: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Ошибка запроса к ЮKassa: {e}")
            return None
    
    def check_payment_status(self, payment_id):
        """Проверить статус платежа"""
        import base64
        auth_string = f"{self.shop_id}:{self.secret_key}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode('ascii')
        
        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(
                f"{self.api_url}/payments/{payment_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            print(f"Ошибка проверки платежа: {e}")
            return None

# Пример использования в боте:
"""
# В new_bot.py добавить:

# Настройки ЮKassa (из переменных окружения)
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY")

# Создание объекта для работы с платежами
if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    payment_service = YookassaPayment(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
else:
    payment_service = None

@dp.callback_query(F.data == "pay_monthly")
async def pay_monthly(callback: types.CallbackQuery):
    if not payment_service:
        await callback.answer("Платежи временно недоступны")
        return
    
    user_id = callback.from_user.id
    payment = payment_service.create_payment(
        amount=150.0,
        description="Подписка на месяц - речевой бот",
        user_id=user_id
    )
    
    if payment and payment.get("confirmation"):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="💳 Оплатить 150₽", 
                url=payment["confirmation"]["confirmation_url"]
            )],
            [InlineKeyboardButton(text="🏠 Вернуться", callback_data="menu")]
        ])
        
        text = "Нажмите кнопку ниже для оплаты подписки на месяц (150₽)"
        await callback.message.edit_text(text, reply_markup=keyboard)
        
        # Сохраняем ID платежа для проверки
        users_data[user_id]["pending_payment"] = payment["id"]
    else:
        await callback.answer("Ошибка создания платежа")

@dp.callback_query(F.data == "pay_lifetime")
async def pay_lifetime(callback: types.CallbackQuery):
    # Аналогично для lifetime платежа (500₽)
    pass

# Webhook для получения уведомлений о платежах
# Нужно настроить в личном кабинете ЮKassa
"""