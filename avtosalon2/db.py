"""Слой базы данных на чистом SQL (sqlite3), без внешних ORM.

Схема создаётся автоматически при первом запуске, данные заполняются
из data.py. Все функции возвращают обычные словари (dict) — шаблоны
работают с ними так же, как раньше.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import data

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "avtosalon.db")

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    phone         TEXT,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user',
    created_at    TEXT NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS cars (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    brand         TEXT NOT NULL,
    model         TEXT NOT NULL,
    year          INTEGER NOT NULL,
    mileage       INTEGER NOT NULL DEFAULT 0,
    price         INTEGER NOT NULL,
    body          TEXT NOT NULL,
    fuel          TEXT NOT NULL,
    transmission  TEXT NOT NULL,
    condition     TEXT NOT NULL DEFAULT 'С пробегом',
    engine        TEXT,
    power         INTEGER DEFAULT 0,
    drive         TEXT,
    country       TEXT,
    color         TEXT,
    vin           TEXT,
    description   TEXT,
    features      TEXT DEFAULT '',
    photo         TEXT,
    views         INTEGER NOT NULL DEFAULT 0,
    is_active     INTEGER NOT NULL DEFAULT 1,
    is_sold       INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS photos (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id   INTEGER NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    is_main  INTEGER NOT NULL DEFAULT 0,
    sort     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS reviews (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id     INTEGER NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    author     TEXT NOT NULL,
    rating     INTEGER NOT NULL DEFAULT 5,
    text       TEXT NOT NULL,
    is_moderated INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    car_id     INTEGER REFERENCES cars(id) ON DELETE SET NULL,
    name       TEXT NOT NULL,
    phone      TEXT NOT NULL,
    email      TEXT,
    message    TEXT,
    kind       TEXT NOT NULL DEFAULT 'order',
    status     TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS favorites (
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    car_id     INTEGER NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, car_id)
);

CREATE TABLE IF NOT EXISTS news (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    published  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cars_brand  ON cars(brand);
CREATE INDEX IF NOT EXISTS idx_cars_price  ON cars(price);
CREATE INDEX IF NOT EXISTS idx_reviews_car ON reviews(car_id);
CREATE INDEX IF NOT EXISTS idx_orders_car ON orders(car_id);
"""


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    # LIKE в SQLite не различает регистр только для латиницы — подключаем свой lower
    conn.create_function("ulower", 1, lambda v: (v or "").lower())
    return conn


