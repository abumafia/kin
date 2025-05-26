import telebot
from telebot import types
import sqlite3
import logging
from flask import Flask, request, abort

API_TOKEN = '8033496372:AAHXsgkyxXq-5ohiH6Gao355ZefY9Vxr0Xc'  # Muhit o'zgaruvchi sifatida olib ishlatish tavsiya qilinadi
ADMIN_ID = 6606638731

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

def get_db_connection():
    # Har so'rov uchun alohida ulanish (thread-safe)
    conn = sqlite3.connect("kinolar.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/", methods=["GET"])
def index():
    return "Bot ishlayapti ✅"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('/add (faqat admin uchun)')  # Kino qo'shish uchun admin komandasi
    markup.add(btn1)
    bot.send_message(message.chat.id, "Salom! Kinolarni qidirish uchun Kodlardan foydalaning: misol: ```123abc```", reply_markup=markup)

@bot.message_handler(commands=['add'])
def add_kino(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Sizda bu komanda uchun ruxsat yo'q.")
        return
    bot.send_message(message.chat.id,
                     "🎥 Kino videosini yuboring. Caption format:\n\n<code>kod|nom|tavsif|muallif|manba</code>",
                     parse_mode="HTML")

@bot.message_handler(content_types=['video'])
def save_video(message):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.caption or '|' not in message.caption:
        bot.send_message(message.chat.id,
                         "❌ Format noto‘g‘ri. To‘g‘ri format:\n<code>kod|nom|tavsif|muallif|manba</code>",
                         parse_mode="HTML")
        return
    try:
        parts = message.caption.split('|')
        if len(parts) != 5:
            bot.send_message(message.chat.id,
                             "❌ Format noto‘g‘ri. To‘g‘ri format:\n<code>kod|nom|tavsif|muallif|manba</code>",
                             parse_mode="HTML")
            return

        kod, nom, tavsif, muallif, manba = [p.strip() for p in parts]
        fayl_id = message.video.file_id

        conn = get_db_connection()
        with conn:
            conn.execute("INSERT INTO kinolar (kod, nom, tavsif, muallif, manba, fayl_id) VALUES (?, ?, ?, ?, ?, ?)",
                         (kod, nom, tavsif, muallif, manba, fayl_id))
        conn.close()
        logging.info(f"Kino saqlandi: kod={kod}, nom={nom}")
        bot.send_message(message.chat.id, "✅ Kino muvaffaqiyatli saqlandi.")
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, "❌ Bu kod allaqachon mavjud.")
    except Exception as e:
        logging.error(f"Kino qo‘shishda xatolik: {e}")
        bot.send_message(message.chat.id, "❌ Xatolik yuz berdi.")

@bot.message_handler(func=lambda m: True)
def get_kino(message):
    kod = message.text.strip()
    try:
        conn = get_db_connection()
        cur = conn.execute("SELECT * FROM kinolar WHERE kod=?", (kod,))
        kino = cur.fetchone()
        conn.close()

        if kino:
            nom = kino["nom"]
            tavsif = kino["tavsif"]
            muallif = kino["muallif"]
            manba = kino["manba"]
            fayl_id = kino["fayl_id"]

            caption = f"🎬 <b>{nom}</b>\n📝 {tavsif}\n👤 {muallif}\n🌐 {manba}"
            bot.send_video(message.chat.id, fayl_id, caption=caption, parse_mode="HTML")
            logging.info(f"Kino yuborildi: kod={kod}")
        else:
            bot.send_message(message.chat.id, "❌ Bunday kodga ega kino topilmadi.")
            logging.info(f"Kino topilmadi: kod={kod}")
    except Exception as e:
        logging.error(f"Kino olishda xatolik: {e}")
        bot.send_message(message.chat.id, "❌ Ma'lumot olishda xatolik yuz berdi.")

