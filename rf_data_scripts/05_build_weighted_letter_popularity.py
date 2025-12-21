# -*- coding: utf-8 -*-
# data_scripts/05_build_weighted_letter_popularity.py
#
# Считает взвешенную популярность букв/символов с учётом носителей.
# Источники:
#   summaries/frequencies_by_language.csv  (lang_code, variant, C_i, M_i, f_i)
#   summaries/speakers_rf.csv          (lang_code, population)
#
# Выход:
#   summaries/rf_letter_popularity_weighted.csv   (по variant)
#   summaries/rf_symbol_popularity_weighted.csv   (по символам/графемам)
#
# Правило для символов:
#   • variant длиной 1 графему → +w этой графеме.
#   • variant длиной 2..4 графем → разбиваем на графемы и КАЖДОЙ графеме добавляем +w
#     (повторы учитываются). Пример: "ЛЛЪ" при w=10 → Л += 20, Ъ += 10.
#   • Длины >4 игнорируем.
#
# Все варианты считаются в NFC + UPPERCASE.
# 'share' оставляем; 'cum_share' не считаем.

import csv
import os
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

FREQ_CSV = Path("summaries/frequencies_by_language.csv")
SPEAK_CSV = Path("summaries/speakers_rf.csv")
OUT_LETTERS = Path("summaries/rf_letter_popularity_weighted.csv")
OUT_SYMBOLS = Path("summaries/rf_symbol_popularity_weighted.csv")

VERBOSE = True

def vprint(*a):
    if VERBOSE: print(*a)

def _sniff_delimiter(sample: str) -> str:
    return ";" if sample.count(";") > sample.count(",") else ","