@contextmanager
def db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Инициализация
# --------------------------------------------------------------------------
def init_db():
    """Создаёт таблицы и наполняет их данными (один раз)."""
    with db() as conn:
        conn.executescript(SCHEMA)

        if conn.execute("SELECT COUNT(*) FROM cars").fetchone()[0] == 0:
            conn.executemany(
                """INSERT INTO cars (brand, model, year, mileage, price, body, fuel,
                       transmission, condition, engine, power, drive, country, color,
                       vin, description, features, photo, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [(
                    c["brand"], c["model"], c["year"], c["mileage"], c["price"],
                    c["body"], c["fuel"], c["transmission"], c["condition"],
                    c["engine"], c["power"], c["drive"], c["country"], c["color"],
                    c["vin"], c["description"], ", ".join(c["features"]),
                    c.get("photo"), now(),
                ) for c in data.CARS])

        if conn.execute("SELECT COUNT(*) FROM news").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO news (title, body, created_at) VALUES (?,?,?)",
                [(n["title"], n["text"], n["date"]) for n in data.NEWS])

        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            from werkzeug.security import generate_password_hash
            conn.execute(
                "INSERT INTO users (name, email, phone, password_hash, role, created_at)"
                " VALUES (?,?,?,?,?,?)",
                ("Администратор", "admin@avtosalon.ru", "+7 (495) 123-45-67",
                 generate_password_hash("admin123"), "admin", now()))


# --------------------------------------------------------------------------
# Преобразование строк БД в словари
# --------------------------------------------------------------------------
def car_row(row):
    if row is None:
        return None
    c = dict(row)
    c["features"] = [f.strip() for f in (c.get("features") or "").split(",") if f.strip()]
    c["title"] = f"{c['brand']} {c['model']}"
    c["url"] = f"/car/{c['id']}"
    return c


def review_row(row):
    d = dict(row)
    d["date"] = d["created_at"][:10]
    return d


# --------------------------------------------------------------------------
# Пользователи
# --------------------------------------------------------------------------
def get_user(user_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_email(email):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE",
                           (email.strip(),)).fetchone()
        return dict(row) if row else None


def create_user(name, email, phone, password_hash, role="user"):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO users (name, email, phone, password_hash, role, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (name.strip(), email.strip(), (phone or "").strip(), password_hash, role, now()))
        return cur.lastrowid


def user_exists(email):
    return get_user_by_email(email) is not None


def change_password(user_id, password_hash):
    with db() as conn:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, user_id))


def toggle_user_active(user_id):
    with db() as conn:
        conn.execute("UPDATE users SET is_active = 1 - is_active WHERE id=?", (user_id,))


def set_user_role(user_id, role):
    with db() as conn:
        conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))


def all_users():
    with db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC")]


def count_users():
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


# --------------------------------------------------------------------------
# Автомобили
# --------------------------------------------------------------------------
SORTS = {
    "price_asc": "price ASC",
    "price_desc": "price DESC",
    "year_desc": "year DESC, price ASC",
    "year_asc": "year ASC",
    "mileage_asc": "mileage ASC",
    "mileage_desc": "mileage DESC",
    "power_desc": "power DESC",
    "model_asc": "brand ASC, model ASC",
    "rating_desc": "(SELECT ROUND(AVG(rating),2) FROM reviews WHERE reviews.car_id=cars.id) DESC",
}

CAR_FIELDS = ("brand", "model", "year", "mileage", "price", "body", "fuel",
              "transmission", "condition", "engine", "power", "drive",
              "country", "color", "vin", "description", "features")

FACET_FIELDS = ("brand", "body", "fuel", "transmission", "condition", "drive", "country", "color")


def all_cars(include_inactive=False):
    sql = "SELECT * FROM cars"
    if not include_inactive:
        sql += " WHERE is_active=1"
    sql += " ORDER BY brand, model"
    with db() as conn:
        return [car_row(r) for r in conn.execute(sql)]


def get_car(car_id):
    with db() as conn:
        return car_row(conn.execute("SELECT * FROM cars WHERE id=? AND is_active=1",
                                    (car_id,)).fetchone())


def active_cars():
    """Только не проданные — для подборов и сравнения."""
    with db() as conn:
        return [car_row(r) for r in conn.execute(
            "SELECT * FROM cars WHERE is_active=1 AND is_sold=0 ORDER BY brand, model")]


def count_cars():
    with db() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM cars WHERE is_active=1 AND is_sold=0").fetchone()[0]


def count_all_cars():
    with db() as conn:
        return conn.execute("SELECT COUNT(*) FROM cars").fetchone()[0]


def _plain(value):
    """Возвращает value как обычную строку: MultiDict-списки -> первый элемент."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    return value if isinstance(value, str) else str(value)


# Русские написания марок и моделей -> как они записаны в базе
RU_ALIASES = {
    "тойота": "toyota", "тоета": "toyota", "камри": "camry", "королла": "corolla", "ленд крузер": "land cruiser",
    "бмв": "bmw", "бэха": "bmw", "мерседес": "mercedes", "мерс": "mercedes", "ауди": "audi",
    "фольксваген": "volkswagen", "поло": "polo", "тигуан": "tiguan", "пассат": "passat",
    "шкода": "skoda", "октавия": "octavia", "киа": "kia", "хендай": "hyundai", "хёндэ": "hyundai",
    "хундай": "hyundai", "крета": "creta", "ниссан": "nissan", "кашкай": "qashqai", "рено": "renault",
    "дастер": "duster", "лада": "lada", "гранта": "granta", "мазда": "mazda", "хонда": "honda",
    "форд": "ford", "фокус": "focus", "шевроле": "chevrolet", "круз": "cruze", "лексус": "lexus",
    "вольво": "volvo", "тесла": "tesla", "субару": "subaru", "форестер": "forester", "джип": "jeep",
    "инфинити": "infiniti", "митсубиси": "mitsubishi", "аутлендер": "outlander", "спортейдж": "sportage",
}


def _norm_query(q):
    q = (q or "").strip().lower().replace("ё", "е")
    for ru, lat in RU_ALIASES.items():
        q = q.replace(ru.replace("ё", "е"), lat)
    return q


def search_cars(params, page=1, per_page=12):
    """Каталог: фильтры, поиск, сортировка, пагинация. Возвращает (items, total)."""
    where, args = ["is_active=1"], []

    q = _plain(params.get("q")).strip()
    if q:
        nq = _norm_query(q)
        where.append("(ulower(brand) LIKE ? OR ulower(model) LIKE ? OR ulower(brand||' '||model) LIKE ?"
                     " OR ulower(description) LIKE ? OR ulower(vin) LIKE ? OR ulower(body) LIKE ?)")
        args += [f"%{nq}%"] * 6

    for field in ("brand", "body", "fuel", "transmission", "condition", "country", "drive"):
        value = _plain(params.get(field))
        if value and value != "all":
            where.append(f"{field}=?")
            args.append(value)

    for key, op, col in (("min_price", ">=", "price"), ("max_price", "<=", "price"),
                         ("min_year", ">=", "year"), ("max_year", "<=", "year"),
                         ("min_mileage", ">=", "mileage"), ("max_mileage", "<=", "mileage"),
                         ("min_power", ">=", "power")):
        value = _plain(params.get(key)).strip()
        if value.isdigit():
            where.append(f"{col} {op} ?")
            args.append(int(value))

    if _plain(params.get("only_available")) == "1":
        where.append("is_sold=0")
    if _plain(params.get("has_photo")) == "1":
        where.append("photo IS NOT NULL")

    brands = params.getlist("brands") if hasattr(params, "getlist") else []
    if brands:
        where.append(f"brand IN ({','.join('?' * len(brands))})")
        args += [_plain(b) for b in brands]

    clause = " AND ".join(where)
    order = SORTS.get(_plain(params.get("sort")) or "price_asc", SORTS["price_asc"])

    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM cars WHERE {clause}",
                             args).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM cars WHERE {clause} ORDER BY {order} LIMIT ? OFFSET ?",
            args + [per_page, (page - 1) * per_page])
        return [car_row(r) for r in rows], total


