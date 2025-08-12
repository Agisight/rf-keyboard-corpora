# -*- coding: utf-8 -*-
"""
data_scripts/aggregate_mappings.py — сводим маппинги «как есть» + атомный свод с особым правилом для ᵸ

Ищем файлы:
  data/**/mapping/*_key_mapping.json

Нормализация:
  • base_letter → UPPERCASE (NFC)  + спец‑правило: 'Ъ' → 'Ь'
  • variant     → UPPERCASE (NFC)
  • has_sequence = 1, если длина NFC(variant) > 1

Выход:
  1) summaries/variant_mapping.csv
     base_letter, variant, source_languages, has_sequence, notes
  2) summaries/variant_mapping_atomic.csv — ТОЛЬКО одногРАФЕМНЫе варианты + спец-правило для ᵸ:
     если ᵸ встречался лишь внутри последовательностей, добавляем агрегированную строку Н,ᵸ (has_sequence=0).
"""

import csv
import glob
import json
import os
import unicodedata
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# --- корень проекта ---
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

OUT_CSV_FULL   = "summaries/variant_mapping.csv"
OUT_CSV_ATOMIC = "summaries/variant_mapping_atomic.csv"
GLOB_PAT = "data/**/mapping/*_key_mapping.json"
VERBOSE  = True

# Исключаем шаблонный язык
EXCLUDED_LANGS = {"lang"}

PREFERRED_VENDOR: Dict[str, str] = {
    "abk": "Tamaz_Kharchlaa",
}

MOD_CYR_EN = "\u1D78"  # ᵸ

def vprint(*a) -> None:
    if VERBOSE:
        print(*a)

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "").strip())

def to_upper(s: str) -> str:
    return nfc(s).upper()

def is_sequence(s: str) -> bool:
    return len(nfc(s)) > 1

def grapheme_count(s: str) -> int:
    """Подсчёт графем: новый кластер — символ с combining==0;
    все последующие combining>0 прилипают к нему."""
    s = nfc(s)
    if not s:
        return 0
    cnt = 0
    have_base = False
    for ch in s:
        if unicodedata.combining(ch) == 0:
            cnt += 1
            have_base = True
        else:
            if not have_base:
                cnt += 1
                have_base = True
    return cnt

def lang_from_filename(path: str) -> Optional[str]:
    name = Path(path).name
    if name.endswith("_key_mapping.json"):
        return name[:-len("_key_mapping.json")]
    return None

def split_lang_vendor(p: str) -> Tuple[Optional[str], Optional[str]]:
    parts = Path(p).parts
    if "data" in parts and "mapping" in parts:
        i = parts.index("data")
        j = parts.index("mapping")
        if i + 2 < j:
            return parts[i + 1], parts[i + 2]
    return None, None

def collect_rows() -> List[Dict]:
    rows: List[Dict] = []

    all_paths = sorted(glob.glob(GLOB_PAT, recursive=True))
    if not all_paths:
        vprint("[JSON *_key_mapping] файлов не найдено")
        return rows

    # сгруппируем пути по языку
    per_lang: Dict[str, List[Tuple[str, str]]] = {}
    for p in all_paths:
        lang, vendor = split_lang_vendor(p)
        if not lang or not vendor:
            continue
        if lang in EXCLUDED_LANGS:
            continue
        per_lang.setdefault(lang, []).append((vendor, p))

    # финальный список путей с учётом предпочтений
    paths: List[str] = []
    for lang, lst in sorted(per_lang.items()):
        pref = PREFERRED_VENDOR.get(lang)
        if pref:
            chosen = [path for vendor, path in lst if vendor == pref]
            if chosen:
                vprint(f"[{lang}] using vendor={pref} ({len(chosen)} file)")
                paths.extend(sorted(chosen))
                continue
            else:
                vprint(f"[{lang}] WARN: preferred vendor '{pref}' not found; using all vendors")
        paths.extend(path for _, path in lst)

    vprint(f"[JSON *_key_mapping] файлов к чтению: {len(paths)}")

    for p in paths:
        lang = lang_from_filename(p)
        if not lang or lang in EXCLUDED_LANGS:
            vprint("  пропуск (язык исключён или не извлечён):", p)
            continue

        try:
            with open(p, encoding="utf-8") as f:
                obj = json.load(f)
        except Exception as e:
            vprint("  ошибка JSON:", p, e)
            continue

        if not isinstance(obj, dict):
            vprint("  пропуск (ожидали dict):", p)
            continue

        before = len(rows)
        for base_raw, arr in obj.items():
            if not isinstance(arr, list):
                continue

            base_up = to_upper(base_raw)
            if base_up == "Ъ":
                base_up = "Ь"
            if not base_up:
                continue

            for var_raw in arr:
                var_up = to_upper(var_raw)
                if not var_up:
                    continue
                rows.append({
                    "language_code": lang,
                    "base_letter": base_up,
                    "variant": var_up,
                    "has_sequence": "1" if is_sequence(var_up) else "0",
                    "notes": "",
                })
        vprint(f"  {p}: +{len(rows) - before} пар")

    return rows

