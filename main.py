import os
import io
import time
import requests
from dotenv import load_dotenv
import telebot
from telebot import types
from instagrapi import Client

# Загружаем переменные окружения
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
INSTAGRAM_SESSIONID = os.getenv('INSTAGRAM_SESSIONID')
CHANNEL_USERNAME = '@instosaverr'

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Красивое описание и команды
bot.set_my_description(
    "🚀 Мгновенная загрузка из Instagram\n"
    "🎬 Видео, Фото, Истории — в одно касание\n"
    "💬 Нажимай на start и качай без ограничений!"
)

bot.set_my_commands([
    telebot.types.BotCommand("start", "🚀 Начать работу"),
    telebot.types.BotCommand("help", "ℹ️ Как пользоваться ботом"),
    telebot.types.BotCommand("check", "✅ Проверить подписку")
])

# Инициализация клиента Instagram
cl = Client()
cl.login_by_sessionid(INSTAGRAM_SESSIONID)

# Храним данные пользователей
user_data = {}

FREE_DOWNLOADS = 3  # Количество бесплатных загрузок

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 Скачать", "📢 Подписаться", "ℹ️ Помощь")
    return markup

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['member', 'creator', 'administrator']
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {'downloads': 0}

    bot.send_message(message.chat.id,
        "👋 Привет!\n"
        "Я помогу тебе скачать посты, Reels и истории из Instagram!\n\n"
        f"📥 Бесплатных загрузок: {FREE_DOWNLOADS}\n"
        "После этого нужна подписка на канал.",
        reply_markup=main_menu())

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(message.chat.id,
        "🔹 *Как пользоваться ботом:*\n\n"
        "1️⃣ Нажмите *«📥 Скачать»*.\n"
        "2️⃣ Отправьте ссылку на пост, Reels или Сторис из Instagram.\n"
        "3️⃣ Получите медиафайл прямо здесь, без водяных знаков!\n\n"
        "⚡ *Бесплатно доступны 3 загрузки!* После — требуется подписка.\n\n"
        "📢 Подписка на канал обязательна для использования бота.\n"
        f"Подписаться 👉 {CHANNEL_USERNAME}",
        parse_mode='Markdown',
        reply_markup=main_menu()
    )

@bot.message_handler(commands=['check'])
def check(message):
    user_id = message.from_user.id
    if check_subscription(user_id):
        bot.send_message(message.chat.id, "✅ Отлично! Вы подписаны, можете пользоваться ботом!", reply_markup=main_menu())
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(types.InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_subscription"))
        bot.send_message(message.chat.id,
            "❌ Вы ещё не подписались на канал. Пожалуйста, подпишитесь и нажмите кнопку ниже для проверки.",
            reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def callback_check_subscription(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.answer_callback_query(call.id, "✅ Отлично! Вы подписаны!")
        bot.send_message(call.message.chat.id, "✅ Вы подписались! Можете пользоваться ботом!", reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, "❌ Вы ещё не подписались!")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(types.InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_subscription"))
        bot.send_message(call.message.chat.id,
            "❌ Вы всё ещё не подписались. Подпишитесь на канал и нажмите «Проверить подписку»!",
            reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id not in user_data:
        user_data[user_id] = {'downloads': 0}

    if text == "📥 Скачать":
        bot.send_message(message.chat.id, "📎 Отправьте ссылку на пост, Reels или Story!")
        return

    if text == "📢 Подписаться":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        markup.add(types.InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_subscription"))
        bot.send_message(message.chat.id, "Подпишитесь на наш канал для использования бота!", reply_markup=markup)
        return

    if text == "ℹ️ Помощь":
        help_command(message)
        return

    # Если текст не кнопка — считаем что это ссылка
    download_instagram_content(message)

def download_instagram_content(message):
    user_id = message.from_user.id

    if user_data[user_id]['downloads'] >= FREE_DOWNLOADS:
        if not check_subscription(user_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
            markup.add(types.InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_subscription"))
            bot.send_message(message.chat.id,
                "❌ Вы использовали все бесплатные загрузки!\n\n"
                "Чтобы продолжить пользоваться ботом, подпишитесь на канал и нажмите «Проверить подписку»!",
                reply_markup=markup)
            return

    url = message.text.strip()
    loading_msg = bot.send_message(message.chat.id, "🔍 Загружаю 0%...")

    try:
        bot.edit_message_text("⏳ Загружаю 25%...", chat_id=message.chat.id, message_id=loading_msg.message_id)
        media_pk = cl.media_pk_from_url(url)
        media_info = cl.media_info(media_pk)

        bot.edit_message_text("⏳ Загружаю 50%...", chat_id=message.chat.id, message_id=loading_msg.message_id)

        if '/stories/' in url:
            story = cl.story_info(media_pk)
            if story.video_url:
                send_file_from_url(story.video_url, message.chat.id, is_video=True)
            elif story.thumbnail_url:
                send_file_from_url(story.thumbnail_url, message.chat.id, is_video=False)

        elif '/reel/' in url or '/reels/' in url:
            if media_info.video_url:
                send_file_from_url(media_info.video_url, message.chat.id, is_video=True)
            else:
                bot.send_message(message.chat.id, "❌ Не удалось скачать Reels.")

        else:
            if media_info.media_type == 1:  # Фото
                send_file_from_url(media_info.thumbnail_url, message.chat.id, is_video=False)

            elif media_info.media_type == 2:  # Видео
                if media_info.video_url:
                    send_file_from_url(media_info.video_url, message.chat.id, is_video=True)
                else:
                    bot.send_message(message.chat.id, "❌ Не удалось скачать видео.")

            elif media_info.media_type == 8:  # Альбом
                for res in media_info.resources:
                    if res.video_url:
                        send_file_from_url(res.video_url, message.chat.id, is_video=True)
                    elif res.thumbnail_url:
                        send_file_from_url(res.thumbnail_url, message.chat.id, is_video=False)

            else:
                bot.send_message(message.chat.id, "❌ Этот тип медиа пока не поддерживается.")

        # Успешная загрузка
        user_data[user_id]['downloads'] += 1
        bot.edit_message_text("✅ Загружено!", chat_id=message.chat.id, message_id=loading_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"⚠️ Ошибка: {str(e)}", chat_id=message.chat.id, message_id=loading_msg.message_id)

    finally:
        time.sleep(2)
        try:
            bot.delete_message(chat_id=message.chat.id, message_id=loading_msg.message_id)
        except:
            pass

def send_file_from_url(file_url, chat_id, is_video=False):
    response = requests.get(file_url, timeout=10)
    file_bytes = io.BytesIO(response.content)
    file_bytes.name = 'file.mp4' if is_video else 'file.jpg'
    if is_video:
        bot.send_video(chat_id, file_bytes)
    else:
        bot.send_photo(chat_id, file_bytes)

# Запуск бота
bot.infinity_polling()
