import os
import sqlite3
import telebot
from telebot import types
from flask import Flask, request

# =========================
# SOZLAMALAR
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6470817755

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("kino.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    username TEXT,
    link TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name TEXT,
    file_id TEXT
)
""")

conn.commit()


# =========================
# FOYDALANUVCHI
# =========================

def save_user(user_id):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()


# =========================
# MAJBURIY A'ZOLIK
# =========================

def check_membership(user_id):
    cursor.execute("SELECT * FROM channels")
    channels = cursor.fetchall()

    not_joined = []

    for channel in channels:
        channel_id = channel[2]

        try:
            member = bot.get_chat_member(channel_id, user_id)

            if member.status in ["left", "kicked"]:
                not_joined.append(channel)

        except Exception:
            not_joined.append(channel)

    return not_joined


def membership_keyboard(channels):
    markup = types.InlineKeyboardMarkup()

    for channel in channels:
        button = types.InlineKeyboardButton(
            f"📢 {channel[1]}",
            url=channel[3]
        )
        markup.add(button)

    markup.add(
        types.InlineKeyboardButton(
            "✅ Tekshirish",
            callback_data="check_membership"
        )
    )

    return markup


def send_membership_message(chat_id):
    cursor.execute("SELECT * FROM channels")
    channels = cursor.fetchall()

    if not channels:
        return False

    bot.send_message(
        chat_id,
        "🔐 Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:\n\n"
        "A'zo bo'lgach, ✅ Tekshirish tugmasini bosing.",
        reply_markup=membership_keyboard(channels)
    )

    return True


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(message):

    user_id = message.from_user.id
    save_user(user_id)

    not_joined = check_membership(user_id)

    if not_joined:
        send_membership_message(message.chat.id)
        return

    bot.send_message(
        message.chat.id,
        "🎬 UZ_Kinomaniya botiga xush kelibsiz!\n\n"
        "🔢 Kino kodini yuboring."
    )


# =========================
# TEKSHIRISH
# =========================

@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def check_button(call):

    user_id = call.from_user.id

    not_joined = check_membership(user_id)

    if not_joined:
        bot.answer_callback_query(
            call.id,
            "❌ Hali barcha kanallarga a'zo bo'lmagansiz!",
            show_alert=True
        )

        return

    bot.answer_callback_query(
        call.id,
        "✅ A'zolik tasdiqlandi!"
    )

    bot.send_message(
        call.message.chat.id,
        "🎉 A'zoligingiz tasdiqlandi!\n\n"
        "🔢 Endi kino kodini yuboring."
    )


# =========================
# ADMIN PANEL
# =========================

def admin_keyboard():

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    markup.row(
        "🎬 Kino qo'shish",
        "🗑 Kino o'chirish"
    )

    markup.row(
        "📢 Kanal qo'shish",
        "🗑 Kanal o'chirish"
    )

    markup.row(
        "📋 Kinolar",
        "📢 Kanallar"
    )

    markup.row(
        "📊 Statistika"
    )

    return markup


@bot.message_handler(commands=["admin"])
def admin(message):

    if message.from_user.id != ADMIN_ID:
        bot.send_message(
            message.chat.id,
            "❌ Siz admin emassiz."
        )
        return

    bot.send_message(
        message.chat.id,
        "👑 ADMIN PANEL\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=admin_keyboard()
    )


# =========================
# KINO QO'SHISH
# =========================

@bot.message_handler(func=lambda message: message.text == "🎬 Kino qo'shish")
def add_movie_start(message):

    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(
        message.chat.id,
        "🔢 Kino kodini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        add_movie_code
    )


def add_movie_code(message):

    if message.from_user.id != ADMIN_ID:
        return

    code = message.text.strip()

    msg = bot.send_message(
        message.chat.id,
        "🎬 Kino nomini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        add_movie_name,
        code
    )


def add_movie_name(message, code):

    if message.from_user.id != ADMIN_ID:
        return

    name = message.text.strip()

    msg = bot.send_message(
        message.chat.id,
        "📹 Endi kino videosini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        add_movie_video,
        code,
        name
    )


def add_movie_video(message, code, name):

    if message.from_user.id != ADMIN_ID:
        return

    if not message.video:

        msg = bot.send_message(
            message.chat.id,
            "❌ Bu video emas.\n\n"
            "📹 Iltimos, kino videosini yuboring:"
        )

        bot.register_next_step_handler(
            msg,
            add_movie_video,
            code,
            name
        )

        return

    file_id = message.video.file_id

    try:

        cursor.execute(
            """
            INSERT INTO movies (code, name, file_id)
            VALUES (?, ?, ?)
            """,
            (code, name, file_id)
        )

        conn.commit()

        bot.send_message(
            message.chat.id,
            f"✅ Kino qo'shildi!\n\n"
            f"🔢 Kod: {code}\n"
            f"🎬 Nomi: {name}"
        )

    except sqlite3.IntegrityError:

        bot.send_message(
            message.chat.id,
            "❌ Bu kod allaqachon mavjud!"
        )


# =========================
# KINO O'CHIRISH
# =========================

@bot.message_handler(func=lambda message: message.text == "🗑 Kino o'chirish")
def delete_movie_start(message):

    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(
        message.chat.id,
        "🔢 O'chiriladigan kino kodini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        delete_movie
    )


def delete_movie(message):

    if message.from_user.id != ADMIN_ID:
        return

    code = message.text.strip()

    cursor.execute(
        "SELECT name FROM movies WHERE code = ?",
        (code,)
    )

    movie = cursor.fetchone()

    if not movie:

        bot.send_message(
            message.chat.id,
            "❌ Bunday kodli kino topilmadi."
        )

        return

    cursor.execute(
        "DELETE FROM movies WHERE code = ?",
        (code,)
    )

    conn.commit()

    bot.send_message(
        message.chat.id,
        f"✅ Kino o'chirildi:\n\n"
        f"🎬 {movie[0]}\n"
        f"🔢 Kod: {code}"
    )


# =========================
# KINO RO'YXATI
# =========================

@bot.message_handler(func=lambda message: message.text == "📋 Kinolar")
def movie_list(message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute(
        "SELECT code, name FROM movies ORDER BY id DESC"
    )

    movies = cursor.fetchall()

    if not movies:

        bot.send_message(
            message.chat.id,
            "🎬 Hozircha kino yo'q."
        )

        return

    text = "🎬 KINOLAR:\n\n"

    for movie in movies:
        text += f"🔢 {movie[0]} — {movie[1]}\n"

    bot.send_message(
        message.chat.id,
        text
    )


# =========================
# KANAL QO'SHISH
# =========================

@bot.message_handler(func=lambda message: message.text == "📢 Kanal qo'shish")
def add_channel_start(message):

    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(
        message.chat.id,
        "📢 Kanal nomini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        add_channel_name
    )


def add_channel_name(message):

    if message.from_user.id != ADMIN_ID:
        return

    name = message.text.strip()

    msg = bot.send_message(
        message.chat.id,
        "🔹 Kanal username yoki ID sini yuboring.\n\n"
        "Masalan:\n"
        "@kanal_username"
    )

    bot.register_next_step_handler(
        msg,
        add_channel_username,
        name
    )


def add_channel_username(message, name):

    if message.from_user.id != ADMIN_ID:
        return

    username = message.text.strip()

    msg = bot.send_message(
        message.chat.id,
        "🔗 Kanalga kirish havolasini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        add_channel_link,
        name,
        username
    )


def add_channel_link(message, name, username):

    if message.from_user.id != ADMIN_ID:
        return

    link = message.text.strip()

    cursor.execute(
        """
        INSERT INTO channels (name, username, link)
        VALUES (?, ?, ?)
        """,
        (name, username, link)
    )

    conn.commit()

    bot.send_message(
        message.chat.id,
        f"✅ Kanal qo'shildi!\n\n"
        f"📢 {name}\n"
        f"🔹 {username}"
    )


# =========================
# KANALLAR RO'YXATI
# =========================

@bot.message_handler(func=lambda message: message.text == "📢 Kanallar")
def channel_list(message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute(
        "SELECT id, name, username FROM channels"
    )

    channels = cursor.fetchall()

    if not channels:

        bot.send_message(
            message.chat.id,
            "📢 Hozircha kanal qo'shilmagan."
        )

        return

    text = "📢 MAJBURIY KANALLAR:\n\n"

    for channel in channels:

        text += (
            f"🆔 {channel[0]}\n"
            f"📢 {channel[1]}\n"
            f"🔹 {channel[2]}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text
    )


# =========================
# KANAL O'CHIRISH
# =========================

@bot.message_handler(func=lambda message: message.text == "🗑 Kanal o'chirish")
def delete_channel_start(message):

    if message.from_user.id != ADMIN_ID:
        return

    msg = bot.send_message(
        message.chat.id,
        "🆔 O'chiriladigan kanal ID sini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        delete_channel
    )


def delete_channel(message):

    if message.from_user.id != ADMIN_ID:
        return

    channel_id = message.text.strip()

    cursor.execute(
        "DELETE FROM channels WHERE id = ?",
        (channel_id,)
    )

    conn.commit()

    bot.send_message(
        message.chat.id,
        "✅ Kanal o'chirildi."
    )


# =========================
# STATISTIKA
# =========================

@bot.message_handler(func=lambda message: message.text == "📊 Statistika")
def statistics(message):

    if message.from_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM movies")
    movies = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM channels")
    channels = cursor.fetchone()[0]

    bot.send_message(
        message.chat.id,
        f"📊 STATISTIKA\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"🎬 Kinolar: {movies}\n"
        f"📢 Majburiy kanallar: {channels}"
    )


# =========================
# KINO KODI
# =========================

@bot.message_handler(func=lambda message: True)
def get_movie(message):

    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        return

    not_joined = check_membership(user_id)

    if not_joined:

        send_membership_message(message.chat.id)

        return

    code = message.text.strip()

    cursor.execute(
        "SELECT name, file_id FROM movies WHERE code = ?",
        (code,)
    )

    movie = cursor.fetchone()

    if not movie:

        bot.send_message(
            message.chat.id,
            "❌ Bunday kodli kino topilmadi.\n\n"
            "🔢 Kino kodini to'g'ri yuboring."
        )

        return

    name = movie[0]
    file_id = movie[1]

    bot.send_video(
        message.chat.id,
        file_id,
        caption=f"🎬 {name}"
    )


# =========================
# FLASK / WEBHOOK
# =========================

@app.route("/")
def home():

    return "UZ_Kinomaniya bot ishlayapti!"


@app.route("/webhook", methods=["POST"])
def webhook():

    json_string = request.get_data().decode("utf-8")

    update = telebot.types.Update.de_json(
        json_string
    )

    bot.process_new_updates([update])

    return "OK"


# =========================
# ISHGA TUSHIRISH
# =========================

if __name__ == "__main__":

    render_url = os.getenv("RENDER_EXTERNAL_URL")

    if render_url:

        webhook_url = render_url + "/webhook"

        bot.remove_webhook()

        bot.set_webhook(
            url=webhook_url
        )

    port = int(
        os.getenv("PORT", 10000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
