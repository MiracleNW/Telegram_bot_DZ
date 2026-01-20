import os
import asyncio
import logging
import aiogram
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from handlers import router

logging.basicConfig(level=logging.DEBUG)  # ← DEBUG, чтобы видеть всё
logger = logging.getLogger(__name__)

logger.info("Старт приложения")
logger.info(f"PORT из env: {os.environ.get('PORT', 'не задан')}")
logger.info(f"BOT_TOKEN: {'задан' if os.environ.get('BOT_TOKEN') else 'НЕ ЗАДАН'}")
logger.info(f"BUCKET_NAME: {os.environ.get('BUCKET_NAME', 'не задан')}")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    logger.critical("BOT_TOKEN не задан!")
    raise ValueError("BOT_TOKEN is required")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
if not WEBHOOK_URL:
    logger.critical("WEBHOOK_URL не задан!")
    raise ValueError("WEBHOOK_URL is required")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)

async def on_startup():
    desired_url = f"{WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"  # убираем лишний слеш если был
    logger.info("Пытаюсь установить/проверить webhook: %s", desired_url)
    
    try:
        current = await bot.get_webhook_info()
        
        if current.url == desired_url:
            logger.info("Webhook уже стоит правильно, пропускаем")
            return
        
        logger.info("Текущий webhook: %s → ставим новый", current.url)
        await bot.set_webhook(url=desired_url)
        logger.info("Webhook успешно установлен!")
        
    except aiogram.exceptions.TelegramRetryAfter as e:
        logger.warning("Флуд, ждём %d сек", e.retry_after)
        await asyncio.sleep(e.retry_after + 1)
        try:
            await bot.set_webhook(url=desired_url)
            logger.info("Webhook установлен после ожидания")
        except Exception as retry_e:
            logger.error("Повторная попытка упала: %s", retry_e)
    
    except Exception as e:
        logger.exception("Ошибка установки webhook: %s", e)

async def main():
    app = web.Application()

    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"Сервер запущен на порту {port}")

    await on_startup()

    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        asyncio.run(on_shutdown())