@bot.message_handler(commands=['delete'])
def delete_kino(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Sizda bu komanda uchun ruxsat yo'q.")
        return
    bot.send_message(message.chat.id, "🗑 Qaysi kodga ega kinoni o‘chirmoqchisiz?")
    bot.register_next_step_handler(message, confirm_delete)

def confirm_delete(message):
    kod = message.text.strip()
    conn = get_db_connection()
    cur = conn.execute("SELECT * FROM kinolar WHERE kod=?", (kod,))
    kino = cur.fetchone()
    if kino:
        with conn:
            conn.execute("DELETE FROM kinolar WHERE kod=?", (kod,))
        bot.send_message(message.chat.id, f"✅ Kino o‘chirildi: {kod}")
    else:
        bot.send_message(message.chat.id, "❌ Bunday kod topilmadi.")
    conn.close()

@bot.message_handler(commands=['elon'])
def ask_elon_type(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Sizda bu komanda uchun ruxsat yo'q.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🖼 Rasm bilan", "🎥 Video bilan", "✉️ Faqat matn")
    bot.send_message(message.chat.id, "📢 Qanday turdagi e'lon yubormoqchisiz?", reply_markup=markup)
    bot.register_next_step_handler(message, get_elon_data)

def get_elon_data(message):
    tip = message.text
    if tip == "🖼 Rasm bilan":
        bot.send_message(message.chat.id, "🖼 Rasm va caption yuboring.\nFormat:\n`Matn|Tugma matni|Havola`", parse_mode="Markdown")
        bot.register_next_step_handler(message, handle_elon_photo)
    elif tip == "🎥 Video bilan":
        bot.send_message(message.chat.id, "🎥 Video va caption yuboring.\nFormat:\n`Matn|Tugma matni|Havola`", parse_mode="Markdown")
        bot.register_next_step_handler(message, handle_elon_video)
    elif tip == "✉️ Faqat matn":
        bot.send_message(message.chat.id, "✍️ Matn, tugma matni va havola yuboring:\n`Matn|Tugma matni|Havola`", parse_mode="Markdown")
        bot.register_next_step_handler(message, handle_elon_text)
    else:
        bot.send_message(message.chat.id, "❌ Noto‘g‘ri tanlov.")

def parse_caption(caption):
    parts = caption.split("|")
    if len(parts) != 3:
        return None, None, None
    return parts[0].strip(), parts[1].strip(), parts[2].strip()

def handle_elon_photo(message):
    if not message.photo or not message.caption:
        bot.send_message(message.chat.id, "❌ Iltimos rasm va caption yuboring.")
        return
    text, btn_text, url = parse_caption(message.caption)
    if not text:
        bot.send_message(message.chat.id, "❌ Format noto‘g‘ri.")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(btn_text, url=url))
    bot.send_photo(message.chat.id, message.photo[-1].file_id, caption=text, parse_mode="HTML", reply_markup=markup)

def handle_elon_video(message):
    if not message.video or not message.caption:
        bot.send_message(message.chat.id, "❌ Iltimos video va caption yuboring.")
        return
    text, btn_text, url = parse_caption(message.caption)
    if not text:
        bot.send_message(message.chat.id, "❌ Format noto‘g‘ri.")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(btn_text, url=url))
    bot.send_video(message.chat.id, message.video.file_id, caption=text, parse_mode="HTML", reply_markup=markup)

def handle_elon_text(message):
    text, btn_text, url = parse_caption(message.text)
    if not text:
        bot.send_message(message.chat.id, "❌ Format noto‘g‘ri.")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(btn_text, url=url))
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

@app.route('/webhook/' + API_TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

if __name__ == "__main__":
    # Webhook URL ni o'zgartiring (Sizning domeningiz)
    WEBHOOK_URL = 'https://kin-r12q.onrender.com/webhook/' + API_TOKEN

    # Telegram botga webhookni o'rnatamiz
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    app.run(host="0.0.0.0", port=5000)
