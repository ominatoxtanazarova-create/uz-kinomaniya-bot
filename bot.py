import os
import sqlite3
import telebot
from telebot import types
from flask import Flask, request


# =========================
# SOZLAMALAR
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = {
    6470817755,
    1361934945
}

RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

DB_NAME = "kino.db"


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT NOT NULL,
            link TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            file_id TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================
# YORDAMCHI FUNKSIYALAR
# =========================

def is_admin(user_id):
    return user_id in ADMIN_IDS


def save_user(user):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO users
        (user_id, first_name, username)
        VALUES (?, ?, ?)
    """, (
        user.id,
        user.first_name or "",
        user.username or ""
    ))

    conn.commit()
    conn.close()


def get_movie_by_code(code):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM movies
        WHERE code = ?
    """, (code,))

    movie = cursor.fetchone()

    conn.close()

    return movie


def get_all_movies():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM movies
        ORDER BY id DESC
    """)

    movies = cursor.fetchall()

    conn.close()

    return movies


def get_all_channels():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM channels
        ORDER BY id DESC
    """)

    channels = cursor.fetchall()

    conn.close()

    return channels


# =========================
# KLAVIATURALAR
# =========================

def user_keyboard():
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    markup.row(
        types.KeyboardButton("🎬 Barcha kinolar"),
        types.KeyboardButton("🔢 Kino kodini kiritish")
    )

    return markup


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

    markup.row(
        types.KeyboardButton("🔢 Kino kodini kiritish")
    )

    return markup


# =========================
# MAJBURIY KANALLAR
# =========================

def check_subscription(user_id):
    channels = get_all_channels()

    not_joined = []

    for channel in channels:

        try:
            member = bot.get_chat_member(
                channel["username"],
                user_id
            )

            if member.status in ["left", "kicked"]:
                not_joined.append(channel)

            elif (
                member.status == "restricted"
                and not getattr(member, "is_member", False)
            ):
                not_joined.append(channel)

        except Exception:
            not_joined.append(channel)

    return not_joined


def send_subscription_message(chat_id, not_joined):
    markup = types.InlineKeyboardMarkup()

    for channel in not_joined:

        markup.add(
            types.InlineKeyboardButton(
                text=f"📢 {channel['name']}",
                url=channel["link"]
            )
        )

    markup.add(
        types.InlineKeyboardButton(
            text="✅ Tekshirish",
            callback_data="check_subscription"
        )
    )

    bot.send_message(
        chat_id,
        "❗ Kinoni olish uchun quyidagi kanallarga a'zo bo‘ling:",
        reply_markup=markup
    )


# =========================
# /START
# =========================

@bot.message_handler(commands=["start"])
def start(message):

    save_user(message.from_user)

    if is_admin(message.from_user.id):

        bot.send_message(
            message.chat.id,
            "👑 Admin panelga xush kelibsiz!",
            reply_markup=admin_keyboard()
        )

    else:

        bot.send_message(
            message.chat.id,
            "🎬 Kino botiga xush kelibsiz!\n\n"
            "Kino olish uchun kino kodini yuboring.",
            reply_markup=user_keyboard()
        )


# =========================
# KINO KODINI KIRITISH
# =========================

def start_movie_code_input(message):

    save_user(message.from_user)

    msg = bot.send_message(
        message.chat.id,
        "🔢 Kino kodini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        process_movie_code
    )


def process_movie_code(message):

    save_user(message.from_user)

    if not message.text:
        msg = bot.send_message(
            message.chat.id,
            "❗ Kino kodini matn ko‘rinishida yuboring."
        )

        bot.register_next_step_handler(
            msg,
            process_movie_code
        )

        return

    code = message.text.strip()

    movie = get_movie_by_code(code)

    # KINO MAVJUD EMAS
    if movie is None:

        if is_admin(message.from_user.id):
            keyboard = admin_keyboard()
        else:
            keyboard = user_keyboard()

        bot.send_message(
            message.chat.id,
            "❌ Bunday kodli kino mavjud emas.",
            reply_markup=keyboard
        )

        return

    # ADMIN BO‘LSA MAJBURIY KANAL TEKSHIRILMAYDI
    if is_admin(message.from_user.id):

        bot.send_video(
            message.chat.id,
            movie["file_id"],
            caption=(
                f"🎬 {movie['name']}\n"
                f"🔢 Kod: {movie['code']}"
            ),
            reply_markup=admin_keyboard()
        )

        return

    # ODDIY USER UCHUN KANAL TEKSHIRISH
    not_joined = check_subscription(
        message.from_user.id
    )

    if not_joined:

        send_subscription_message(
            message.chat.id,
            not_joined
        )

        return

    # KINO YUBORISH
    bot.send_video(
        message.chat.id,
        movie["file_id"],
        caption=(
            f"🎬 {movie['name']}\n"
            f"🔢 Kod: {movie['code']}"
        ),
        reply_markup=user_keyboard()
    )


