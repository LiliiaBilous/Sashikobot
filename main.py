import os
import random
import string
import matplotlib.pyplot as plt
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from texts import WELCOME_TEXT, HOW_IT_WORKS_TEXT

TOKEN = os.getenv("TOKEN")

ACTIVE_WIDTH = 2.5
GRID_COLOR = "gray"
GRID_ALPHA = 0.25
GRID_WIDTH = 0.6
MARGIN = 1


# =========================
# ПОСТІЙНЕ МЕНЮ
# =========================
def persistent_menu():
    keyboard = [
        [KeyboardButton("🚀 Створити візерунок")],
        [KeyboardButton("🎲 Випадковий узор")],
        [KeyboardButton("🧠 Як це працює?")]
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True
    )


# =========================
# БІНАРНА ТАБЛИЦЯ
# =========================
binary_code = {
    **{c: format(i + 1, "05b") for i, c in enumerate(string.ascii_uppercase)},
    " ": "00000"
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
def generate_image(horizontal_text, vertical_text, active_color, with_label, hd=False):

    h_bits = text_to_bits(horizontal_text)
    v_bits = text_to_bits(vertical_text)

    height = len(h_bits) if h_bits else 5
    width = len(v_bits) if v_bits else 5

    H = build_horizontal(h_bits or "0" * 5, width)
    V = build_vertical(v_bits or "0" * 5, height)

    extra_space = 2 if with_label else 0
    total_height = height + 2 * MARGIN + extra_space
    total_width = width + 2 * MARGIN

    # HD режим
    if hd:
        figsize = (15, 15)
        dpi = 600
        line_width = 4
        font_size = 20
        filename = "pattern_hd.png"
    else:
        figsize = (8, 8)
        dpi = 300
        line_width = ACTIVE_WIDTH
        font_size = 10
        filename = "pattern.png"

    fig, ax = plt.subplots(figsize=figsize)

    # Сітка
    for x in range(total_width + 1):
        ax.plot([x, x], [extra_space, total_height],
                color=GRID_COLOR, alpha=GRID_ALPHA, linewidth=GRID_WIDTH)

    for y in range(extra_space, total_height + 1):
        ax.plot([0, total_width], [y, y],
                color=GRID_COLOR, alpha=GRID_ALPHA, linewidth=GRID_WIDTH)

    # Лінії
    for r in range(height):
        for c in range(width):
            draw_x = c + MARGIN
            draw_y = height - r - 1 + MARGIN + extra_space

            if H[r][c] == 1:
                ax.plot([draw_x, draw_x + 1], [draw_y, draw_y],
                        color=active_color, linewidth=line_width)

            if V[r][c] == 1:
                ax.plot([draw_x + 1, draw_x + 1], [draw_y, draw_y + 1],
                        color=active_color, linewidth=line_width)

    # Підпис
    if with_label:
        label = f"H: {horizontal_text} | V: {vertical_text}"
        ax.text(
            total_width / 2,
            0.8,
            label,
            ha="center",
            fontsize=font_size
        )

    ax.set_xlim(0, total_width)
    ax.set_ylim(0, total_height)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")

    fig.savefig(filename, dpi=dpi, bbox_inches="tight")
    plt.close(fig)

    return filename


# =========================
# TELEGRAM ЛОГІКА
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=persistent_menu()
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🧠 Як це працює?":
        context.user_data.clear()
        await update.message.reply_text(
            HOW_IT_WORKS_TEXT,
            reply_markup=persistent_menu()
        )
        return

    if text == "🎲 Випадковий узор":
        context.user_data["horizontal"] = ''.join(random.choices(string.ascii_uppercase, k=4))
        context.user_data["vertical"] = ''.join(random.choices(string.ascii_uppercase, k=4))
        context.user_data["step"] = "label_choice"

    elif text == "🚀 Створити візерунок":
        context.user_data.clear()
        context.user_data["step"] = "horizontal"
        await update.message.reply_text("Введи горизонтальний текст:")
        return

    elif context.user_data.get("step") == "horizontal":
        context.user_data["horizontal"] = text
        context.user_data["step"] = "vertical"
        await update.message.reply_text("Тепер введи вертикальний текст:")
        return

    elif context.user_data.get("step") == "vertical":
        context.user_data["vertical"] = text
        context.user_data["step"] = "label_choice"

    else:
        return

    keyboard = [
        [InlineKeyboardButton("🏷 З підписом", callback_data="label_yes")],
        [InlineKeyboardButton("🚫 Без підпису", callback_data="label_no")]
    ]

    await update.message.reply_text(
        "Додати підпис?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("label_"):
        context.user_data["with_label"] = data == "label_yes"

        keyboard = [
            [InlineKeyboardButton("🖼 Звичайна якість", callback_data="quality_normal")],
            [InlineKeyboardButton("🖨 HD для друку", callback_data="quality_hd")]
        ]

        await query.message.reply_text(
            "Обери якість зображення:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("quality_"):
        context.user_data["hd"] = data == "quality_hd"

        keyboard = [
            [InlineKeyboardButton("⚫ Black", callback_data="black"),
             InlineKeyboardButton("🔴 Red", callback_data="red")],
            [InlineKeyboardButton("🔵 Blue", callback_data="blue"),
             InlineKeyboardButton("🟢 Green", callback_data="green")]
        ]

        await query.message.reply_text(
            "Обери колір:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Генерація
    filename = generate_image(
        context.user_data["horizontal"],
        context.user_data["vertical"],
        data,
        context.user_data.get("with_label", False),
        context.user_data.get("hd", False)
    )

    with open(filename, "rb") as photo:
        await query.message.reply_photo(
            photo=photo,
            reply_markup=persistent_menu()
        )

    context.user_data.clear()


# =========================
# ЗАПУСК
# =========================
def main():
    if not TOKEN:
        raise ValueError("TOKEN не знайдено. Додай його у Railway Variables.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
