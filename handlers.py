from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from datetime import date
from io import BytesIO
import matplotlib.pyplot as plt

from storage import users, save_users
from calculations import calculate_water_goal, calculate_calorie_goal
from food_api import search_food
from weather_api import get_temperature
import tempfile

router = Router()

# =========================
# FSM для профиля
# =========================
class ProfileStates(StatesGroup):
    sex = State()
    weight = State()
    height = State()
    age = State()
    activity = State()
    city = State()

# =========================
# FSM для еды
# =========================
class FoodStates(StatesGroup):
    choosing = State()
    weight = State()

# =========================
# FSM для тренировок
# =========================
class WorkoutStates(StatesGroup):
    type = State()
    duration = State()

# =========================
# FSM для воды
# =========================
class WaterStates(StatesGroup):
    amount = State()

# =========================
# Вспомогательные функции
# =========================
def check_daily_reset(uid: str):
    today = str(date.today())
    user = users[uid]
    if user.get("last_update") != today:
        yesterday = user.get("last_update")
        if yesterday:
            # сохраняем вчерашние данные в историю
            user.setdefault("history", {})[yesterday] = {
                "water": user.get("logged_water", 0),
                "calories": user.get("logged_calories", 0),
                "burned": user.get("burned_calories", 0)
            }
        # сброс значений на новый день
        user["logged_water"] = 0
        user["logged_calories"] = 0
        user["burned_calories"] = 0
        user["last_update"] = today
        save_users()

# =========================
# /start
# =========================
@router.message(Command("start"))
async def start(message: Message):
    uid = str(message.from_user.id)
    if uid not in users:
        users[uid] = {
            "weight": None, "height": None, "age": None,
            "activity": 0, "city": None, "sex": None,
            "water_goal": 0, "calorie_goal": 0,
            "logged_water": 0, "logged_calories": 0,
            "burned_calories": 0, "last_update": str(date.today()),
            "history": {}
        }
        save_users()
    await message.answer(
        "👋 Привет! Я бот для воды, калорий и тренировок.\n"
        "Используй /set_profile для настройки профиля.\n"
        "Доступные команды:\n"
        "/set_profile - Настройка профиля\n"
        "/log_water <мл> - Записать воду\n"
        "/log_food - Записать еду\n"
        "/log_workout - Записать тренировку\n"
        "/check_progress - Показать прогресс\n"
        "/history - Показать историю\n"
        "/plot <water/calories/burned> - График за последние дни"
    )