# =========================
# KINO KODI TUGMASI
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "🔢 Kino kodini kiritish"
)
def movie_code_button(message):

    start_movie_code_input(message)


# =========================
# BARCHA KINOLAR
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "🎬 Barcha kinolar"
)
def all_movies(message):

    save_user(message.from_user)

    movies = get_all_movies()

    if not movies:

        bot.send_message(
            message.chat.id,
            "❌ Hozircha kinolar mavjud emas.",
            reply_markup=user_keyboard()
        )

        return

    text = "🎬 <b>Barcha kinolar:</b>\n\n"

    for movie in movies:

        text += (
            f"🔢 <b>{movie['code']}</b> — "
            f"{movie['name']}\n"
        )

    text += "\n📌 Kino olish uchun kodini yuboring."

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=user_keyboard()
    )


# =========================
# ADMIN - KINO QO‘SHISH
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "🎬 Kino qo‘shish"
    and is_admin(message.from_user.id)
)
def add_movie_button(message):

    msg = bot.send_message(
        message.chat.id,
        "🎬 Kino kodini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        add_movie_code
    )


def add_movie_code(message):

    code = message.text.strip()

    if not code:

        msg = bot.send_message(
            message.chat.id,
            "❗ Kod bo‘sh bo‘lishi mumkin emas.\n"
            "Kino kodini yuboring:"
        )

        bot.register_next_step_handler(
            msg,
            add_movie_code
        )

        return

    existing = get_movie_by_code(code)

    if existing:

        msg = bot.send_message(
            message.chat.id,
            "❌ Bu kod allaqachon mavjud.\n\n"
            "Boshqa kod yuboring:"
        )

        bot.register_next_step_handler(
            msg,
            add_movie_code
        )

        return

    msg = bot.send_message(
        message.chat.id,
        "🎬 Endi kino nomini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        add_movie_name,
        code
    )


def add_movie_name(message, code):

    name = message.text.strip()

    if not name:

        msg = bot.send_message(
            message.chat.id,
            "❗ Kino nomi bo‘sh bo‘lishi mumkin emas."
        )

        bot.register_next_step_handler(
            msg,
            add_movie_name,
            code
        )

        return

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

    if not message.video:

        msg = bot.send_message(
            message.chat.id,
            "❗ Iltimos, kino videosini yuboring."
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

        conn = get_db()
        cursor = conn.cursor()

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
        conn.close()

        bot.send_message(
            message.chat.id,
            "✅ Kino muvaffaqiyatli qo‘shildi!\n\n"
            f"🔢 Kod: {code}\n"
            f"🎬 Nomi: {name}",
            reply_markup=admin_keyboard()
        )

    except sqlite3.IntegrityError:

        bot.send_message(
            message.chat.id,
            "❌ Bu kino kodi allaqachon mavjud.",
            reply_markup=admin_keyboard()
        )


# =========================
# ADMIN - KINOLAR RO‘YXATI
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "📋 Kinolar ro‘yxati"
    and is_admin(message.from_user.id)
)
def admin_movies_list(message):

    movies = get_all_movies()

    if not movies:

        bot.send_message(
            message.chat.id,
            "❌ Hozircha kino mavjud emas.",
            reply_markup=admin_keyboard()
        )

        return

    text = "📋 <b>Kinolar ro‘yxati:</b>\n\n"

    for movie in movies:

        text += (
            f"🆔 ID: {movie['id']}\n"
            f"🔢 Kod: <b>{movie['code']}</b>\n"
            f"🎬 Nomi: {movie['name']}\n"
            f"━━━━━━━━━━━━\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


# =========================
# ADMIN - KINO O‘CHIRISH
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "🗑 Kino o‘chirish"
    and is_admin(message.from_user.id)
)
def delete_movie_button(message):

    msg = bot.send_message(
        message.chat.id,
        "🗑 O‘chiriladigan kino kodini yuboring:"
    )

    bot.register_next_step_handler(
        msg,
        delete_movie
    )


