#!/usr/bin/env python3
"""
Simple Flask app for deployment with gunicorn
"""
import os
import logging
import requests
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-me")

def load_real_user_data():
    """Загрузить реальные данные пользователей из всех источников"""
    all_users = {}
    
    # Загружаем данные из users_data.json (основные данные бота)
    try:
        with open("users_data.json", "r", encoding="utf-8") as f:
            bot_users = json.load(f)
            all_users.update(bot_users)
    except Exception as e:
        logger.warning(f"Не удалось загрузить users_data.json: {e}")
        bot_users = {}
    
    # Загружаем данные из data/users.json (старые данные)
    try:
        with open("data/users.json", "r", encoding="utf-8") as f:
            old_users = json.load(f)
            for user_id, user_data in old_users.items():
                if user_id not in all_users:
                    # Конвертируем старый формат в новый
                    all_users[user_id] = {
                        "registered": user_data.get("registration_date", "2025-07-24T00:00:00"),
                        "age_group": "Не выбран",  # В старых данных возрастная группа не сохранялась
                        "trial_started": user_data.get("last_activity", "2025-07-24T00:00:00"),
                        "trial_used": user_data.get("subscription_status") == "active",
                        "subscription": "active" if user_data.get("subscription_status") == "active" else None,
                        "last_task_date": user_data.get("last_activity", "")[:10],
                        "current_day": user_data.get("tasks_completed", 0),
                        "username": user_data.get("username", "")
                    }
    except Exception as e:
        logger.warning(f"Не удалось загрузить data/users.json: {e}")
    
    # Загружаем данные из analytics
    try:
        with open("data/analytics.json", "r", encoding="utf-8") as f:
            analytics = json.load(f)
            for user_id, user_data in analytics.get("user_registrations", {}).items():
                if user_id not in all_users:
                    all_users[user_id] = {
                        "registered": user_data.get("registration_date", "2025-07-24T00:00:00"),
                        "age_group": "Не выбран",
                        "trial_started": user_data.get("registration_date", "2025-07-24T00:00:00"),
                        "trial_used": user_data.get("completed_registration", False),
                        "subscription": None,
                        "last_task_date": "",
                        "current_day": 0,
                        "username": user_data.get("username", "")
                    }
    except Exception as e:
        logger.warning(f"Не удалось загрузить analytics.json: {e}")
    
    # Подсчитываем статистику
    stats = {
        'total_users': len(all_users),
        'trial_users': 0,
        'monthly_subscribers': 0,
        'lifetime_subscribers': 0,
        'promocode_users': 0,
        'total_payments': 0,
        'monthly_revenue': 0,
        'lifetime_revenue': 0
    }
    
    users_list = []
    
    for user_id, user_data in all_users.items():
        # Анализируем статистику
        if user_data.get("trial_used"):
            stats['trial_users'] += 1
            
        subscription = user_data.get("subscription")
        if subscription == "monthly":
            stats['monthly_subscribers'] += 1
            stats['monthly_revenue'] += 150
            stats['total_payments'] += 150
        elif subscription == "lifetime":
            stats['lifetime_subscribers'] += 1
            stats['lifetime_revenue'] += 500
            stats['total_payments'] += 500
        elif subscription == "promocode":
            stats['promocode_users'] += 1
        elif subscription == "active":
            stats['trial_users'] += 1  # Считаем как активных пользователей
        
        # Создаем запись пользователя для отображения
        username = user_data.get("username", f"user_{user_id[-4:]}")
        users_list.append({
            'user_id': user_id,
            'username': username if username else f"user_{user_id[-4:]}",
            'registration_date': user_data.get("registered", "2025-07-27T00:00:00"),
            'age_group': user_data.get("age_group", "Не выбран"),
            'subscription_status': subscription or ("trial" if user_data.get("trial_used") else "new"),
            'trial_started': user_data.get("trial_started"),
            'last_task_date': user_data.get("last_task_date"),
            'tasks_completed': user_data.get("current_day", 0),
            'tasks_viewed': user_data.get("current_day", 0) + 1 if user_data.get("trial_used") else 0,
            'last_activity': user_data.get("trial_started", user_data.get("registered", "2025-07-27T00:00:00")),
            'level': get_user_level(user_data.get("current_day", 0))
        })
    
    return stats, users_list

