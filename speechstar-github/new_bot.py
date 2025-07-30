#!/usr/bin/env python3
"""
Обновленный Telegram бот с новыми требованиями:
- Новые возрастные группы (9-14, 15-19 месяцев)
- Пробный период 7 дней
- Подписки (150₽/месяц, 500₽ навсегда)
- Промокоды
- Новые комплексные задания
"""
import asyncio
import logging
import json
import os
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Настройки ЮKassa для платежей
YOOKASSA_SHOP_ID = os.environ.get("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.environ.get("YOOKASSA_SECRET_KEY")

# Импорт системы платежей
try:
    from payment_integration import YookassaPayment
    if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
        payment_service = YookassaPayment(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
        logger.info("💳 ЮKassa интегрирована для приема платежей")
        PAYMENT_AVAILABLE = True
    else:
        payment_service = None
        logger.warning("⚠️ ЮKassa ключи не найдены, платежи недоступны")
        PAYMENT_AVAILABLE = False
except ImportError as e:
    payment_service = None
    PAYMENT_AVAILABLE = False
    logger.warning(f"❌ Модуль платежей недоступен: {e}")

# Создаем бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Новые возрастные группы
AGES = {
    "9-14": "9-14 месяцев",
    "15-19": "15-19 месяцев"
}

# Промокоды для бесплатного доступа
PROMOCODES = [
    "MAMA2025", "BABY001", "SPEECH10", "RAZVIT20", "FREE100", "RODIT50", 
    "DETKI99", "MAMA123", "BABY456", "BEST001", "SUPER10", "GIFT777",
    "PROMO88", "MAMA321", "KIDS100", "LOVE555", "BABY777", "HAPPY99",
    "SMART10", "CLEVER5", "GROW123", "LEARN50", "PLAY789", "JOY2025",
    "SPEECH1", "WORDS99", "TALK123", "SPEAK50", "VOICE10", "SOUND77"
] + [f"CODE{i:03d}" for i in range(1, 71)]  # CODE001-CODE070 - итого 100 промокодов

# Хранение данных пользователей
users_data = {}

def save_user_data():
    """Сохранить данные пользователей в файл"""
    try:
        import json
        with open("users_data.json", "w", encoding="utf-8") as f:
            # Конвертируем datetime в строки для JSON
            data_to_save = {}
            for user_id, data in users_data.items():
                data_copy = data.copy()
                if data_copy.get("registered"):
                    data_copy["registered"] = data_copy["registered"].isoformat()
                if data_copy.get("trial_started"):
                    data_copy["trial_started"] = data_copy["trial_started"].isoformat()
                if data_copy.get("last_task_date"):
                    data_copy["last_task_date"] = data_copy["last_task_date"].isoformat()
                data_to_save[str(user_id)] = data_copy
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")

def load_user_data():
    """Загрузить данные пользователей из файла"""
    try:
        import json
        with open("users_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            for user_id, user_data in data.items():
                # Конвертируем строки обратно в datetime
                if user_data.get("registered"):
                    user_data["registered"] = datetime.fromisoformat(user_data["registered"])
                if user_data.get("trial_started"):
                    user_data["trial_started"] = datetime.fromisoformat(user_data["trial_started"])
                if user_data.get("last_task_date"):
                    user_data["last_task_date"] = datetime.fromisoformat(user_data["last_task_date"]).date()
                users_data[int(user_id)] = user_data
            logger.info(f"📁 Загружено данных пользователей: {len(users_data)}")
    except FileNotFoundError:
        logger.info("📁 Файл данных пользователей не найден, создается новый")
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")

# Загружаем данные при старте
load_user_data()

def load_tasks_from_cms():
    """Загрузить задания из CMS"""
    try:
        import json
        with open("data/tasks.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            tasks = {}
            for task in data.get("tasks", []):
                age_group = task["age_group"]
                if age_group not in tasks:
                    tasks[age_group] = []
                tasks[age_group].append({
                    "day": task["day"],
                    "title": task["title"],
                    "text": task["description"],
                    "image": None
                })
            logger.info(f"📋 Загружено заданий из CMS: {sum(len(v) for v in tasks.values())}")
            return tasks
    except Exception as e:
        logger.error(f"Ошибка загрузки заданий из CMS: {e}")
        return {}

# Комплексные задания по возрастным группам - загружаем из CMS
TASKS_FROM_CMS = load_tasks_from_cms()

# Встроенные задания как fallback
TASKS_FALLBACK = {
    "9-14": [
        {
            "day": 1,
            "title": "Комплексное развитие 9-14 месяцев - День 1",
            "text": """🧠 **Внимание и восприятие (слух):**
«Что за звук?» — берём металлическую крышку, пластиковую и деревянную ложку. Постучите по разным поверхностям: стол, пол, коробка. Комментируйте:
«Звенит!» — (ложка по крышке),
«Глухо!» — (ложка по дивану),
«Стук-стук!» — (ложка по полу).
➡️ Побуждаем малыша прислушиваться и различать звуки.

🤸 **Физическая активность:**
«Собери зверей» — разложите мягкие игрушки змейкой. Говорите: «Вот лисичка! А вот зайка!» — малыш ползёт или идёт по маршруту, собирая их в коробку.
➡️ Укрепляем моторику, внимание и понимание слов.

🗣️ **Предречевое развитие:**
«Мяч и звук» — отбивайте мячик от пола или стола и ритмично произносите:
«Бух» → отскок,
«Бух» → отскок,
➡️ Побуждаем малыша повторять, смотрим на реакцию и поощряем попытки.

😊 **Эмоциональное развитие:**
«Грусть — радость» — с мягкой игрушкой проигрываем мини-сценки:
«Ой-ой, зайка упал…» (грустный голос)
→ «Ура! Зайка встал!» (весёлый голос, хлопаем в ладоши)
➡️ Помогаем ребёнку различать эмоции, сопереживать, подражать.

✋ **Тактильное/предметное развитие:**
«Мягко или жёстко» — в одной миске положите вату, тряпочку, помпон. В другой — ложку, пуговицы, крышку. Предложите малышу по очереди трогать и называть ощущения:
«Мягко!» — (трогает вату),
«Твёрдо!» — (трогает ложку).
➡️ Развиваем тактильную чувствительность и словарь.""",
            "image": None
        }
    ],
    "15-19": [
        {
            "day": 1,
            "title": "Комплексное развитие 15-19 месяцев - День 1", 
            "text": """🧠 **Внимание и восприятие:**
Игра «Покажи и назови» — разложите перед ребёнком 4–5 знакомых игрушек. Спрашивайте: «Где машинка?», «Покажи мишку», «А где лошадка?» — поощряйте, если малыш указывает правильно.

🤸 **Физическая активность:**
Игра с мячом — катайте мячик друг другу. При этом сопровождайте действия словами: «Кати!», «Поймал!», «Бросай!» — это помогает закреплять глаголы и имя предмета.

🗣️ **Предречевое развитие:**
Читаем короткие звукоподражательные стишки, делая акцент на ударных звуках, ритме и повторениях:

Зайка взял свой барабан —
И ударил: трам-там-там!

Ку-ку, ку-ку, кукушечка,
Лети скорей в лесок.
Ку-ку, ку-ку, кукушечка,
Подай свой голосок!

Тук-тук-тук-тук —
Это что за стук?
Деревянный это звук:
Тук-тук-тук-тук.

😊 **Эмоциональное развитие:**
«Зеркальные эмоции» — сядьте с малышом перед зеркалом и по очереди изображайте разные эмоции: радость, грусть, удивление, страх, веселье. Побуждайте ребёнка повторять мимику: «А теперь как будто ты испугался!»

✋ **Тактильное/предметное развитие:**
«Корзина текстур» — наполните коробку или корзину разными материалами (мешочек с фасолью, кусочек губки, фольга, мех, бархат). Пусть малыш ощупывает предметы, а вы называете ощущения: «Мягкий», «Шуршит», «Гладкий», «Колючий».""",
            "image": None
        }
    ]
}

# Используем задания из CMS, если есть, иначе встроенные
TASKS = TASKS_FROM_CMS if TASKS_FROM_CMS else TASKS_FALLBACK

# Создаем планировщик задач
scheduler = AsyncIOScheduler()

async def send_daily_tasks():
    """Отправка ежедневных заданий в 9:00 по Москве"""
    logger.info("🕘 Запуск автоматической отправки заданий...")
    
    # Перезагружаем задания из CMS для получения свежих данных
    global TASKS
    fresh_tasks = load_tasks_from_cms()
    if fresh_tasks:
        TASKS = fresh_tasks
        logger.info(f"📋 Обновлены задания из CMS: {sum(len(v) for v in TASKS.values())}")
    
    sent_count = 0
    try:
        for user_id, user_data in users_data.items():
            # Проверяем, есть ли подписка
            if not has_subscription(user_data):
                continue
                
            age_group = user_data.get("age_group")
            if not age_group or age_group not in TASKS:
                continue
                
            # Определяем день задания
            trial_start = user_data.get("trial_started")
            if trial_start:
                days_since_start = (datetime.now() - trial_start).days
                day_number = (days_since_start % len(TASKS[age_group])) + 1
            else:
                day_number = 1
            
            # Выбираем задание по дню
            task_index = day_number - 1
            if task_index >= len(TASKS[age_group]):
                task_index = 0
            task = TASKS[age_group][task_index]
            
            # Отправляем задание
            text = f"🌅 Доброе утро! Вот твое ежедневное задание:\n\n{task['text']}"
            
            try:
                await bot.send_message(user_id, text)
                sent_count += 1
                
                # Обновляем дату последнего задания
                user_data["last_task_date"] = datetime.now().date()
                save_user_data()
                
            except Exception as e:
                logger.error(f"Ошибка отправки задания пользователю {user_id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка при автоматической отправке заданий: {e}")
    
    logger.info(f"📨 Отправлено заданий: {sent_count}")

def start_scheduler():
    """Запуск планировщика заданий"""
    # Ежедневная отправка в 9:00 по московскому времени (UTC+3)
    scheduler.add_job(
        send_daily_tasks,
        CronTrigger(hour=6, minute=0, timezone="UTC"),  # 9:00 MSK = 6:00 UTC
        id='daily_tasks',
        replace_existing=True
    )
    scheduler.start()
    logger.info("⏰ Планировщик заданий запущен (отправка в 9:00 МСК)")

def get_user_data(user_id):
    """Получить данные пользователя"""
    if user_id not in users_data:
        users_data[user_id] = {
            "registered": datetime.now(),
            "age_group": None,
            "trial_started": None,
            "trial_used": False,
            "subscription": None,  # "monthly", "lifetime", "promocode"
            "last_task_date": None,
            "current_day": 0
        }
        # Сохраняем данные после создания нового пользователя
        save_user_data()
    return users_data[user_id]

def is_trial_active(user_data):
    """Проверить активен ли пробный период"""
    if not user_data["trial_started"] or user_data["subscription"]:
        return False
    trial_end = user_data["trial_started"] + timedelta(days=7)
    return datetime.now() < trial_end

def get_age_keyboard():
    """Клавиатура выбора возраста"""
    buttons = []
    for code, name in AGES.items():
        buttons.append([InlineKeyboardButton(text=f"👶 {name}", callback_data=f"age_{code}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Приветственное сообщение до /start
WELCOME_MESSAGE = """Привет! 👋

Я не логопед. Я просто мама, которая устала искать по кусочкам информацию о развитии речи. Хотелось чего-то понятного, ежедневного и рядом — прямо в Telegram. Так родился этот бот.

Нажми «Старт», чтобы начать."""

@dp.message(Command("start"))
async def start_command(message: types.Message):
    """Команда /start"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    # Первый экран без кнопок
    welcome_text = """Больше не нужно ничего искать.
Просто открываешь Telegram — и каждый день получаешь готовое задание.

👶 Формат: 5 мини-упражнений — сенсорика, речь, движение, эмоции и тактильность
🧺 Без развивающих девайсов — всё из подручных средств"""
    
    await message.answer(welcome_text)
    
    # Автоматически отправляем второй экран с информацией о пробном периоде
    await asyncio.sleep(1)
    
    text = """🎉 Первые 7 дней — совершенно бесплатно. Пробуй, играй, смотри, как реагирует малыш.

Дальше будет два варианта оплаты:
• 150 ₽ в месяц
• или 500 ₽ — один раз и навсегда (на выбранный возраст)

Эта оплата помогает мне поддерживать бот и добавлять новые задания 🙌

ℹ️ Обратите внимание: пробный период доступен только для одного возраста.
После его выбора изменить возраст можно будет только с платной подпиской."""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Понимаю 🤝", callback_data="show_age_selection")],
        [InlineKeyboardButton(text="🎟️ Промокод", callback_data="promocode")]
    ])
    
    await message.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data == "show_age_selection")
async def show_age_selection(callback: types.CallbackQuery):
    """Показать выбор возраста"""
    text = """Выбирай возраст, и я пришлю первое занятие 💛"""
    
    keyboard = get_age_keyboard()
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("age_"))
async def select_age(callback: types.CallbackQuery):
    """Выбор возраста и сразу отправка задания"""
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    age_code = callback.data.split("_")[1]
    
    # Устанавливаем возрастную группу
    user_data["age_group"] = age_code
    
    if not user_data["trial_started"]:
        user_data["trial_started"] = datetime.now()
        user_data["trial_used"] = True
    
    # Сохраняем данные
    save_user_data()
    
    logger.info(f"✅ Установлен возраст {age_code} для пользователя {user_id}")
    
    # Сразу отправляем задание
    await send_daily_task(callback.message, user_id)
    await callback.answer()

@dp.callback_query(F.data == "change_age")
async def change_age(callback: types.CallbackQuery):
    """Изменить возраст"""
    text = """Больше не нужно ничего искать.
Просто открываешь Telegram — и каждый день получаешь готовое задание.

👶 Формат: 5 мини-упражнений — сенсорика, речь, движение, эмоции и тактильность
🧺 Без развивающих девайсов — всё из подручных средств

Выбирай возраст, и я пришлю первое занятие 💛"""
    
    keyboard = get_age_keyboard()
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()



@dp.callback_query(F.data == "promocode")
async def enter_promocode(callback: types.CallbackQuery):
    """Ввод промокода"""
    text = "🎟️ Введите промокод:"
    
    await callback.message.answer(text)
    await callback.answer()
    
    # Ждем следующее сообщение как промокод
    users_data[callback.from_user.id]["waiting_promocode"] = True

@dp.message()
async def handle_promocode(message: types.Message):
    """Обработка промокода"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    if user_data.get("waiting_promocode"):
        user_data["waiting_promocode"] = False
        code = message.text.strip().upper()
        
        if code in PROMOCODES:
            user_data["subscription"] = "promocode"
            await message.answer("🎉 Промокод принят! У вас теперь бесплатный доступ навсегда!")
            
            # Отправляем задание
            await send_daily_task(message, user_id)
        else:
            text = "❌ Промокод не найден. Попробуйте еще раз или выберите другой способ оплаты."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Подписка на месяц (150 ₽)", callback_data="pay_monthly")],
                [InlineKeyboardButton(text="💎 Доступ навсегда (500 ₽)", callback_data="pay_lifetime")],
                [InlineKeyboardButton(text="🎟️ Промокод", callback_data="promocode")]
            ])
            await message.answer(text, reply_markup=keyboard)

async def send_daily_task(message, user_id, repeat_task=False):
    """Отправить ежедневное задание"""
    user_data = get_user_data(user_id)
    age_group = user_data.get("age_group")
    
    logger.info(f"🔍 send_daily_task: user={user_id}, age_group={age_group}, TASKS keys={list(TASKS.keys())}")
    
    if not age_group:
        await message.answer("❌ Возрастная группа не выбрана")
        return
        
    if age_group not in TASKS:
        await message.answer(f"❌ Задания для возраста {age_group} не найдены")
        return
    
    # Проверяем доступ
    if not is_trial_active(user_data) and not user_data["subscription"]:
        # Пробный период закончился
        text = """Пробный период закончился. Чтобы продолжить — выберите вариант подписки."""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Подписка на месяц (150 ₽)", callback_data="pay_monthly")],
            [InlineKeyboardButton(text="💎 Доступ навсегда (500 ₽)", callback_data="pay_lifetime")],
            [InlineKeyboardButton(text="🎟️ Промокод", callback_data="promocode")]
        ])
        
        await message.answer(text, reply_markup=keyboard)
        return
    
    # Определяем день задания на основе даты начала пробного периода
    trial_start = user_data.get("trial_started")
    if trial_start:
        days_since_start = (datetime.now() - trial_start).days
        day_number = (days_since_start % len(TASKS[age_group])) + 1
    else:
        day_number = 1
    
    # Выбираем задание по дню
    task_index = day_number - 1
    if task_index >= len(TASKS[age_group]):
        task_index = 0
    task = TASKS[age_group][task_index]
    
    # Если повторный запрос - добавляем примечание о времени
    prefix = ""
    if repeat_task:
        prefix = "🕘 На сегодня у тебя уже есть задание, следующие упражнения упадут в бот завтра в 9 утра по Москве.\n\n"
    
    # Если задание уже содержит полный текст с заголовком, используем как есть
    if task['text'].startswith('📋 Задание'):
        text = f"{prefix}{task['text']}"
    else:
        # Иначе добавляем заголовок
        text = f"""{prefix}📋 Задание на сегодня для возраста {AGES[age_group]}:

{task['text']}

💡 Совет: Повторяйте упражнения несколько раз в день, но не принуждайте. Если малыш не в настроении - попробуйте позже.

✨ Хвалите за любые попытки!

До встречи завтра за новым заданием! 🌙"""

    # После выполнения задания только кнопка "Меню"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Меню", callback_data="main_menu")]
    ])
    
    await message.answer(text, reply_markup=keyboard)
    
    user_data["last_task_date"] = datetime.now().date()
    save_user_data()  # Сохраняем после обновления даты задания

@dp.callback_query(F.data == "get_task")
async def get_task_callback(callback: types.CallbackQuery):
    """Получить задание через callback"""
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    # Если возраст не выбран, предлагаем выбрать
    if not user_data.get("age_group"):
        text = "Сначала нужно выбрать возраст малыша 👶"
        keyboard = get_age_keyboard()
        await callback.message.answer(text, reply_markup=keyboard)
        await callback.answer()
        return
    
    await send_daily_task(callback.message, user_id, repeat_task=True)
    await callback.answer()

@dp.callback_query(F.data == "main_menu")
async def show_main_menu(callback: types.CallbackQuery):
    """Показать главное меню"""
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    # Отладка для понимания проблемы
    age_group = user_data.get('age_group')
    logger.info(f"🔍 main_menu: user={user_id}, age_group={age_group}, user_data={user_data}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Получить задание", callback_data="get_task")],
        [InlineKeyboardButton(text="👶 Изменить возраст", callback_data="menu_change_age")]
    ])
    
    # Проверяем есть ли возрастная группа
    age_display = AGES.get(age_group, 'Не выбран') if age_group else 'Не выбран'
    
    text = f"""🏠 Главное меню

Возраст: {age_display}

Выберите действие:"""
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()



