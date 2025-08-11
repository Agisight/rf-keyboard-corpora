# -*- coding: utf-8 -*-
# 03e_find_mapping_conflicts.py
# Находит варианты (нормализованные) которые привязаны к >1 базовой русской клавише.
# Вариант нормализуем: NFC + UPPERCASE (чтобы Ң/ң склеились). Русские буквы [А-ЯЁ] отбрасываем.
#
# Выход:
#  - metadata/conflicts_overview.csv   (variant, bases, count_bases, has_sequence, W, p)
#  - metadata/conflicts_breakdown.csv  (variant, base_letter, originals, source_languages)

import csv, os, unicodedata
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

MAP_CSV = "metadata/variant_mapping.csv"
GF_CSV  = "metadata/global_frequencies.csv"

OUT_OVERVIEW  = "metadata/conflicts_overview.csv"
OUT_BREAKDOWN = "metadata/conflicts_breakdown.csv"

RU_SET = set("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")

def nfc_up(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "")).upper()

def load_global():
    """variant(W,p) из global_frequencies.csv (если файл есть)."""
    W = {}
    if not Path(GF_CSV).exists():
        return W
    with open(GF_CSV, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            v = nfc_up(row.get("variant",""))
            if not v: 
                continue
            W[v] = {
                "W": row.get("W",""),
                "p": row.get("p",""),
            }
    return W

def main():
    if not Path(MAP_CSV).exists():
        raise SystemExit(f"ERR: нет {MAP_CSV}. Сначала запусти 04_aggregate_mappings.py")

    glob_weights = load_global()

    # variant_norm -> { 'bases': set, 'has_seq': bool, 'per_base': {base: {'orig': set, 'langs': set}} }
    idx = {}
    with open(MAP_CSV, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            base = nfc_up(row.get("base_letter",""))
            var_orig = unicodedata.normalize("NFC", (row.get("variant","") or "").strip())
            if not base or not var_orig:
                continue
            var_norm = nfc_up(var_orig)
            has_seq  = (row.get("has_sequence","0") == "1")

            # отбрасываем русские ОДИНОЧНЫЕ буквы — нас интересуют нестандартные
            if len(var_norm) == 1 and var_norm in RU_SET:
                continue

            if var_norm not in idx:
                idx[var_norm] = {
                    "bases": set(),
                    "has_seq": False,
                    "per_base": defaultdict(lambda: {"orig": set(), "langs": set()}),
                }

            idx[var_norm]["bases"].add(base)
            idx[var_norm]["has_seq"] = idx[var_norm]["has_seq"] or has_seq

            # собираем оригинальные написания и языки, где встречалось
            idx[var_norm]["per_base"][base]["orig"].add(var_orig)
            langs = (row.get("source_languages") or "").split(",")
            for lg in langs:
                lg = lg.strip()
                if lg:
                    idx[var_norm]["per_base"][base]["langs"].add(lg)

    # оставляем только случаи, где один и тот же variant_norm сидит на >1 базе
    conflicts = {v: data for v, data in idx.items() if len(data["bases"]) > 1}

    # --- пишем overview
    rows_over = []
    for var, data in sorted(conflicts.items(), key=lambda kv: kv[0]):
        bases_sorted = sorted(list(data["bases"]))
        rec = {
            "variant": var,
            "bases": ";".join(bases_sorted),
            "count_bases": len(bases_sorted),
            "has_sequence": "1" if data["has_seq"] else "0",
            "W": glob_weights.get(var, {}).get("W", ""),
            "p": glob_weights.get(var, {}).get("p", ""),
        }
        rows_over.append(rec)

    # сортируем сводку по убыванию W (если есть), иначе по alnum
    def to_float(x):
        try: return float(str(x).replace(",", "."))
        except: return -1.0
    rows_over.sort(key=lambda r: (-(to_float(r["W"]) if r["W"] != "" else -1.0), r["variant"]))

    Path("metadata").mkdir(parents=True, exist_ok=True)
    with open(OUT_OVERVIEW, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["variant","bases","count_bases","has_sequence","W","p"])
        w.writeheader(); w.writerows(rows_over)

    # --- пишем breakdown
    rows_det = []
    for var, data in sorted(conflicts.items(), key=lambda kv: kv[0]):
        for base in sorted(data["bases"]):
            originals = ",".join(sorted(data["per_base"][base]["orig"]))
            langs     = ",".join(sorted(data["per_base"][base]["langs"]))
            rows_det.append({
                "variant": var,
                "base_letter": base,
                "originals": originals,           # как именно записан вариант под этой базой у разных вендоров
                "source_languages": langs,        # языки, давшие этот маппинг на эту базу
            })

    with open(OUT_BREAKDOWN, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["variant","base_letter","originals","source_languages"])
        w.writeheader(); w.writerows(rows_det)

    print(f"OK: wrote {OUT_OVERVIEW} (conflicts={len(rows_over)})")
    print(f"OK: wrote {OUT_BREAKDOWN} (rows={len(rows_det)})")
    if not rows_over:
        print("No conflicts — один и тот же вариант не встречается под разными базовыми буквами.")

if __name__ == "__main__":
    main()
