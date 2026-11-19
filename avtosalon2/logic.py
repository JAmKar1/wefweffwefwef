"""Бизнес-логика: кредитный калькулятор, trade-in, сравнение, пагинация."""

import math


# --------------------------------------------------------------------------
# Кредитный калькулятор (аннуитетный платёж)
# --------------------------------------------------------------------------
def credit_payment(price, down_payment, years, rate):
    """Аннуитетный платёж в месяц.

    price        — стоимость автомобиля, ₽
    down_payment — первоначальный взнос, ₽
    years        — срок в годах
    rate         — процентная ставка годовых
    """
    body = max(price - down_payment, 0)
    if body <= 0 or years <= 0:
        return 0.0

    months = years * 12
    monthly_rate = rate / 100 / 12
    if monthly_rate == 0:
        return body / months

    factor = (1 + monthly_rate) ** months
    return body * monthly_rate * factor / (factor - 1)


def credit_schedule(price, down_payment, years, rate):
    """График платежей: (номер, платёж, проценты, тело, остаток)."""
    body = max(price - down_payment, 0)
    monthly = credit_payment(price, down_payment, years, rate)
    if monthly <= 0:
        return []

    months = years * 12
    monthly_rate = rate / 100 / 12
    rows, balance = [], body

    for n in range(1, months + 1):
        interest = balance * monthly_rate
        principal = monthly - interest
        if principal > balance:
            principal = balance
        balance -= principal
        rows.append((n, monthly, interest, principal, max(balance, 0)))
    return rows


def credit_summary(price, down_payment, years, rate):
    """Итоги: переплата, полная сумма, эффективная ставка."""
    monthly = credit_payment(price, down_payment, years, rate)
    body = max(price - down_payment, 0)
    total = monthly * years * 12
    overpay = total - body
    return {
        "monthly": round(monthly),
        "total": round(total),
        "overpay": round(overpay),
        "body": round(body),
        "months": years * 12,
    }


# --------------------------------------------------------------------------
# Trade-in
# --------------------------------------------------------------------------
def trade_in_value(year, mileage, brand_group, condition="С пробегом", fuel="Бензин"):
    """Оценочная стоимость автомобиля для trade-in.

    Используется упрощённая модель: базовая стоимость по классу марки,
    амортизация по возрасту и пробегу, поправки на топливо и состояние.
    """
    base = {
        "premium": 4_200_000,   # BMW, Mercedes, Audi, Lexus, Porsche
        "mid": 2_100_000,       # Volkswagen, Skoda, Toyota, Honda, Mazda
        "main": 1_350_000,      # Hyundai, Kia, Nissan, Renault, LADA
    }.get(brand_group, 1_500_000)

    age = max(2026 - year, 0)
    depreciation = max(1 - 0.11 * age, 0.12)      # ~11% в год
    km_factor = max(1 - (mileage / 100_000) * 0.08, 0.35)  # износ по пробегу
    fuel_factor = {"Электро": 0.95, "Гибрид": 1.05, "Дизель": 0.92, "Бензин": 1.0}.get(
        fuel, 1.0)
    state_factor = 1.0 if condition == "Новый" else 0.95

    return int(base * depreciation * km_factor * fuel_factor * state_factor)


def brand_group(brand):
    premium = {"BMW", "Mercedes-Benz", "Audi", "Lexus", "Infiniti", "Volvo", "Tesla"}
    mid = {"Volkswagen", "Skoda", "Toyota", "Honda", "Mazda", "Subaru", "Mitsubishi"}
    if brand in premium:
        return "premium"
    if brand in mid:
        return "mid"
    return "main"


# --------------------------------------------------------------------------
# Сравнение
# --------------------------------------------------------------------------
COMPARE_FIELDS = [
    ("brand", "Марка", False),
    ("model", "Модель", False),
    ("year", "Год выпуска", False),
    ("mileage", "Пробег", True),
    ("price", "Цена", True),
    ("body", "Кузов", False),
    ("fuel", "Топливо", False),
    ("transmission", "Коробка", False),
    ("engine", "Двигатель", False),
    ("power", "Мощность, л.с.", True),
    ("drive", "Привод", False),
    ("country", "Страна", False),
    ("condition", "Состояние", False),
    ("color", "Цвет", False),
    ("vin", "VIN", False),
]

_COMPARE_NUMERIC = {"year", "mileage", "price", "power"}


def compare_cars(cars):
    """Готовит строки таблицы сравнения и отмечает лучший вариант в каждой строке."""
    if len(cars) < 2:
        return [], []

    rows, diffs = [], []
    for key, label, higher_is_better in COMPARE_FIELDS:
        values = [c.get(key) for c in cars]
        if len(set(map(str, values))) > 1:
            diffs.append(label)

        best = None
        if key in _COMPARE_NUMERIC and all(isinstance(v, (int, float)) for v in values):
            best = max(values) if higher_is_better else min(values)

        rows.append({
            "key": key,
            "label": label,
            "values": values,
            "best": best,
            "is_diff": len(set(map(str, values))) > 1,
        })
    return rows, diffs


# --------------------------------------------------------------------------
# Пагинация
# --------------------------------------------------------------------------
def paginate(total, page, per_page):
    pages = max(math.ceil(total / per_page), 1)
    page = min(max(page, 1), pages)
    start = (page - 1) * per_page + 1
    end = min(page * per_page, total)
    return {
        "page": page,
        "pages": pages,
        "per_page": per_page,
        "total": total,
        "start": start if total else 0,
        "end": end,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev": page - 1,
        "next": page + 1,
    }


def page_url_args(args, page):
    """Строит набор GET-параметров для ссылки на страницу пагинации.

    Ключ 'page' сюда не входит: шаблон передаёт номер страницы отдельно
    (url_for('catalog', page=N, **page_args)), иначе Jinja2 упадёт
    с 'got multiple values for keyword argument page'.
    """
    return {k: v for k, v in args.items()
            if k not in ("page",) and v not in (None, "", "all")}
