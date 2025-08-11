# -*- coding: utf-8 -*-
# 02_collect_speakers_global.py  → metadata/speakers_global.csv (lang_code,population)
# Проходим ТОЛЬКО по папкам языков: data/<lang>/
# Для каждого языка берём первого по имени вендора: data/<lang>/<vendor>/stats/<lang>_population.csv
# Поле приоритета: total_speakers_global, иначе total_speakers_rf. Если есть несколько лет — берём максимальный year.

import csv, glob, os, re
from pathlib import Path
from typing import Optional, List, Dict, Tuple

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

DATA_DIR  = Path("data")
OUT_CSV   = "metadata/speakers_global.csv"

# Исключения
EXCLUDED_LANGS = {"lang", "ru", "rus"}   # убери 'ru','rus', если всё-таки хочешь включить русский

def _num(s: str) -> Optional[int]:
    """Парсить '1 234 567', '1,234,567', '12.3 млн', '12k', '1.2e6' → int."""
    if s is None: return None
    s = str(s).strip()
    if not s: return None
    txt = s.lower().replace("\u00a0", " ")
    mult = 1.0
    if any(w in txt for w in [" тыс", "тыс."]): mult = max(mult, 1_000.0)
    if "k" in txt: mult = max(mult, 1_000.0)
    if any(w in txt for w in [" млн", "млн.", " million", "mn", "m "]): mult = max(mult, 1_000_000.0)
    if any(w in txt for w in [" млрд", "миллиард", " billion", "bn"]): mult = max(mult, 1_000_000_000.0)
    cleaned = re.sub(r"[^\d.,eE+-]", "", s).replace(",", ".")
    try:
        return int(float(cleaned) * mult)
    except Exception:
        only = re.sub(r"\D", "", s)
        return int(only) if only else None

def _sniff_delimiter(sample: str) -> str:
    return ";" if sample.count(";") > sample.count(",") else ","

def _read_csv_flex(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as f:
        head = f.read(4096)
        delim = _sniff_delimiter(head)
        f.seek(0)
        return list(csv.DictReader(f, delimiter=delim))

def _pick_population(rows: List[dict]) -> Optional[int]:
    """Берём по приоритету: total_speakers_global, иначе total_speakers_rf; с максимальным year, если есть."""
    if not rows: return None
    norm = [{(k or "").strip().lower(): v for k, v in r.items()} for r in rows]
    YEAR_KEYS = ["year"]
    GLOBAL_KEYS = ["total_speakers_global", "speakers_global", "global_speakers",
                   "total_speakers", "speakers_total", "population_global", "population"]
    RF_KEYS = ["total_speakers_rf", "speakers_rf", "rf_speakers",
               "speakers_in_rf", "population_rf", "population_in_rf"]

    # если есть год — выберем запись с макс. годом, где есть валидное значение
    years_vals: List[Tuple[int, int]] = []
    for r in norm:
        y = None
        for yk in YEAR_KEYS:
            if yk in r and str(r[yk]).strip():
                y = _num(r[yk]); break
        # приоритет: global -> rf
        g = None
        for gk in GLOBAL_KEYS:
            if gk in r:
                g = _num(r[gk]); 
                if g is not None: break
        if g is None:
            for rk in RF_KEYS:
                if rk in r:
                    g = _num(r[rk])
                    if g is not None: break
        if y is not None and g is not None:
            years_vals.append((y, g))
    if years_vals:
        years_vals.sort(key=lambda t: t[0])
        return years_vals[-1][1]

    # иначе — первая валидная: global → rf
    for r in norm:
        for gk in GLOBAL_KEYS:
            if gk in r:
                v = _num(r[gk])
                if v is not None:
                    return v
    for r in norm:
        for rk in RF_KEYS:
            if rk in r:
                v = _num(r[rk])
                if v is not None:
                    return v
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
            continue
    return None

def main():
    if not DATA_DIR.exists():
        print("ERR: нет папки data/")
        return

    # список языков = имена подпапок data/<lang>/
    langs = sorted([d.name for d in DATA_DIR.iterdir() if d.is_dir()])
    langs = [lg for lg in langs if lg not in EXCLUDED_LANGS]

    rows_out: List[Dict[str, int]] = []
    missing: List[str] = []

    for lang in langs:
        pop = _first_vendor_population(lang)
        if pop is None:
            missing.append(lang)
        else:
            rows_out.append({"lang_code": lang, "population": pop})

    Path("metadata").mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["lang_code", "population"])
        w.writeheader()
        for r in rows_out:
            w.writerow(r)

    print(f"OK: wrote {OUT_CSV}  | found {len(rows_out)} of {len(langs)} languages")
    if missing:
        print("MISSING:", ", ".join(missing))

if __name__ == "__main__":
    main()