def get_user_level(tasks_completed):
    """Определить уровень пользователя по количеству выполненных заданий"""
    if tasks_completed == 0:
        return "Новичок"
    elif tasks_completed < 7:
        return "Пробник"
    elif tasks_completed < 30:
        return "Активный"
    else:
        return "Постоянный"

# Загружаем реальные данные
REAL_STATS, REAL_USERS = load_real_user_data()

MOCK_TASK_STATS = {
    '9-14 мес': {'total': 1, 'with_images': 0, 'with_videos': 0},
    '15-19 мес': {'total': 1, 'with_images': 0, 'with_videos': 0}
}

MOCK_TASKS = [
    {
        'id': 1,
        'title': 'Комплексное развитие 9-14 месяцев - День 1',
        'description': '📋 Задание на сегодня для возраста 9-14 месяцев:\n\n🧠 **Внимание и восприятие (слух):**\n«Что за звук?» — берём металлическую крышку, пластиковую и деревянную ложку. Постучите по разным поверхностям: стол, пол, коробка. Комментируйте:\n«Звенит!» — (ложка по крышке),\n«Глухо!» — (ложка по дивану),\n«Стук-стук!» — (ложка по полу).\n➡️ Побуждаем малыша прислушиваться и различать звуки.\n\n🤸 **Физическая активность:**\n«Собери зверей» — разложите мягкие игрушки змейкой. Говорите: «Вот лисичка! А вот зайка!» — малыш ползёт или идёт по маршруту, собирая их в коробку.\n➡️ Укрепляем моторику, внимание и понимание слов.\n\n🗣️ **Предречевое развитие:**\n«Мяч и звук» — отбивайте мячик от пола или стола и ритмично произносите:\n«Бух» → отскок,\n«Бух» → отскок,\n➡️ Побуждаем малыша повторять, смотрим на реакцию и поощряем попытки.\n\n😊 **Эмоциональное развитие:**\n«Грусть — радость» — с мягкой игрушкой проигрываем мини-сценки:\n«Ой-ой, зайка упал…» (грустный голос)\n→ «Ура! Зайка встал!» (весёлый голос, хлопаем в ладоши)\n➡️ Помогаем ребёнку различать эмоции, сопереживать, подражать.\n\n✋ **Тактильное/предметное развитие:**\n«Мягко или жёстко» — в одной миске положите вату, тряпочку, помпон. В другой — ложку, пуговицы, крышку. Предложите малышу по очереди трогать и называть ощущения:\n«Мягко!» — (трогает вату),\n«Твёрдо!» — (трогает ложку).\n➡️ Развиваем тактильную чувствительность и словарь.\n\n💡 Совет: Повторяйте упражнения несколько раз в день, но не принуждайте. Если малыш не в настроении - попробуйте позже.\n\n✨ Хвалите за любые попытки!\n\nДо встречи завтра за новым заданием! 🌙',
        'age_group': '9-14 мес',
        'day_number': 1,
        'image_url': None,
        'video_url': None
    },
    {
        'id': 2,
        'title': 'Комплексное развитие 15-19 месяцев - День 1',
        'description': '📋 Задание на сегодня для возраста 15-19 месяцев:\n\n🧠 **Внимание и восприятие:**\nИгра «Покажи и назови» — разложите перед ребёнком 4–5 знакомых игрушек. Спрашивайте: «Где машинка?», «Покажи мишку», «А где лошадка?» — поощряйте, если малыш указывает правильно.\n\n🤸 **Физическая активность:**\nИгра с мячом — катайте мячик друг другу. При этом сопровождайте действия словами: «Кати!», «Поймал!», «Бросай!» — это помогает закреплять глаголы и имя предмета.\n\n🗣️ **Предречевое развитие:**\nЧитаем короткие звукоподражательные стишки, делая акцент на ударных звуках, ритме и повторениях:\n\nЗайка взял свой барабан —\nИ ударил: трам-там-там!\n\nКу-ку, ку-ку, кукушечка,\nЛети скорей в лесок.\nКу-ку, ку-ку, кукушечка,\nПодай свой голосок!\n\nТук-тук-тук-тук —\nЭто что за стук?\nДеревянный это звук:\nТук-тук-тук-тук.\n\n😊 **Эмоциональное развитие:**\n«Зеркальные эмоции» — сядьте с малышом перед зеркалом и по очереди изображайте разные эмоции: радость, грусть, удивление, страх, веселье. Побуждайте ребёнка повторять мимику: «А теперь как будто ты испугался!»\n\n✋ **Тактильное/предметное развитие:**\n«Корзина текстур» — наполните коробку или корзину разными материалами (мешочек с фасолью, кусочек губки, фольга, мех, бархат). Пусть малыш ощупывает предметы, а вы называете ощущения: «Мягкий», «Шуршит», «Гладкий», «Колючий».\n\n💡 Совет: Повторяйте упражнения несколько раз в день, но не принуждайте. Если малыш не в настроении - попробуйте позже.\n\n✨ Хвалите за любые попытки!\n\nДо встречи завтра за новым заданием! 🌙',
        'age_group': '15-19 мес',
        'day_number': 1,
        'image_url': None,
        'video_url': None
    }
]

