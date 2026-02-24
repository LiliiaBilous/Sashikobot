import os
import uuid
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from PIL import Image, ImageDraw
from reportlab.platypus import SimpleDocTemplate, Image as RLImage
from reportlab.lib.pagesizes import A3

# =========================
# CONFIG
# =========================

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEXTURES = {
    "premium_dark_indigo": os.path.join(BASE_DIR, "assets/textures/Premium_Dark_Indigo.jpg"),
    "soft_indigo": os.path.join(BASE_DIR, "assets/textures/Soft_Indigo.jpg"),
    "natural_linen": os.path.join(BASE_DIR, "assets/textures/Natural_Linen.jpg"),
    "artisan_linen": os.path.join(BASE_DIR, "assets/textures/Artisan_Linen.jpg"),
    "wabi_indigo": os.path.join(BASE_DIR, "assets/textures/Wabi_Indigo.png"),
}

CELL_SIZE = 60
THREAD_WIDTH = 8

THREAD_COLORS = {
    "white": (245, 245, 245),
    "gold": (212, 175, 55),
    "red": (200, 30, 30),
    "burgundy": (110, 20, 45),
    "darkgreen": (20, 80, 40),
    "black": (30, 30, 30),
    "navy": (15, 35, 85),
    "brown": (120, 70, 30),
}

logging.basicConfig(level=logging.INFO)

# =========================
# STATES
# =========================

STATE_WAIT_TRIGGER = "wait_trigger"
STATE_CHOOSE_TYPE = "choose_type"
STATE_CHOOSE_THREAD = "choose_thread"
STATE_CHOOSE_TEXTURE = "choose_texture"
STATE_WAIT_HORIZONTAL = "wait_horizontal"
STATE_WAIT_VERTICAL = "wait_vertical"

# =========================
# BINARY ENGINE
# =========================

def text_to_bits(text):
    return "".join(format(ord(c), "08b") for c in text)

def alternating(start_bit, length):
    row = []
    current = int(start_bit)
    for _ in range(length):
        row.append(current)
        current = 1 - current
    return row

def build_horizontal(bits, width):
    return [alternating(bit, width) for bit in bits]

def build_vertical(bits, height):
    matrix = [[0]*len(bits) for _ in range(height)]
    for col, bit in enumerate(bits):
        current = int(bit)
        for row in range(height):
            matrix[row][col] = current
            current = 1 - current
    return matrix

def draw_thread(draw, x1, y1, x2, y2, color):
    shadow = tuple(max(c-50,0) for c in color)
    draw.line((x1, y1+3, x2, y2+3), fill=shadow, width=THREAD_WIDTH+2)
    draw.line((x1, y1, x2, y2), fill=color, width=THREAD_WIDTH)

# =========================
# POSTER
# =========================

def generate_poster(horizontal, vertical, texture_key, thread_key):

    bits_h = text_to_bits(horizontal)
    bits_v = text_to_bits(vertical)

    height = len(bits_h)
    width  = len(bits_v)

    H = build_horizontal(bits_h, width)
    V = build_vertical(bits_v, height)

    size = 3000

    try:
        bg = Image.open(TEXTURES[texture_key]).convert("RGB")
        bg = bg.resize((size, size))
    except:
        bg = Image.new("RGB", (size, size), (230,230,230))

    draw = ImageDraw.Draw(bg)
    thread_color = THREAD_COLORS[thread_key]

    offset_x = (size - width*CELL_SIZE)//2
    offset_y = (size - height*CELL_SIZE)//2

    for r in range(height):
        for c in range(width):

            x = offset_x + c*CELL_SIZE
            y = offset_y + (height-r-1)*CELL_SIZE

            if H[r][c] == 1:
                draw_thread(draw, x, y, x+CELL_SIZE, y, thread_color)

            if V[r][c] == 1:
                draw_thread(draw, x+CELL_SIZE, y, x+CELL_SIZE, y+CELL_SIZE, thread_color)

    file_id = str(uuid.uuid4())
    path = f"poster_{file_id}.jpg"
    bg.save(path, quality=95)
    return path

