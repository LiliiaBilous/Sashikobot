import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

# =========================
# СТАНИ
# =========================
user_state = {}
user_data = {}

# Кольори ниток
THREAD_COLORS = [
    "Білий",
    "Золотий",
    "Червоний",
    "Бордовий",
    "Темно зелений",
    "Чорний",
    "Темно синій",
    "Коричневий",
]

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привіт 🌸 Напиши 'Сашіко', щоб почати."
    )


# =========================
# ОБРОБКА ТЕКСТУ
# =========================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id

    # Якщо написали "Сашіко"
    if text.lower() == "сашіко":
        user_state[user_id] = "choose_type"

        keyboard = [["Постер", "Схема"]]
        await update.message.reply_text(
            "✨ Вітаю у генераторі Сашіко!\n\nОберіть що хочете створити:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        )
        return

    # =========================
    # ВИБІР ТИПУ
    # =========================
    if user_state.get(user_id) == "choose_type":

        if text == "Постер":
            user_data[user_id] = {"type": "poster"}
            user_state[user_id] = "choose_thread"

            keyboard = [[color] for color in THREAD_COLORS]

            await update.message.reply_text(
                "Оберіть колір ниток:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            )
            return

        if text == "Схема":
            user_data[user_id] = {"type": "scheme"}
            user_state[user_id] = "enter_text"

            await update.message.reply_text("Введіть текст для схеми:")
            return

    # =========================
    # ВИБІР КОЛЬОРУ
    # =========================
    if user_state.get(user_id) == "choose_thread":

        if text in THREAD_COLORS:
            user_data[user_id]["thread_color"] = text
            user_state[user_id] = "choose_fabric"

            keyboard = [["Білий льон", "Натуральний льон"]]

            await update.message.reply_text(
                "Оберіть тканину:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            )
            return

    # =========================
    # ВИБІР ТКАНИНИ
    # =========================
    if user_state.get(user_id) == "choose_fabric":

        user_data[user_id]["fabric"] = text
        user_state[user_id] = "enter_text"

        await update.message.reply_text("Тепер введіть текст для постера:")
        return

    # =========================
    # ВВІД ТЕКСТУ
    # =========================
    if user_state.get(user_id) == "enter_text":

        user_data[user_id]["final_text"] = text

        data = user_data[user_id]

        if data["type"] == "poster":
            await update.message.reply_text(
                f"✅ Постер створено!\n\n"
                f"Текст: {data['final_text']}\n"
                f"Колір ниток: {data.get('thread_color')}\n"
                f"Тканина: {data.get('fabric')}"
            )
        else:
            await update.message.reply_text(
                f"✅ Схема створена!\n\n"
                f"Текст: {data['final_text']}"
            )

        user_state[user_id] = None
        user_data[user_id] = {}
        return


# =========================
# ГОЛОВНА ФУНКЦІЯ
# =========================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Бот запущено...")
    app.run_polling()


if __name__ == "__main__":
    main()
