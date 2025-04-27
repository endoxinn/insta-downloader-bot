import os
import io
import time
import re
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
ADMIN_USERNAMES = os.getenv('ADMIN_USERNAMES')
if ADMIN_USERNAMES is None:
    print("Ошибка: переменная окружения ADMIN_USERNAMES не задана.")
    ADMIN_USERNAMES = []
else:
    ADMIN_USERNAMES = [username.strip() for username in ADMIN_USERNAMES.split(',')]

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Установка команд бота
bot.set_my_commands([
    telebot.types.BotCommand("start", "🚀 Начать работу"),
    telebot.types.BotCommand("help", "ℹ️ Как пользоваться ботом"),
    telebot.types.BotCommand("check", "✅ Проверить подписку"),
    telebot.types.BotCommand("admin", "⚙️ Админ Панель")  # Команда для админов
])

# Инициализация клиента Instagram
cl = Client()
try:
    cl.login_by_sessionid(INSTAGRAM_SESSIONID)
except Exception as e:
    print(f"Ошибка входа в Instagram: {e}")

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

def is_admin(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status == 'administrator' or (member.user.username and member.user.username in ADMIN_USERNAMES)
    except Exception as e:
        print(f"Ошибка проверки администратора: {e}")
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
        send_subscription_prompt(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def callback_check_subscription(call):
    user_id = call.from_user.id
    if check_subscription(user_id):
        bot.answer_callback_query(call.id, "✅ Отлично! Вы подписаны!")
        bot.send_message(call.message.chat.id, "✅ Вы подписались! Можете пользоваться ботом!", reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, "❌ Вы ещё не подписались!")
        send_subscription_prompt(call.message.chat.id)

def send_subscription_prompt(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
    markup.add(types.InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_subscription"))
    bot.send_message(chat_id,
        "❌ Вы ещё не подписались. Пожалуйста, подпишитесь и нажмите кнопку ниже для проверки.",
        reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if is_admin(user_id):
        bot.send_message(message.chat.id, "⚙️ Добро пожаловать в панель администратора.", reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, "❌ У вас нет прав администратора.")

def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🗣 Сообщение пользователям", "📊 Статистика")
    markup.add("🔙 Назад")
    return markup

@bot.message_handler(func=lambda message: message.text == "🗣 Сообщение пользователям")
def send_message_to_users(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "📝 Введите сообщение для всех пользователей.")
        bot.register_next_step_handler(message, broadcast_message)
    else:
        bot.send_message(message.chat.id, "❌ У вас нет прав.")

def broadcast_message(message):
    if is_admin(message.from_user.id):
        text = message.text
        success = 0
        for user_id in list(user_data.keys()):
            try:
                bot.send_message(user_id, text)
                success += 1
            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
        bot.send_message(message.chat.id, f"✅ Сообщение отправлено {success} пользователям.")
    else:
        bot.send_message(message.chat.id, "❌ У вас нет прав.")

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def show_stats(message):
    if is_admin(message.from_user.id):
        total_users = len(user_data)
        bot.send_message(message.chat.id, f"📊 Всего пользователей: {total_users}")
    else:
        bot.send_message(message.chat.id, "❌ У вас нет прав.")

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id not in user_data:
        user_data[user_id] = {'downloads': 0}

    if text == "📥 Скачать":
        bot.send_message(message.chat.id, "📎 Отправьте ссылку на пост, Reels или Story!")
    elif text == "📢 Подписаться":
        send_subscription_prompt(message.chat.id)
    elif text == "ℹ️ Помощь":
        help_command(message)
    elif text == "🔙 Назад":
        bot.send_message(message.chat.id, "🔙 Главное меню", reply_markup=main_menu())
    else:
        download_instagram_content(message)

def download_instagram_content(message):
    user_id = message.from_user.id
    url = message.text.strip()

    if not re.match(r'https?://(www\.)?(instagram\.com|instagr\.am)/', url):
        bot.send_message(message.chat.id, "❌ Это не ссылка на Instagram! Пожалуйста, отправьте корректную ссылку.")
        return

    if user_data[user_id]['downloads'] >= FREE_DOWNLOADS and not check_subscription(user_id):
        send_subscription_prompt(message.chat.id)
        return

    loading_msg = bot.send_message(message.chat.id, "🔍 Загружаю 0%...")

    try:
        bot.edit_message_text("⏳ Загружаю 25%...", chat_id=message.chat.id, message_id=loading_msg.message_id)

        media_pk = cl.media_pk_from_url(url)
        media_info = cl.media_info(media_pk)

        bot.edit_message_text("⏳ Загружаю 50%...", chat_id=message.chat.id, message_id=loading_msg.message_id)

        if '/stories/highlights/' in url:
            highlight = cl.highlight_info(media_pk)
            media_group = [download_media(item.video_url or item.thumbnail_url, bool(item.video_url)) for item in highlight.items]
            media_group = [m for m in media_group if m]
            if media_group:
                bot.send_media_group(message.chat.id, media_group[:10])

        elif '/stories/' in url:
            story = cl.story_info(media_pk)
            file_url = story.video_url or story.thumbnail_url
            send_file_from_url(file_url, message.chat.id, bool(story.video_url))

        elif '/reel/' in url or '/reels/' in url:
            send_file_from_url(media_info.video_url or media_info.thumbnail_url, message.chat.id, bool(media_info.video_url))

        else:
            if media_info.media_type == 1:  # Фото
                send_file_from_url(media_info.thumbnail_url, message.chat.id, False)
            elif media_info.media_type == 2:  # Видео
                send_file_from_url(media_info.video_url, message.chat.id, True)
            elif media_info.media_type == 8:  # Альбом
                media_group = [download_media(res.video_url or res.thumbnail_url, bool(res.video_url)) for res in media_info.resources]
                media_group = [m for m in media_group if m]
                if media_group:
                    bot.send_media_group(message.chat.id, media_group[:10])
            else:
                bot.send_message(message.chat.id, "❌ Этот тип медиа пока не поддерживается.")

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
    try:
        response = requests.get(file_url, stream=True, timeout=10)
        response.raise_for_status()
        file_bytes = io.BytesIO(response.content)
        file_bytes.name = "file.mp4" if is_video else "file.jpg"

        if is_video:
            bot.send_video(chat_id, file_bytes)
        else:
            bot.send_photo(chat_id, file_bytes)

    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка при отправке файла: {e}")

def download_media(file_url, is_video=False):
    try:
        response = requests.get(file_url, stream=True, timeout=10)
        response.raise_for_status()
        file_bytes = io.BytesIO(response.content)
        file_bytes.name = "file.mp4" if is_video else "file.jpg"

        return types.InputMediaVideo(file_bytes) if is_video else types.InputMediaPhoto(file_bytes)

    except:
        return None

# Запуск бота
bot.infinity_polling()
