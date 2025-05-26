import telebot
from telebot import types
import sqlite3
import logging

API_TOKEN = '8033496372:AAHXsgkyxXq-5ohiH6Gao355ZefY9Vxr0Xc'
ADMIN_ID = 6606638731

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = telebot.TeleBot(API_TOKEN)

def get_db_connection():
    conn = sqlite3.connect("kinolar.db")
    conn.row_factory = sqlite3.Row
    return conn

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('/add')
    markup.add(btn1)
    bot.send_message(message.chat.id, "Salom! Kinolarni qidirish uchun kod yuboring. Misol: `123abc`", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['add'])
def add_kino(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ Sizda ruxsat yo'q.")
        return
    bot.send_message(message.chat.id,
                     "🎥 Kino videosini yuboring. Caption format:\n\n`kod|nom|tavsif|muallif|manba`",
                     parse_mode="Markdown")

@bot.message_handler(content_types=['video'])
def save_video(message):
    if message.from_user.id != ADMIN_ID:
        return
    if not message.caption or '|' not in message.caption:
        bot.send_message(message.chat.id,
                         "❌ Format noto‘g‘ri. To‘g‘ri format:\n`kod|nom|tavsif|muallif|manba`",
                         parse_mode="Markdown")
        return
    try:
        parts = message.caption.split('|')
        if len(parts) != 5:
            bot.send_message(message.chat.id,
                             "❌ Format noto‘g‘ri. To‘g‘ri format:\n`kod|nom|tavsif|muallif|manba`",
                             parse_mode="Markdown")
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
        bot.send_message(message.chat.id, "❌ Sizda ruxsat yo'q.")
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

# Endi e'lon funksiyalarini ham shunga moslab qo'yish kerak (register_next_step_handler ishlatgan joylari)

# Bu yerda webhook qismi olib tashlandi, bot.polling() ishlatilmoqda

if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling()
