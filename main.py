import os
import uuid
from PIL import Image, ImageDraw, ImageFont
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

# ======================
# СТАНИ
# ======================
user_state = {}
user_data = {}

THREAD_COLORS = {
    "Білий": (245, 245, 245),
    "Золотий": (212, 175, 55),
    "Червоний": (180, 0, 0),
    "Бордовий": (128, 0, 32),
    "Темно зелений": (0, 100, 0),
    "Чорний": (20, 20, 20),
    "Темно синій": (0, 0, 100),
    "Коричневий": (101, 67, 33),
}

FABRICS = {
    "Білий льон": (240, 240, 230),
    "Натуральний льон": (222, 200, 160),
}

ORIENTATION = ["Горизонтально", "Вертикально"]


# ======================
# ГЕНЕРАЦІЯ СХЕМИ
# ======================
def generate_scheme(text):
    img = Image.new("RGB", (800, 800), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 120)
    except:
        font = ImageFont.load_default()

    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    draw.text(((800 - w) / 2, (800 - h) / 2), text, fill="black", font=font)

    filename = f"scheme_{uuid.uuid4().hex}.png"
    img.save(filename)
    return filename


# ======================
# ГЕНЕРАЦІЯ ПОСТЕРА З НИТКАМИ
# ======================
def generate_poster(text, thread_color, fabric_color, orientation):
    img = Image.new("RGB", (800, 800), fabric_color)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 120)
    except:
        font = ImageFont.load_default()

    if orientation == "Вертикально":
        text = "\n".join(list(text))

    w, h = draw.multiline_textbbox((0, 0), text, font=font, spacing=20)[2:]
    x = (800 - w) / 2
    y = (800 - h) / 2

    # Малюємо ефект стібків
    for offset in range(-2, 3):
        draw.multiline_text(
            (x + offset, y),
            text,
            font=font,
            fill=thread_color,
            spacing=20,
        )
        draw.multiline_text(
            (x, y + offset),
            text,
            font=font,
            fill=thread_color,
            spacing=20,
        )

    filename = f"poster_{uuid.uuid4().hex}.png"
    img.save(filename)
    return filename


# ======================
# START
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✨ Вітаю у генераторі Сашіко!\nНапишіть 'Сашіко' щоб почати."
    )


# ======================
# ТЕКСТ
# ======================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    # Запуск
    if text.lower() == "сашіко":
        user_state[user_id] = "choose_type"
        keyboard = [["Постер", "Схема"]]
        await update.message.reply_text(
            "Оберіть що хочете створити:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return

    # Тип
    if user_state.get(user_id) == "choose_type":
        user_data[user_id] = {"type": text}

        if text == "Постер":
            user_state[user_id] = "choose_thread"
            keyboard = [[c] for c in THREAD_COLORS.keys()]
            await update.message.reply_text(
                "Оберіть колір ниток:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            )
        else:
            user_state[user_id] = "enter_scheme_text"
            await update.message.reply_text("Введіть текст для схеми:")
        return

    # Колір ниток
    if user_state.get(user_id) == "choose_thread":
        user_data[user_id]["thread"] = text
        user_state[user_id] = "choose_fabric"
        keyboard = [[f] for f in FABRICS.keys()]
        await update.message.reply_text(
            "Оберіть тканину:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return

    # Тканина
    if user_state.get(user_id) == "choose_fabric":
        user_data[user_id]["fabric"] = text
        user_state[user_id] = "choose_orientation"
        keyboard = [[o] for o in ORIENTATION]
        await update.message.reply_text(
            "Оберіть орієнтацію тексту:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return

    # Орієнтація
    if user_state.get(user_id) == "choose_orientation":
        user_data[user_id]["orientation"] = text
        user_state[user_id] = "enter_poster_text"
        await update.message.reply_text("Введіть текст для постера:")
        return

    # Текст постера
    if user_state.get(user_id) == "enter_poster_text":
        data = user_data[user_id]
        filename = generate_poster(
            text,
            THREAD_COLORS[data["thread"]],
            FABRICS[data["fabric"]],
            data["orientation"],
        )

        await update.message.reply_photo(photo=open(filename, "rb"))
        os.remove(filename)

        user_state[user_id] = None
        user_data[user_id] = {}
        return

    # Текст схеми
    if user_state.get(user_id) == "enter_scheme_text":
        filename = generate_scheme(text)

        await update.message.reply_photo(photo=open(filename, "rb"))
        os.remove(filename)

        user_state[user_id] = None
        user_data[user_id] = {}
        return


# ======================
# MAIN
# ======================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