def generate_pattern_pdf(horizontal, vertical):

    bits_h = text_to_bits(horizontal)
    bits_v = text_to_bits(vertical)

    height = len(bits_h)
    width  = len(bits_v)

    H = build_horizontal(bits_h, width)
    V = build_vertical(bits_v, height)

    img = Image.new("RGB", (2500,2500), "white")
    draw = ImageDraw.Draw(img)

    cell = 20
    offset = 250

    for r in range(height):
        for c in range(width):
            x = offset + c*cell
            y = offset + (height-r-1)*cell

            if H[r][c] == 1:
                draw.line((x, y, x+cell, y), fill="black", width=2)
            if V[r][c] == 1:
                draw.line((x+cell, y, x+cell, y+cell), fill="black", width=2)

    img_path = f"pattern_{uuid.uuid4()}.png"
    pdf_path = img_path.replace(".png",".pdf")

    img.save(img_path)

    doc = SimpleDocTemplate(pdf_path, pagesize=A3)
    doc.build([RLImage(img_path, width=A3[0], height=A3[1])])

    os.remove(img_path)
    return pdf_path

# =========================
# BOT LOGIC
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = STATE_WAIT_TRIGGER
    await update.message.reply_text("Напишіть «сашіко», щоб почати ✨")

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "type_poster":
        context.user_data["mode"] = "poster"
        context.user_data["state"] = STATE_CHOOSE_THREAD

        keyboard = [
            [InlineKeyboardButton("⚪ Білий", callback_data="thread_white"),
             InlineKeyboardButton("🟡 Золотий", callback_data="thread_gold")],
            [InlineKeyboardButton("🔴 Червоний", callback_data="thread_red"),
             InlineKeyboardButton("🟥 Бордовий", callback_data="thread_burgundy")],
            [InlineKeyboardButton("🟢 Темно-зелений", callback_data="thread_darkgreen"),
             InlineKeyboardButton("⚫ Чорний", callback_data="thread_black")],
            [InlineKeyboardButton("🔵 Темно-синій", callback_data="thread_navy"),
             InlineKeyboardButton("🟤 Коричневий", callback_data="thread_brown")],
        ]

        await query.edit_message_text("Оберіть колір нитки:",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data == "type_pattern":
        context.user_data["mode"] = "pattern"
        context.user_data["state"] = STATE_WAIT_HORIZONTAL
        await query.edit_message_text("Введіть горизонтальний текст:")
        return

    if data.startswith("thread_"):
        context.user_data["thread"] = data.replace("thread_","")
        context.user_data["state"] = STATE_CHOOSE_TEXTURE

        keyboard = [
            [InlineKeyboardButton("Premium Dark Indigo", callback_data="tex_premium_dark_indigo")],
            [InlineKeyboardButton("Soft Indigo", callback_data="tex_soft_indigo")],
            [InlineKeyboardButton("Natural Linen", callback_data="tex_natural_linen")],
            [InlineKeyboardButton("Artisan Linen", callback_data="tex_artisan_linen")],
            [InlineKeyboardButton("Wabi Indigo", callback_data="tex_wabi_indigo")],
        ]

        await query.edit_message_text("Оберіть тканину:",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("tex_"):
        context.user_data["texture"] = data.replace("tex_","")
        context.user_data["state"] = STATE_WAIT_HORIZONTAL
        await query.edit_message_text("Введіть горизонтальний текст:")
        return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    state = context.user_data.get("state")

    if state == STATE_WAIT_TRIGGER and update.message.text.lower() == "сашіко":
        keyboard = [[
            InlineKeyboardButton("🖼 Постер", callback_data="type_poster"),
            InlineKeyboardButton("📐 Схема", callback_data="type_pattern"),
        ]]
        context.user_data["state"] = STATE_CHOOSE_TYPE
        await update.message.reply_text("Що створюємо?",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if state == STATE_WAIT_HORIZONTAL:
        context.user_data["horizontal"] = update.message.text
        context.user_data["state"] = STATE_WAIT_VERTICAL
        await update.message.reply_text("Введіть вертикальний текст:")
        return

    if state == STATE_WAIT_VERTICAL:

        horizontal = context.user_data["horizontal"]
        vertical = update.message.text

        if context.user_data["mode"] == "poster":
            path = generate_poster(
                horizontal,
                vertical,
                context.user_data["texture"],
                context.user_data["thread"],
            )
            await update.message.reply_photo(photo=open(path,"rb"))
            os.remove(path)
        else:
            pdf = generate_pattern_pdf(horizontal, vertical)
            await update.message.reply_document(document=open(pdf,"rb"))
            os.remove(pdf)

        context.user_data.clear()
        return

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
