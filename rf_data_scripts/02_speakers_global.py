# -*- coding: utf-8 -*-
# data_scripts/speakers_global.py
# → summaries/speakers_global.csv (lang_code,population)
# Проходим ТОЛЬКО по папкам языков: data/<lang>/
# Для каждого языка берём первого по имени вендора: data/<lang>/<vendor>/stats/<lang>_population.csv
# Поле: ТОЛЬКО total_speakers_rf (БЕЗ fallback на global). Если есть несколько лет — берём максимальный year.

import csv, glob, os, re, itertools
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# Переходим в корень репозитория (скрипт лежит в data_scripts/)
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

DATA_DIR = Path("data")
OUT_CSV  = Path("summaries/speakers_global.csv")

# Исключения
EXCLUDED_LANGS = {"lang", "ru", "rus"}   # убери 'ru','rus', если всё-таки хочешь включить русский

def _num(s: str) -> Optional[int]:
    """Парсить '1 234 567', '1,234,567', '12.3 млн', '12k', '1.2e6' → int."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None

    txt = s.lower().replace("\u00a0", " ")
    mult = 1.0
    # множители
    if any(w in txt for w in [" тыс", "тыс."]):
        mult = max(mult, 1_000.0)
    if "k" in txt:
        mult = max(mult, 1_000.0)
    if any(w in txt for w in [" млн", "млн.", " million", "mn", "m "]):
        mult = max(mult, 1_000_000.0)
    if any(w in txt for w in [" млрд", "миллиард", " billion", "bn"]):
        mult = max(mult, 1_000_000_000.0)

    # вычищаем всё, кроме цифр, . , e E + -
    cleaned = re.sub(r"[^\d.,eE+-]", "", s).replace(",", ".")
    try:
        return int(float(cleaned) * mult)
    except Exception:
        only = re.sub(r"\D", "", s)
        return int(only) if only else None

def _sniff_delimiter(sample: str) -> str:
    # простая эвристика: больше ; → ';' иначе ','
    return ";" if sample.count(";") > sample.count(",") else ","

def _read_csv_flex(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as f:
        head = f.read(4096)
        delim = _sniff_delimiter(head)
        f.seek(0)
        return list(csv.DictReader(f, delimiter=delim))

def _pick_population(rows: List[dict]) -> Optional[int]:
    """Берём ТОЛЬКО total_speakers_rf (БЕЗ fallback на global).
    Если есть несколько лет — берём максимальный year.
    Если в одном и том же году несколько строк — берём максимум значения для этого года.
    """
    if not rows:
        return None

    # нормализуем ключи
    norm = [{(k or "").strip().lower(): v for k, v in r.items()} for r in rows]

    YEAR_KEYS = ["year"]
    # ТОЛЬКО РФ данные
    RF_KEYS = [
        "total_speakers_rf", "speakers_rf", "rf_speakers",
        "speakers_in_rf", "population_rf", "population_in_rf"
    ]

    def candidate_value(r: dict) -> Optional[int]:
        # Только РФ данные (БЕЗ global)
        for rk in RF_KEYS:
            if rk in r and str(r[rk]).strip():
                v = _num(r[rk])
                if v is not None:
                    return v
        return None

    # 1) собираем максимум по каждому году
    best_by_year: Dict[int, int] = {}
    for r in norm:
        # год (если есть)
        y = None
        for yk in YEAR_KEYS:
            if yk in r and str(r[yk]).strip():
                y = _num(r[yk])
                break
        v = candidate_value(r)
        if y is not None and v is not None:
            if (y not in best_by_year) or (v > best_by_year[y]):
                best_by_year[y] = v

    # если есть годы — берём max(year) и максимум для него
    if best_by_year:
        y_max = max(best_by_year.keys())
        return best_by_year[y_max]

    # 2) иначе — первая валидная (только RF)
    for r in norm:
        v = candidate_value(r)
        if v is not None:
            return v
            
    # НОВОЕ: Если не удалось найти валидное значение total_speakers_rf, выбрасываем ошибку
    raise ValueError("Required data for 'total_speakers_rf' not found or is invalid in the population data. Cannot continue.")

    return None

def _first_vendor_population(lang: str) -> Optional[int]:
    """Находит первого по имени вендора, читает stats/<lang>_population.csv, возвращает population."""
    # кандидаты stats-файлов строго под этим языком
    candidates = sorted(glob.glob(f"data/{lang}/*/stats/{lang}_population.csv"))
    if not candidates:
        # на случай иной вложенности — рекурсивно
        candidates = sorted(glob.glob(f"data/{lang}/**/{lang}_population.csv", recursive=True))
    for p in candidates:
        try:
            rows = _read_csv_flex(Path(p))
            v = _pick_population(rows)
            if v is not None and v > 0:
                return v
        except Exception:
            # пропускаем битые или неожиданные файлы
            continue
    return None

def main():
    if not DATA_DIR.exists():
        print("ERR: нет папки data/")
        return

    # список языков = имена подпапок data/<lang>/ (игнорим скрытые/служебные)
    langs = sorted(
        d.name for d in DATA_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    langs = [lg for lg in langs if lg not in EXCLUDED_LANGS]

    rows_out: List[Dict[str, int]] = []
    missing: List[str] = []

    for lang in langs:
        pop = _first_vendor_population(lang)
        if pop is None:
            missing.append(lang)
        else:
            rows_out.append({"lang_code": lang, "population": pop})

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["lang_code", "population"])
        w.writeheader()
        for r in rows_out:
            w.writerow(r)

    total_population = sum(r["population"] for r in rows_out)

    print(f"OK: wrote {OUT_CSV}  | found {len(rows_out)} of {len(langs)} languages")
    print(f"SUM OF RF SPEAKERS: {total_population:,}  [only total_speakers_rf, no global fallback]")

    if rows_out:
        print("HEAD (first 10 rows):")
        for r in itertools.islice(rows_out, 10):
            print(f"  {r['lang_code']},{r['population']}")

    if missing:
        print("MISSING (no RF data):", ", ".join(missing))

if __name__ == "__main__":
    main()
