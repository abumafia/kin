import telebot
from telebot import types
import sqlite3
import logging
from flask import Flask, request, abort

API_TOKEN = '8033496372:AAHXsgkyxXq-5ohiH6Gao355ZefY9Vxr0Xc'
ADMIN_ID = 6606638731

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('/add (faqat admin uchun)')       # Kino qo'shish uchun admin komandasi
    markup.add(btn1)
    bot.send_message(message.chat.id, "Salom! Kinolarni qidirish uchun Kodlardan foydalaning: misol: ```123abc```", reply_markup=markup)

# Baza ulanish (global)
conn = sqlite3.connect("kinolar.db", check_same_thread=False)

# Jadvalni yaratish (faqat bir marta)
with conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS kinolar (
        kod TEXT PRIMARY KEY,
        nom TEXT,
        tavsif TEXT,
        muallif TEXT,
        manba TEXT,
        fayl_id TEXT
    )''')

@bot.message_handler(commands=['add'])
def add_kino(message):
    if message.from_user.id != ADMIN_ID:
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

        with conn:
            conn.execute("INSERT INTO kinolar VALUES (?, ?, ?, ?, ?, ?)",
                         (kod, nom, tavsif, muallif, manba, fayl_id))
        logging.info(f"Kino saqlandi: kod={kod}, nom={nom}")
        bot.send_message(message.chat.id, "✅ Kino muvaffaqiyatli saqlandi.")
    except Exception as e:
        logging.error(f"Kino qo‘shishda xatolik: {e}")
        bot.send_message(message.chat.id,
                         "❌ Xatolik. Ehtimol kod allaqachon mavjud yoki boshqa muammo bor.")

@bot.message_handler(func=lambda m: True)
def get_kino(message):
    kod = message.text.strip()
    try:
        with conn:
            cur = conn.execute("SELECT * FROM kinolar WHERE kod=?", (kod,))
            kino = cur.fetchone()
        if kino:
            _, nom, tavsif, muallif, manba, fayl_id = kino
            caption = f"🎬 <b>{nom}</b>\n📝 {tavsif}\n👤 {muallif}\n🌐 {manba}"
            bot.send_video(message.chat.id, fayl_id, caption=caption, parse_mode="HTML")
            logging.info(f"Kino yuborildi: kod={kod}")
        else:
            bot.send_message(message.chat.id, "❌ Bunday kodga ega kino topilmadi.")
            logging.info(f"Kino topilmadi: kod={kod}")
    except Exception as e:
        logging.error(f"Kino olishda xatolik: {e}")
        bot.send_message(message.chat.id, "❌ Ma'lumot olishda xatolik yuz berdi.")

# Flask endpoint webhook uchun
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
    WEBHOOK_URL = 'https://SIZNING_DOMEN/renderda_yaratilgan_url/webhook/' + API_TOKEN

    # Telegram botga webhookni o'rnatamiz
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    app.run(host="0.0.0.0", port=5000)
