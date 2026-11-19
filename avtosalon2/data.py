"""Статичные данные автосалона: справочники, каталог-сид, новости, контакты.

Все динамические данные (автомобили, заявки, пользователи и т.д.) хранятся
в SQLite — см. db.py. Здесь только справочники и данные для первичного
заполнения базы.
"""

BRANDS = [
    "Audi", "BMW", "Chevrolet", "Ford", "Honda", "Hyundai", "Infiniti",
    "Jeep", "Kia", "LADA", "Lexus", "Mazda", "Mercedes-Benz", "Mitsubishi",
    "Nissan", "Renault", "Skoda", "Subaru", "Tesla", "Toyota", "Volkswagen", "Volvo",
]

BODY_TYPES = ["Седан", "Кроссовер", "Хэтчбек", "Универсал", "Купе", "Внедорожник"]
FUEL_TYPES = ["Бензин", "Дизель", "Гибрид", "Электро"]
TRANSMISSIONS = ["Механика", "Автомат"]
CONDITIONS = ["Новый", "С пробегом"]

# Латинские CSS-классы для кузовов: кириллица в классах ломает линтеры
# и невалидные селекторы в отдельных сборках.
BODY_CLASS = {
    "Седан": "sedan",
    "Кроссовер": "crossover",
    "Хэтчбек": "hatchback",
    "Универсал": "wagon",
    "Купе": "coupe",
    "Внедорожник": "suv",
}

BRAND_STYLE = {
    "Audi": ("#0f2b46", "#4fc3f7"),
    "BMW": ("#12325c", "#7fb3ff"),
    "Chevrolet": ("#0d3b66", "#f7b733"),
    "Ford": ("#0b2d4d", "#4db8ff"),
    "Honda": ("#1a2b4a", "#ff7b7b"),
    "Hyundai": ("#0f3350", "#5ad2ff"),
    "Infiniti": ("#2b2b3a", "#c9a227"),
    "Kia": ("#12324f", "#7dd3fc"),
    "LADA": ("#1f3a5f", "#9fb8d1"),
    "Lexus": ("#241d2f", "#c8a951"),
    "Mazda": ("#1a1f2b", "#e05b4b"),
    "Mercedes-Benz": ("#1b1f27", "#a9b4c4"),
    "Mitsubishi": ("#132a3f", "#e0553f"),
    "Nissan": ("#12233d", "#e34c3f"),
    "Skoda": ("#12343f", "#4db6ac"),
    "Subaru": ("#132a4a", "#9bc2e6"),
    "Tesla": ("#12303a", "#e82127"),
    "Toyota": ("#2b2f38", "#e03c31"),
    "Volkswagen": ("#16232f", "#7fa8d4"),
    "Volvo": ("#12242e", "#5f8fa8"),
}

CAR_COLORS = [
    {"name": "Белый", "hex": "#f2f4f7"},
    {"name": "Чёрный", "hex": "#1b1e24"},
    {"name": "Серый", "hex": "#8c939c"},
    {"name": "Серебристый", "hex": "#c3c8ce"},
    {"name": "Синий", "hex": "#1f4e8c"},
    {"name": "Красный", "hex": "#b32222"},
    {"name": "Зелёный", "hex": "#1e6b4f"},
    {"name": "Бежевый", "hex": "#d8c9ae"},
]


def _car(**kwargs):
    kwargs.setdefault("features", [])
    kwargs.setdefault("color", "Серебристый")
    kwargs.setdefault("vin", f"X{abs(hash(kwargs['model'])) % 10**12:012d}")
    return kwargs


