# -*- coding: utf-8 -*-
# data_scripts/collect_language_frequencies.py → rf_summaries/frequencies_by_language.csv
# Собирает частоты по ПЕРВОМУ (или заданному) вендору каждого языка и нормализует варианты:
#  - всё в NFC+UPPERCASE,
#  - любые строки, содержащие ᵸ / ᴴ / ʰ, сводит к единому варианту 'ᵸ'.
# ИСКЛЮЧАЕМ Ё и Ъ из анализа (фильтрация на входе)
import csv, glob, os, unicodedata
from pathlib import Path
from typing import Optional, Dict, List

# ——— корень проекта ———
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

DATA_DIR = Path("data")
OUT_CSV  = "rf_summaries/frequencies_by_language.csv"
VERBOSE  = True

# исключаем служебный шаблон и русский
EXCLUDED_LANGS = {"lang", "ru", "rus"}

# ИСКЛЮЧАЕМ Ё и Ъ из анализа
EXCLUDED_LETTERS = {"Ё", "Ъ"}

# если для языка нужно жёстко выбрать вендора — укажи здесь
PREFERRED_VENDOR: Dict[str, str] = {
    "abk": "Tamaz_Kharchlaa",
}

# возможные имена колонок (регистронезависимо)
VAR_KEYS = ["variant", "letter", "symbol", "char"]
C_KEYS   = ["c_i", "c", "count", "freq", "frequency"]
M_KEYS   = ["m_i", "m", "total", "sum", "size"]

# модификаторы, которые канонизируем в 'ᵸ'
SUP_H_CAP  = "\u1D34"  # ᴴ  MODIFIER LETTER CAPITAL H
SUP_h_SM   = "\u02B0"  # ʰ  MODIFIER LETTER SMALL H
SUP_CYR_EN = "\u1D78"  # ᵸ  MODIFIER LETTER CYRILLIC EN

def vprint(*a):
    if VERBOSE:
        print(*a)

def _norm_keys(row: dict) -> dict:
    return {(k or "").strip().lower(): v for k, v in row.items()}

def _sniff_delimiter(sample: str) -> str:
    return ";" if sample.count(";") > sample.count(",") else ","

def _read_csv_flex(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as f:
        head = f.read(4096)
        delim = _sniff_delimiter(head)
        f.seek(0)
        return list(csv.DictReader(f, delimiter=delim))

def _pick_first_present(row: dict, keys: List[str]) -> Optional[str]:
    for k in keys:
        if k in row and str(row[k]).strip() != "":
            return k
    return None

def _first_vendor_freq_path(lang: str) -> Optional[str]:
    patterns = [
        f"data/{lang}/*/frequencies/*.csv",
        f"data/{lang}/*/frequences/*.csv",
        f"data/{lang}/**/frequen*/**/*.csv",
        f"data/{lang}/**/frequen*/*.csv",
    ]
    candidates: List[str] = []
    for pat in patterns:
        candidates += glob.glob(pat, recursive=True)
    if not candidates:
        return None
    candidates = sorted(set(candidates))

    pref = PREFERRED_VENDOR.get(lang)
    if pref:
        pref_only = [p for p in candidates if f"/{lang}/{pref}/" in p]
        if pref_only:
            return pref_only[0]

    return candidates[0]

def _vendor_from_path(p: str) -> str:
    parts = Path(p).parts
    if "data" in parts:
        i = parts.index("data")
        if i + 2 < len(parts):
            return parts[i + 2]
    for key in ("frequencies", "frequences"):
        if key in parts:
            j = parts.index(key)
            if j - 1 >= 0:
                return parts[j - 1]
    return ""

def canonicalize_variant(s: str) -> str:
    """
    Канонизация варианта для подсчётов:
    - если строка содержит ᵸ / ᴴ / ʰ в любом месте → вернуть ровно 'ᵸ'
    - иначе: NFC + UPPERCASE.
    """
    n = unicodedata.normalize("NFC", s or "")
    if (SUP_CYR_EN in n) or (SUP_H_CAP in n) or (SUP_h_SM in n):
        return SUP_CYR_EN
    return unicodedata.normalize("NFC", n).upper()

def main():
    rows_out: List[dict] = []

    if not DATA_DIR.exists():
        print("ERR: нет папки data/")
        return

    langs = sorted([d.name for d in DATA_DIR.iterdir() if d.is_dir()])
    langs = [lg for lg in langs if lg not in EXCLUDED_LANGS]

    for lang in langs:
        freq_path = _first_vendor_freq_path(lang)
        if not freq_path:
            vprint(f"[{lang}] нет frequencies/*.csv — пропуск")
            continue

        vendor = _vendor_from_path(freq_path)
        try:
            raw_rows = _read_csv_flex(Path(freq_path))
        except Exception as e:
            vprint(f"[{lang}] ошибка чтения {freq_path}: {e}")
            continue

        if not raw_rows:
            vprint(f"[{lang}] пустой файл частот: {freq_path}")
            continue

        Csum: Dict[str, float] = {}
        M_seen: float = 0.0

        for raw in raw_rows:
            row = _norm_keys(raw)

            v_key = _pick_first_present(row, VAR_KEYS)
            c_key = _pick_first_present(row, C_KEYS)
            m_key = _pick_first_present(row, M_KEYS)

            if not v_key or not c_key:
                continue

            variant_raw = str(row[v_key]).strip()
            if not variant_raw:
                continue

            variant = canonicalize_variant(variant_raw)
            
            # ИСКЛЮЧАЕМ Ё и Ъ
            if variant in EXCLUDED_LETTERS:
                continue

            try:
                Ci = float(str(row[c_key]).strip())
            except Exception:
                continue

            Csum[variant] = Csum.get(variant, 0.0) + Ci

            if m_key:
                try:
                    Mi = float(str(row[m_key]).strip())
                    if Mi > M_seen:
                        M_seen = Mi
                except Exception:
                    pass

        if M_seen <= 0.0:
            M_seen = sum(Csum.values())

        if M_seen <= 0.0 or not Csum:
            vprint(f"[{lang}] не удалось вычислить M_i / C_i — пропуск")
            continue

        added = 0
        for variant, Ci in sorted(Csum.items()):
            fi = Ci / M_seen if M_seen > 0 else 0.0
            rows_out.append({
                "lang_code": lang,
                "vendor": vendor,
                "variant": variant,
                "C_i": f"{Ci:.0f}" if float(Ci).is_integer() else f"{Ci}",
                "M_i": f"{M_seen:.0f}" if float(M_seen).is_integer() else f"{M_seen}",
                "f_i": f"{fi:.10f}",
            })
            added += 1

        vprint(f"[{lang}] {vendor}: добавлено {added} строк (M_i={M_seen})")

    Path("rf_summaries").mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["lang_code","vendor","variant","C_i","M_i","f_i"])
        w.writeheader()
        w.writerows(rows_out)

    print(f"OK: wrote {OUT_CSV} (rows={len(rows_out)}) [Ё and Ъ excluded]")

if __name__ == "__main__":
    main()
