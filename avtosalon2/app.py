"""Автосалон «Премиум Моторс» — Flask-приложение.

Запуск:
    pip install -r requirements.txt
    python app.py

Демо-доступ администратора: admin@avtosalon.ru / admin123
"""

import os
import re
import secrets
import time
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from markupsafe import Markup, escape
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

import db
import data
import logic

app = Flask(__name__)
_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".secret_key")


def _load_secret():
    """SECRET_KEY из окружения, иначе случайный ключ, сохранённый рядом с приложением."""
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    if not os.path.exists(_KEY_FILE):
        with open(_KEY_FILE, "w") as fh:
            fh.write(secrets.token_hex(32))
    with open(_KEY_FILE) as fh:
        return fh.read().strip()


app.secret_key = _load_secret()
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.permanent_session_lifetime = 60 * 60 * 24 * 30
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 МБ на загрузку
app.config["UPLOAD_FOLDER"] = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "static", "uploads")

ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "gif"}
PER_PAGE = 12

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# --------------------------------------------------------------------------
# Шаблоны: фильтры
# --------------------------------------------------------------------------
@app.template_filter("number_format")
def number_format(value):
    """1234567 -> '1 234 567'"""
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return value


@app.template_filter("money")
def money(value):
    """1234567 -> '1 234 567 ₽'"""
    formatted = number_format(value)
    return formatted + " ₽" if formatted is not value else value


@app.template_filter("stars")
def stars(rating):
    """4.5 -> '★★★★☆'"""
    try:
        full = int(float(rating))
    except (TypeError, ValueError):
        full = 0
    return "★" * max(full, 0) + "☆" * (5 - max(full, 0))


@app.template_filter("plural")
def plural(n, forms):
    """plural(21, 'автомобиль,автомобиля,автомобилей') -> 'автомобиль'"""
    one, few, many = [f.strip() for f in forms.split(",")]
    n = abs(int(n or 0))
    if 11 <= n % 100 <= 14:
        return many
    return one if n % 10 == 1 else few if 2 <= n % 10 <= 4 else many


@app.template_filter("nl2br")
def nl2br(text):
    return Markup("<br>".join(escape(text or "").split("\n")))


# --------------------------------------------------------------------------
# CSRF-токен
# --------------------------------------------------------------------------
def generate_csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


# --------------------------------------------------------------------------
# Авторизация
# --------------------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = db.get_user(session.get("user_id"))
        if not user:
            flash("Требуется вход в аккаунт.", "error")
            return redirect(url_for("login", next=request.full_path))
        if user["role"] != "admin":
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Войдите в аккаунт, чтобы продолжить.", "error")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_globals():
    """Переменные, доступные во всех шаблонах."""
    user = db.get_user(session["user_id"]) if session.get("user_id") else None
    if session.get("user_id") and not user:
        session.clear()
    favs = set(db.favorite_ids(user["id"])) if user else set()
    compare = session.get("compare", [])
    return {
        "current_user": user,
        "is_admin": bool(user and user["role"] == "admin"),
        "fav_ids": favs,
        "fav_count": len(favs),
        "compare_ids": compare,
        "compare_count": len(compare),
        "csrf_token": generate_csrf(),
        "current_year": 2026,
        "demo_mode": os.environ.get("DEMO_MODE", "1") == "1",
        "new_orders": (db.order_stats().get("new") or 0) if user and user["role"] == "admin" else 0,
    }