def aggregate_and_save() -> None:
    raw_rows = collect_rows()
    vprint(f"[AGGR] всего исходных строк: {len(raw_rows)}")

    # агрегируем по (base_letter, variant)
    by_key: Dict[Tuple[str, str], Dict] = defaultdict(
        lambda: {"langs": set(), "seq": False, "notes": []}
    )
    for r in raw_rows:
        k = (r["base_letter"], r["variant"])
        by_key[k]["langs"].add(r["language_code"])
        by_key[k]["seq"] = by_key[k]["seq"] or (r["has_sequence"] == "1")
        note = r.get("notes")
        if note:
            by_key[k]["notes"].append(note)

    rows_out: List[Dict] = []
    for (base, var), agg in by_key.items():
        rows_out.append({
            "base_letter": base,
            "variant": var,
            "source_languages": ",".join(sorted(agg["langs"])),
            "has_sequence": "1" if agg["seq"] else "0",
            "notes": "; ".join(sorted(set(agg["notes"]))),
        })
    rows_out.sort(key=lambda x: (x["base_letter"], x["variant"]))

    Path("summaries").mkdir(parents=True, exist_ok=True)
    # 1) Полный файл
    with open(OUT_CSV_FULL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["base_letter", "variant", "source_languages", "has_sequence", "notes"]
        )
        w.writeheader()
        w.writerows(rows_out)
    print(f"OK: wrote {OUT_CSV_FULL} (pairs={len(rows_out)})")

    # 2) Атомный файл + спец-правило для ᵸ
    #    - оставляем строки с 1 графемой
    #    - все строки, где variant содержит ᵸ (и были бы удалены), агрегируем в (base='Н', variant='ᵸ')
    atomic_rows: List[Dict] = []
    # агрегатор для спец-правила ᵸ
    special_key = ("Н", MOD_CYR_EN)
    special_langs: set = set()
    special_notes: set = set()

    for r in rows_out:
        var = r["variant"]
        if grapheme_count(var) == 1:
            # уже однографемные — оставляем как есть, но has_sequence=0
            atomic_rows.append({
                **r,
                "has_sequence": "0",
            })
        else:
            if MOD_CYR_EN in var:
                # копим языки/ноты для агрегированной строки Н,ᵸ
                for lg in r.get("source_languages", "").split(","):
                    lg = lg.strip()
                    if lg:
                        special_langs.add(lg)
                note = r.get("notes", "").strip()
                if note:
                    special_notes.add(note)

    # если ᵸ встречался только в последовательностях — добавим агрегированную строку Н,ᵸ
    already_has_special = any(r["base_letter"] == special_key[0] and r["variant"] == special_key[1]
                              for r in atomic_rows)
    if (special_langs or special_notes) and not already_has_special:
        atomic_rows.append({
            "base_letter": special_key[0],
            "variant": special_key[1],
            "source_languages": ",".join(sorted(special_langs)),
            "has_sequence": "0",
            "notes": "; ".join(sorted(special_notes)),
        })

    # сортировка и запись
    atomic_rows.sort(key=lambda x: (x["base_letter"], x["variant"]))
    with open(OUT_CSV_ATOMIC, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["base_letter", "variant", "source_languages", "has_sequence", "notes"]
        )
        w.writeheader()
        w.writerows(atomic_rows)
    print(f"OK: wrote {OUT_CSV_ATOMIC} (pairs={len(atomic_rows)})")

if __name__ == "__main__":
    aggregate_and_save()
