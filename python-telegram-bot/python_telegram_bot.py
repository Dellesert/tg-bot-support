from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from dotenv import load_dotenv
import os
from pathlib import Path

# Указываем путь к .env файлу
env_path = Path('C:/Users/user/source/repos/python-telegram-bot/python-telegram-bot/env/Scripts/.env')
load_dotenv(dotenv_path=env_path)

# Получаем переменные окружения
api_token = os.getenv("API_TOKEN")
support_chat_id = os.getenv("SUPPORT_CHAT_ID")

# Печатаем значения, чтобы убедиться, что все загружено правильно
print(f"API Token: {api_token}")
print(f"Support Chat ID: {support_chat_id}")


# Состояния для обработки сообщений
NICKNAME, SUPPORT_MESSAGE, WAITING_RESPONSE = range(3)

# Хранилище для никнеймов
user_nicks = {}

# Создание объекта приложения с вашим API токеном
application = Application.builder().token(api_token).build()

# Функция для начала работы с ботом
async def start(update, context):   
    keyboard = [
        [InlineKeyboardButton("Написать в техподдержку", callback_data='support')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("Привет! Чем я могу вам помочь?", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text("Привет! Чем я могу вам помочь?", reply_markup=reply_markup)
        await update.callback_query.answer()

# Функция для обработки кнопки "Написать в техподдержку"
async def support(update, context):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Как я могу к вам обращаться? Введите ваш НИК (подписки):")
    return NICKNAME

# Функция для получения и проверки никнейма
async def get_nickname(update, context):
    nickname = update.message.text.strip()
    user_id = update.message.from_user.id

    if nickname in user_nicks and user_nicks[nickname] != user_id:
        await update.message.reply_text("Этот ник уже используется другим пользователем. Пожалуйста, выберите другой.")
        return NICKNAME

    user_nicks[nickname] = user_id
    context.user_data['nickname'] = nickname

    await update.message.reply_text(f"Ник {nickname} сохранен! Теперь опишите вашу проблему:")
    return SUPPORT_MESSAGE

# Функция для отправки сообщения в техподдержку
async def send_support_message(update, context):
    user_message = update.message.text
    nickname = context.user_data.get('nickname')
    user_id = update.message.from_user.id

    # Отправка сообщения в канал техподдержки
    await context.bot.send_message(
        chat_id=support_chat_id,
        text=f"Запрос от пользователя:\nНик: {nickname}\nID: @{user_id}\nСообщение: {user_message}"
    )

    keyboard = [
        [InlineKeyboardButton("Жду ответ", callback_data='waiting_response')],
        [InlineKeyboardButton("Отменить запрос", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Ваш запрос принят! Мы постараемся ответить как можно скорее.",
        reply_markup=reply_markup
    )
    return WAITING_RESPONSE

# Функция для кнопки "Жду ответ"
async def waiting_response(update, context):
    await update.callback_query.answer("Пожалуйста, дождитесь ответа от техподдержки.")
    return WAITING_RESPONSE

# Функция для кнопки "Отменить запрос"
async def cancel(update, context):
    user_id = update.callback_query.from_user.id
    nickname = context.user_data.get('nickname', 'Неизвестный пользователь')

    await context.bot.send_message(
        chat_id=support_chat_id,
        text=f"Пользователь {nickname} с ID {user_id} отменил запрос."
    )

    keyboard = [[InlineKeyboardButton("На главную", callback_data='to_start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text(
        "Ваш запрос отменен. Если потребуется помощь, вы всегда можете обратиться.",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

# Функция для кнопки "На главную"
async def to_start(update, context):
    await update.callback_query.answer()
    await context.bot.send_message(
        chat_id=update.callback_query.from_user.id,
        text="Процесс был сброшен, и вы возвращаетесь в главное меню. Пропишите /start"
    )

    # Завершаем текущий диалог
    return ConversationHandler.END

# Функция для кнопки "Написать новую проблему"
async def write_new(update, context):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Опишите вашу проблему:")
    return SUPPORT_MESSAGE

# Основной код бота
application.add_handler(CommandHandler('start', start))
conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(support, pattern='^support$')],
    states={
        NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_nickname)],
        SUPPORT_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_support_message)],
        WAITING_RESPONSE: [
            CallbackQueryHandler(waiting_response, pattern='^waiting_response$'),
            CallbackQueryHandler(cancel, pattern='^cancel$')
        ]
    },
    fallbacks=[CommandHandler('start', start)]
)

application.add_handler(conversation_handler)
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_support_message))
application.add_handler(CallbackQueryHandler(to_start, pattern='^to_start$'))
application.add_handler(CallbackQueryHandler(write_new, pattern='^write_new$'))

# Запуск бота
application.run_polling()
