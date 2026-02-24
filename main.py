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
from PIL import Image, ImageDraw, ImageFont
from reportlab.platypus import SimpleDocTemplate, Image as RLImage
from reportlab.lib.pagesizes import A3

# =========================
# ENV
# =========================

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEXTURES = {
    "premium_dark_indigo": os.path.join(BASE_DIR, "assets/textures/Premium_Dark_Indigo.jpg"),
    "soft_indigo": os.path.join(BASE_DIR, "assets/textures/Soft_Indigo.avif"),
    "natural_linen": os.path.join(BASE_DIR, "assets/textures/Natural_Linen.avif"),
    "artisan_linen": os.path.join(BASE_DIR, "assets/textures/Artisan_Linen.jpg"),
    "wabi_indigo": os.path.join(BASE_DIR, "assets/textures/Wabi_Indigo.png"),
}

FONT_PATH = os.path.join(BASE_DIR, "assets/fonts/DejaVuSans.ttf")

CELL_SIZE = 70
THREAD_WIDTH = 10

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
    bits = ""
    for char in text:
        bits += format(ord(char), "08b")
    return bits

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

# =========================
# DRAW THREAD
# =========================

def draw_thread(draw, x1, y1, x2, y2, color):
    shadow = tuple(max(c-60,0) for c in color)
    draw.line((x1, y1+4, x2, y2+4), fill=shadow, width=THREAD_WIDTH+2)
    draw.line((x1, y1, x2, y2), fill=color, width=THREAD_WIDTH)
    highlight = tuple(min(c+40,255) for c in color)
    draw.line((x1, y1-2, x2, y2-2), fill=highlight, width=3)

def add_white_frame(img):
    outer = 250
    w, h = img.size
    framed = Image.new("RGB", (w+outer*2, h+outer*2), (245,245,245))
    framed.paste(img, (outer, outer))
    return framed

# =========================
# POSTER
# =========================

def generate_poster(horizontal_text, vertical_text, texture_key, thread_key):

    h_bits = text_to_bits(horizontal_text)
    v_bits = text_to_bits(vertical_text)

    height = len(h_bits)
    width  = len(v_bits)

    H = build_horizontal(h_bits, width)
    V = build_vertical(v_bits, height)

    canvas_size = 4000

    texture_path = TEXTURES.get(texture_key)

    try:
        bg = Image.open(texture_path).convert("RGB")
        bg = bg.resize((canvas_size, canvas_size))
    except Exception as e:
        print("Texture load error:", e)
        bg = Image.new("RGB", (canvas_size, canvas_size), (230,230,230))

    draw = ImageDraw.Draw(bg)

    pattern_w = width * CELL_SIZE
    pattern_h = height * CELL_SIZE

    offset_x = (canvas_size - pattern_w)//2
    offset_y = (canvas_size - pattern_h)//2 - 100

    thread_color = THREAD_COLORS.get(thread_key, (212,175,55))

    for r in range(height):
        for c in range(width):

            x = offset_x + c*CELL_SIZE
            y = offset_y + (height-r-1)*CELL_SIZE

            if H[r][c] == 1:
                draw_thread(draw, x, y, x+CELL_SIZE, y, thread_color)

            if V[r][c] == 1:
                draw_thread(draw, x+CELL_SIZE, y, x+CELL_SIZE, y+CELL_SIZE, thread_color)

    font = ImageFont.truetype(FONT_PATH, 120)

    title = f"{horizontal_text.upper()} | {vertical_text.upper()}"
    bbox = draw.textbbox((0,0), title, font=font)
    text_w = bbox[2]-bbox[0]

    draw.text(((canvas_size-text_w)//2, canvas_size-350),
              title, fill=(40,40,40), font=font)

    framed = add_white_frame(bg)

    file_id = str(uuid.uuid4())
    output_path = f"poster_{file_id}.jpg"
    framed.save(output_path, quality=95)

    return output_path

# =========================
# PATTERN PDF
# =========================

def generate_pattern_pdf(horizontal_text, vertical_text):

    h_bits = text_to_bits(horizontal_text)
    v_bits = text_to_bits(vertical_text)

    height = len(h_bits)
    width  = len(v_bits)

    H = build_horizontal(h_bits, width)
    V = build_vertical(v_bits, height)

    img_size = 3500
    img = Image.new("RGB", (img_size, img_size), "white")
    draw = ImageDraw.Draw(img)

    cell = 25
    offset = 300

    for r in range(height):
        for c in range(width):

            x = offset + c*cell
            y = offset + (height-r-1)*cell

            if H[r][c] == 1:
                draw.line((x, y, x+cell, y), fill="black", width=3)

            if V[r][c] == 1:
                draw.line((x+cell, y, x+cell, y+cell), fill="black", width=3)

    file_id = str(uuid.uuid4())
    img_path = f"pattern_{file_id}.png"
    pdf_path = f"pattern_{file_id}.pdf"

    img.save(img_path)

    doc = SimpleDocTemplate(pdf_path, pagesize=A3)
    elements = [RLImage(img_path, width=A3[0], height=A3[1])]
    doc.build(elements)

    os.remove(img_path)

    return pdf_path

# =========================
# BOT LOGIC
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["state"] = STATE_WAIT_TRIGGER
    await update.message.reply_text("Напишіть «сашіко», щоб почати ✨")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot started...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
