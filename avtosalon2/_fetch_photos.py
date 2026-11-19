# -*- coding: utf-8 -*-
"""Скачивает реальные фото автомобилей с Wikimedia Commons и прописывает их в БД."""
import io
import json
import sys
import time
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import db  # noqa: E402
import data  # noqa: E402

import os  # noqa: E402
UPLOAD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
os.makedirs(UPLOAD, exist_ok=True)

UA = {"User-Agent": "AutoSalonDemo/1.0 (educational project)"}

# модельные семейства для поиска: (марка, модель, запрос в Commons)
QUERIES = {
    1: "Toyota Camry XV70",
    2: "BMW X5 G05",
    3: "Kia Sportage NQ5",
    4: "Lexus ES",
    5: "Volkswagen Passat B8 variant",
    6: "Nissan Qashqai J12",
    7: "Mercedes-Benz C-Class W206",
    8: "Hyundai Creta",
    9: "Mazda CX-5",
    10: "Jeep Wrangler JL",
    11: "Audi A4 B9",
    12: "Skoda Octavia IV",
    13: "Mitsubishi Outlander",
    14: "Renault Duster",
    15: "Ford Focus Mk4",
    16: "LADA Granta",
    17: "Volkswagen Polo hatchback 2021",
    18: "Toyota Corolla E210",
    19: "BMW 3 Series G20",
    20: "Audi Q5",
    21: "Tesla Model 3",
    22: "Volvo XC60 II",
    23: "Infiniti QX50",
    24: "Subaru Forester SK",
    25: "Honda CR-V",
    26: "Chevrolet Cruze",
    27: "Kia K5",
    28: "BMW i4",
    29: "Volkswagen Tiguan II",
    30: "Toyota Land Cruiser 200",
}


def commons_search(query):
    """Ищет на Commons фото авто (side/front view), возвращает URL миниатюры 960px."""
    q = urllib.parse.urlencode({
        "action": "query", "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6, "gsrlimit": 8,
        "prop": "imageinfo", "iiprop": "url|size|mime", "iiurlwidth": 960, "format": "json",
    })
    url = "https://commons.wikimedia.org/w/api.php?" + q
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(4):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=25).read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            raise
    pages = sorted(d.get("query", {}).get("pages", {}).values(),
                   key=lambda p: p.get("index", 99))
    for p in pages:
        ii = p.get("imageinfo", [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        # фото, а не логотип: достаточно широкое, горизонтальное
        if w >= 700 and w > h and "logo" not in p["title"].lower():
            return ii.get("thumburl") or ii.get("url")
    return None


def download(url, path):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r, open(path, "wb") as f:
        f.write(r.read())


def main():
    ok, fail = 0, []
    for car in db.all_cars(True):
        if car["photo"]:
            ok += 1
            continue
        query = QUERIES.get(car["id"], f'{car["brand"]} {car["model"]}')
        try:
            img_url = commons_search(query)
            if not img_url:
                fail.append((car["id"], query, "no result"))
                continue
            fname = f'{car["brand"].lower().replace("-", "")}_{car["model"].lower().replace(" ", "_").replace("-", "_")}.jpg'
            fname = "".join(ch for ch in fname if ch.isalnum() or ch in "_.")
            download(img_url, os.path.join(UPLOAD, fname))
            db.set_car_photo(car["id"], fname)
            ok += 1
            print(f'OK  id={car["id"]:>2} {car["brand"]} {car["model"]} -> {fname}')
            time.sleep(6)  # вежливость к Commons (лимит запросов)
        except Exception as e:
            fail.append((car["id"], query, str(e)[:80]))
            print(f'ERR id={car["id"]:>2} {query}: {e}')
    print("---")
    print("ok:", ok, "fail:", len(fail))
    for f_ in fail:
        print("  ", f_)


if __name__ == "__main__":
    main()
