import os
import random
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

MAGIC_WORD = "сашіко"


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
# КОДУВАННЯ
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
    matrix = [[0] * len(bits) for _ in range(height)]
    for col, bit in enumerate(bits):
        current = int(bit)
        for row in range(height):
            matrix[row][col] = current
            current = 1 - current
    return matrix


# =========================
# ГЕНЕРАЦІЯ
# =========================
def generate_image(horizontal_text, vertical_text, color, with_label, hd=False):

    h_bits = text_to_bits(horizontal_text)
    v_bits = text_to_bits(vertical_text)

    MAX_BITS = 120
    h_bits = h_bits[:MAX_BITS]
    v_bits = v_bits[:MAX_BITS]

    height = len(h_bits) if h_bits else 8
    width = len(v_bits) if v_bits else 8

    H = build_horizontal(h_bits or "00000000", width)
    V = build_vertical(v_bits or "00000000", height)

    extra_space = 2 if with_label else 0
    total_height = height + 2 * MARGIN + extra_space
    total_width = width + 2 * MARGIN

    max_side = max(total_width, total_height)
    scale = 0.15 if max_side > 100 else 0.25

    figsize = (
        max(total_width * scale, 6),
        max(total_height * scale, 6)
    )

    dpi = 300 if hd else 200
    line_width = 3 if hd else ACTIVE_WIDTH
    font_size = 14 if hd else 10

    filename = "pattern.png"

    fig, ax = plt.subplots(figsize=figsize)

    for x in range(total_width + 1):
        ax.plot([x, x], [extra_space, total_height],
                color=GRID_COLOR, alpha=GRID_ALPHA, linewidth=GRID_WIDTH)

    for y in range(extra_space, total_height + 1):
        ax.plot([0, total_width], [y, y],
                color=GRID_COLOR, alpha=GRID_ALPHA, linewidth=GRID_WIDTH)

    for r in range(height):
        for c in range(width):
            draw_x = c + MARGIN
            draw_y = height - r - 1 + MARGIN + extra_space

            if H[r][c] == 1:
                ax.plot([draw_x, draw_x + 1], [draw_y, draw_y],
                        color=color, linewidth=line_width)

            if V[r][c] == 1:
                ax.plot([draw_x + 1, draw_x + 1], [draw_y, draw_y + 1],
                        color=color, linewidth=line_width)

    if with_label:
        if horizontal_text == vertical_text:
            label = horizontal_text
        else:
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
# TELEGRAM
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=persistent_menu()
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lower = text.lower()

    # 🔥 Магічне слово
    if lower == MAGIC_WORD:
        context.user_data.clear()

        keyboard = [
            [InlineKeyboardButton("✨ Почати творити", callback_data="enter_creator")]
        ]

        await update.message.reply_text(
            HOW_IT_WORKS_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if text == "🧠 Як це працює?":
        await update.message.reply_text(
            HOW_IT_WORKS_TEXT,
            reply_markup=persistent_menu()
        )
        return

    if text == "🎲 Випадковий узор":
        context.user_data["horizontal"] = random.choice(["СОНЦЕ", "КОД", "ART", "LOVE"])
        context.user_data["vertical"] = random.choice(["СОНЦЕ", "КОД", "ART", "LOVE"])
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

    if data == "enter_creator":
        await query.message.reply_text(
            "🧵 STITCH & CODE активовано.\nОбери дію:",
            reply_markup=persistent_menu()
        )
        return

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
            [InlineKeyboardButton("🟦 Індиго класика", callback_data="#1E3A8A")],
            [InlineKeyboardButton("⚪ Молочний", callback_data="#F8F5EC")],
            [InlineKeyboardButton("⚫ Сажа", callback_data="#111827")],
            [InlineKeyboardButton("🌿 Хвоя", callback_data="#065F46")],
            [InlineKeyboardButton("🌾 Гірчичний", callback_data="#B45309")],
            [InlineKeyboardButton("🔴 Бордо", callback_data="#8B0000")],
            [InlineKeyboardButton("🌸 Пудровий", callback_data="#BE185D")],
            [InlineKeyboardButton("💜 Сливовий", callback_data="#6B21A8")],
        ]

        await query.message.reply_text(
            "Обери колір нитки (Sashiko palette):",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

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


def main():
    if not TOKEN:
        raise ValueError("TOKEN не знайдено.")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