def delete_movie(message):

    code = message.text.strip()

    movie = get_movie_by_code(code)

    if movie is None:

        bot.send_message(
            message.chat.id,
            "❌ Bunday kodli kino topilmadi.",
            reply_markup=admin_keyboard()
        )

        return

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM movies
        WHERE code = ?
    """, (code,))

    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        "✅ Kino o‘chirildi!\n\n"
        f"🔢 Kod: {code}\n"
        f"🎬 Nomi: {movie['name']}",
        reply_markup=admin_keyboard()
    )


# =========================
# ADMIN - KANAL QO‘SHISH
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "📢 Kanal qo‘shish"
    and is_admin(message.from_user.id)
)
def add_channel_button(message):

    msg = bot.send_message(
        message.chat.id,
        "📢 Kanal username yoki ID sini yuboring.\n\n"
        "Masalan:\n"
        "@kanal_nomi\n\n"
        "Bot kanal ichida ADMIN bo‘lishi kerak."
    )

    bot.register_next_step_handler(
        msg,
        add_channel
    )


def add_channel(message):

    username = message.text.strip()

    if not username:

        bot.send_message(
            message.chat.id,
            "❌ Kanal ma'lumoti kiritilmadi.",
            reply_markup=admin_keyboard()
        )

        return

    try:

        chat = bot.get_chat(username)

        # Botning kanal ichidagi holatini tekshirish
        me = bot.get_me()

        bot_member = bot.get_chat_member(
            chat.id,
            me.id
        )

        if bot_member.status not in [
            "administrator",
            "creator"
        ]:

            bot.send_message(
                message.chat.id,
                "❌ Bot ushbu kanalda ADMIN emas.\n\n"
                "Avval botni kanalga administrator qilib qo‘shing.",
                reply_markup=admin_keyboard()
            )

            return

        channel_name = chat.title or username

        # Tekshirish uchun haqiqiy chat ID saqlanadi
        channel_id = str(chat.id)

        # Link
        if getattr(chat, "username", None):

            link = f"https://t.me/{chat.username}"

        else:

            bot.send_message(
                message.chat.id,
                "❌ Bu kanal uchun public username topilmadi.\n\n"
                "Private kanal bo‘lsa, kanalning invite linkini yuborish tizimi kerak bo‘ladi.",
                reply_markup=admin_keyboard()
            )

            return

        # Oldindan qo‘shilganligini tekshirish
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM channels
            WHERE username = ?
        """, (channel_id,))

        existing = cursor.fetchone()

        if existing:

            conn.close()

            bot.send_message(
                message.chat.id,
                "❌ Bu kanal allaqachon qo‘shilgan.",
                reply_markup=admin_keyboard()
            )

            return

        cursor.execute("""
            INSERT INTO channels
            (name, username, link)
            VALUES (?, ?, ?)
        """, (
            channel_name,
            channel_id,
            link
        ))

        conn.commit()
        conn.close()

        bot.send_message(
            message.chat.id,
            "✅ Majburiy kanal qo‘shildi!\n\n"
            f"📢 Kanal: {channel_name}\n"
            f"🔗 {link}",
            reply_markup=admin_keyboard()
        )

    except Exception as e:

        print("KANAL QO‘SHISH XATOSI:", e)

        bot.send_message(
            message.chat.id,
            "❌ Kanalni qo‘shib bo‘lmadi.\n\n"
            "Username to‘g‘ri ekanini va bot kanalga admin "
            "qilinganini tekshiring.",
            reply_markup=admin_keyboard()
        )


# =========================
# ADMIN - KANALLAR RO‘YXATI
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "📢 Kanallar ro‘yxati"
    and is_admin(message.from_user.id)
)
def channels_list(message):

    channels = get_all_channels()

    if not channels:

        bot.send_message(
            message.chat.id,
            "❌ Hozircha majburiy kanallar mavjud emas.",
            reply_markup=admin_keyboard()
        )

        return

    text = "📢 <b>Majburiy kanallar:</b>\n\n"

    for channel in channels:

        text += (
            f"🆔 ID: {channel['id']}\n"
            f"📢 {channel['name']}\n"
            f"🔗 {channel['link']}\n"
            f"━━━━━━━━━━━━\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


# =========================
# ADMIN - KANAL O‘CHIRISH
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "🗑 Kanal o‘chirish"
    and is_admin(message.from_user.id)
)
def delete_channel_button(message):

    msg = bot.send_message(
        message.chat.id,
        "🗑 O‘chiriladigan kanal ID sini yuboring.\n\n"
        "ID ni '📢 Kanallar ro‘yxati' bo‘limidan ko‘rishingiz mumkin."
    )

    bot.register_next_step_handler(
        msg,
        delete_channel
    )