CARS = [
    _car(id=1, brand="Toyota", model="Camry", year=2024, mileage=15000, price=3_500_000,
         body="Седан", fuel="Гибрид", transmission="Автомат", condition="С пробегом",
         engine="2.5 Hybrid", power=218, drive="Передний", country="Япония",
         description="Премиальный седан, идеален для семьи и бизнеса. Надёжность, комфорт и современный дизайн.",
         features=["Гибридная установка", "Кожаный салон", "Камера 360°", "Адаптивный круиз"]),
    _car(id=2, brand="BMW", model="X5", year=2023, mileage=22000, price=6_200_000,
         body="Кроссовер", fuel="Бензин", transmission="Автомат", condition="С пробегом",
         engine="3.0 Turbo", power=340, drive="Полный", country="Германия",
         description="Мощный и элегантный кроссовер для активного образа жизни.",
         features=["Полный привод xDrive", "Пневмоподвеска", "Панорамная крыша", "Bowers & Wilkins"]),
    _car(id=3, brand="Kia", model="Sportage", year=2024, mileage=8000, price=2_100_000,
         body="Кроссовер", fuel="Бензин", transmission="Автомат", condition="С пробегом",
         engine="1.6 T-GDI", power=180, drive="Полный", country="Корея",
         description="Компактный и экономичный кроссовер с высоким уровнем безопасности.",
         features=["ADAS", "Подогрев сидений", "Беспроводная зарядка"], color="Синий"),
    _car(id=4, brand="Lexus", model="ES", year=2023, mileage=18000, price=5_100_000,
         body="Седан", fuel="Гибрид", transmission="Автомат", condition="С пробегом",
         engine="2.5 Hybrid", power=215, drive="Передний", country="Япония",
         description="Роскошь и плавность хода. Идеальный выбор для премиум-сегмента.",
         features=["Кожа", "Проекционный дисплей", "Mark Levinson"], color="Чёрный"),
    _car(id=5, brand="Volkswagen", model="Passat", year=2024, mileage=10000, price=3_200_000,
         body="Универсал", fuel="Дизель", transmission="Автомат", condition="С пробегом",
         engine="2.0 TDI", power=200, drive="Передний", country="Германия",
         description="Надёжный и универсал для ежедневной эксплуатации и дальних поездок.",
         features=["Большой багажник", "Сенсорный дисплей", "Тяга прицепки"]),
    _car(id=6, brand="Nissan", model="Qashqai", year=2023, mileage=35000, price=1_950_000,
         body="Кроссовер", fuel="Бензин", transmission="Вариатор", condition="С пробегом",
         engine="1.5 VC-Turbo", power=190, drive="Передний", country="Япония",
         description="Отличный городской кроссовер для начинающих водителей.",
         features=["ProPILOT Assist", "Климат-контроль"]),
    _car(id=7, brand="Mercedes-Benz", model="C-Class", year=2024, mileage=5000, price=6_800_000,
         body="Седан", fuel="Бензин", transmission="Автомат", condition="С пробегом",
         engine="2.0 Turbo", power=258, drive="Задний", country="Германия",
         description="Современная элегантность и высокий статус.",
         features=["MBUX", "Матовая краска", "Пневмоподвеска"]),
    _car(id=8, brand="Hyundai", model="Creta", year=2023, mileage=45000, price=1_700_000,
         body="Кроссовер", fuel="Бензин", transmission="Механика", condition="С пробегом",
         engine="1.6", power=123, drive="Передний", country="Корея",
         description="Надёжный и доступный городской автомобиль.",
         features=["Тёплый салон", "Подогрев руля"]),
    _car(id=9, brand="Mazda", model="CX-5", year=2024, mileage=12000, price=3_800_000,
         body="Кроссовер", fuel="Бензин", transmission="Автомат", condition="С пробегом",
         engine="2.5 Turbo", power=256, drive="Полный", country="Япония",
         description="Спортивный и стильный кроссовер с отличной управляемостью.",
         features=["Система G-Vectoring", "Кожаный салон", "Стеклянная крыша"], color="Красный"),
    _car(id=10, brand="Jeep", model="Wrangler", year=2023, mileage=7000, price=6_500_000,
         body="Внедорожник", fuel="Бензин", transmission="Автомат", condition="С пробегом",
         engine="2.0 Turbo", power=272, drive="Полный", country="США",
         description="Внедорожник для любых приключений. Съёмные двери и крыша.",
         features=["Съёмная крыша", "Блокировки дифференциалов", "Тяга 1600 кг"], color="Зелёный"),
    _car(id=11, brand="Audi", model="A4", year=2024, mileage=9000, price=5_500_000,
         body="Седан", fuel="Бензин", transmission="Автомат", condition="С пробегом",
         engine="2.0 TFSI", power=265, drive="Полный", country="Германия",
         description="Совершенство немецкой инженерии и дизайна.",
         features=["Virtual Cockpit", " quattro", "Bang & Olufsen"]),
    _car(id=12, brand="Skoda", model="Octavia", year=2023, mileage=55000, price=2_500_000,
         body="Универсал", fuel="Бензин", transmission="Механика", condition="С пробегом",
         engine="1.5 TSI", power=150, drive="Передний", country="Чехия",
         description="Просторный и практичный автомобиль для большой семьи.",
         features=["600 л багажника", "Климат-контроль", "Эко-режим"]),
    _car(id=13, brand="Mitsubishi", model="Outlander", year=2024, mileage=18000, price=3_100_000,
         body="Кроссовер", fuel="Гибрид", transmission="Автомат", condition="С пробегом",
         engine="2.0 PHEV", power=213, drive="Полный", country="Япония",
         description="Надёжный и универсальный кроссовер с зарядкой от сети.",
         features=["PHEV-гибрид", "Электро-тёплый пол", "Камера 360°"], color="Белый"),
    _car(id=14, brand="Renault", model="Duster", year=2023, mileage=60000, price=1_500_000,
         body="Внедорожник", fuel="Бензин", transmission="Механика", condition="С пробегом",
         engine="1.6", power=117, drive="Передний", country="Франция",
         description="Бюджетный и проходимый автомобиль для города и дачи.",
         features=["Защита картера", "Режим 4x4 Lock", "Низкий расход"]),
    _car(id=15, brand="Ford", model="Focus", year=2024, mileage=7000, price=2_300_000,
         body="Универсал", fuel="Бензин", transmission="Автомат", condition="С пробегом",
         engine="1.5 EcoBoost", power=190, drive="Передний", country="США",
         description="Отличная управляемость и огромный запас запчастей.",
         features=["Ford SYNC 3", "Система Active Parking", "Зимний пакет"]),
    _car(id=16, brand="LADA", model="Granta", year=2023, mileage=85000, price=900_000,
         body="Седан", fuel="Бензин", transmission="Механика", condition="С пробегом",
         engine="1.6", power=90, drive="Передний", country="Россия",
         description="Самый бюджетный вариант для ежедневных поездок.",
         features=["Цена от 900 000 ₽", "Гарантия 3 года"]),
    _car(id=17, brand="Volkswagen", model="Polo", year=2024, mileage=5000, price=2_000_000,
         body="Хэтчбек", fuel="Бензин", transmission="Механика", condition="С пробегом",
         engine="1.4 TSI", power=150, drive="Передний", country="Германия",
         description="Идеальный городской автомобиль для первой машины.",
         features=["Компактный кузов", "Apple CarPlay", "Датчики парковки"]),
    _car(id=18, brand="Toyota", model="Corolla", year=2023, mileage=25000, price=2_900_000,
         body="Хэтчбек", fuel="Гибрид", transmission="Вариатор", condition="С пробегом",
         engine="1.8 Hybrid", power=122, drive="Передний", country="Япония",
         description="Легендарная надёжность и низкая стоимость владения.",
         features=["Гибрид", "Toyota Safety Sense", "Сервисное обслуживание 15 мин"]),
    _car(id=19, brand="BMW", model="3-Series", year=2024, mileage=8000, price=6_500_000,
         body="Седан", fuel="Бензин", transmission="Автомат", condition="С пробегом",
         engine="2.0 Turbo", power=258, drive="Задний", country="Германия",
         description="Баланс между спортивностью и комфортом.",
         features=["M Sport пакет", "Harman Kardon", "Адаптивная подвеска"]),
    _car(id=20, brand="Audi", model="Q5", year=2023, mileage=15000, price=5_800_000,
         body="Кроссовер", fuel="Дизель", transmission="Автомат", condition="С пробегом",
         engine="2.0 TDI", power=245, drive="Полный", country="Германия",
         description="Элегантный и технологичный кроссовер для семьи.",
         features=[" quattro", "Виртуальная приборная панель", "Пакет S line"]),
    _car(id=21, brand="Tesla", model="Model 3", year=2024, mileage=12000, price=5_400_000,
         body="Седан", fuel="Электро", transmission="Автомат", condition="С пробегом",
         engine="Электро 346 кВт", power=346, drive="Задний", country="США",
         description="Электрический седан с огромным запасом хода и автопилотом.",
         features=["Autopilot", "Запас хода 600 км", "Суперзарядка 250 кВт", "Обновления по воздуху"]),
    _car(id=22, brand="Volvo", model="XC60", year=2023, mileage=19000, price=4_900_000,
         body="Кроссовер", fuel="Гибрид", transmission="Автомат", condition="С пробегом",
         engine="2.0 T6 Recharge", power=320, drive="Полный", country="Швеция",
         description="Скандинавский комфорт и лучшая безопасность в классе.",
         features=["City Safety", "Кожаный салон", "Панорамная крыша"], color="Бежевый"),
    _car(id=23, brand="Infiniti", model="QX50", year=2023, mileage=20000, price=4_300_000,
         body="Кроссовер", fuel="Гибрид", transmission="Автомат", condition="С пробегом",
         engine="2.2 Hybrid", power=230, drive="Полный", country="Япония",
         description="Японский премиум-кроссовер с богатым оснащением.",
         features=["Премиум-аудио", "Проекционный HUD", "Кожа"]),
    _car(id=24, brand="Subaru", model="Forester", year=2024, mileage=16000, price=3_600_000,
         body="Внедорожник", fuel="Бензин", transmission="Автомат", condition="С пробегом",
         engine="2.0 Boxer", power=185, drive="Полный", country="Япония",
         description="Симметричный полный привод — уверенность на любом покрытии.",
         features=["Symmetrical AWD", "X-Mode", "Панорамная крыша"]),
    _car(id=25, brand="Honda", model="CR-V", year=2024, mileage=11000, price=2_950_000,
         body="Кроссовер", fuel="Гибрид", transmission="Автомат", condition="С пробегом",
         engine="2.0 e:HEV", power=184, drive="Полный", country="Япония",
         description="Просторный кроссовер с гибридной силовой установкой.",
         features=["Гибрид", "7 дюймов экрана", "Honda Sensing"]),
    _car(id=26, brand="Chevrolet", model="Cruze", year=2022, mileage=40000, price=1_850_000,
         body="Седан", fuel="Бензин", transmission="Автомат", condition="С пробегом",
         engine="1.5 Turbo", power=200, drive="Передний", country="США",
         description="Яркий примерён с атмосферным турбодвигателем и мультимедиа.",
         features=["MyLink", "Turbo", "Премиум-аудио"]),
    _car(id=27, brand="Kia", model="K5", year=2024, mileage=9000, price=2_600_000,
         body="Седан", fuel="Гибрид", transmission="Автомат", condition="С пробегом",
         engine="1.6 T-GDI HEV", power=195, drive="Передний", country="Корея",
         description="Спортивный седан с богатой мультимедийной системой.",
         features=["Палитра для интерьера", "Беспроводной CarPlay", "Kia Connect"], color="Серый"),
    _car(id=28, brand="BMW", model="i4", year=2024, mileage=6000, price=6_900_000,
         body="Седан", fuel="Электро", transmission="Автомат", condition="С пробегом",
         engine="Электро 250 кВт", power=340, drive="Задний", country="Германия",
         description="Электрическое гран-туризмо нового поколения.",
         features=["Запас хода 510 км", "iDrive 8", "Curved Display"]),
    _car(id=29, brand="Volkswagen", model="Tiguan", year=2023, mileage=27000, price=3_400_000,
         body="Кроссовер", fuel="Бензин", transmission="Автомат", condition="С пробегом",
         engine="2.0 TSI", power=220, drive="Полный", country="Германия",
         description="Семейный кроссовер с просторным салоном и полным приводом.",
         features=["DSG", "Подогрев сидений", "Три зоны климата"]),
    _car(id=30, brand="Toyota", model="Land Cruiser 200", year=2022, mileage=48000, price=8_400_000,
         body="Внедорожник", fuel="Дизель", transmission="Автомат", condition="С пробегом",
         engine="4.6 V8", power=318, drive="Полный", country="Япония",
         description="Легендарный рамный внедорожник для настоящих условий бездорожья.",
         features=["Тормоза TrailBlazer", "KDSS", "Гидравлика CCR"], color="Белый"),
]

