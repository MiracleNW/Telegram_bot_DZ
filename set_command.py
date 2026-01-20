import asyncio
import os
from aiogram import Bot
from aiogram.types import BotCommand
from dotenv import load_dotenv

load_dotenv()

async def main():
    bot = Bot(os.getenv("BOT_TOKEN"))
    await bot.set_my_commands([
        BotCommand(command="/start", description="Приветствие и создание профиля"),
        BotCommand(command="/set_profile", description="Настроить профиль"),
        BotCommand(command="/log_water", description="Записать воду"),
        BotCommand(command="/log_food", description="Записать еду"),
        BotCommand(command="/log_workout", description="Записать тренировку"),
        BotCommand(command="/check_progress", description="Показать прогресс"),
        BotCommand(command="/history", description="История"),
        BotCommand(command="/plot", description="График"),
    ])
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