def _read_csv_flex(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as f:
        head = f.read(4096)
        delim = _sniff_delimiter(head)
        f.seek(0)
        return list(csv.DictReader(f, delimiter=delim))

def _to_float(x) -> float:
    if x is None: return 0.0
    s = str(x).strip().replace(" ", "")
    if not s: return 0.0
    try:
        return float(s)
    except Exception:
        try:
            return float(s.replace(",", ""))
        except Exception:
            return 0.0

def _nfc_upper(s: str) -> str:
    return unicodedata.normalize("NFC", s or "").upper()

def _graphemes(s: str) -> List[str]:
    """
    Простейший сегментатор графем: новая графема начинается на символе
    с combining==0; все последующие combining>0 цепляются к ней.
    Этого достаточно для кириллицы с диакритикой (например 'А̄').
    """
    out: List[str] = []
    cur = ""
    for ch in s:
        if not cur:
            cur = ch
        else:
            if unicodedata.combining(ch) > 0:
                cur += ch
            else:
                out.append(cur)
                cur = ch
    if cur:
        out.append(cur)
    return out

def _rank_and_share(items: List[Tuple[str, float]], langs_map: Dict[str, set]):
    grand_total = sum(v for _, v in items) or 1.0
    out_rows = []
    for rank, (key, weighted) in enumerate(items, start=1):
        share = weighted / grand_total
        out_rows.append({
            "rank": rank,
            "key": key,
            "weighted_population": f"{weighted:.6f}",
            "share": f"{share:.10f}",
            "langs_count": len(langs_map.get(key, ()))
        })
    return out_rows, grand_total

def main():
    if not FREQ_CSV.exists():
        print(f"ERR: not found {FREQ_CSV}"); return
    if not SPEAK_CSV.exists():
        print(f"ERR: not found {SPEAK_CSV}"); return

    freqs = _read_csv_flex(FREQ_CSV)
    pops  = _read_csv_flex(SPEAK_CSV)
    if not freqs: print(f"ERR: empty {FREQ_CSV}"); return
    if not pops:  print(f"ERR: empty {SPEAK_CSV}"); return

    # носители
    pop_by_lang: Dict[str, float] = {}
    for r in pops:
        lang = str(r.get("lang_code", "")).strip()
        pop  = _to_float(r.get("population"))
        if lang and pop > 0:
            pop_by_lang[lang] = pop

    missing_pop = set()

    # 1) Взвешенная популярность ВАРИАНТОВ (как есть)
    weight_by_variant: Dict[str, float] = {}
    langs_per_variant: Dict[str, set] = {}

    for r in freqs:
        lang = str(r.get("lang_code", "")).strip()
        if not lang: continue
        pop = pop_by_lang.get(lang)
        if not pop:
            missing_pop.add(lang)
            continue

        variant = _nfc_upper(str(r.get("variant", "")).strip())
        if not variant: continue

        fi = _to_float(r.get("f_i"))
        if fi <= 0.0:
            Ci = _to_float(r.get("C_i")); Mi = _to_float(r.get("M_i"))
            fi = (Ci / Mi) if Mi > 0 else 0.0
        if fi <= 0.0: continue

        w = fi * pop
        weight_by_variant[variant] = weight_by_variant.get(variant, 0.0) + w
        langs_per_variant.setdefault(variant, set()).add(lang)

    # 2) Взвешенная популярность СИМВОЛОВ (по графемам)
    weight_by_symbol: Dict[str, float] = {}
    langs_per_symbol: Dict[str, set] = {}

    for r in freqs:
        lang = str(r.get("lang_code", "")).strip()
        if not lang: continue
        pop = pop_by_lang.get(lang)
        if not pop: continue

        variant = _nfc_upper(str(r.get("variant", "")).strip())
        if not variant: continue

        fi = _to_float(r.get("f_i"))
        if fi <= 0.0:
            Ci = _to_float(r.get("C_i")); Mi = _to_float(r.get("M_i"))
            fi = (Ci / Mi) if Mi > 0 else 0.0
        if fi <= 0.0: continue

        w = fi * pop
        clusters = _graphemes(variant)        # <-- разбиваем на графемы
        L = len(clusters)

        if L == 1:
            s = clusters[0]
            weight_by_symbol[s] = weight_by_symbol.get(s, 0.0) + w
            langs_per_symbol.setdefault(s, set()).add(lang)
        elif 2 <= L <= 4:
            # каждому кластеру начисляем полный w (повторы учитываются)
            for s in clusters:
                weight_by_symbol[s] = weight_by_symbol.get(s, 0.0) + w
                langs_per_symbol.setdefault(s, set()).add(lang)
        else:
            # длины >4 игнорируем
            continue

    # вывод 1: по вариантам
    items_var = sorted(weight_by_variant.items(), key=lambda t: t[1], reverse=True)
    rows_var, grand_w_var = _rank_and_share(items_var, langs_per_variant)

    OUT_LETTERS.parent.mkdir(parents=True, exist_ok=True)
    with OUT_LETTERS.open("w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=["rank","variant","weighted_population","share","langs_count"])
        wcsv.writeheader()
        for r in rows_var:
            wcsv.writerow({
                "rank": r["rank"],
                "variant": r["key"],
                "weighted_population": r["weighted_population"],
                "share": r["share"],
                "langs_count": r["langs_count"],
            })

    # вывод 2: по символам (графемам)
    items_sym = sorted(weight_by_symbol.items(), key=lambda t: t[1], reverse=True)
    rows_sym, grand_w_sym = _rank_and_share(items_sym, langs_per_symbol)

    with OUT_SYMBOLS.open("w", newline="", encoding="utf-8") as f:
        wcsv = csv.DictWriter(f, fieldnames=["rank","symbol","weighted_population","share","langs_count"])
        wcsv.writeheader()
        for r in rows_sym:
            wcsv.writerow({
                "rank": r["rank"],
                "symbol": r["key"],
                "weighted_population": r["weighted_population"],
                "share": r["share"],
                "langs_count": r["langs_count"],
            })

    print(f"OK: wrote {OUT_LETTERS} (variants={len(rows_var)}, grand_total_weight={grand_w_var:.2f})")
    print(f"OK: wrote {OUT_SYMBOLS} (symbols={len(rows_sym)},  grand_total_weight={grand_w_sym:.2f})")
    if missing_pop:
        vprint(f"NOTE: no population for {len(missing_pop)} languages → skipped: {', '.join(sorted(missing_pop))}")

if __name__ == "__main__":
    main()