@dp.callback_query(F.data == "menu_change_age")
async def menu_change_age(callback: types.CallbackQuery):
    """Изменить возраст из меню"""
    user_data = get_user_data(callback.from_user.id)
    
    # Если пользователь уже начал пробный период
    if user_data.get("trial_started") and not user_data.get("subscription"):
        text = """🔒 Пробный период уже использован на выбранный ранее возраст.
Чтобы получить доступ к материалам другого возраста, пожалуйста,
оформите подписку:
– Подписка на месяц (150 ₽)
– Доступ навсегда (500 ₽)"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Подписка на месяц (150 ₽)", callback_data="pay_monthly")],
            [InlineKeyboardButton(text="💎 Доступ навсегда (500 ₽)", callback_data="pay_lifetime")]
        ])
        
        await callback.message.answer(text, reply_markup=keyboard)
    else:
        # Если есть подписка или еще не начинал пробный период
        text = """Больше не нужно ничего искать.
Просто открываешь Telegram — и каждый день получаешь готовое задание.

👶 Формат: 5 мини-упражнений — сенсорика, речь, движение, эмоции и тактильность
🧺 Без развивающих девайсов — всё из подручных средств

Выбирай возраст, и я пришлю первое занятие 💛"""
        
        keyboard = get_age_keyboard()
        await callback.message.answer(text, reply_markup=keyboard)
    
    await callback.answer()

# === ОБРАБОТЧИКИ ПЛАТЕЖЕЙ ===

@dp.callback_query(F.data == "pay_monthly")
async def pay_monthly(callback: types.CallbackQuery):
    """Обработка месячной подписки"""
    user_id = callback.from_user.id
    
    if not PAYMENT_AVAILABLE:
        await callback.answer("💳 Платежи временно недоступны. Попробуйте позже или свяжитесь с поддержкой.")
        return
    
    # Создаем платеж через ЮKassa
    payment = payment_service.create_payment(
        amount=150.0,
        description="Подписка на месяц - Речевой бот для детей",
        user_id=user_id,
        return_url="https://t.me/SpeechStarBot"
    )
    
    if payment and payment.get("confirmation"):
        # Сохраняем ID платежа для отслеживания
        user_data = get_user_data(user_id)
        user_data["pending_payment"] = {
            "payment_id": payment["id"],
            "type": "monthly",
            "amount": 150.0
        }
        save_user_data()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="💳 Оплатить 150₽", 
                url=payment["confirmation"]["confirmation_url"]
            )],
            [InlineKeyboardButton(text="❓ Проверить оплату", callback_data="check_payment")],
            [InlineKeyboardButton(text="🔄 Назад", callback_data="main_menu")]
        ])
        
        text = """💳 **Месячная подписка** - 150₽

