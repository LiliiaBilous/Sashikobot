import os
import matplotlib.pyplot as plt
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =========================
# TOKEN береться з Railway Variables
# =========================
TOKEN = os.getenv("TOKEN")

# =========================
# НАЛАШТУВАННЯ
# =========================
ACTIVE_WIDTH = 2.5
GRID_COLOR = "gray"
GRID_ALPHA = 0.25
GRID_WIDTH = 0.6
MARGIN = 1

# =========================
# БІНАРНА ТАБЛИЦЯ
# =========================
binary_code = {

    # LATIN
    "A": "00001","B": "00010","C": "00011","D": "00100","E": "00101",
    "F": "00110","G": "00111","H": "01000","I": "01001","J": "01010",
    "K": "01011","L": "01100","M": "01101","N": "01110","O": "01111",
    "P": "10000","Q": "10001","R": "10010","S": "10011","T": "10100",
    "U": "10101","V": "10110","W": "10111","X": "11000","Y": "11001",
    "Z": "11010",

    # CYRILLIC
    "А": "000001","Б": "000010","В": "000011","Г": "000100",
    "Ґ": "000101","Д": "000110","Е": "000111","Є": "001000",
    "Ж": "001001","З": "001010","И": "001011","І": "001100",
    "Ї": "001101","Й": "001110","К": "001111","Л": "010000",
    "М": "010001","Н": "010010","О": "010011","П": "010100",
    "Р": "010101","С": "010110","Т": "010111","У": "011000",
    "Ф": "011001","Х": "011010","Ц": "011011","Ч": "011100",
    "Ш": "011101","Щ": "011110","Ь": "011111","Ю": "100000",
    "Я": "100001",

    # NUMBERS
    "0": "100010","1": "100011","2": "100100","3": "100101",
    "4": "100110","5": "100111","6": "101000","7": "101001",
    "8": "101010","9": "101011",

    # SYMBOLS
    ".": "101100",
    ",": "101101",
    "!": "101110",
    "?": "101111",
    "&": "110000",

    # SPACE
    " ": "000000"
}

# =========================
# ЛОГІКА
# =========================
def text_to_bits(text):
    bits = ""
    for letter in text.upper():
        if letter in binary_code:
            bits += binary_code[letter]
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
    matrix = [[0] * len(bits) for _ in range(height)]
    for col, bit in enumerate(bits):
        current = int(bit)
        for row in range(height):
            matrix[row][col] = current
            current = 1 - current
    return matrix


# =========================
# ГЕНЕРАЦІЯ ЗОБРАЖЕННЯ
# =========================
def generate_image(horizontal_text, vertical_text, active_color):
    h_bits = text_to_bits(horizontal_text)
    v_bits = text_to_bits(vertical_text)

    height = len(h_bits) if h_bits else 5
    width = len(v_bits) if v_bits else 5

    H = build_horizontal(h_bits or "0"*5, width)
    V = build_vertical(v_bits or "0"*5, height)

    total_height = height + 2 * MARGIN
    total_width = width + 2 * MARGIN

    fig, ax = plt.subplots(figsize=(8, 8))

    # Решітка
    for x in range(total_width + 1):
        ax.plot([x, x], [0, total_height],
                color=GRID_COLOR,
                alpha=GRID_ALPHA,
                linewidth=GRID_WIDTH)

    for y in range(total_height + 1):
        ax.plot([0, total_width], [y, y],
                color=GRID_COLOR,
                alpha=GRID_ALPHA,
                linewidth=GRID_WIDTH)

    # Активні лінії
    for r in range(height):
        for c in range(width):
            draw_x = c + MARGIN
            draw_y = height - r - 1 + MARGIN

            if H[r][c] == 1:
                ax.plot([draw_x, draw_x + 1],
                        [draw_y, draw_y],
                        color=active_color,
                        linewidth=ACTIVE_WIDTH)

            if V[r][c] == 1:
                ax.plot([draw_x + 1, draw_x + 1],
                        [draw_y, draw_y + 1],
                        color=active_color,
                        linewidth=ACTIVE_WIDTH)

    ax.set_xlim(0, total_width)
    ax.set_ylim(0, total_height)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect('equal')

    filename = "pattern.png"
    fig.savefig(filename, dpi=300)
    plt.close(fig)

    return filename


# =========================
# TELEGRAM ЛОГІКА
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("🚀 Старт")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    context.user_data.clear()

    await update.message.reply_text(
        "Привіт 👋 Натисни кнопку щоб почати:",
        reply_markup=reply_markup
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text in ["🚀 Старт", "🔁 Знову"]:
        context.user_data["step"] = "horizontal"
        await update.message.reply_text("Введи горизонтальний текст:")
        return

    if context.user_data.get("step") == "horizontal":
        context.user_data["horizontal"] = text
        context.user_data["step"] = "vertical"
        await update.message.reply_text("Тепер введи вертикальний текст:")
        return

    if context.user_data.get("step") == "vertical":
        context.user_data["vertical"] = text
        context.user_data["step"] = "color"

        keyboard = [
            [InlineKeyboardButton("⚫ Black", callback_data="black"),
             InlineKeyboardButton("🔴 Red", callback_data="red")],
            [InlineKeyboardButton("🔵 Blue", callback_data="blue"),
             InlineKeyboardButton("🟢 Green", callback_data="green")],
            [InlineKeyboardButton("🎨 Свій HEX", callback_data="hex")]
        ]

        await update.message.reply_text(
            "Обери колір:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if context.user_data.get("step") == "hex":
        filename = generate_image(
            context.user_data["horizontal"],
            context.user_data["vertical"],
            text.strip()
        )

        await update.message.reply_photo(
            photo=open(filename, "rb"),
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("🔁 Знову")]],
                resize_keyboard=True
            )
        )


async def handle_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "hex":
        context.user_data["step"] = "hex"
        await query.message.reply_text("Введи HEX колір (наприклад #FF00AA):")
        return

    filename = generate_image(
        context.user_data["horizontal"],
        context.user_data["vertical"],
        query.data
    )

    await query.message.reply_photo(
        photo=open(filename, "rb"),
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("🔁 Знову")]],
            resize_keyboard=True
        )
    )


# =========================
# ЗАПУСК
# =========================
def main():
    if not TOKEN:
        raise ValueError("TOKEN не знайдено. Додай його у Railway Variables.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(handle_color))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
