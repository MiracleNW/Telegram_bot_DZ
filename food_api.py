import requests

def search_food(name: str, limit: int = 5):
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        "search_terms": name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": limit
    }
    r = requests.get(url, params=params)
    data = r.json()
    products = data.get("products")
    if not products:
        return []

    result = []
    for product in products:
        nutriments = product.get("nutriments", {})
        calories = (
            nutriments.get("energy-kcal_100g") or
            nutriments.get("energy-kcal") or
            nutriments.get("energy-kcal_value") or
            nutriments.get("energy-kcal_value_computed") or
            # если есть только кДж — грубо переводим (1 ккал ≈ 4.184 кДж)
            (nutriments.get("energy_100g") / 4.184 if nutriments.get("energy_100g") else None) or
            0
        )
        if calories is None:
            calories = 0
        name = product.get("product_name", "Без имени")
        result.append((name, calories))
    return result
