import logging
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

#настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

#статес для анкеты
NAME, AGE, INTERESTS, OCCASION, BUDGET, RELATIONSHIP, CONTACT = range(7)
REVIEW = 8
#настройки бд
DB_NAME = "gift_shop.db"

EMAIL_SETTINGS = {
    'smtp_server': 'smtp.yandex.ru',
    'smtp_port': 587,
    'email': 'Vagner.da24@yandex.ru',
    'password': 'rrnffecjzvdsqjqw',
    'admin_email': 'Vagner.da24@yandex.ru'
}

#инициализация базы данных
def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questionnaires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            contact_info TEXT,
            name TEXT,
            age TEXT,
            interests TEXT,
            occasion TEXT,
            budget TEXT,
            relationship TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            review_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

#сохранение анкеты в базу данных
def save_questionnaire(user_data, user_id, username, contact_info):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO questionnaires 
        (user_id, username, contact_info, name, age, interests, occasion, budget, relationship)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        username,
        contact_info,
        user_data.get('name'),
        user_data.get('age'),
        user_data.get('interests'),
        user_data.get('occasion'),
        user_data.get('budget'),
        user_data.get('relationship')
    ))
    
    conn.commit()
    questionnaire_id = cursor.lastrowid
    conn.close()
    
    return questionnaire_id

