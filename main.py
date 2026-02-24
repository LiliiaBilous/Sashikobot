import os
import uuid
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

user_state = {}
user_data = {}

THREAD_COLORS = {
    "Білий": "white",
    "Золотий": "#D4AF37",
    "Червоний": "#B00000",
    "Бордовий": "#800020",
    "Темно зелений": "#006400",
    "Чорний": "black",
    "Темно синій": "#000064",
    "Коричневий": "#654321",
}

FABRICS = {
    "Білий льон": "#F0F0E6",
    "Натуральний льон": "#DEC8A0",
}

binary_code = {
    "A": "00001","B": "00010","C": "00011","D": "00100","E": "00101",
    "F": "00110","G": "00111","H": "01000","I": "01001","J": "01010",
    "K": "01011","L": "01100","M": "01101","N": "01110","O": "01111",
    "P": "10000","Q": "10001","R": "10010","S": "10011","T": "10100",
    "U": "10101","V": "10110","W": "10111","X": "11000","Y": "11001",
    "Z": "11010"
}

MARGIN = 1


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
    matrix = [[0]*len(bits) for _ in range(height)]
    for col, bit in enumerate(bits):
        current = int(bit)
        for row in range(height):
            matrix[row][col] = current
            current = 1 - current
    return matrix


def generate_pattern(horizontal_text, vertical_text, mode, thread=None, fabric=None):

    h_bits = text_to_bits(horizontal_text)
    v_bits = text_to_bits(vertical_text)

    height = len(h_bits)
    width = len(v_bits)

    H = build_horizontal(h_bits, width)
    V = build_vertical(v_bits, height)

    total_height = height + 2*MARGIN
    total_width = width + 2*MARGIN

    fig, ax = plt.subplots(figsize=(8, 8))

    if mode == "poster":
        ax.set_facecolor(fabric)

    # GRID
    for x in range(total_width + 1):
        ax.plot([x, x], [0, total_height],
                color="gray", alpha=0.25, linewidth=0.6)

    for y in range(total_height + 1):
        ax.plot([0, total_width], [y, y],
                color="gray", alpha=0.25, linewidth=0.6)

    active_color = thread if mode == "poster" else "black"

    for r in range(height):
        for c in range(width):

            draw_x = c + MARGIN
            draw_y = height - r - 1 + MARGIN

            if H[r][c] == 1:
                ax.plot([draw_x, draw_x+1],
                        [draw_y, draw_y],
                        color=active_color,
                        linewidth=2.5)

            if V[r][c] == 1:
                ax.plot([draw_x+1, draw_x+1],
                        [draw_y, draw_y+1],
                        color=active_color,
                        linewidth=2.5)

    # =============================
    # ПОСТЕР ДОДАТКОВІ ЕЛЕМЕНТИ
    # =============================
    if mode == "poster":

        # РАМКА
        ax.add_patch(
            plt.Rectangle(
                (0.5, 0.5),
                total_width - 1,
                total_height - 1,
                fill=False,
                edgecolor=thread,
                linewidth=6
            )
        )

        # ПІДПИС
        if horizontal_text.upper() == vertical_text.upper():
            label = horizontal_text.upper()
        else:
            label = f"{horizontal_text.upper()} | {vertical_text.upper()}"

        ax.text(
            total_width / 2,
            -2,
            label,
            ha='center',
            va='center',
            fontsize=18,
            color=thread,
            fontweight='bold'
        )

    ax.set_xlim(0, total_width)
    ax.set_ylim(-4, total_height)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect('equal')

    filename = f"{uuid.uuid4().hex}.png"
    fig.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close(fig)

    return filename


# =============================
# TELEGRAM
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Напишіть 'Сашіко' щоб почати.")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    if text.lower() == "сашіко":
        user_state[user_id] = "choose_type"
        keyboard = [["Постер", "Схема"]]
        await update.message.reply_text(
            "Оберіть тип:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    if user_state.get(user_id) == "choose_type":
        user_data[user_id] = {"mode": text}
        user_state[user_id] = "horizontal"
        await update.message.reply_text("Введіть горизонтальний текст:")
        return

    if user_state.get(user_id) == "horizontal":
        user_data[user_id]["horizontal"] = text
        user_state[user_id] = "vertical"
        await update.message.reply_text("Введіть вертикальний текст:")
        return

    if user_state.get(user_id) == "vertical":
        user_data[user_id]["vertical"] = text

        if user_data[user_id]["mode"] == "Схема":
            filename = generate_pattern(
                user_data[user_id]["horizontal"],
                user_data[user_id]["vertical"],
                mode="scheme"
            )
            await update.message.reply_photo(photo=open(filename, "rb"))
            os.remove(filename)
            user_state[user_id] = None
            return
        else:
            user_state[user_id] = "thread"
            keyboard = [[c] for c in THREAD_COLORS.keys()]
            await update.message.reply_text(
                "Оберіть колір ниток:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return

    if user_state.get(user_id) == "thread":
        user_data[user_id]["thread"] = THREAD_COLORS[text]
        user_state[user_id] = "fabric"
        keyboard = [[f] for f in FABRICS.keys()]
        await update.message.reply_text(
            "Оберіть тканину:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return

    if user_state.get(user_id) == "fabric":
        user_data[user_id]["fabric"] = FABRICS[text]

        filename = generate_pattern(
            user_data[user_id]["horizontal"],
            user_data[user_id]["vertical"],
            mode="poster",
            thread=user_data[user_id]["thread"],
            fabric=user_data[user_id]["fabric"]
        )

        await update.message.reply_photo(photo=open(filename, "rb"))
        os.remove(filename)

        user_state[user_id] = None
        user_data[user_id] = {}
        return


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