# =========================
# /set_profile
# =========================
@router.message(Command("set_profile"))
async def set_profile(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    if uid not in users:
        users[uid] = {"logged_water": 0, "logged_calories": 0, "burned_calories": 0}
        save_users()
    await message.answer("Введите ваш пол (муж/жен):")
    await state.set_state(ProfileStates.sex)

@router.message(ProfileStates.sex)
async def process_sex(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    sex_input = message.text.strip().lower()
    if sex_input in ["муж", "м", "мужской"]:
        sex = "male"
    elif sex_input in ["жен", "ж", "женский"]:
        sex = "female"
    else:
        await message.answer("Введите корректно: муж или жен")
        return
    await state.update_data(sex=sex)
    await message.answer("Введите ваш вес (кг):")
    await state.set_state(ProfileStates.weight)

@router.message(ProfileStates.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text)
        if weight <= 0: raise ValueError
    except ValueError:
        await message.answer("Введите корректный вес в кг (число > 0).")
        return
    await state.update_data(weight=weight)
    await message.answer("Введите ваш рост (см):")
    await state.set_state(ProfileStates.height)

@router.message(ProfileStates.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text)
        if height <= 0: raise ValueError
    except ValueError:
        await message.answer("Введите корректный рост в см (число > 0).")
        return
    await state.update_data(height=height)
    await message.answer("Введите ваш возраст:")
    await state.set_state(ProfileStates.age)

@router.message(ProfileStates.age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age <= 0: raise ValueError
    except ValueError:
        await message.answer("Введите корректный возраст (число > 0).")
        return
    await state.update_data(age=age)
    await message.answer("Сколько минут активности у вас в день?")
    await state.set_state(ProfileStates.activity)

@router.message(ProfileStates.activity)
async def process_activity(message: Message, state: FSMContext):
    try:
        activity = int(message.text)
        if activity < 0: raise ValueError
    except ValueError:
        await message.answer("Введите корректное количество минут активности (число >=0).")
        return
    await state.update_data(activity=activity)
    await message.answer("В каком городе вы находитесь?")
    await state.set_state(ProfileStates.city)

@router.message(ProfileStates.city)
async def process_city(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    city = message.text.strip()
    await state.update_data(city=city)

    data = await state.get_data()
    sex = data["sex"]
    weight = data["weight"]
    height = data["height"]
    age = data["age"]
    activity = data["activity"]

    temp = await get_temperature(city)
    water_goal = calculate_water_goal(weight, activity, temp)
    calorie_goal = calculate_calorie_goal(weight, height, age, activity, sex=sex)

    users[uid].update({
        "sex": sex,
        "weight": weight, "height": height, "age": age,
        "activity": activity, "city": city,
        "water_goal": water_goal, "calorie_goal": calorie_goal
    })
    save_users()

    await message.answer(
        f"✅ Профиль установлен!\n"
        f"💧 Вода: {water_goal:.0f} мл/день\n"
        f"🍽 Калории: {calorie_goal:.0f} ккал/день"
    )
    await state.clear()

# =========================
# /log_water
# =========================
@router.message(Command("log_water"))
async def log_water_start(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    if uid not in users:
        await message.answer("Сначала настройте профиль /set_profile")
        return

    check_daily_reset(uid)
    await message.answer("💧 Сколько воды вы выпили? (в мл)")
    await state.set_state(WaterStates.amount)

@router.message(WaterStates.amount)
async def process_water_amount(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    check_daily_reset(uid)

    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное количество воды в мл (число > 0).")
        return

    users[uid]["logged_water"] += amount
    save_users()

    left = max(0, users[uid]["water_goal"] - users[uid]["logged_water"])

    await message.answer(
        f"💧 Записано: {amount:.0f} мл\n"
        f"Всего сегодня: {users[uid]['logged_water']:.0f} мл\n"
        f"Осталось: {left:.0f} мл"
    )

    await state.clear()

# =========================
# /check_progress
# =========================
@router.message(Command("check_progress"))
async def check_progress(message: Message):
    uid = str(message.from_user.id)
    if uid not in users:
        await message.answer("Сначала настройте профиль /set_profile")
        return

    check_daily_reset(uid)
    u = users[uid]
    balance = u["calorie_goal"] - u["logged_calories"] + u["burned_calories"]
    left_water = max(0, u["water_goal"] - u["logged_water"])

    await message.answer(
        f"📊 Прогресс:\n"
        f"💧 Вода: {u['logged_water']:.0f} / {u['water_goal']:.0f} мл\n"
        f"Осталось: {left_water:.0f} мл\n"
        f"🍽 Калории: {u['logged_calories']:.0f} / {u['calorie_goal']:.0f} ккал\n"
        f"Сожжено: {u['burned_calories']:.0f} ккал\n"
        f"Баланс: {balance:.0f} ккал"
    )

# =========================
# /log_food
# =========================
@router.message(Command("log_food"))
async def log_food_start(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    if uid not in users:
        await message.answer("Сначала настройте профиль /set_profile")
        return

    check_daily_reset(uid)
    await message.answer("🍽 Введите название продукта:")
    await state.set_state(FoodStates.choosing)

@router.message(FoodStates.choosing)
async def process_food_choice(message: Message, state: FSMContext):
    query = message.text
    results = search_food(query, limit=5)
    if not results:
        await message.answer("❌ Продукт не найден.")
        return

    await state.update_data(results=results)

    buttons = [
        [InlineKeyboardButton(text=f"{name} — {cal} ккал/100г", callback_data=str(i))]
        for i, (name, cal) in enumerate(results)
    ]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выберите продукт:", reply_markup=markup)

@router.callback_query(F.data)
async def food_selected(callback: CallbackQuery, state: FSMContext):
    index = int(callback.data)
    data = await state.get_data()
    results = data.get("results", [])
    if index >= len(results):
        await callback.message.answer("Ошибка выбора.")
        return

    name, calories = results[index]
    await state.update_data(chosen_name=name, chosen_calories=calories)
    await callback.message.answer(f"{name} — {calories} ккал/100г\nСколько грамм?")
    await state.set_state(FoodStates.weight)

@router.message(FoodStates.weight)
async def process_food_weight(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    check_daily_reset(uid)

    try:
        grams = float(message.text)
        if grams <= 0: raise ValueError
    except ValueError:
        await message.answer("Введите число в граммах (число >0).")
        return

    data = await state.get_data()
    total_calories = data["chosen_calories"] * grams / 100
    users[uid]["logged_calories"] += total_calories
    save_users()
    await message.answer(f"✅ Записано: {total_calories:.1f} ккал")
    await state.clear()


# =========================
# /log_workout
# =========================
MET_VALUES = {
    "бег": 9.8,
    "ходьба": 3.5,
    "плавание": 8.0,
    "велосипед": 7.5,
    "йога": 3.0,
    "силовая тренировка": 6.0,
    "тренажер": 5.5,
}

@router.message(Command("log_workout"))
async def log_workout_start(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    if uid not in users:
        await message.answer("Сначала настройте профиль /set_profile")
        return

    check_daily_reset(uid)
    await message.answer("🏋️‍♂️ Введите тип тренировки (например, бег, йога, плавание):")
    await state.set_state(WorkoutStates.type)

@router.message(WorkoutStates.type)
async def process_workout_type(message: Message, state: FSMContext):
    workout_type = message.text.strip().lower()
    await state.update_data(type=workout_type)
    await message.answer("Введите длительность тренировки в минутах:")
    await state.set_state(WorkoutStates.duration)

@router.message(WorkoutStates.duration)
async def process_workout_duration(message: Message, state: FSMContext):
    uid = str(message.from_user.id)
    check_daily_reset(uid)

    try:
        duration = float(message.text)
        if duration <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите корректное время тренировки (число >0).")
        return

    user = users.get(uid)
    data = await state.get_data()
    workout_type = data.get("type", "тренировка")
    weight = user.get("weight", 70)

    met = MET_VALUES.get(workout_type, 6.0)
    burned_calories = (met * 3.5 * weight / 200) * duration
    water_added = 200 * (duration / 30)  # +200 мл за каждые 30 мин

    user["burned_calories"] += burned_calories
    user["water_goal"] += water_added
    save_users()

    await message.answer(
        f"🏃‍♂️ {workout_type.capitalize()} {duration:.0f} мин — {burned_calories:.0f} ккал сожжено.\n"
        f"💧 Цель по воде увеличена на {water_added:.0f} мл."
    )
    await state.clear()


# =========================
# /history
# =========================
@router.message(Command("history"))
async def show_history(message: Message):
    uid = str(message.from_user.id)
    if uid not in users:
        await message.answer("Сначала настройте профиль /set_profile")
        return

    user = users[uid]
    history = user.get("history", {})
    if not history:
        await message.answer("История пока пуста.")
        return

    text = "📅 История:\n"
    for d, stats in sorted(history.items()):
        text += f"{d} — 💧 {stats['water']:.0f} мл, 🍽 {stats['calories']:.0f} ккал, 🔥 {stats['burned']:.0f} ккал\n"
    await message.answer(text)

# =========================
# /plot <metric>
# =========================
@router.message(Command("plot"))
async def plot_metric(message: Message):
    args = message.text.split()
    if len(args) < 2 or args[1] not in ["water", "calories", "burned"]:
        await message.answer("Используйте: /plot water, /plot calories или /plot burned")
        return

    metric = args[1]
    uid = str(message.from_user.id)
    u = users.get(uid)
    if not u:
        await message.answer("Сначала настройте профиль /set_profile")
        return

    # История за последние 7 дней
    history_dict = u.get("history", {})
    sorted_dates = sorted(history_dict.keys())
    last_dates = sorted_dates[-7:]
    values = [history_dict[d].get(metric, 0) for d in last_dates]

    # Добавляем текущий день
    today_str = str(date.today())
    if today_str not in last_dates:
        last_dates.append(today_str)
        current_value = u.get(f"logged_{metric}" if metric != "burned" else "burned_calories", 0)
        values.append(current_value)
        if len(last_dates) > 7:
            last_dates = last_dates[-7:]
            values = values[-7:]

    # Рисуем график
    plt.figure(figsize=(8, 4))
    plt.plot(last_dates, values, marker="o")
    plt.title(f"{metric.capitalize()} за последние {len(last_dates)} дней")
    plt.xlabel("Дата")
    plt.ylabel(metric.capitalize())
    plt.grid(True)
    plt.tight_layout()

    # Сохраняем в временный файл
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
        plt.savefig(tmpfile.name)
        tmpfile_path = tmpfile.name
    plt.close()

    photo = FSInputFile(tmpfile_path)
    await message.answer_photo(photo=photo, caption=f"📊 {metric.capitalize()} за последние {len(last_dates)} дней")
