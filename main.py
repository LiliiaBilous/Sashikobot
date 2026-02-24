import os
import logging
import smtplib
from email.message import EmailMessage
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------------- CONFIG ----------------

TOKEN = os.getenv("BOT_TOKEN")

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

logging.basicConfig(level=logging.INFO)

TEXTURES = {
    "premium_dark_indigo": "assets/textures/premium_dark_indigo.jpg",
    "soft_indigo": "assets/textures/soft_indigo.jpg",
    "natural_linen": "assets/textures/natural_linen.jpg",
    "artisan_linen": "assets/textures/artisan_linen.jpg",
    "wabi_indigo": "assets/textures/wabi_indigo.jpg",
}

COLORS = {
    "white": (245, 245, 245),
    "cream": (255, 244, 220),
    "gold": (212, 175, 55),
    "red": (180, 30, 30),
    "black": (30, 30, 30),
}

FONT_PATH = "assets/fonts/PlayfairDisplay-Bold.ttf"

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Напишіть слово САШІКО щоб почати створення постера 🧵✨"
    )

# ---------------- HANDLE TEXT ----------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if text.lower() == "сашіко":
        await update.message.reply_text(
            "✨ Як працює бот:\n\n"
            "1️⃣ Оберіть тканину\n"
            "2️⃣ Оберіть стиль (Artisan або Zen)\n"
            "3️⃣ Оберіть колір нитки\n"
            "4️⃣ Введіть текст\n\n"
            "Після цього ви отримаєте HQ постер.\n"
        )

        keyboard = [
            [InlineKeyboardButton("Premium Indigo", callback_data="premium_dark_indigo")],
            [InlineKeyboardButton("Soft Indigo", callback_data="soft_indigo")],
            [InlineKeyboardButton("Natural Linen", callback_data="natural_linen")],
            [InlineKeyboardButton("Artisan Linen", callback_data="artisan_linen")],
            [InlineKeyboardButton("Wabi Indigo", callback_data="wabi_indigo")],
        ]

        await update.message.reply_text(
            "Оберіть тканину:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if context.user_data.get("awaiting_text"):
        await generate_poster(update, context, text)
        return

    if context.user_data.get("awaiting_email"):
        await send_email(update, context, text)
        return

# ---------------- TEXTURE ----------------

async def texture_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["texture"] = query.data

    keyboard = [
        [InlineKeyboardButton("🪡 Artisan", callback_data="mode_artisan")],
        [InlineKeyboardButton("🧘 Zen", callback_data="mode_zen")],
    ]

    await query.edit_message_text(
        "Оберіть режим:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- MODE ----------------

async def mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["mode"] = query.data.replace("mode_", "")

    keyboard = [
        [InlineKeyboardButton("White", callback_data="color_white")],
        [InlineKeyboardButton("Cream", callback_data="color_cream")],
        [InlineKeyboardButton("Gold", callback_data="color_gold")],
        [InlineKeyboardButton("Red", callback_data="color_red")],
        [InlineKeyboardButton("Black", callback_data="color_black")],
    ]

    await query.edit_message_text(
        "Оберіть колір нитки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- COLOR ----------------

async def color_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    color_key = query.data.replace("color_", "")
    context.user_data["color"] = COLORS[color_key]

    context.user_data["awaiting_text"] = True

    await query.edit_message_text("Введіть текст для постера:")

# ---------------- RENDER ----------------

async def generate_poster(update, context, text):

    texture_path = TEXTURES[context.user_data["texture"]]
    mode = context.user_data["mode"]
    color = context.user_data["color"]

    # HQ size
    base = Image.open(texture_path).convert("RGB")
    base = base.resize((3000, 3000))
    draw = ImageDraw.Draw(base)

    font_size = 260
    font = ImageFont.truetype(FONT_PATH, font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    x = (3000 - w) // 2
    y = (3000 - h) // 2

    if mode == "artisan":
        shadow = tuple(max(c - 40, 0) for c in color)
        draw.text((x+6, y+6), text, font=font, fill=shadow)
        draw.text((x, y), text, font=font, fill=color)
        base = base.filter(ImageFilter.GaussianBlur(0.4))
    else:
        draw.text((x, y), text, font=font, fill=color)

    output_path = "poster_hq.jpg"
    base.save(output_path, quality=100)

    context.user_data["file_path"] = output_path
    context.user_data["awaiting_text"] = False

    await update.message.reply_photo(photo=open(output_path, "rb"))

    keyboard = [
        [InlineKeyboardButton("📩 Надіслати на Email", callback_data="send_email")]
    ]

    await update.message.reply_text(
        "Бажаєте отримати файл у високій якості на пошту?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- EMAIL ----------------

async def email_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["awaiting_email"] = True

    await query.edit_message_text("Введіть вашу email адресу:")

async def send_email(update, context, email):

    file_path = context.user_data["file_path"]

    msg = EmailMessage()
    msg["Subject"] = "Ваш Sashiko Poster HQ"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email
    msg.set_content("Ваш постер у високій якості у вкладенні.")

    with open(file_path, "rb") as f:
        msg.add_attachment(f.read(),
                           maintype="image",
                           subtype="jpeg",
                           filename="sashiko_poster.jpg")

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

    context.user_data.clear()

    await update.message.reply_text("✅ Файл надіслано на пошту!")

# ---------------- MAIN ----------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_handler(CallbackQueryHandler(texture_selected, pattern="^(premium_dark_indigo|soft_indigo|natural_linen|artisan_linen|wabi_indigo)$"))
    app.add_handler(CallbackQueryHandler(mode_selected, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(color_selected, pattern="^color_"))
    app.add_handler(CallbackQueryHandler(email_button, pattern="send_email"))

    app.run_polling()

if __name__ == "__main__":
    main()
