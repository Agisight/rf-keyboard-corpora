#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, sys, unicodedata as ud
from pathlib import Path
from collections import defaultdict

META = Path("metadata")
IN_FILE  = META / "variant_mapping.csv"
OUT_FILE = META / "variant_mapping_modcanon.csv"

MOD_EQUIV = {"ᴴ": "ᵸ", "ʰ": "ᵸ", "ᵸ": "ᵸ"}

def canon_upper(s: str) -> str:
    return ud.normalize("NFC", (s or "").strip()).upper()

def pick_col(headers, *cands):
    for c in cands:
        if c in headers:
            return c
    raise KeyError(f"Нет столбца из {cands}. Есть: {headers}")

def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except:
        return False

def main():
    with open(IN_FILE, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        headers = rd.fieldnames or []
        base_col = pick_col(headers, "base_letter", "base", "key", "Base", "BASE")
        var_col  = pick_col(headers, "variant", "Variant", "letter", "char")
        rows = list(rd)

    # 1) Нормализация + канонизация модификаторов (одиночных)
    normed = []
    changed_single = 0
    for row in rows:
        base_u = canon_upper(row.get(base_col, ""))
        var_u  = canon_upper(row.get(var_col, ""))

        if var_u in MOD_EQUIV:
            new_var = MOD_EQUIV[var_u]
            if new_var != var_u:
                changed_single += 1
            var_u = new_var

        r = dict(row)
        r[base_col] = base_u
        r[var_col]  = var_u
        normed.append(r)

    # 2) Агрегация по (base, variant)
    agg = {}
    def add_to_set(d: dict, key: str, val: str):
        if not val:
            return
        d.setdefault(key, set()).add(val)

    for r in normed:
        key = (r[base_col], r[var_col])
        bucket = agg.setdefault(key, {
            "_sets": defaultdict(set),
            "_max": {},
            "_first": {},
        })

        for h in headers:
            val = (r.get(h) or "").strip()
            if h in {base_col, var_col}:
                continue
            if h == "source_languages":
                # union языков
                if val:
                    for code in val.replace(" ", "").split(","):
                        if code:
                            add_to_set(bucket["_sets"], h, code)
            elif h == "has_sequence":
                # логическое OR для 0/1
                prev = bucket["_max"].get(h)
                cur = 1 if val == "1" else 0
                bucket["_max"][h] = max(prev or 0, cur)
            elif val and is_int(val):
                prev = bucket["_max"].get(h)
                bucket["_max"][h] = max(prev or int(val), int(val))
            else:
                # строковые поля — собираем уникальные
                if val:
                    add_to_set(bucket["_sets"], h, val)
            # сохраним первый встретившийся как fallback
            bucket["_first"].setdefault(h, val)

    # 3) Формирование результирующих строк
    out_rows = []
    for (base_u, var_u), b in agg.items():
        out = {h: "" for h in headers}
        out[base_col] = base_u
        out[var_col]  = var_u

        for h in headers:
            if h in {base_col, var_col}:
                continue
            if h in b["_sets"]:
                # сортируем для стабильности
                vals = sorted(v for v in b["_sets"][h] if v)
                if h == "source_languages":
                    out[h] = ",".join(vals)
                else:
                    out[h] = "; ".join(vals)
            elif h in b["_max"]:
                out[h] = str(b["_max"][h])
            else:
                out[h] = b["_first"].get(h, "")

        out_rows.append(out)

    # стабильный порядок: по base→variant
    out_rows.sort(key=lambda r: (r[base_col], r[var_col]))

    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=headers)
        wr.writeheader()
        wr.writerows(out_rows)

    print(f"[modcanon] input:  {IN_FILE}")
    print(f"[modcanon] output: {OUT_FILE}")
    print(f"[modcanon] rows_in: {len(rows)}, rows_out: {len(out_rows)}, changed_single_mods: {changed_single}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[modcanon] ERROR: {e}", file=sys.stderr)
        raise
