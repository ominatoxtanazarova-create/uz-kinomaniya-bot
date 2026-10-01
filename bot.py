import os
import sqlite3
import telebot
from telebot import types
from flask import Flask, request

# =========================================================
# SOZLAMALAR
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

# 2 TA ADMIN
ADMIN_IDS = [
    6470817755,
    1361934945
]

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
# ADMIN TEKSHIRISH
# =========================================================

def is_admin(user_id):
    return user_id in ADMIN_IDS


# =========================================================
# FOYDALANUVCHINI SAQLASH
# =========================================================

def save_user(user):

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (user_id, first_name, username)
        VALUES (?, ?, ?)
    """, (
        user.id,
        user.first_name or "",
        user.username or ""
    ))

    cursor.execute("""
        UPDATE users
        SET first_name = ?, username = ?
        WHERE user_id = ?
    """, (
        user.first_name or "",
        user.username or "",
        user.id
    ))

    conn.commit()


# =========================================================
# FOYDALANUVCHI MENYUSI
# =========================================================

def user_keyboard():

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    markup.row(
        types.KeyboardButton("🎬 Barcha kinolar"),
        types.KeyboardButton("🔢 Kino kodini kiritish")
    )

    return markup


# =========================================================
# ADMIN MENYUSI
# =========================================================

def admin_keyboard():

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    markup.row(
        types.KeyboardButton("🎬 Kino qo‘shish"),
        types.KeyboardButton("🗑 Kino o‘chirish")
    )

    markup.row(
        types.KeyboardButton("📋 Kinolar ro‘yxati")
    )

    markup.row(
        types.KeyboardButton("📢 Kanal qo‘shish"),
        types.KeyboardButton("🗑 Kanal o‘chirish")
    )

    markup.row(
        types.KeyboardButton("📢 Kanallar ro‘yxati")
    )

    markup.row(
        types.KeyboardButton("📊 Statistika")
    )

    return markup


# =========================================================
# MAJBURIY KANALLARNI OLISH
# =========================================================

def get_channels():

    cursor.execute("""
        SELECT id, name, username, link
        FROM channels
        ORDER BY id
    """)

    return cursor.fetchall()


# =========================================================
# A'ZOLIKNI TEKSHIRISH
# =========================================================

def check_membership(user_id):

    channels = get_channels()

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
# KANALLAR KLAVIATURASI
# =========================================================

def membership_keyboard():

    markup = types.InlineKeyboardMarkup()

    channels = get_channels()

    for channel in channels:

        markup.add(
            types.InlineKeyboardButton(
                text=f"📢 {channel[1]}",
                url=channel[3]
            )
        )

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

    channels = get_channels()

    if not channels:
        return False

    bot.send_message(
        chat_id,
        "🔐 Botdan foydalanish uchun quyidagi "
        "kanallarga a'zo bo‘ling.\n\n"
        "1️⃣ Barcha kanallarga a'zo bo‘ling\n"
        "2️⃣ «✅ Tekshirish» tugmasini bosing.",
        reply_markup=membership_keyboard()
    )

    return True


# =========================================================
# KINO KODINI SO'RASH
# =========================================================

def ask_movie_code(chat_id):

    bot.send_message(
        chat_id,
        "🔢 Kino kodini yuboring:",
        reply_markup=user_keyboard()
    )


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    save_user(message.from_user)

    user_id = message.from_user.id

    # Admin
    if is_admin(user_id):

        bot.send_message(
            message.chat.id,
            "👑 UZ_Kinomaniya botiga xush kelibsiz!\n\n"
            "Admin panelga kirish uchun /admin ni bosing.",
            reply_markup=admin_keyboard()
        )

        return

    # Oddiy foydalanuvchi
    not_joined = check_membership(user_id)

    if not_joined:

        send_membership_message(
            message.chat.id
        )

        return

    bot.send_message(
        message.chat.id,
        "🎬 UZ_Kinomaniya botiga xush kelibsiz!\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=user_keyboard()
    )


# =========================================================
# MAJBURIY A'ZOLIKNI TEKSHIRISH
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
            "❌ Hali barcha kanallarga a'zo bo‘lmagansiz!",
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
        "Endi kino kodini yuborishingiz mumkin.",
        reply_markup=user_keyboard()
    )


# =========================================================
# ADMIN PANEL
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
        "Kerakli bo‘limni tanlang:",
        reply_markup=admin_keyboard()
    )


# =========================================================
# KINO QO'SHISH
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🎬 Kino qo‘shish"
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

    if not message.text:

        msg = bot.send_message(
            message.chat.id,
            "❌ Kod noto‘g‘ri.\n"
            "Qaytadan kod yuboring:"
        )

        bot.register_next_step_handler(
            msg,
            add_movie_code
        )

        return

    code = message.text.strip()

    # Kod oldindan mavjudligini tekshirish
    cursor.execute(
        "SELECT id FROM movies WHERE code = ?",
        (code,)
    )

    if cursor.fetchone():

        msg = bot.send_message(
            message.chat.id,
            "❌ Bu kino kodi allaqachon mavjud!\n\n"
            "Boshqa kod yuboring:"
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

    if not message.text:

        msg = bot.send_message(
            message.chat.id,
            "❌ Kino nomi bo‘sh bo‘lmasligi kerak.\n"
            "Qaytadan yuboring:"
        )

        bot.register_next_step_handler(
            msg,
            add_movie_name,
            code
        )

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

    if not is_admin(message.from_user.id):
        return

    if not message.video:

        msg = bot.send_message(
            message.chat.id,
            "❌ Video yuborilmadi.\n\n"
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

        cursor.execute("""
            INSERT INTO movies
            (code, name, file_id)
            VALUES (?, ?, ?)
        """, (
            code,
            name,
            file_id
        ))

        conn.commit()

        bot.send_message(
            message.chat.id,
            "✅ KINO MUVAFFAQIYATLI QO‘SHILDI!\n\n"
            f"🔢 Kod: {code}\n"
            f"🎬 Nomi: {name}",
            reply_markup=admin_keyboard()
        )

    except sqlite3.IntegrityError:

        bot.send_message(
            message.chat.id,
            "❌ Bu kod allaqachon mavjud!",
            reply_markup=admin_keyboard()
        )


# =========================================================
# KINO O'CHIRISH
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🗑 Kino o‘chirish"
)
def delete_movie_start(message):

    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(
        message.chat.id,
        "🔢 O‘chiriladigan kino kodini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        delete_movie
    )


def delete_movie(message):

    if not is_admin(message.from_user.id):
        return

    if not message.text:
        return

    code = message.text.strip()

    cursor.execute("""
        SELECT name
        FROM movies
        WHERE code = ?
    """, (code,))

    movie = cursor.fetchone()

    if not movie:

        bot.send_message(
            message.chat.id,
            "❌ Bunday kodli kino topilmadi.",
            reply_markup=admin_keyboard()
        )

        return

    cursor.execute(
        "DELETE FROM movies WHERE code = ?",
        (code,)
    )

    conn.commit()

    bot.send_message(
        message.chat.id,
        "✅ Kino o‘chirildi!\n\n"
        f"🎬 {movie[0]}\n"
        f"🔢 Kod: {code}",
        reply_markup=admin_keyboard()
    )


# =========================================================
# KINOLAR RO'YXATI
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📋 Kinolar ro‘yxati"
)
def admin_movie_list(message):

    if not is_admin(message.from_user.id):
        return

    cursor.execute("""
        SELECT code, name
        FROM movies
        ORDER BY id DESC
    """)

    movies = cursor.fetchall()

    if not movies:

        bot.send_message(
            message.chat.id,
            "🎬 Hozircha kino qo‘shilmagan.",
            reply_markup=admin_keyboard()
        )

        return

    text = "🎬 KINOLAR RO‘YXATI\n\n"

    for movie in movies:

        text += (
            f"🔢 {movie[0]} — {movie[1]}\n"
        )

    # Juda uzun xabarlarni bo‘lib yuborish
    max_length = 3800

    for i in range(
        0,
        len(text),
        max_length
    ):

        bot.send_message(
            message.chat.id,
            text[i:i + max_length]
        )


# =========================================================
# KANAL QO'SHISH
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📢 Kanal qo‘shish"
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

    if not message.text:
        return

    name = message.text.strip()

    msg = bot.send_message(
        message.chat.id,
        "🔹 Kanal username yoki ID sini yuboring.\n\n"
        "Ommaviy kanal:\n"
        "@kanal_username\n\n"
        "Masalan:\n"
        "@uz_kinomaniya"
    )

    bot.register_next_step_handler(
        msg,
        add_channel_username,
        name
    )


def add_channel_username(message, name):

    if not is_admin(message.from_user.id):
        return

    if not message.text:
        return

    username = message.text.strip()

    msg = bot.send_message(
        message.chat.id,
        "🔗 Endi kanal havolasini yuboring.\n\n"
        "Masalan:\n"
        "https://t.me/uz_kinomaniya"
    )

    bot.register_next_step_handler(
        msg,
        add_channel_link,
        name,
        username
    )


def add_channel_link(message, name, username):

    if not is_admin(message.from_user.id):
        return

    if not message.text:
        return

    link = message.text.strip()

    # Kanalni bot tekshira olishini tekshirish
    try:

        chat = bot.get_chat(username)

        # Botning kanalga adminligini tekshirish
        bot_member = bot.get_chat_member(
            chat.id,
            bot.get_me().id
        )

        if bot_member.status not in [
            "administrator",
            "creator"
        ]:

            bot.send_message(
                message.chat.id,
                "❌ Bot bu kanalda administrator emas!\n\n"
                "Avval botni kanalga administrator qilib qo‘ying."
            )

            return

    except Exception as e:

        bot.send_message(
            message.chat.id,
            "❌ Kanalni tekshirib bo‘lmadi.\n\n"
            "Quyidagilarni tekshiring:\n"
            "• Kanal username to‘g‘ri yozilganmi?\n"
            "• Bot kanalga qo‘shilganmi?\n"
            "• Bot kanalga administrator qilinganmi?"
        )

        return

    cursor.execute("""
        INSERT INTO channels
        (name, username, link)
        VALUES (?, ?, ?)
    """, (
        name,
        username,
        link
    ))

    conn.commit()

    bot.send_message(
        message.chat.id,
        "✅ MAJBURIY KANAL QO‘SHILDI!\n\n"
        f"📢 {name}\n"
        f"🔹 {username}\n"
        f"🔗 {link}",
        reply_markup=admin_keyboard()
    )


# =========================================================
# KANALLAR RO'YXATI
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📢 Kanallar ro‘yxati"
)
def channel_list(message):

    if not is_admin(message.from_user.id):
        return

    channels = get_channels()

    if not channels:

        bot.send_message(
            message.chat.id,
            "📢 Hozircha majburiy kanal yo‘q.",
            reply_markup=admin_keyboard()
        )

        return

    text = "📢 MAJBURIY KANALLAR\n\n"

    for channel in channels:

        text += (
            f"🆔 ID: {channel[0]}\n"
            f"📢 {channel[1]}\n"
            f"🔹 {channel[2]}\n"
            f"🔗 {channel[3]}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=admin_keyboard()
    )


# =========================================================
# KANAL O'CHIRISH
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🗑 Kanal o‘chirish"
)
def delete_channel_start(message):

    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(
        message.chat.id,
        "🆔 O‘chiriladigan kanal ID sini yuboring.\n\n"
        "Masalan: 1"
    )

    bot.register_next_step_handler(
        msg,
        delete_channel
    )


def delete_channel(message):

    if not is_admin(message.from_user.id):
        return

    if not message.text:
        return

    channel_id = message.text.strip()

    cursor.execute("""
        SELECT name
        FROM channels
        WHERE id = ?
    """, (channel_id,))

    channel = cursor.fetchone()

    if not channel:

        bot.send_message(
            message.chat.id,
            "❌ Bunday ID li kanal topilmadi.",
            reply_markup=admin_keyboard()
        )

        return

    cursor.execute("""
        DELETE FROM channels
        WHERE id = ?
    """, (channel_id,))

    conn.commit()

    bot.send_message(
        message.chat.id,
        "✅ Kanal o‘chirildi!\n\n"
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
        f"📢 Majburiy kanallar: {channels}",
        reply_markup=admin_keyboard()
    )


# =========================================================
# BARCHA KINOLAR
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🎬 Barcha kinolar"
)
def all_movies(message):

    save_user(message.from_user)

    user_id = message.from_user.id

    # Admin bo‘lsa admin panelga tegmaymiz
    if is_admin(user_id):
        return

    not_joined = check_membership(
        user_id
    )

    if not_joined:

        send_membership_message(
            message.chat.id
        )

        return

    cursor.execute("""
        SELECT code, name
        FROM movies
        ORDER BY id DESC
    """)

    movies = cursor.fetchall()

    if not movies:

        bot.send_message(
            message.chat.id,
            "🎬 Hozircha hech qanday kino yo‘q.",
            reply_markup=user_keyboard()
        )

        return

    page_size = 30

    for start_index in range(
        0,
        len(movies),
        page_size
    ):

        page_movies = movies[
            start_index:start_index + page_size
        ]

        text = "🎬 BARCHA KINOLAR\n\n"

        for movie in page_movies:

            text += (
                f"🔢 {movie[0]} — {movie[1]}\n"
            )

        text += (
            "\n💡 Kino olish uchun "
            "«🔢 Kino kodini kiritish» tugmasini bosing."
        )

        bot.send_message(
            message.chat.id,
            text,
            reply_markup=user_keyboard()
        )


# =========================================================
# KINO KODINI KIRITISH TUGMASI
# =========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🔢 Kino kodini kiritish"
)
def movie_code_button(message):

    save_user(message.from_user)

    if is_admin(message.from_user.id):
        return

    not_joined = check_membership(
        message.from_user.id
    )

    if not_joined:

        send_membership_message(
            message.chat.id
        )

        return

    bot.send_message(
        message.chat.id,
        "🔢 Kino kodini yuboring:",
        reply_markup=user_keyboard()
    )


# =========================================================
# KINO KODINI QABUL QILISH
# =========================================================

@bot.message_handler(
    func=lambda message: True
)
def get_movie(message):

    user_id = message.from_user.id

    # Admin uchun oddiy xabarlarni o'tkazib yuboramiz
    if is_admin(user_id):
        return

    save_user(
        message.from_user
    )

    if not message.text:
        return

    code = message.text.strip()

    # Avval kod mavjudligini tekshiramiz
    cursor.execute("""
        SELECT name, file_id
        FROM movies
        WHERE code = ?
    """, (code,))

    movie = cursor.fetchone()

    # Kod mavjud bo'lmasa
    if not movie:

        bot.send_message(
            message.chat.id,
            "❌ Bunday kodli kino mavjud emas.\n\n"
            "🔢 Kino kodini tekshirib qaytadan yuboring.\n\n"
            "🎬 Mavjud kinolarni ko‘rish uchun "
            "«🎬 Barcha kinolar» tugmasini bosing.",
            reply_markup=user_keyboard()
        )

        return

    # Kino mavjud bo'lsa, kanal a'zoligini tekshiramiz
    not_joined = check_membership(
        user_id
    )

    if not_joined:

        send_membership_message(
            message.chat.id
        )

        return

    name = movie[0]
    file_id = movie[1]

    try:

        bot.send_video(
            message.chat.id,
            file_id,
            caption=f"🎬 {name}",
            reply_markup=user_keyboard()
        )

    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ Videoni yuborishda xatolik yuz berdi.",
            reply_markup=user_keyboard()
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
            render_url.rstrip("/") +
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