Нажмите кнопку ниже для оплаты. После успешной оплаты вам откроется доступ к заданиям на месяц.

После оплаты нажмите "Проверить оплату"."""
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
    else:
        await callback.answer("❌ Ошибка создания платежа. Попробуйте позже.")

@dp.callback_query(F.data == "pay_lifetime")
async def pay_lifetime(callback: types.CallbackQuery):
    """Обработка пожизненной подписки"""
    user_id = callback.from_user.id
    
    if not PAYMENT_AVAILABLE:
        await callback.answer("💳 Платежи временно недоступны. Попробуйте позже или свяжитесь с поддержкой.")
        return
    
    # Создаем платеж через ЮKassa
    payment = payment_service.create_payment(
        amount=500.0,
        description="Пожизненный доступ - Речевой бот для детей",
        user_id=user_id,
        return_url="https://t.me/SpeechStarBot"
    )
    
    if payment and payment.get("confirmation"):
        # Сохраняем ID платежа для отслеживания
        user_data = get_user_data(user_id)
        user_data["pending_payment"] = {
            "payment_id": payment["id"],
            "type": "lifetime",
            "amount": 500.0
        }
        save_user_data()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="💎 Оплатить 500₽", 
                url=payment["confirmation"]["confirmation_url"]
            )],
            [InlineKeyboardButton(text="❓ Проверить оплату", callback_data="check_payment")],
            [InlineKeyboardButton(text="🔄 Назад", callback_data="main_menu")]
        ])
        
        text = """💎 **Пожизненный доступ** - 500₽

