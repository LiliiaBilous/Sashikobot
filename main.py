import os
import logging
import smtplib
from email.message import EmailMessage
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from reportlab.platypus import SimpleDocTemplate, Image as RLImage
from reportlab.lib.pagesizes import A3
from reportlab.lib.units import inch

# ---------------- SAFE TOKEN ----------------

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN not found in environment variables.")

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

logging.basicConfig(level=logging.INFO)

TEXTURES = {
    "premium_dark_indigo": "assets/textures/premium_dark_indigo.jpg",
    "soft_indigo": "assets/textures/soft_indigo.jpg",
    "natural_linen": "assets/textures/natural_linen.jpg",
}

COLORS = {
    "white": (245, 245, 245),
    "gold": (212, 175, 55),
    "red": (180, 30, 30),
    "black": (30, 30, 30),
}

FONT_PATH = "assets/fonts/PlayfairDisplay-Bold.ttf"

# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧵 SASHIKO ART BOT\n\n"
        "1️⃣ Оберіть тканину\n"
        "2️⃣ Оберіть стиль\n"
        "3️⃣ Оберіть колір\n"
        "4️⃣ Введіть текст\n\n"
        "Отримаєте HQ постер + PDF для друку"
    )

# ---------------- TEXTURE ----------------

async def texture_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["texture"] = query.data

    keyboard = [
        [InlineKeyboardButton("🪡 Artisan", callback_data="mode_artisan")],
        [InlineKeyboardButton("🧘 Zen", callback_data="mode_zen")],
    ]

    await query.edit_message_text("Оберіть стиль:", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- MODE ----------------

async def mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["mode"] = query.data.replace("mode_", "")

    keyboard = [
        [InlineKeyboardButton("White", callback_data="color_white")],
        [InlineKeyboardButton("Gold", callback_data="color_gold")],
        [InlineKeyboardButton("Red", callback_data="color_red")],
        [InlineKeyboardButton("Black", callback_data="color_black")],
    ]

    await query.edit_message_text("Оберіть колір нитки:", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- COLOR ----------------

async def color_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["color"] = COLORS[query.data.replace("color_", "")]
    context.user_data["awaiting_text"] = True

    await query.edit_message_text("Введіть текст для постера:")

# ---------------- STITCH EFFECT ----------------

def draw_stitch(draw, position, text, font, color):
    x, y = position
    shadow = tuple(max(c - 50, 0) for c in color)

    # lower stitch
    draw.text((x+4, y+4), text, font=font, fill=shadow)
    # main stitch
    draw.text((x, y), text, font=font, fill=color)

# ---------------- FRAME ----------------

def add_gallery_frame(image):
    border = 120
    framed = Image.new("RGB", (image.width + border*2, image.height + border*2), (255,255,255))
    framed.paste(image, (border, border))
    return framed

# ---------------- PDF ----------------

def create_pdf(image_path):
    pdf_path = "poster_print_A3.pdf"
    doc = SimpleDocTemplate(pdf_path, pagesize=A3)
    elements = []

    img = RLImage(image_path, width=16*inch, height=16*inch)
    elements.append(img)
    doc.build(elements)

    return pdf_path

# ---------------- GENERATE ----------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("awaiting_text"):
        return

    text = update.message.text
    texture = TEXTURES[context.user_data["texture"]]
    mode = context.user_data["mode"]
    color = context.user_data["color"]

    base = Image.open(texture).convert("RGB").resize((3000, 3000))
    draw = ImageDraw.Draw(base)

    font = ImageFont.truetype(FONT_PATH, 260)
    bbox = draw.textbbox((0,0), text, font=font)
    w = bbox[2]-bbox[0]
    h = bbox[3]-bbox[1]

    x = (3000 - w)//2
    y = (3000 - h)//2

    if mode == "artisan":
        draw_stitch(draw, (x,y), text, font, color)
        base = base.filter(ImageFilter.GaussianBlur(0.3))
    else:
        draw.text((x,y), text, font=font, fill=color)

    base = add_gallery_frame(base)

    jpg_path = "poster_hq.jpg"
    base.save(jpg_path, quality=100)

    pdf_path = create_pdf(jpg_path)

    context.user_data["jpg"] = jpg_path
    context.user_data["pdf"] = pdf_path
    context.user_data["awaiting_text"] = False

    await update.message.reply_photo(open(jpg_path,"rb"))
    await update.message.reply_document(open(pdf_path,"rb"))

    if EMAIL_ADDRESS and EMAIL_PASSWORD:
        keyboard = [[InlineKeyboardButton("📩 Надіслати на Email", callback_data="send_email")]]
        await update.message.reply_text("Надіслати файл на пошту?", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------------- EMAIL ----------------

async def send_email_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["awaiting_email"] = True
    await query.edit_message_text("Введіть email:")

async def send_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_email"):
        return

    email = update.message.text
    msg = EmailMessage()
    msg["Subject"] = "Ваш Sashiko Poster"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = email
    msg.set_content("Ваші файли у вкладенні.")

    for file in ["poster_hq.jpg", "poster_print_A3.pdf"]:
        with open(file,"rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="octet-stream", filename=file)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)

    context.user_data["awaiting_email"] = False
    await update.message.reply_text("✅ Надіслано!")

# ---------------- MAIN ----------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_handler(CallbackQueryHandler(texture_selected, pattern="^(premium_dark_indigo|soft_indigo|natural_linen)$"))
    app.add_handler(CallbackQueryHandler(mode_selected, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(color_selected, pattern="^color_"))
    app.add_handler(CallbackQueryHandler(send_email_button, pattern="send_email"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_email))

    app.run_polling()

if __name__ == "__main__":
    main()