AGE_GROUPS = ['9-14 мес', '15-19 мес']

# Импорт модуля Telegram аналитики с обработкой ошибок
try:
    from telegram_analytics import create_telegram_exporter
    from analytics_scheduler import start_analytics_scheduler, stop_analytics_scheduler, get_scheduler_status
    # Создаем экземпляр экспортера
    telegram_exporter = create_telegram_exporter()
except ImportError as e:
    logger.warning(f"Telegram analytics modules not available: {e}")
    # Mock объекты для работы без Telegram функций
    class MockTelegramExporter:
        def send_daily_analytics(self, stats, task_stats):
            logger.info("Mock: Daily analytics would be sent")
            return True
        def send_weekly_analytics(self, stats, task_stats):
            logger.info("Mock: Weekly analytics would be sent") 
            return True
    
    telegram_exporter = MockTelegramExporter()
    
    def start_analytics_scheduler(daily_time="09:00", weekly_day="monday", weekly_time="10:00"):
        logger.info("Mock: Analytics scheduler would start")
    
    def stop_analytics_scheduler():
        logger.info("Mock: Analytics scheduler would stop")
    
    def get_scheduler_status():
        return {'running': False, 'next_runs': []}

@app.route('/')
def dashboard():
    """Главная страница с обзором"""
    # Загружаем свежие данные пользователей
    stats, users = load_real_user_data()
    
    # Статистика по заданиям
    task_stats = MOCK_TASK_STATS.copy()
    
    # Последние 5 пользователей
    recent_users = sorted(users, key=lambda x: x['registration_date'], reverse=True)[:5]
    
    return render_template('dashboard.html', 
                          stats=stats, 
                          task_stats=task_stats,
                          recent_users=recent_users)

@app.route('/tasks')
def tasks_list():
    """List tasks with age filtering"""
    age_filter = request.args.get('age_group', 'all')
    
    if age_filter == 'all':
        filtered_tasks = MOCK_TASKS
    else:
        filtered_tasks = [t for t in MOCK_TASKS if t['age_group'] == age_filter]
    
    return render_template('tasks_list.html',
                           tasks=filtered_tasks,
                           age_groups=AGE_GROUPS,
                           current_filter=age_filter)