def facets(field):
    """Список уникальных значений поля со счётчиками — для умных фильтров."""
    if field not in FACET_FIELDS:
        raise ValueError(f"Недопустимое поле для фасетов: {field!r}")
    with db() as conn:
        rows = conn.execute(
            f"SELECT {field} AS value, COUNT(*) AS n FROM cars"
            " WHERE is_active=1 GROUP BY value ORDER BY n DESC, value").fetchall()
        return [{"value": r["value"], "count": r["n"]} for r in rows if r["value"]]


def price_range():
    with db() as conn:
        r = conn.execute(
            "SELECT MIN(price) AS lo, MAX(price) AS hi FROM cars WHERE is_active=1").fetchone()
        return r["lo"] or 0, r["hi"] or 0


def year_range():
    with db() as conn:
        r = conn.execute(
            "SELECT MIN(year) AS lo, MAX(year) AS hi FROM cars WHERE is_active=1").fetchone()
        return r["lo"] or 2020, r["hi"] or 2026


def increment_views(car_id):
    with db() as conn:
        conn.execute("UPDATE cars SET views = views + 1 WHERE id=?", (car_id,))


def similar_cars(car, limit=3):
    with db() as conn:
        rows = conn.execute(
            """SELECT * FROM cars WHERE id != ? AND is_active=1
               ORDER BY (body=? ) DESC, (brand=?) DESC, ABS(price-?) ASC
               LIMIT ?""",
            (car["id"], car["body"], car["brand"], car["price"], limit)).fetchall()
        return [car_row(r) for r in rows]


def popular_cars(limit=3):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM cars WHERE is_active=1 ORDER BY views DESC, id LIMIT ?",
            (limit,)).fetchall()
        return [car_row(r) for r in rows]


def search_suggestions(query, limit=6):
    query = _norm_query(query)
    if len(query) < 1:
        return []
    with db() as conn:
        rows = conn.execute(
            "SELECT id, brand, model FROM cars WHERE is_active=1"
            " AND (ulower(brand) LIKE ? OR ulower(model) LIKE ? OR ulower(brand||' '||model) LIKE ?)"
            " ORDER BY views DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", f"%{query}%", limit)).fetchall()
    return [{"title": f"{r['brand']} {r['model']}", "url": f"/car/{r['id']}"} for r in rows]