def delete_channel(message):

    try:
        channel_id = int(message.text.strip())
    except:
        bot.send_message(
            message.chat.id,
            "❌ ID noto‘g‘ri.",
            reply_markup=admin_keyboard()
        )
        return

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM channels
        WHERE id = ?
    """, (channel_id,))

    channel = cursor.fetchone()

    if channel is None:

        conn.close()

        bot.send_message(
            message.chat.id,
            "❌ Bunday kanal topilmadi.",
            reply_markup=admin_keyboard()
        )

        return

    cursor.execute("""
        DELETE FROM channels
        WHERE id = ?
    """, (channel_id,))

    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        "✅ Kanal o‘chirildi!\n\n"
        f"📢 {channel['name']}",
        reply_markup=admin_keyboard()
    )


# =========================
# STATISTIKA
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "📊 Statistika"
    and is_admin(message.from_user.id)
)
def statistics(message):

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM movies")
    movies_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM channels")
    channels_count = cursor.fetchone()[0]

    conn.close()

    text = (
        "📊 <b>BOT STATISTIKASI</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users_count}</b>\n"
        f"🎬 Kinolar: <b>{movies_count}</b>\n"
        f"📢 Majburiy kanallar: <b>{channels_count}</b>"
    )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML",
        reply_markup=admin_keyboard()
    )


# =========================
# OBUNA TEKSHIRISH
# =========================

@bot.callback_query_handler(
    func=lambda call:
    call.data == "check_subscription"
)
def check_subscription_callback(call):

    user_id = call.from_user.id

    not_joined = check_subscription(user_id)

    if not_joined:

        bot.answer_callback_query(
            call.id,
            "❌ Hali barcha kanallarga a'zo bo‘lmagansiz.",
            show_alert=True
        )

        send_subscription_message(
            call.message.chat.id,
            not_joined
        )

        return

    bot.answer_callback_query(
        call.id,
        "✅ Obuna tasdiqlandi!"
    )

    bot.send_message(
        call.message.chat.id,
        "✅ Barcha kanallarga a'zo bo‘lgansiz.\n\n"
        "🔢 Endi kino kodini yuboring:",
        reply_markup=user_keyboard()
    )


# =========================
# ODDIY USER KOD YUBORSA
# =========================

USER_BUTTONS = {
    "🎬 Barcha kinolar",
    "🔢 Kino kodini kiritish"
}


@bot.message_handler(
    func=lambda message:
    (
        message.text is not None
        and not is_admin(message.from_user.id)
        and message.text not in USER_BUTTONS
    )
)
def user_direct_code(message):

    process_movie_code(message)


# =========================
# ADMIN PANELDAGI BEGONA MATNLAR
# =========================

@bot.message_handler(
    func=lambda message:
    (
        message.text is not None
        and is_admin(message.from_user.id)
        and message.text not in {
            "🎬 Kino qo‘shish",
            "🗑 Kino o‘chirish",
            "📋 Kinolar ro‘yxati",
            "📢 Kanal qo‘shish",
            "🗑 Kanal o‘chirish",
            "📢 Kanallar ro‘yxati",
            "📊 Statistika",
            "🔢 Kino kodini kiritish"
        }
    )
)
def admin_unknown_message(message):

    bot.send_message(
        message.chat.id,
        "👑 Admin paneldan kerakli bo‘limni tanlang.",
        reply_markup=admin_keyboard()
    )


# =========================
# FLASK WEBHOOK
# =========================

@app.route("/")
def home():
    return "Bot ishlayapti!"


@app.route("/webhook", methods=["POST"])
def webhook():

    json_string = request.get_data().decode("utf-8")

    update = telebot.types.Update.de_json(
        json_string
    )

    bot.process_new_updates([update])

    return "OK"


# =========================
# WEBHOOKNI O‘RNATISH
# =========================

if __name__ == "__main__":

    if RENDER_EXTERNAL_URL:

        webhook_url = (
            RENDER_EXTERNAL_URL.rstrip("/")
            + "/webhook"
        )

        try:
            bot.remove_webhook()
            bot.set_webhook(
                url=webhook_url
            )

            print(
                "Webhook o‘rnatildi:",
                webhook_url
            )

        except Exception as e:

            print(
                "Webhook xatosi:",
                e
            )

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