NEWS = [
    {"date": "2026-09-20", "title": "В автосалоне пополнение: 4 новых кроссовера",
     "text": "Мы расширили ассортимент городских кроссоверов 2023–2024 годов выпуска. На все автомобили действует расширенная гарантия до 24 месяцев."},
    {"date": "2026-09-05", "title": "Запущена программа trade-in",
     "text": "Оцениваем ваш автомобиль за 30 минут и засчитываем стоимость в счёт покупки. Выкуп от 90% рыночной цены."},
    {"date": "2026-08-22", "title": "Сервисный центр работает без выходных",
     "text": "Запись на ТО и ремонт доступна с 08:00 до 21:00, включая воскресенье. Для клиентов автосалона — скидка 15% на первый визит."},
]

SERVICES = [
    ("Кредит под 4.9%", "Поможем подобрать выгодную программу финансирования от 7 банков-партнёров.", "₽/мес от 49 000"),
    ("Trade-in за 30 минут", "Быстрая и честная оценка вашего автомобиля, выкуп от 90% рыночной цены.", "Оценка 0 ₽"),
    ("Гарантия до 24 месяцев", "Расширенная гарантия на двигатель и трансмиссию с сервисным обслуживанием.", "До 24 мес."),
    ("Сервис и ремонт", "Оригинальные и качественные запчасти, диагностика на профессиональном оборудовании.", "Скидка 15%"),
]

CONTACTS = {
    "address": "г. Москва, ул. Автозаводская, д. 12",
    "phone": "+7 (495) 123-45-67",
    "email": "info@avtosalon.ru",
    "work": "Пн–Вс: 09:00 – 21:00",
    "inn": "7701234567",
    "ogrn": "1157746000000",
    "site": "avtosalon.ru",
}

# Версия телефона для ссылок tel: без пробелов и скобок
CONTACTS["phone_digits"] = "".join(ch for ch in CONTACTS["phone"] if ch.isdigit())


def brand_colors(brand):
    return BRAND_STYLE.get(brand, ("#1c2a3a", "#7fb3ff"))


def brand_accent(brand):
    """Акцентный цвет марки (второй элемент пары brand_colors)."""
    return brand_colors(brand)[1]


def brand_dark(brand):
    """Тёмный цвет марки (первый элемент пары brand_colors)."""
    return brand_colors(brand)[0]


def body_class(body):
    """CSS-класс кузова на латинице."""
    return BODY_CLASS.get(body, "sedan")


def price_label(value):
    return f"{value:,}".replace(",", " ") + " ₽"