@app.before_request
def csrf_protect():
    """Проверка CSRF-токена для всех изменяющих запросов."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        token = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        if not token or token != session.get("csrf"):
            if request.headers.get("X-Requested-With") == "fetch":
                return jsonify({"ok": False, "error": "Сессия истекла"}), 400
            flash("Сессия истекла, попробуйте ещё раз.", "error")
            return redirect(request.referrer or url_for("index"))
    g.csrf = session.get("csrf")


# --------------------------------------------------------------------------
# Вспомогательные функции
# --------------------------------------------------------------------------
def _to_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def validate_upload(file):
    """Проверяет расширение и возвращает безопасное имя файла."""
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXT:
        return None
    stem = secure_filename(file.filename.rsplit(".", 1)[0]) or "photo"
    return f"{stem}_{time.strftime('%Y%m%d%H%M%S')}.{ext}"


def _car_errors(v):
    errors = []
    if not v["brand"] or not v["model"]:
        errors.append("Укажите марку и модель.")
    if v["price"] <= 0:
        errors.append("Цена должна быть больше нуля.")
    if not 1990 <= v["year"] <= 2027:
        errors.append("Год выпуска указан неверно.")
    if v["mileage"] < 0 or v["power"] < 0:
        errors.append("Пробег и мощность не могут быть отрицательными.")
    return errors


def _car_from_form(form):
    return {
        "brand": (form.get("brand") or "").strip(),
        "model": (form.get("model") or "").strip(),
        "year": _to_int(form.get("year"), 2024),
        "mileage": _to_int(form.get("mileage")),
        "price": _to_int(form.get("price")),
        "body": form.get("body") or "Седан",
        "fuel": form.get("fuel") or "Бензин",
        "transmission": form.get("transmission") or "Автомат",
        "condition": form.get("condition") or "С пробегом",
        "engine": (form.get("engine") or "").strip(),
        "power": _to_int(form.get("power")),
        "drive": (form.get("drive") or "").strip(),
        "country": (form.get("country") or "").strip(),
        "color": (form.get("color") or "").strip(),
        "vin": (form.get("vin") or "").strip(),
        "description": (form.get("description") or "").strip(),
        "features": [f.strip() for f in (form.get("features") or "").split(",") if f.strip()],
    }


app.jinja_env.globals.update(
    brand_colors=data.brand_colors,
    brand_dark=data.brand_dark,
    brand_accent=data.brand_accent,
    body_class=data.body_class,
    price_label=data.price_label,
    brand_list=data.BRANDS,
    contacts=data.CONTACTS,
    COMPARE_FIELDS=logic.COMPARE_FIELDS,
)


# --------------------------------------------------------------------------
# Публичные страницы
# --------------------------------------------------------------------------
@app.route("/")
def index():
    cars = sorted(db.active_cars(), key=lambda c: c["price"])
    return render_template(
        "index.html",
        hits=db.popular_cars(3),
        cheap=cars[:3],
        expensive=cars[-3:],
        count=db.count_cars(),
        brands=db.facets("brand"),
        news=db.all_news()[:3],
    )


FILTER_LABELS = {
    "brand": "Марка", "body": "Кузов", "fuel": "Топливо",
    "transmission": "Коробка", "condition": "Состояние",
    "drive": "Привод", "country": "Страна",
    "min_price": "Цена от", "max_price": "Цена до",
    "min_year": "Год от", "max_year": "Год до",
    "min_mileage": "Пробег от", "max_mileage": "Пробег до",
    "min_power": "Мощность от", "only_available": "В наличии", "q": "Поиск",
}


def build_active_filters(args):
    """Список применённых фильтров для чипов «сбросить» над каталогом."""
    chips = []
    for key, label in FILTER_LABELS.items():
        value = args.get(key)
        if not value or value == "all":
            continue
        rest = {k: v for k, v in args.items() if k != key and v not in ("", "all")}
        if key in ("min_price", "max_price", "min_year", "max_year",
                   "min_mileage", "max_mileage", "min_power"):
            shown = f"{value} {'₽' if 'price' in key else ''}"
        else:
            shown = value
        chips.append({"label": f"{label}: {shown}", "value": rest})
    return chips


@app.route("/catalog")
def catalog():
    page = max(_to_int(request.args.get("page"), 1), 1)
    cars, total = db.search_cars(request.args, page, PER_PAGE)
    lo, hi = db.price_range()
    ylo, yhi = db.year_range()
    return render_template(
        "catalog.html",
        cars=cars,
        pagination=logic.paginate(total, page, PER_PAGE),
        page_args=logic.page_url_args(request.args, page),
        active_filters=build_active_filters(request.args),
        price_bounds=(lo, hi),
        year_bounds=(ylo, yhi),
        f_brand=db.facets("brand"),
        f_body=db.facets("body"),
        f_fuel=db.facets("fuel"),
        f_transmission=db.facets("transmission"),
        f_condition=db.facets("condition"),
        f_drive=db.facets("drive"),
        f_country=db.facets("country"),
    )


@app.route("/car/<int:car_id>")
def car_details(car_id):
    car = db.get_car(car_id)
    if not car:
        abort(404)
    db.increment_views(car_id)
    return render_template("car.html", **build_car_page_context(car, car_id))


def build_car_page_context(car, car_id, **overrides):
    """Общий контекст страницы автомобиля (detail + заявка)."""
    ctx = {
        "car": car,
        "similar": db.similar_cars(car, 3),
        "car_colors": data.CAR_COLORS,
        "photos": db.car_photos(car_id),
        "reviews": db.car_reviews(car_id),
        "rating": db.car_rating(car_id),
        "credit": logic.credit_summary(car["price"], int(car["price"] * 0.2), 5, 9.9),
    }
    ctx.update(overrides)
    return ctx


@app.route("/about")
def about():
    return render_template("about.html", news=db.all_news(), services=data.SERVICES,
                           stats=db.dashboard_stats())


@app.route("/contacts", methods=["GET", "POST"])
def contacts():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        email = (request.form.get("email") or "").strip()
        message = (request.form.get("message") or "").strip()

        errors = []
        if len(name) < 2:
            errors.append("Укажите имя (минимум 2 символа).")
        if len(re.sub(r"\D", "", phone)) < 6:
            errors.append("Укажите корректный номер телефона.")
        if email and "@" not in email:
            errors.append("E-mail указан некорректно.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("contacts.html", sent=False, form=request.form)
        db.create_order(name, phone, email, message, kind="contact",
                        user_id=session.get("user_id"))
        flash("Заявка отправлена. Мы свяжемся с вами в ближайшее время!", "success")
        return redirect(url_for("contacts"))
    user = db.get_user(session["user_id"]) if session.get("user_id") else None
    return render_template("contacts.html", sent=False,
                           form={"name": user["name"], "phone": user["phone"], "email": user["email"]} if user else {})


@app.route("/order", methods=["POST"])
def order():
    car_id = _to_int(request.form.get("car_id"))
    car = db.get_car(car_id) if car_id else None
    name = (request.form.get("name") or "").strip()
    phone = (request.form.get("phone") or "").strip()

    if not car:
        flash("Автомобиль не найден.", "error")
        return redirect(url_for("catalog"))

    if not name or len(re.sub(r"\D", "", phone)) < 6:
        flash("Заполните имя и телефон для заявки.", "error")
        return redirect(url_for("car_details", car_id=car_id))

    db.create_order(name, phone, (request.form.get("email") or "").strip(),
                    (request.form.get("message") or "").strip(),
                    kind="order", car_id=car_id, user_id=session.get("user_id"))
    return render_template("car.html", **build_car_page_context(
        car, car_id, credit=logic.credit_summary(car["price"], 0, 5, 9.9), ordered=True))


# --------------------------------------------------------------------------
# Калькуляторы
# --------------------------------------------------------------------------
@app.route("/credit")
def credit_page():
    form = {
        "price": _to_int(request.values.get("price"), 3_500_000),
        "down": _to_int(request.values.get("down"), 700_000),
        "years": min(max(_to_int(request.values.get("years"), 5), 1), 10),
        "rate": min(max(_to_float(request.values.get("rate"), 9.9), 0.1), 40),
    }
    summary = logic.credit_summary(form["price"], form["down"], form["years"], form["rate"])
    schedule = logic.credit_schedule(form["price"], form["down"], form["years"], form["rate"])
    return render_template("credit.html", form=form, summary=summary,
                           schedule=schedule[:60], total_months=summary["months"])


@app.route("/trade-in")
def trade_in():
    form = {
        "brand": request.values.get("brand", "Toyota"),
        "year": _to_int(request.values.get("year"), 2019),
        "mileage": _to_int(request.values.get("mileage"), 60000),
        "condition": request.values.get("condition", "С пробегом"),
        "fuel": request.values.get("fuel", "Бензин"),
    }
    form["year"] = min(max(form["year"], 2005), 2026)
    group = logic.brand_group(form["brand"])
    value = logic.trade_in_value(form["year"], form["mileage"], group, form["condition"], form["fuel"])
    return render_template("trade-in.html", form=form, value=value, group=group,
                           brands=data.BRANDS)


@app.route("/compare")
def compare():
    raw = request.args.getlist("ids") or session.get("compare", [])
    ids = []
    for chunk in raw:
        for part in str(chunk).replace(",", " ").split():
            if part.isdigit():
                ids.append(int(part))
    ids = list(dict.fromkeys(ids))[:4]
    cars = [c for c in (db.get_car(i) for i in ids) if c]
    rows, diffs = logic.compare_cars(cars) if len(cars) > 1 else ([], [])
    return render_template("compare.html", cars=cars, rows=rows, diffs=diffs, max_cars=4)


@app.route("/compare/toggle", methods=["POST"])
def compare_toggle():
    car_id = _to_int(request.form.get("car_id"))
    if not db.get_car(car_id):
        abort(404)
    current = session.get("compare", [])
    if car_id in current:
        current.remove(car_id)
        flash("Убрано из сравнения", "success")
    elif len(current) >= 4:
        flash("Максимум 4 автомобиля для сравнения", "error")
    else:
        current.append(car_id)
        flash("Добавлено к сравнению", "success")
    session["compare"] = current
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"ok": True, "ids": current, "count": len(current)})
    return redirect(request.referrer or url_for("compare"))


@app.route("/compare/clear", methods=["POST"])
def compare_clear():
    session["compare"] = []
    flash("Сравнение очищено", "success")
    return redirect(url_for("compare"))


# --------------------------------------------------------------------------
# Отзывы
# --------------------------------------------------------------------------
@app.route("/car/<int:car_id>/review", methods=["POST"])
def add_review(car_id):
    if not db.get_car(car_id):
        abort(404)
    author = (request.form.get("author") or "").strip()
    text = (request.form.get("text") or "").strip()
    rating = _to_int(request.form.get("rating"), 5)

    if len(author) < 2:
        flash("Укажите ваше имя.", "error")
    elif len(text) < 10:
        flash("Отзыв должен содержать минимум 10 символов.", "error")
    else:
        user = db.get_user(session.get("user_id"))
        db.add_review(car_id, author, min(max(rating, 1), 5), text,
                      user["id"] if user else None)
        flash("Спасибо! Ваш отзыв опубликован.", "success")
    return redirect(url_for("car_details", car_id=car_id) + "#reviews")


# --------------------------------------------------------------------------
# Избранное
# --------------------------------------------------------------------------
@app.route("/favorites")
@login_required
def favorites():
    return render_template("favorites.html", cars=db.favorites_of(session["user_id"]))


@app.route("/favorites/<int:car_id>", methods=["POST"])
def toggle_favorite(car_id):
    if not db.get_car(car_id):
        abort(404)
    is_fetch = request.headers.get("X-Requested-With") == "fetch"
    if not session.get("user_id"):
        msg = "Чтобы добавлять в избранное, войдите или зарегистрируйтесь."
        if is_fetch:
            return jsonify({"ok": False, "login": True, "error": msg}), 401
        flash(msg, "error")
        return redirect(url_for("login", next=request.referrer or url_for("car_details", car_id=car_id)))
    added = db.toggle_favorite(session["user_id"], car_id)
    count = len(db.favorite_ids(session["user_id"]))
    if is_fetch:
        return jsonify({"ok": True, "added": added, "count": count})
    flash("Добавлено в избранное" if added else "Удалено из избранного", "success")
    return redirect(request.referrer or url_for("car_details", car_id=car_id))


# --------------------------------------------------------------------------
# Авторизация
# --------------------------------------------------------------------------
def _safe_next(default):
    nxt = request.args.get("next") or request.form.get("next") or ""
    return nxt if nxt.startswith("/") and not nxt.startswith("//") else default


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))
    email = ""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        user = db.get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], request.form.get("password") or ""):
            if not user["is_active"]:
                flash("Аккаунт заблокирован.", "error")
                return render_template("login.html", email=email)
            session["user_id"] = user["id"]
            flash(f"Здравствуйте, {user['name']}!", "success")
            default = url_for("admin_dashboard") if user["role"] == "admin" else url_for("index")
            return redirect(_safe_next(default))
        flash("Неверный e-mail или пароль.", "error")
    return render_template("login.html", email=email)


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("index"))
    form = {"name": "", "email": "", "phone": ""}
    if request.method == "POST":
        form = {k: (request.form.get(k) or "").strip() for k in ("name", "email", "phone")}
        password = request.form.get("password") or ""
        errors = []
        if len(form["name"]) < 2:
            errors.append("Укажите имя (минимум 2 символа).")
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", form["email"]):
            errors.append("Укажите корректный e-mail.")
        elif db.user_exists(form["email"]):
            errors.append("Аккаунт с таким e-mail уже существует. Попробуйте войти.")
        if len(password) < 6:
            errors.append("Пароль должен быть не короче 6 символов.")
        if password != (request.form.get("password2") or ""):
            errors.append("Пароли не совпадают.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form=form)
        uid = db.create_user(form["name"], form["email"], form["phone"], generate_password_hash(password))
        session["user_id"] = uid
        flash("Аккаунт создан. Теперь можно добавлять авто в избранное.", "success")
        return redirect(_safe_next(url_for("index")))
    return render_template("register.html", form=form)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("user_id", None)
    session.pop("favorites", None)
    flash("Вы вышли из аккаунта.", "success")
    return redirect(url_for("index"))


# --------------------------------------------------------------------------
# Загрузка фото
# --------------------------------------------------------------------------
@app.route("/car/<int:car_id>/photo", methods=["POST"])
@admin_required
def upload_photo(car_id):
    if not any(c["id"] == car_id for c in db.all_cars(True)):
        abort(404)
    filename = validate_upload(request.files.get("photo"))
    if not filename:
        flash("Нужен файл изображения (png, jpg, webp, gif).", "error")
        return redirect(url_for("admin_car_edit", car_id=car_id))
    request.files["photo"].save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    db.add_photo(car_id, filename, is_main=bool(request.form.get("is_main")))
    flash("Фото загружено.", "success")
    return redirect(url_for("admin_car_edit", car_id=car_id))


@app.route("/photo/<int:photo_id>/delete", methods=["POST"])
@admin_required
def delete_photo(photo_id):
    car_id = _to_int(request.form.get("car_id"))
    deleted = db.delete_photo(photo_id)
    if deleted:
        flash("Фото удалено.", "success")
    else:
        flash("Фото не найдено — возможно, оно уже удалено.", "error")
    return redirect(url_for("admin_car_edit", car_id=car_id) if car_id else url_for("admin_cars"))


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
@app.route("/api/cars")
def api_cars():
    limit = min(_to_int(request.args.get("limit"), 50), 200)
    cars, total = db.search_cars(request.args, 1, limit)
    return jsonify({
        "total": total,
        "items": [{
            "id": c["id"], "brand": c["brand"], "model": c["model"], "year": c["year"],
            "mileage": c["mileage"], "price": c["price"],
            "price_label": data.price_label(c["price"]), "body": c["body"],
            "fuel": c["fuel"], "color": c["color"], "power": c["power"],
            "transmission": c["transmission"], "photo": c["photo"], "features": c["features"],
            "url": url_for("car_details", car_id=c["id"]),
        } for c in cars],
    })


@app.route("/api/suggest")
def api_suggest():
    return jsonify({"items": db.search_suggestions(request.args.get("q", ""))})


@app.route("/api/credit")
def api_credit():
    return jsonify(logic.credit_summary(
        _to_int(request.args.get("price"), 0),
        _to_int(request.args.get("down"), 0),
        _to_int(request.args.get("years"), 5),
        _to_float(request.args.get("rate"), 9.9)))


@app.route("/api/trade-in")
def api_trade_in():
    brand = request.args.get("brand", "Toyota")
    group = logic.brand_group(brand)
    value = logic.trade_in_value(
        min(max(_to_int(request.args.get("year"), 2019), 1990), 2026),
        max(_to_int(request.args.get("mileage"), 60000), 0), group,
        request.args.get("condition", "С пробегом"), request.args.get("fuel", "Бензин"))
    return jsonify({"value": value, "group": group})


@app.route("/api/rating/<int:car_id>")
def api_rating(car_id):
    return jsonify(db.car_rating(car_id))


# --------------------------------------------------------------------------
# SEO
# --------------------------------------------------------------------------
@app.route("/robots.txt")
def robots():
    body = ("User-agent: *\nAllow: /\nDisallow: /admin\n"
            f"Sitemap: {request.url_root}sitemap.xml\n")
    return body, 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.route("/sitemap.xml")
def sitemap():
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for endpoint, priority in [("index", 1.0), ("catalog", 0.9), ("about", 0.6),
                               ("contacts", 0.6), ("credit_page", 0.5), ("trade_in", 0.5)]:
        parts.append(f"<url><loc>{url_for(endpoint, _external=True)}</loc>"
                     f"<priority>{priority}</priority></url>")
    for c in db.all_cars():
        parts.append(f"<url><loc>{url_for('car_details', car_id=c['id'], _external=True)}</loc>"
                     "<changefreq>weekly</changefreq></url>")
    parts.append("</urlset>")
    return "\n".join(parts), 200, {"Content-Type": "application/xml; charset=utf-8"}


# --------------------------------------------------------------------------
# Админ-панель
# --------------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template("admin/dashboard.html", stats=db.dashboard_stats(),
                           orders=db.all_orders(8), reviews=db.all_reviews(8))


@app.route("/admin/cars")
@admin_required
def admin_cars():
    cars = db.all_cars(include_inactive=True)
    return render_template("admin/cars.html", cars=cars, total=len(cars))


@app.route("/admin/cars/new", methods=["GET", "POST"])
@admin_required
def admin_car_new():
    if request.method == "POST":
        values = _car_from_form(request.form)
        errors = _car_errors(values)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/car_form.html", car=values, action="create", photos=[], car_id=None)
        new_id = db.create_car(values)
        flash("Автомобиль добавлен. Теперь загрузите фотографии.", "success")
        return redirect(url_for("admin_car_edit", car_id=new_id))
    return render_template("admin/car_form.html", car=None, action="create", photos=[], car_id=None)


@app.route("/admin/cars/<int:car_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_car_edit(car_id):
    car = next((c for c in db.all_cars(True) if c["id"] == car_id), None)
    if not car:
        abort(404)
    if request.method == "POST":
        values = _car_from_form(request.form)
        errors = _car_errors(values)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("admin/car_form.html", car={**car, **values}, action="edit",
                                   photos=db.car_photos(car_id), car_id=car_id)
        db.update_car(car_id, values)
        flash("Автомобиль сохранён.", "success")
        return redirect(url_for("admin_car_edit", car_id=car_id))
    return render_template("admin/car_form.html", car=car, action="edit",
                           photos=db.car_photos(car_id), car_id=car_id)


@app.route("/admin/cars/<int:car_id>/delete", methods=["POST"])
@admin_required
def admin_car_delete(car_id):
    db.delete_car(car_id)
    flash("Автомобиль удалён.", "success")
    return redirect(url_for("admin_cars"))


@app.route("/admin/cars/<int:car_id>/toggle", methods=["POST"])
@admin_required
def admin_car_toggle(car_id):
    db.toggle_sold(car_id)
    flash("Статус продажи изменён.", "success")
    return redirect(url_for("admin_cars"))


@app.route("/admin/cars/<int:car_id>/active", methods=["POST"])
@admin_required
def admin_car_active(car_id):
    db.toggle_active(car_id)
    flash("Публикация изменена.", "success")
    return redirect(url_for("admin_cars"))


@app.route("/admin/orders", methods=["GET", "POST"])
@admin_required
def admin_orders():
    if request.method == "POST":
        oid = _to_int(request.form.get("id"))
        if request.form.get("action") == "delete":
            db.delete_order(oid)
            flash("Заявка удалена.", "success")
        else:
            status = request.form.get("status", "new")
            db.set_order_status(oid, status if status in ("new", "in_progress", "done") else "new")
            flash("Статус заявки обновлён.", "success")
        return redirect(url_for("admin_orders"))
    titles = {c["id"]: f"{c['brand']} {c['model']}" for c in db.all_cars(True)}
    flt = request.args.get("status", "")
    orders = [o for o in db.all_orders() if not flt or o["status"] == flt]
    return render_template("admin/orders.html", orders=orders, stats=db.order_stats(),
                           titles=titles, flt=flt)


@app.route("/admin/reviews", methods=["GET", "POST"])
@admin_required
def admin_reviews():
    if request.method == "POST":
        rid = _to_int(request.form.get("id"))
        if request.form.get("action") == "delete":
            db.delete_review(rid)
            flash("Отзыв удалён.", "success")
        else:
            db.toggle_review_moderation(rid)
            flash("Отзыв обновлён.", "success")
        return redirect(url_for("admin_reviews"))
    return render_template("admin/reviews.html", reviews=db.all_reviews())


@app.route("/admin/users", methods=["GET", "POST"])
@admin_required
def admin_users():
    if request.method == "POST":
        uid = _to_int(request.form.get("id"))
        action = request.form.get("action")
        if uid == session["user_id"]:
            flash("Нельзя изменить свой собственный аккаунт.", "error")
        elif action == "toggle":
            db.toggle_user_active(uid)
            flash("Статус пользователя изменён.", "success")
        elif action == "role":
            role = request.form.get("role", "user")
            db.set_user_role(uid, role if role in ("user", "admin") else "user")
            flash("Роль изменена.", "success")
        return redirect(url_for("admin_users"))
    return render_template("admin/users.html", users=db.all_users())


@app.route("/admin/news", methods=["GET", "POST"])
@admin_required
def admin_news():
    if request.method == "POST":
        if request.form.get("action") == "delete":
            db.delete_news(_to_int(request.form.get("id")))
            flash("Новость удалена.", "success")
        else:
            title = (request.form.get("title") or "").strip()
            body = (request.form.get("body") or "").strip()
            if not title or not body:
                flash("Заполните заголовок и текст.", "error")
            else:
                db.create_news(title, body)
                flash("Новость опубликована.", "success")
        return redirect(url_for("admin_news"))
    return render_template("admin/news.html", news=db.all_news(only_published=False))


# --------------------------------------------------------------------------
# Ошибки
# --------------------------------------------------------------------------
@app.errorhandler(403)
def forbidden(error):
    return render_template("403.html"), 403


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(error):
    flash("Файл слишком большой — максимум 16 МБ.", "error")
    return redirect(url_for("admin_cars"))


@app.errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500


with app.app_context():
    db.init_db()


if __name__ == "__main__":
    app.run(debug=True)