@app.route('/tasks/new', methods=['GET', 'POST'])
def new_task():
    """Create new task"""
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            description = request.form.get('description')
            age_group = request.form.get('age_group')
            day_number = int(request.form.get('day_number', 1))
            
            if not all([title, description, age_group]):
                flash('Все обязательные поля должны быть заполнены', 'error')
                return render_template('task_form.html', 
                                       age_groups=AGE_GROUPS,
                                       edit_mode=False,
                                       task={})
            
            # Simulate task creation
            new_task = {
                'id': len(MOCK_TASKS) + 1,
                'title': title,
                'description': description,
                'age_group': age_group,
                'day_number': day_number,
                'image_url': None,
                'video_url': None
            }
            MOCK_TASKS.append(new_task)
            
            flash(f'Задание "{title}" успешно создано!', 'success')
            return redirect(url_for('tasks_list'))
            
        except Exception as e:
            logger.error(f"Task creation error: {e}")
            flash(f'Ошибка при создании задания: {e}', 'error')
    
    return render_template('task_form.html',
                           age_groups=AGE_GROUPS,
                           edit_mode=False,
                           task={})

@app.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
def edit_task(task_id):
    """Edit existing task"""
    task = next((t for t in MOCK_TASKS if t['id'] == task_id), None)
    if not task:
        flash('Задание не найдено', 'error')
        return redirect(url_for('tasks_list'))
    
    if request.method == 'POST':
        try:
            task['title'] = request.form.get('title')
            task['description'] = request.form.get('description')
            task['age_group'] = request.form.get('age_group')
            task['day_number'] = int(request.form.get('day_number', 1))
            
            flash(f'Задание "{task["title"]}" успешно обновлено!', 'success')
            return redirect(url_for('tasks_list'))
            
        except Exception as e:
            logger.error(f"Task edit error: {e}")
            flash(f'Ошибка при редактировании: {e}', 'error')
    
    return render_template('task_form.html',
                           age_groups=AGE_GROUPS,
                           edit_mode=True,
                           task=task)

@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    """Delete task"""
    global MOCK_TASKS
    MOCK_TASKS = [t for t in MOCK_TASKS if t['id'] != task_id]
    flash('Задание удалено', 'success')
    return redirect(url_for('tasks_list'))

@app.route('/users')
def users():
    """Управление пользователями"""
    # Загружаем реальные данные пользователей
    stats, users_list = load_real_user_data()
    
    return render_template('users.html', users=users_list)

@app.route('/analytics')
def analytics():
    """Analytics page"""
    engagement_stats = MOCK_STATS
    popular_tasks = MOCK_TASKS[:5]  # Top 5 tasks
    
    return render_template('analytics.html',
                           engagement_stats=engagement_stats,
                           popular_tasks=popular_tasks)

@app.route('/analytics/export-telegram', methods=['POST'])
def export_analytics_telegram():
    """Экспорт аналитики в Telegram канал"""
    try:
        # Отправляем ежедневную аналитику
        success = telegram_exporter.send_daily_analytics(MOCK_STATS, MOCK_TASK_STATS)
        
        if success:
            flash('Аналитика успешно экспортирована в Telegram канал!', 'success')
        else:
            flash('Ошибка при экспорте в Telegram. Проверьте настройки канала.', 'error')
            
    except Exception as e:
        logger.error(f"Ошибка экспорта аналитики: {e}")
        flash(f'Ошибка при экспорте: {e}', 'error')
    
    return redirect(url_for('analytics'))

@app.route('/analytics/export-weekly', methods=['POST'])
def export_weekly_analytics():
    """Экспорт еженедельной аналитики в Telegram канал"""
    try:
        # Отправляем еженедельную аналитику
        success = telegram_exporter.send_weekly_analytics(MOCK_STATS, MOCK_TASK_STATS)
        
        if success:
            flash('Еженедельная аналитика успешно экспортирована в Telegram канал!', 'success')
        else:
            flash('Ошибка при экспорте еженедельной аналитики.', 'error')
            
    except Exception as e:
        logger.error(f"Ошибка экспорта еженедельной аналитики: {e}")
        flash(f'Ошибка при экспорте: {e}', 'error')
    
    return redirect(url_for('analytics'))