# --------------------------------------------------------------------------
# Админ: CRUD автомобилей
# --------------------------------------------------------------------------
def create_car(values):
    features = values.get("features") or ""
    if isinstance(features, list):
        features = ", ".join(features)
    payload = dict(values)
    payload["features"] = features
    with db() as conn:
        cur = conn.execute(
            f"""INSERT INTO cars ({','.join(CAR_FIELDS)}, created_at)
                VALUES ({','.join('?' * len(CAR_FIELDS))}, ?)""",
            [payload.get(f) for f in CAR_FIELDS] + [now()])
        return cur.lastrowid


def update_car(car_id, values):
    features = values.get("features") or ""
    if isinstance(features, list):
        features = ", ".join(features)
    payload = dict(values)
    payload["features"] = features
    with db() as conn:
        conn.execute(
            f"UPDATE cars SET {','.join(f'{f}=?' for f in CAR_FIELDS)} WHERE id=?",
            [payload.get(f) for f in CAR_FIELDS] + [car_id])


def delete_car(car_id):
    with db() as conn:
        conn.execute("DELETE FROM cars WHERE id=?", (car_id,))


def set_car_photo(car_id, filename):
    with db() as conn:
        conn.execute("UPDATE cars SET photo=? WHERE id=?", (filename, car_id))


def toggle_sold(car_id):
    with db() as conn:
        conn.execute("UPDATE cars SET is_sold = 1 - is_sold WHERE id=?", (car_id,))


def toggle_active(car_id):
    with db() as conn:
        conn.execute("UPDATE cars SET is_active = 1 - is_active WHERE id=?", (car_id,))


# --------------------------------------------------------------------------
# Отзывы
# --------------------------------------------------------------------------
def add_review(car_id, author, rating, text, user_id=None):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO reviews (car_id, user_id, author, rating, text, created_at)"
            " VALUES (?,?,?,?,?,?)",
            (car_id, user_id, author, rating, text, now()))
        return cur.lastrowid


def car_reviews(car_id):
    with db() as conn:
        return [review_row(r) for r in conn.execute(
            "SELECT * FROM reviews WHERE car_id=? AND is_moderated=1"
            " ORDER BY created_at DESC", (car_id,))]


def car_rating(car_id):
    with db() as conn:
        r = conn.execute(
            "SELECT COUNT(*) AS n, ROUND(AVG(rating),1) AS avg FROM reviews"
            " WHERE car_id=? AND is_moderated=1", (car_id,)).fetchone()
    return {"count": r["n"] or 0, "avg": r["avg"] or 0}


def all_reviews(limit=100):
    with db() as conn:
        return [review_row(r) for r in conn.execute(
            "SELECT * FROM reviews ORDER BY created_at DESC LIMIT ?", (limit,))]


def delete_review(review_id):
    with db() as conn:
        conn.execute("DELETE FROM reviews WHERE id=?", (review_id,))


def toggle_review_moderation(review_id):
    with db() as conn:
        conn.execute("UPDATE reviews SET is_moderated = 1 - is_moderated WHERE id=?",
                     (review_id,))


# --------------------------------------------------------------------------
# Заявки
# --------------------------------------------------------------------------
def create_order(name, phone, email="", message="", kind="order", car_id=None, user_id=None):
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO orders (user_id, car_id, name, phone, email, message,
                                    kind, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (user_id, car_id, name, phone, email, message, kind, now()))
        return cur.lastrowid


def all_orders(limit=200):
    with db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM orders ORDER BY created_at DESC, id DESC LIMIT ?", (limit,))]


