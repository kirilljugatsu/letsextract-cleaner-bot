"""Telegram bot entry point for LetsExtract Cleaner Bot."""
from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from cleaner import DataCleaner
from config import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    TEMP_DIR,
    TELEGRAM_BOT_TOKEN,
)

# Configure logging once for the entire application.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    message = (
        "Привет! Я бот для очистки выгрузок LetsExtract.\n\n"
        "Отправьте мне Excel файл (.xlsx или .xls), и я удалю мусорные записи,"
        " оставлю только релевантные домены и пришлю результат."
    )
    await update.message.reply_text(message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    message = (
        "ℹ️ Как использовать бота:\n"
        "1. Отправьте файл Excel с колонками: Значение, Домен, Заголовок, META Description.\n"
        "2. Размер файла не должен превышать 10 MB.\n"
        "3. Дополнительные колонки будут удалены автоматически.\n\n"
        "После обработки вы получите очищенный файл и статистику."
    )
    await update.message.reply_text(message)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process an incoming Excel document."""
    if not update.message or not update.message.document:
        return

    document = update.message.document
    file_name = document.file_name or "file.xlsx"
    file_extension = Path(file_name).suffix.lower()

    if document.file_size and document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text("❌ Файл слишком большой. Максимальный размер — 10 MB.")
        return

    if file_extension not in ALLOWED_EXTENSIONS:
        await update.message.reply_text("❌ Неверный формат файла. Отправьте .xlsx или .xls.")
        return

    processing_message = await update.message.reply_text("⏳ Обрабатываю файл...")

    unique_id = uuid4().hex
    user_id = update.effective_user.id if update.effective_user else "anonymous"
    temp_input_path = TEMP_DIR / f"{user_id}_{unique_id}{file_extension}"
    cleaned_file_name = f"cleaned_{Path(file_name).stem}.xlsx"
    temp_output_path = TEMP_DIR / cleaned_file_name

    try:
        telegram_file = await document.get_file()
        await telegram_file.download_to_drive(custom_path=str(temp_input_path))

        data_cleaner = DataCleaner()
        data_cleaner.clean_file(temp_input_path, temp_output_path)

        stats_message = data_cleaner.get_stats_message()
        await update.message.reply_text(stats_message)

        with temp_output_path.open("rb") as cleaned_file:
            await update.message.reply_document(
                document=cleaned_file,
                filename=cleaned_file_name,
                caption="Готово! Вот очищенный файл.",
            )
    except ValueError as exc:
        logger.error("Validation error while cleaning file: %s", exc)
        await update.message.reply_text(f"❌ Ошибка: {exc}")
    except Exception as exc:  # pragma: no cover - runtime safety
        logger.error("Unexpected error: %s", exc, exc_info=True)
        await update.message.reply_text(
            "❌ Произошла непредвиденная ошибка при обработке файла. Попробуйте позже."
        )
    finally:
        try:
            if processing_message:
                await processing_message.delete()
        except Exception:  # pragma: no cover - best effort cleanup of message
            pass

        for path in [temp_input_path, temp_output_path]:
            try:
                if path.exists():
                    path.unlink()
            except Exception:  # pragma: no cover - filesystem cleanup
                logger.warning("Failed to delete temporary file %s", path)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask the user to send a file when they send plain text."""
    if not update.message:
        return

    await update.message.reply_text(
        "Я умею обрабатывать только Excel файлы. Пожалуйста, отправьте документ."
    )


def main() -> None:
    """Entry point for running the bot."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN не задан. Установите переменную окружения перед запуском."
        )

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text,
        )
    )

    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
