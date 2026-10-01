import os
import sqlite3
import telebot
from telebot import types
from flask import Flask, request

# =========================================================
# SOZLAMALAR
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6470817755

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi!")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# =========================================================
# DATABASE
# =========================================================

conn = sqlite3.connect(
    "kino.db",
    check_same_thread=False
)

cursor = conn.cursor()

# Foydalanuvchilar
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    username TEXT
)
""")

# Majburiy kanallar
cursor.execute("""
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT NOT NULL,
    link TEXT NOT NULL
)
""")

# Kinolar
cursor.execute("""
CREATE TABLE IF NOT EXISTS movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    file_id TEXT NOT NULL
)
""")

conn.commit()


# =========================================================
# FOYDALANUVCHINI SAQLASH
# =========================================================

def save_user(user):

    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, first_name, username)
        VALUES (?, ?, ?)
        """,
        (
            user.id,
            user.first_name or "",
            user.username or ""
        )
    )

    # Agar user avval mavjud bo'lsa,
    # ma'lumotlarini yangilaymiz.
    cursor.execute(
        """
        UPDATE users
        SET first_name = ?, username = ?
        WHERE user_id = ?
        """,
        (
            user.first_name or "",
            user.username or "",
            user.id
        )
    )

    conn.commit()


# =========================================================
# ADMIN TEKSHIRISH
# =========================================================

def is_admin(user_id):

    return user_id == ADMIN_ID


# =========================================================
# MAJBURIY A'ZOLIKNI TEKSHIRISH
# =========================================================

def check_membership(user_id):

    cursor.execute(
        "SELECT * FROM channels ORDER BY id"
    )

    channels = cursor.fetchall()

    not_joined = []

    for channel in channels:

        channel_id = channel[2]

        try:

            member = bot.get_chat_member(
                channel_id,
                user_id
            )

            if member.status in [
                "left",
                "kicked"
            ]:

                not_joined.append(channel)

        except Exception:

            # Bot kanalni tekshira olmasa,
            # xavfsizlik uchun a'zo emas deb hisoblaymiz.
            not_joined.append(channel)

    return not_joined


# =========================================================
# MAJBURIY KANALLAR KLAVIATURASI
# =========================================================

def membership_keyboard():

    markup = types.InlineKeyboardMarkup()

    cursor.execute(
        "SELECT * FROM channels ORDER BY id"
    )

    channels = cursor.fetchall()

    for channel in channels:

        button = types.InlineKeyboardButton(
            text=f"📢 {channel[1]}",
            url=channel[3]
        )

        markup.add(button)

    markup.add(
        types.InlineKeyboardButton(
            text="✅ Tekshirish",
            callback_data="check_membership"
        )
    )

    return markup


# =========================================================
# MAJBURIY A'ZOLIK XABARI
# =========================================================

def send_membership_message(chat_id):

    cursor.execute(
        "SELECT COUNT(*) FROM channels"
    )

    channel_count = cursor.fetchone()[0]

    if channel_count == 0:
        return False

    bot.send_message(
        chat_id,
        "🔐 UZ_Kinomaniya botidan foydalanish uchun "
        "quyidagi kanallarga a'zo bo'ling.\n\n"
        "1️⃣ Kanallarga a'zo bo'ling\n"
        "2️⃣ Keyin «✅ Tekshirish» tugmasini bosing.",
        reply_markup=membership_keyboard()
    )

    return True


# =========================================================
# FOYDALANUVCHI ASOSIY MENYUSI
# =========================================================

def user_keyboard():

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    markup.row(
        types.KeyboardButton("🎬 Barcha kinolar")
    )

    return markup


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    save_user(message.from_user)

    user_id = message.from_user.id

    not_joined = check_membership(user_id)

    if not_joined:

        send_membership_message(
            message.chat.id
        )

        return

    bot.send_message(
        message.chat.id,
        "🎬 UZ_Kinomaniya botiga xush kelibsiz!\n\n"
        "🔢 Kino kodini yuboring.\n\n"
        "Yoki pastdagi «🎬 Barcha kinolar» "
        "tugmasini bosing.",
        reply_markup=user_keyboard()
    )


# =========================================================
# A'ZOLIKNI QAYTA TEKSHIRISH
# =========================================================

@bot.callback_query_handler(
    func=lambda call: call.data == "check_membership"
)
def check_membership_button(call):

    user_id = call.from_user.id

    not_joined = check_membership(
        user_id
    )

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
        "🔢 Endi kino kodini yuboring.",
        reply_markup=user_keyboard()
    )


# =========================================================
# ADMIN MENYU
# =========================================================

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


# =========================================================
# ADMIN
# =========================================================

@bot.message_handler(commands=["admin"])
def admin_panel(message):

    if not is_admin(message.from_user.id):

        bot.send_message(
            message.chat.id,
            "❌ Siz admin emassiz."
        )

        return

    bot.send_message(
        message.chat.id,
        "👑 UZ_Kinomaniya ADMIN PANEL\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=admin_keyboard()
    )


