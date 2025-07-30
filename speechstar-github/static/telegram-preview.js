// Global Telegram Preview Functions

function showTelegramPreview(taskId) {
    // Try to find task in different data sources
    let task = null;
    
    // Check if tasksData exists (from tasks_list.html)
    if (typeof tasksData !== 'undefined') {
        task = tasksData.find(t => t.id == taskId);
    }
    
    // Check if tasks exists (from content.html)
    if (!task && typeof tasks !== 'undefined') {
        task = tasks.find(t => t.id == taskId);
    }
    
    // If still no task, create a placeholder
    if (!task) {
        task = {
            id: taskId,
            title: 'Задание не найдено',
            description: 'Ошибка загрузки данных задания',
            age_group: '8-12'
        };
    }
    
    const previewContent = generateTelegramPreview(task);
    document.getElementById('telegramPreviewContent').innerHTML = previewContent;
    
    const modal = new bootstrap.Modal(document.getElementById('telegramPreviewModal'));
    modal.show();
}

function generateTelegramPreview(task) {
    const now = new Date();
    const timeStr = now.getHours().toString().padStart(2, '0') + ':' + 
                   now.getMinutes().toString().padStart(2, '0');
    
    // Use real bot task format if age_group matches bot structure
    let content = '';
    let title = task.title || 'Комплекс развития на сегодня';
    
    // Real bot tasks structure from simple_speech_bot.py
    const botTasks = {
        "8-12": `🎯 Комплекс развития на сегодня:

🖼️ Сенсорика + речь: карточки с 6 животными (🐶 – «ав-ав», 🐱 – «мяу», 🐮 – «му-у», 🐑 – «бе-е», 🦆 – «кря-кря», 🐓 – «ко-ко-ко»).

🤸 Физическая активность: полоса препятствий из подушек, свернутых одеял и коробок – малыш ползёт и карабкается.

🗣️ Предречевое развитие: спрятать игрушку за спину и вдруг показать – «Кто там?».

😊 Эмоциональное развитие: грустная мимика – «Ой-ой, мишка упал» → оживляемся: «Ура, подняли!»

✋ Тактильное развитие: шуршащий пакет и мягкая тряпочка – «шур-шур», «мягко».`,
        "12-15": "🏠 Показывайте предметы и четко называйте: 'Дом', 'Мяч', 'Кот'. Ждите попытки повторить.",
        "15-18": "🙏 Учите простым просьбам: 'Дай мячик', 'Покажи носик', 'Где мама?'",
        "18-24": "💬 Стройте фразы из двух слов: 'Мама дай', 'Папа иди', 'Киса мяу'.",
        "24-36": "❓ Задавайте простые вопросы: 'Что это?', 'Какого цвета?', 'Где лежит?'"
    };
    
    // Use bot task if age group matches, otherwise use custom description
    if (task.age_group && botTasks[task.age_group]) {
        content = botTasks[task.age_group];
        if (task.age_group === "8-12") {
            title = "Комплекс развития на сегодня";
        }
    } else {
        content = task.description || '';
    }
    
    content = content.replace(/\n/g, '<br>');
    
    // Age group badge
    const ageGroupNames = {
        "8-12": "8-12 месяцев",
        "12-15": "12-15 месяцев", 
        "15-18": "15-18 месяцев",
        "18-24": "18-24 месяца",
        "24-36": "2-3 года"
    };
    
    const ageGroupName = ageGroupNames[task.age_group] || task.age_group || '';
    
    // Generate preview HTML
    let html = `
        <div class="telegram-preview">
            <div class="telegram-header">
                <div class="bot-icon">🤖</div>
                <div>
                    <div>Бот Запуск речи. Каждый день задание</div>
                    <div style="font-size: 12px; opacity: 0.7;">@SpeechStartBot</div>
                </div>
            </div>
            
            <div class="telegram-message">
                ${(task.image_url || task.image_path) ? `<img src="${task.image_url || task.image_path}" class="telegram-image" alt="Изображение задания">` : ''}
                
                <div style="margin-bottom: 8px;">
                    <span style="background: rgba(74, 158, 255, 0.2); padding: 2px 8px; border-radius: 12px; font-size: 11px; color: #4a9eff;">
                        ${ageGroupName}
                    </span>
                </div>
                
                <div style="margin-bottom: 12px;">
                    <strong>${title}</strong>
                </div>
                
                <div style="white-space: pre-line;">${content}</div>
                
                <div class="telegram-buttons">
                    <div class="telegram-button primary">✅ Выполнено</div>
                    <div class="telegram-button">📚 Еще задание</div>
                    <div class="telegram-button">👶 Изменить возраст</div>
                    <div class="telegram-button">ℹ️ О боте</div>
                </div>
                
                <div class="telegram-time">${timeStr}</div>
            </div>
        </div>
    `;
    
    return html;
}