def order_stats():
    with db() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS total,
                      SUM(CASE WHEN status='new' THEN 1 ELSE 0 END) AS new,
                      SUM(CASE WHEN status='in_progress' THEN 1 ELSE 0 END) AS in_progress,
                      SUM(CASE WHEN status='done' THEN 1 ELSE 0 END) AS done
               FROM orders""").fetchone()
        return dict(row)


def set_order_status(order_id, status):
    with db() as conn:
        conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))


def delete_order(order_id):
    with db() as conn:
        conn.execute("DELETE FROM orders WHERE id=?", (order_id,))


# --------------------------------------------------------------------------
# Избранное
# --------------------------------------------------------------------------
def favorite_ids(user_id):
    if not user_id:
        return []
    with db() as conn:
        return [r["car_id"] for r in conn.execute(
            "SELECT car_id FROM favorites WHERE user_id=?", (user_id,))]


def toggle_favorite(user_id, car_id):
    if not user_id:
        return False
    with db() as conn:
        row = conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND car_id=?",
                           (user_id, car_id)).fetchone()
        if row:
            conn.execute("DELETE FROM favorites WHERE user_id=? AND car_id=?",
                         (user_id, car_id))
            return False
        conn.execute("INSERT INTO favorites (user_id, car_id, created_at) VALUES (?,?,?)",
                     (user_id, car_id, now()))
        return True


def favorites_of(user_id):
    if not user_id:
        return []
    with db() as conn:
        rows = conn.execute(
            """SELECT c.* FROM favorites f JOIN cars c ON c.id=f.car_id
               WHERE f.user_id=? AND c.is_active=1 ORDER BY f.created_at DESC""",
            (user_id,))
        return [car_row(r) for r in rows]


# --------------------------------------------------------------------------
# Фото
# --------------------------------------------------------------------------
def car_photos(car_id):
    with db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM photos WHERE car_id=? ORDER BY is_main DESC, sort, id",
            (car_id,))]


def add_photo(car_id, filename, is_main=False):
    with db() as conn:
        conn.execute("INSERT INTO photos (car_id, filename, is_main) VALUES (?,?,?)",
                     (car_id, filename, 1 if is_main else 0))
        if is_main:
            conn.execute("UPDATE photos SET is_main=0 WHERE car_id=? AND id != "
                         "(SELECT id FROM photos WHERE car_id=? ORDER BY is_main DESC,"
                         " id DESC LIMIT 1)", (car_id, car_id))
        conn.execute("UPDATE cars SET photo=? WHERE id=? AND photo IS NULL",
                     (filename, car_id))


def delete_photo(photo_id):
    with db() as conn:
        cur = conn.execute("DELETE FROM photos WHERE id=?", (photo_id,))
        return cur.rowcount > 0


# --------------------------------------------------------------------------
# Новости
# --------------------------------------------------------------------------
def all_news(only_published=True):
    sql = "SELECT * FROM news"
    if only_published:
        sql += " WHERE published=1"
    sql += " ORDER BY created_at DESC"
    with db() as conn:
        return [{"id": r["id"], "title": r["title"], "text": r["body"],
                 "body": r["body"], "published": r["published"],
                 "date": r["created_at"][:10]} for r in conn.execute(sql)]


def create_news(title, body):
    with db() as conn:
        conn.execute("INSERT INTO news (title, body, created_at) VALUES (?,?,?)",
                     (title, body, now()))


def delete_news(news_id):
    with db() as conn:
        conn.execute("DELETE FROM news WHERE id=?", (news_id,))


# --------------------------------------------------------------------------
# Сводная статистика для дашборда
# --------------------------------------------------------------------------
def dashboard_stats():
    with db() as conn:
        cars = conn.execute("SELECT COUNT(*) FROM cars WHERE is_active=1").fetchone()[0]
        sold = conn.execute("SELECT COUNT(*) FROM cars WHERE is_sold=1").fetchone()[0]
        views = conn.execute("SELECT COALESCE(SUM(views),0) FROM cars").fetchone()[0]
        orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        reviews = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        revenue = conn.execute(
            "SELECT COALESCE(SUM(price),0) FROM cars WHERE is_sold=1").fetchone()[0]
        avg_price = conn.execute(
            "SELECT COALESCE(ROUND(AVG(price)),0) FROM cars WHERE is_active=1").fetchone()[0]
        top = conn.execute(
            "SELECT brand, model, views FROM cars ORDER BY views DESC LIMIT 5").fetchall()
    return {
        "cars": cars, "sold": sold, "views": views, "orders": orders,
        "reviews": reviews, "users": users, "revenue": revenue, "avg_price": avg_price,
        "top_cars": [dict(r) for r in top],
    }