# =========================================================
# KINO QO'SHISH
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🎬 Kino qo'shish"
)
def add_movie_start(message):

    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(
        message.chat.id,
        "🔢 Kino kodini yuboring.\n\n"
        "Masalan: 101"
    )

    bot.register_next_step_handler(
        msg,
        add_movie_code
    )


def add_movie_code(message):

    if not is_admin(message.from_user.id):
        return

    code = message.text.strip()

    if not code:

        msg = bot.send_message(
            message.chat.id,
            "❌ Kod bo'sh bo'lmasligi kerak.\n"
            "Qaytadan kod yuboring:"
        )

        bot.register_next_step_handler(
            msg,
            add_movie_code
        )

        return

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

    if not is_admin(message.from_user.id):
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


def add_movie_video(
    message,
    code,
    name
):

    if not is_admin(message.from_user.id):
        return

    if not message.video:

        msg = bot.send_message(
            message.chat.id,
            "❌ Siz video yubormadingiz.\n\n"
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
            INSERT INTO movies
            (code, name, file_id)
            VALUES (?, ?, ?)
            """,
            (
                code,
                name,
                file_id
            )
        )

        conn.commit()

        bot.send_message(
            message.chat.id,
            "✅ KINO MUVAFFAQIYATLI QO'SHILDI!\n\n"
            f"🔢 Kod: {code}\n"
            f"🎬 Nomi: {name}",
            reply_markup=admin_keyboard()
        )

    except sqlite3.IntegrityError:

        bot.send_message(
            message.chat.id,
            "❌ Bu kino kodi allaqachon mavjud!\n\n"
            "Boshqa kod tanlang."
        )


# =========================================================
# KINO O'CHIRISH
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🗑 Kino o'chirish"
)
def delete_movie_start(message):

    if not is_admin(message.from_user.id):
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

    if not is_admin(message.from_user.id):
        return

    code = message.text.strip()

    cursor.execute(
        """
        SELECT name
        FROM movies
        WHERE code = ?
        """,
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
        "✅ Kino o'chirildi!\n\n"
        f"🎬 {movie[0]}\n"
        f"🔢 Kod: {code}",
        reply_markup=admin_keyboard()
    )


# =========================================================
# ADMIN KINOLAR RO'YXATI
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📋 Kinolar"
)
def admin_movie_list(message):

    if not is_admin(message.from_user.id):
        return

    cursor.execute(
        """
        SELECT code, name
        FROM movies
        ORDER BY id DESC
        """
    )

    movies = cursor.fetchall()

    if not movies:

        bot.send_message(
            message.chat.id,
            "🎬 Hozircha kino qo'shilmagan."
        )

        return

    text = "🎬 KINOLAR RO'YXATI\n\n"

    for movie in movies:

        text += (
            f"🔢 {movie[0]} — "
            f"{movie[1]}\n"
        )

    bot.send_message(
        message.chat.id,
        text
    )


# =========================================================
# KANAL QO'SHISH
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📢 Kanal qo'shish"
)
def add_channel_start(message):

    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(
        message.chat.id,
        "📢 Kanal nomini yuboring.\n\n"
        "Masalan:\n"
        "UZ Kinomaniya"
    )

    bot.register_next_step_handler(
        msg,
        add_channel_name
    )


def add_channel_name(message):

    if not is_admin(message.from_user.id):
        return

    name = message.text.strip()

    msg = bot.send_message(
        message.chat.id,
        "🔹 Kanal username yoki ID sini yuboring.\n\n"
        "Ommaviy kanal uchun:\n"
        "@kanal_username\n\n"
        "Maxfiy kanal uchun Telegram kanal ID sini kiriting."
    )

    bot.register_next_step_handler(
        msg,
        add_channel_username,
        name
    )


def add_channel_username(
    message,
    name
):

    if not is_admin(message.from_user.id):
        return

    username = message.text.strip()

    msg = bot.send_message(
        message.chat.id,
        "🔗 Endi kanal havolasini yuboring.\n\n"
        "Masalan:\n"
        "https://t.me/kanal_username"
    )

    bot.register_next_step_handler(
        msg,
        add_channel_link,
        name,
        username
    )


def add_channel_link(
    message,
    name,
    username
):

    if not is_admin(message.from_user.id):
        return

    link = message.text.strip()

    cursor.execute(
        """
        INSERT INTO channels
        (name, username, link)
        VALUES (?, ?, ?)
        """,
        (
            name,
            username,
            link
        )
    )

    conn.commit()

    bot.send_message(
        message.chat.id,
        "✅ MAJBURIY KANAL QO'SHILDI!\n\n"
        f"📢 {name}\n"
        f"🔹 {username}",
        reply_markup=admin_keyboard()
    )


# =========================================================
# KANALLAR RO'YXATI
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📢 Kanallar"
)
def channel_list(message):

    if not is_admin(message.from_user.id):
        return

    cursor.execute(
        """
        SELECT id, name, username
        FROM channels
        ORDER BY id
        """
    )

    channels = cursor.fetchall()

    if not channels:

        bot.send_message(
            message.chat.id,
            "📢 Hozircha majburiy kanal yo'q."
        )

        return

    text = "📢 MAJBURIY KANALLAR\n\n"

    for channel in channels:

        text += (
            f"🆔 ID: {channel[0]}\n"
            f"📢 {channel[1]}\n"
            f"🔹 {channel[2]}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text
    )


# =========================================================
# KANAL O'CHIRISH
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🗑 Kanal o'chirish"
)
def delete_channel_start(message):

    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(
        message.chat.id,
        "🆔 O'chiriladigan kanal ID sini yuboring.\n\n"
        "Masalan: 1"
    )

    bot.register_next_step_handler(
        msg,
        delete_channel
    )


def delete_channel(message):

    if not is_admin(message.from_user.id):
        return

    channel_id = message.text.strip()

    cursor.execute(
        """
        SELECT name
        FROM channels
        WHERE id = ?
        """,
        (channel_id,)
    )

    channel = cursor.fetchone()

    if not channel:

        bot.send_message(
            message.chat.id,
            "❌ Bunday ID li kanal topilmadi."
        )

        return

    cursor.execute(
        """
        DELETE FROM channels
        WHERE id = ?
        """,
        (channel_id,)
    )

    conn.commit()

    bot.send_message(
        message.chat.id,
        f"✅ Kanal o'chirildi:\n"
        f"📢 {channel[0]}",
        reply_markup=admin_keyboard()
    )


# =========================================================
# STATISTIKA
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📊 Statistika"
)
def statistics(message):

    if not is_admin(message.from_user.id):
        return

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM movies"
    )

    movies = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM channels"
    )

    channels = cursor.fetchone()[0]

    bot.send_message(
        message.chat.id,
        "📊 UZ_Kinomaniya STATISTIKA\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"🎬 Kinolar: {movies}\n"
        f"📢 Majburiy kanallar: {channels}"
    )


# =========================================================
# BARCHA KINOLAR
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🎬 Barcha kinolar"
)
def all_movies(message):

    user_id = message.from_user.id

    not_joined = check_membership(
        user_id
    )

    if not_joined:

        send_membership_message(
            message.chat.id
        )

        return

    cursor.execute(
        """
        SELECT code, name
        FROM movies
        ORDER BY id DESC
        """
    )

    movies = cursor.fetchall()

    if not movies:

        bot.send_message(
            message.chat.id,
            "🎬 Hozircha hech qanday kino yo'q."
        )

        return

    # Telegram xabar uzunligini oshirib yubormaslik
    # uchun 30 tadan bo'lib chiqaramiz.

    page_size = 30

    for start_index in range(
        0,
        len(movies),
        page_size
    ):

        page_movies = movies[
            start_index:start_index + page_size
        ]

        text = (
            "🎬 BARCHA KINOLAR\n\n"
        )

        for movie in page_movies:

            text += (
                f"🔢 {movie[0]} — "
                f"{movie[1]}\n"
            )

        text += (
            "\n💡 Kino olish uchun "
            "yuqoridagi kodni yuboring."
        )

        bot.send_message(
            message.chat.id,
            text
        )


# =========================================================
# KINO KODINI QABUL QILISH
# =========================================================

@bot.message_handler(
    func=lambda message: True
)
def get_movie(message):

    user_id = message.from_user.id

    # Adminning boshqa xabarlariga tegmaymiz
    if is_admin(user_id):
        return

    save_user(
        message.from_user
    )

    not_joined = check_membership(
        user_id
    )

    if not_joined:

        send_membership_message(
            message.chat.id
        )

        return

    code = message.text.strip()

    cursor.execute(
        """
        SELECT name, file_id
        FROM movies
        WHERE code = ?
        """,
        (code,)
    )

    movie = cursor.fetchone()

    if not movie:

        bot.send_message(
            message.chat.id,
            "❌ Bunday kodli kino topilmadi.\n\n"
            "🔢 Kodni tekshirib qaytadan yuboring.\n\n"
            "🎬 Barcha kinolar tugmasi orqali "
            "mavjud kodlarni ko'rishingiz mumkin."
        )

        return

    name = movie[0]
    file_id = movie[1]

    try:

        bot.send_video(
            message.chat.id,
            file_id,
            caption=f"🎬 {name}"
        )

    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ Videoni yuborishda xatolik yuz berdi."
        )


# =========================================================
# FLASK
# =========================================================

@app.route("/")
def home():

    return "UZ_Kinomaniya bot ishlayapti!"


@app.route(
    "/webhook",
    methods=["POST"]
)
def webhook():

    json_string = (
        request
        .get_data()
        .decode("utf-8")
    )

    update = telebot.types.Update.de_json(
        json_string
    )

    bot.process_new_updates(
        [update]
    )

    return "OK"


# =========================================================
# ISHGA TUSHIRISH
# =========================================================

if __name__ == "__main__":

    render_url = os.getenv(
        "RENDER_EXTERNAL_URL"
    )

    if render_url:

        webhook_url = (
            render_url +
            "/webhook"
        )

        bot.remove_webhook()

        bot.set_webhook(
            url=webhook_url
        )

    port = int(
        os.getenv(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