@app.route('/analytics/schedule-export', methods=['POST'])
def schedule_analytics_export():
    """Настройка автоматического экспорта аналитики"""
    try:
        export_time = request.form.get('export_time', '09:00')
        export_enabled = request.form.get('export_enabled') == 'on'
        weekly_day = request.form.get('weekly_day', 'monday')
        weekly_time = request.form.get('weekly_time', '10:00')
        
        if export_enabled:
            # Останавливаем старый планировщик
            stop_analytics_scheduler()
            
            # Запускаем новый с обновленными настройками
            start_analytics_scheduler(
                daily_time=export_time,
                weekly_day=weekly_day,
                weekly_time=weekly_time
            )
            
            flash(f'Автоматический экспорт настроен: ежедневно в {export_time}, еженедельно в {weekly_day} {weekly_time}', 'success')
        else:
            stop_analytics_scheduler()
            flash('Автоматический экспорт отключен', 'info')
            
    except Exception as e:
        logger.error(f"Ошибка настройки экспорта: {e}")
        flash(f'Ошибка настройки: {e}', 'error')
    
    return redirect(url_for('analytics'))

@app.route('/analytics/scheduler-status')
def scheduler_status():
    """Получить статус планировщика аналитики"""
    try:
        status = get_scheduler_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Ошибка получения статуса планировщика: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/promocodes')
def promocodes():
    """Страница управления промокодами"""
    return render_template('promocodes.html')

@app.errorhandler(404)
def not_found(error):
    return render_template('base.html'), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    flash('Произошла внутренняя ошибка сервера', 'error')
    return render_template('base.html'), 500

@app.route('/bot-status')
def bot_status():
    """Статус интеграции бота с CMS"""
    try:
        with open("data/tasks.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            tasks_count = len(data.get("tasks", []))
        
        status = {
            "cms_tasks_count": tasks_count,
            "bot_integration": "active",
            "auto_delivery": "enabled",
            "delivery_time": "9:00 AM Moscow Time",
            "last_update": datetime.now().isoformat(),
            "message": f"Бот загружает {tasks_count} заданий из CMS автоматически"
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "error": str(e),
            "bot_integration": "error",
            "last_update": datetime.now().isoformat()
        }), 500

# ЮKassa webhook для автоматической обработки платежей
@app.route('/webhook/yookassa', methods=['POST'])
def yookassa_webhook():
    """Обработчик webhook уведомлений от ЮKassa"""
    try:
        import hmac
        import hashlib
        
        # Получаем тело запроса
        body = request.get_data(as_text=True)
        data = json.loads(body)
        
        event_type = data.get('event')
        payment_object = data.get('object')
        
        if event_type == 'payment.succeeded':
            # Платеж успешен
            payment_id = payment_object.get('id')
            user_id = payment_object.get('metadata', {}).get('user_id')
            amount = float(payment_object.get('amount', {}).get('value', 0))
            
            logger.info(f"🎉 Webhook: платеж {payment_id} успешен для пользователя {user_id}, сумма {amount}₽")
            
            if user_id:
                # Загружаем данные пользователей
                try:
                    with open("users_data.json", "r", encoding="utf-8") as f:
                        users_data = json.load(f)
                except:
                    users_data = {}
                
                # Обновляем подписку пользователя
                if user_id in users_data:
                    if amount == 150.0:
                        users_data[user_id]["subscription"] = "monthly"
                        users_data[user_id]["subscription_end"] = (datetime.now() + timedelta(days=30)).isoformat()
                        logger.info(f"✅ Активирована месячная подписка для {user_id}")
                    elif amount == 500.0:
                        users_data[user_id]["subscription"] = "lifetime"
                        logger.info(f"✅ Активирован пожизненный доступ для {user_id}")
                    
                    # Очищаем pending платеж
                    if "pending_payment" in users_data[user_id]:
                        del users_data[user_id]["pending_payment"]
                    
                    # Сохраняем обновленные данные
                    with open("users_data.json", "w", encoding="utf-8") as f:
                        json.dump(users_data, f, ensure_ascii=False, indent=2)
        
        elif event_type == 'payment.canceled':
            payment_id = payment_object.get('id')
            logger.info(f"❌ Webhook: платеж {payment_id} отменен")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return jsonify({'error': 'Internal error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)