Нажмите кнопку ниже для оплаты. После успешной оплаты вам откроется постоянный доступ к заданиям для выбранного возраста.

После оплаты нажмите "Проверить оплату"."""
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
    else:
        await callback.answer("❌ Ошибка создания платежа. Попробуйте позже.")

@dp.callback_query(F.data == "check_payment")
async def check_payment(callback: types.CallbackQuery):
    """Проверка статуса платежа"""
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    pending_payment = user_data.get("pending_payment")
    if not pending_payment:
        await callback.answer("❌ Активный платеж не найден.")
        return
    
    if not PAYMENT_AVAILABLE:
        await callback.answer("💳 Проверка платежей временно недоступна.")
        return
    
    # Проверяем статус платежа в ЮKassa
    payment_status = payment_service.check_payment_status(pending_payment["payment_id"])
    
    if payment_status and payment_status.get("status") == "succeeded":
        # Платеж успешен - активируем подписку
        if pending_payment["type"] == "monthly":
            user_data["subscription"] = "monthly"
            user_data["subscription_end"] = (datetime.now() + timedelta(days=30)).isoformat()
            await callback.answer("🎉 Месячная подписка активирована!")
        elif pending_payment["type"] == "lifetime":
            user_data["subscription"] = "lifetime"
            await callback.answer("🎉 Пожизненный доступ активирован!")
        
        # Очищаем данные о платеже
        del user_data["pending_payment"]
        save_user_data()
        
        # Отправляем первое задание
        text = "✅ Оплата прошла успешно! Теперь у вас есть полный доступ к заданиям. Вот ваше первое задание:"
        await callback.message.edit_text(text)
        await send_daily_task(callback.message, user_id)
        
    elif payment_status and payment_status.get("status") == "canceled":
        await callback.answer("❌ Платеж отменен. Попробуйте еще раз.")
    else:
        await callback.answer("⏳ Платеж еще обрабатывается. Проверьте позже.")

async def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден")
        return
        
    logger.info("🚀 Запуск обновленного бота...")
    logger.info(f"⚡ Возрастных групп: {len(AGES)}")
    logger.info(f"🎟️ Промокодов: {len(PROMOCODES)}")
    
    # Запускаем планировщик заданий
    start_scheduler()
    
    logger.info("📡 Подключение к Telegram...")
    
    try:
        await dp.start_polling(bot, skip_updates=True, handle_signals=False)
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if scheduler.running:
            scheduler.shutdown()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())