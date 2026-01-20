def calculate_water_goal(weight, activity_minutes, temp):
    water = weight * 30  # базовая норма мл
    water += (activity_minutes // 30) * 500  # +500 мл за каждые 30 мин активности

    # корректировка по погоде
    if temp > 30:
        water += 1000
    elif temp > 25:
        water += 500

    return water


def calculate_calorie_goal(weight, height, age, activity_minutes, sex="male"):
    # BMR
    if sex == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    # Перевод минут активности в коэффициент PAL
    if activity_minutes <= 30:
        pal = 1.2
    elif activity_minutes <= 60:
        pal = 1.375
    elif activity_minutes <= 90:
        pal = 1.55
    elif activity_minutes <= 120:
        pal = 1.725
    else:
        pal = 1.9

    return bmr * pal
