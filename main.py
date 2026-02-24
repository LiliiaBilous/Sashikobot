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
    "premium_dark_indigo": os.path.join(BASE_DIR, "assets/textures/premium_dark_indigo.jpg"),
    "soft_indigo": os.path.join(BASE_DIR, "assets/textures/soft_indigo.jpg"),
    "natural_linen": os.path.join(BASE_DIR, "assets/textures/natural_linen.jpg"),
}

FONT_PATH = os.path.join(BASE_DIR, "assets/fonts/DejaVuSans.ttf")

CELL_SIZE = 70
THREAD_WIDTH = 10
MARGIN = 1

logging.basicConfig(level=logging.INFO)

# =========================
# BINARY ENGINE (Unicode)
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
# THREAD DRAW
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
    draw = ImageDraw.Draw(framed)
    draw.rectangle([outer-8, outer-8, w+outer+8, h+outer+8],
                   outline=(220,220,220), width=8)
    return framed

# =========================
# POSTER GENERATOR
# =========================

def generate_poster(horizontal_text, vertical_text, texture_key):
    h_bits = text_to_bits(horizontal_text)
    v_bits = text_to_bits(vertical_text)

    height = len(h_bits)
    width  = len(v_bits)

    H = build_horizontal(h_bits, width)
    V = build_vertical(v_bits, height)

    canvas_size = 4000
    bg = Image.open(TEXTURES[texture_key]).convert("RGB")
    bg = bg.resize((canvas_size, canvas_size))
    draw = ImageDraw.Draw(bg)

    pattern_w = width * CELL_SIZE
    pattern_h = height * CELL_SIZE

    offset_x = (canvas_size - pattern_w)//2
    offset_y = (canvas_size - pattern_h)//2 - 100

    thread_color = (212,175,55)

    for r in range(height):
        for c in range(width):

            x = offset_x + c*CELL_SIZE
            y = offset_y + (height-r-1)*CELL_SIZE

            if H[r][c] == 1:
                draw_thread(draw, x, y, x+CELL_SIZE, y, thread_color)

            if V[r][c] == 1:
                draw_thread(draw, x+CELL_SIZE, y, x+CELL_SIZE, y+CELL_SIZE, thread_color)

    font = ImageFont.truetype(FONT_PATH, 120)

    if horizontal_text.strip().lower() == vertical_text.strip().lower():
        title = horizontal_text.upper()
    else:
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
# TELEGRAM BOT
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Premium Dark Indigo", callback_data="premium_dark_indigo")],
        [InlineKeyboardButton("Soft Indigo", callback_data="soft_indigo")],
        [InlineKeyboardButton("Natural Linen", callback_data="natural_linen")]
    ]
    await update.message.reply_text("Оберіть текстуру:", reply_markup=InlineKeyboardMarkup(keyboard))

async def texture_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["texture"] = query.data
    context.user_data["step"] = "horizontal"
    await query.edit_message_text("Введіть горизонтальний текст:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    step = context.user_data.get("step")

    if step == "horizontal":
        context.user_data["horizontal"] = update.message.text
        context.user_data["step"] = "vertical"
        await update.message.reply_text("Введіть вертикальний текст:")
        return

    if step == "vertical":
        context.user_data["vertical"] = update.message.text

        horizontal = context.user_data["horizontal"]
        vertical   = context.user_data["vertical"]
        texture    = context.user_data["texture"]

        await update.message.reply_text("Генерую постер...")

        poster_path = generate_poster(horizontal, vertical, texture)
        pdf_path    = generate_pattern_pdf(horizontal, vertical)

        await update.message.reply_photo(open(poster_path,"rb"))
        await update.message.reply_document(open(pdf_path,"rb"))

        os.remove(poster_path)
        os.remove(pdf_path)

        context.user_data.clear()

# =========================
# MAIN
# =========================

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(texture_selected))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