#сохранение отзыва в базу данных
def save_review(user_id, username, review_text):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO reviews (user_id, username, review_text)
        VALUES (?, ?, ?)
    ''', (user_id, username, review_text))
    
    conn.commit()
    conn.close()

#отправка email уведомления
def send_email_notification(questionnaire_data, questionnaire_id):
    try:
        subject = f"🎁 Новая анкета для подарка #{questionnaire_id}"
        
        body = f"""
        Новая анкета заполнена в боте!

        📋 Детали анкеты:
        • ID анкеты: {questionnaire_id}
        • Пользователь: {questionnaire_data['username']} (ID: {questionnaire_data['user_id']})
        • Контакты: {questionnaire_data['contact_info']}
        
        🎯 Информация о получателе:
        • Имя: {questionnaire_data['name']}
        • Возраст: {questionnaire_data['age']}
        • Интересы: {questionnaire_data['interests']}
        • Повод: {questionnaire_data['occasion']}
        • Бюджет: {questionnaire_data['budget']} руб.
        • Отношения: {questionnaire_data['relationship']}
        
        ⏰ Время заполнения: {questionnaire_data['created_at']}
        
        Свяжитесь с клиентом как можно скорее!
        """
        
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SETTINGS['email']
        msg['To'] = EMAIL_SETTINGS['admin_email']
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(EMAIL_SETTINGS['smtp_server'], EMAIL_SETTINGS['smtp_port'])
        server.starttls()
        server.login(EMAIL_SETTINGS['email'], EMAIL_SETTINGS['password'])
        text = msg.as_string()
        server.sendmail(EMAIL_SETTINGS['email'], EMAIL_SETTINGS['admin_email'], text)
        server.quit()
        
        logger.info(f"Email уведомление отправлено для анкеты #{questionnaire_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при отправке email: {e}")
        return False

#главное меню
def main_menu_keyboard():
    keyboard = [
        [KeyboardButton("🎁 Заполнить анкету для подарка")],
        [KeyboardButton("🏪 О нашем магазине"), KeyboardButton("📝 Оставить отзыв")],
        [KeyboardButton("📞 Контакты")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def cancel_keyboard():
    keyboard = [
        [KeyboardButton("❌ Отменить заполнение")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def review_keyboard():
    keyboard = [
        [KeyboardButton("❌ Отменить отзыв")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
# Старт бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎁 Добро пожаловать в магазин подарков 'PickMe'!\n\n"
        "Мы создаем неповторимые подарки, которые точно понравятся вашим близким!\n\n"
        "Выберите действие:",
        reply_markup=main_menu_keyboard()
    )

# Информация о магазине
async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = """
🏪 *О нашем магазине*

Мы - PickMe! Команда творческих людей, которые превращают обычные подарки в незабываемые впечатления!

Что мы предлагаем:
• Персонализированные подарки ручной работы
• Подарки по индивидуальному дизайну
• Быструю доставку по всему Томску
• Консультацию по выбору идеального подарка

Наши преимущества:
✅ Уникальность каждого подарка
✅ Качественные материалы
✅ Доступные цены
✅ Гарантия удовлетворения
    """
    await update.message.reply_text(about_text, parse_mode='Markdown')

# Контакты
async def contacts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contacts_text = """
📞 Наши контакты:

Социальные сети:
Instagram: что-то
VK: что-то

Мы всегда на связи! ✨
    """
    await update.message.reply_text(contacts_text, parse_mode='Markdown')

#начало анкеты
async def start_questionnaire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 Отлично! Давайте заполним анкету, чтобы мы могли подобрать идеальный подарок!\n\n"
        "Для начала, как зовут человека, для которого предназначен подарок?\n\n"
        "*Вы можете отменить заполнение в любой момент*",
        parse_mode = 'Markdown',
        reply_markup = cancel_keyboard()
    )
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить заполнение":
        return await cancel(update, context)

    context.user_data['name'] = update.message.text
    await update.message.reply_text(
        "Сколько лет человеку, для которого предназначен подарок?",
        reply_markup=cancel_keyboard()
    )
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить заполнение":
        return await cancel(update, context)

    context.user_data['age'] = update.message.text
    await update.message.reply_text(
        "Какие увлечения и интересы у этого человека?\n"
        "(например: чтение, спорт, музыка, кулинария и т.д.)",
        reply_markup=cancel_keyboard()
    )
    return INTERESTS

async def get_interests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить заполнение":
        return await cancel(update, context)

    context.user_data['interests'] = update.message.text
    await update.message.reply_text(
        "По какому поводу подарок?\n"
        "(день рождения, годовщина, новый год, просто так и т.д.)",
        reply_markup=cancel_keyboard()
    )
    return OCCASION

async def get_occasion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить заполнение":
        return await cancel(update, context)

    context.user_data['occasion'] = update.message.text
    await update.message.reply_text(
        "Какой у вас бюджет на подарок?\n"
        "(укажите примерную сумму в рублях)",
        reply_markup=cancel_keyboard()
    )
    return BUDGET

async def get_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить заполнение":
        return await cancel(update, context)

    context.user_data['budget'] = update.message.text
    await update.message.reply_text(
        "Какие у вас отношения с этим человеком?\n"
        "(друг/подруга, родственник, коллега, вторая половинка и т.д.)",
        reply_markup=cancel_keyboard()
    )
    return RELATIONSHIP

async def get_relationship(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить заполнение":
        return await cancel(update, context)

    context.user_data['relationship'] = update.message.text
    await update.message.reply_text(
        "📞 Отлично! Остался последний шаг.\n\n"
        "Пожалуйста, укажите ваши контактные данные для связи:\n"
        "(телефон, email или username Telegram)",
        reply_markup=cancel_keyboard()
    )
    return CONTACT

#завершение анкеты
async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить заполнение":
        return await cancel(update, context)

    contact_info = update.message.text
    user = update.message.from_user
    
    # Сохраняем анкету в базу данных
    questionnaire_id = save_questionnaire(
        context.user_data, 
        user.id, 
        user.username or f"{user.first_name} {user.last_name or ''}", 
        contact_info
    )
    
    # Формируем данные для email
    questionnaire_data = {
        'user_id': user.id,
        'username': user.username or f"{user.first_name} {user.last_name or ''}",
        'contact_info': contact_info,
        'name': context.user_data['name'],
        'age': context.user_data['age'],
        'interests': context.user_data['interests'],
        'occasion': context.user_data['occasion'],
        'budget': context.user_data['budget'],
        'relationship': context.user_data['relationship'],
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Отправляем email уведомление
    email_sent = send_email_notification(questionnaire_data, questionnaire_id)
    
    # Формируем сводку анкеты для пользователя
    summary = f"""
✅ *Анкета заполнена!*

*Информация о получателе:*
👤 Имя: {context.user_data['name']}
🎂 Возраст: {context.user_data['age']}
🎯 Интересы: {context.user_data['interests']}
🎉 Повод: {context.user_data['occasion']}
💰 Бюджет: {context.user_data['budget']} руб.
🤝 Отношения: {context.user_data['relationship']}
📞 Ваши контакты: {contact_info}

*Спасибо за анкету!* 
Наш менеджер свяжется с вами в течение дня для обсуждения вариантов подарков. 🎁

Номер вашей анкеты: #{questionnaire_id}
    """
    
    if not email_sent:
        summary += "\n\n⚠️ *Примечание:* Извините, возникли технические неполадки. Мы свяжемся с вами в ближайшее время."
    
    await update.message.reply_text(summary, parse_mode='Markdown', reply_markup=main_menu_keyboard())
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return ConversationHandler.END


# Начало отзыва
async def start_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📝 Пожалуйста, напишите ваш отзыв о нашем магазине:\n\n"
        "Что вам понравилось? Что можно улучшить? Ваши пожелания и предложения!\n\n"
        "*Вы можете отменить оставление отзыва*",
        parse_mode='Markdown',
        reply_markup=review_keyboard()
    )
    return REVIEW


# Обработка отзыва
async def get_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отменить отзыв":
        await update.message.reply_text(
            "Оставление отзыва отменено.",
            reply_markup=main_menu_keyboard()
        )
        return ConversationHandler.END

    review_text = update.message.text
    user = update.message.from_user

    # Сохраняем отзыв в базу данных
    save_review(
        user.id,
        user.username or f"{user.first_name} {user.last_name or ''}",
        review_text
    )

    logger.info(f"Новый отзыв от пользователя {user.id}: {review_text}")

    await update.message.reply_text(
        "💫 Спасибо за ваш отзыв! Мы ценим каждое мнение и обязательно учтем ваши пожелания.",
        reply_markup=main_menu_keyboard()
    )

    return ConversationHandler.END

# Отмена анкеты
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Анкета отменена. Если решите заполнить её позже - мы всегда к вашим услугам!",
        reply_markup=main_menu_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END

# Отмена отзыва
async def cancel_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Оставление отзыва отменено.",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END


# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🎁 Заполнить анкету для подарка":
        await start_questionnaire(update, context)
        return NAME
    elif text == "🏪 О нашем магазине":
        await about_us(update, context)
    elif text == "📝 Оставить отзыв":
        await start_review(update, context)
        return REVIEW
    elif text == "📞 Контакты":
        await contacts(update, context)
    else:
        # Если это не команда и пользователь не в состоянии диалога, показываем главное меню
        await update.message.reply_text(
            "Выберите действие из меню:",
            reply_markup=main_menu_keyboard()
        )

# Команда для просмотра статистики (только для администраторов)
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    ADMIN_IDS = [1956747196]
    
    if update.message.from_user.id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет доступа к этой команде.")
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Статистика по анкетам
    cursor.execute("SELECT COUNT(*) FROM questionnaires")
    total_questionnaires = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM reviews")
    total_reviews = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM questionnaires WHERE date(created_at) = date('now')")
    today_questionnaires = cursor.fetchone()[0]
    
    conn.close()
    
    stats_text = f"""
📊 *Статистика бота*

*Анкеты:*
• Всего анкет: {total_questionnaires}
• Анкет сегодня: {today_questionnaires}

*Отзывы:*
• Всего отзывов: {total_reviews}

База данных: {DB_NAME}
    """
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

# Обработка ошибок
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


# Главная функция
def main():

    init_database()
    TOKEN = "8557527419:AAFWDPd26_csVh9fjWiIK_kNIlSMMooAX5k"
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("🎁 Заполнить анкету для подарка"), start_questionnaire)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_interests)],
            OCCASION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_occasion)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_budget)],
            RELATIONSHIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_relationship)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
        },
        fallbacks=[
            MessageHandler(filters.Text("❌ Отменить заполнение"), cancel),
            CommandHandler('cancel', cancel)
        ],
        map_to_parent={
            ConversationHandler.END: ConversationHandler.END
        }
    )
    # Создаем обработчик диалога для отзывов
    review_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Text("📝 Оставить отзыв"), start_review)],
        states={
            REVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_review)],
        },
        fallbacks=[
            MessageHandler(filters.Text("❌ Отменить отзыв"), cancel_review),
            CommandHandler('cancel', cancel_review)
        ]
    )

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error)
    
    # Запускаем бота
    print("Бот запущен...")
    print(f"База данных: {DB_NAME}")
    application.run_polling()

if __name__ == '__main__':
    main()