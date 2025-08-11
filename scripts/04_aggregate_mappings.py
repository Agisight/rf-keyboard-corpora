# -*- coding: utf-8 -*-
"""
04_aggregate_mappings.py  — сводим маппинги «как есть»

Ищем только файлы:
  data/**/mapping/*_key_mapping.json

Ожидаемый формат JSON:
  {
    "Й": ["…", "…"],
    "Ц": ["…"],
    ...
  }

Нормализация:
  • base_letter → UPPERCASE (NFC)
  • variant     → КАК В ФАЙЛЕ (NFC, регистр/состав не меняем)
  • has_sequence = 1, если длина NFC(variant) > 1

Выход:
  metadata/variant_mapping.csv  со столбцами:
    base_letter, variant, source_languages, has_sequence, notes

Примечание:
  Можно ограничить маппинги по вендору для конкретных языков через PREFERRED_VENDOR.
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

OUT_CSV  = "metadata/variant_mapping.csv"
GLOB_PAT = "data/**/mapping/*_key_mapping.json"
VERBOSE  = True

# Если нужно зафиксировать конкретного вендора для языка — укажи здесь.
# Пример: для abk берём только Tamaz_Kharchlaa
PREFERRED_VENDOR: Dict[str, str] = {
    "abk": "Tamaz_Kharchlaa",
    # добавляй при необходимости: "xxx": "SomeVendor",
}

def vprint(*a) -> None:
    if VERBOSE:
        print(*a)

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "").strip())

def is_sequence(s: str) -> bool:
    return len(nfc(s)) > 1

def lang_from_filename(path: str) -> Optional[str]:
    """Имя файла вида '<lang>_key_mapping.json' → <lang>."""
    name = Path(path).name
    if name.endswith("_key_mapping.json"):
        return name[:-len("_key_mapping.json")]
    return None

def split_lang_vendor(p: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Ожидаем путь: data/<lang>/<vendor>/mapping/<lang>_key_mapping.json
    Возвращаем (<lang>, <vendor>) либо (None, None)
    """
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

    # сгруппируем пути по языку, чтобы можно было применить PREFERRED_VENDOR
    per_lang: Dict[str, List[Tuple[str, str]]] = {}
    for p in all_paths:
        lang, vendor = split_lang_vendor(p)
        if not lang or not vendor:
            continue
        per_lang.setdefault(lang, []).append((vendor, p))

    # сформируем финальный список путей с учётом предпочтений
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
        # по умолчанию берём все файлы для языка (объединим языки ниже)
        paths.extend(path for _, path in lst)

    vprint(f"[JSON *_key_mapping] файлов к чтению: {len(paths)}")

    for p in paths:
        lang = lang_from_filename(p)
        if not lang:
            vprint("  пропуск (язык не извлечён):", p)
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
            base_up = nfc(base_raw).upper()  # базовую букву поднимаем в UPPERCASE
            if not base_up:
                continue
            for var_raw in arr:
                var = nfc(var_raw)           # вариант оставляем «как есть» (только NFC)
                if not var:
                    continue
                rows.append({
                    "language_code": lang,
                    "base_letter": base_up,
                    "variant": var,
                    "has_sequence": "1" if is_sequence(var) else "0",
                    "notes": "",
                })
        vprint(f"  {p}: +{len(rows) - before} пар")

    return rows

def aggregate_and_save(out_csv: str = OUT_CSV) -> None:
    raw_rows = collect_rows()
    vprint(f"[AGGR] всего исходных строк: {len(raw_rows)}")

    # агрегируем по (base_letter, variant) и копим список языков
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
            "base_letter": base,                               # всегда UPPERCASE
            "variant": var,                                    # как в исходном JSON (NFC)
            "source_languages": ",".join(sorted(agg["langs"])),
            "has_sequence": "1" if agg["seq"] else "0",
            "notes": "; ".join(sorted(set(agg["notes"]))),
        })

    rows_out.sort(key=lambda x: (x["base_letter"], x["variant"]))

    Path("metadata").mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["base_letter", "variant", "source_languages", "has_sequence", "notes"]
        )
        w.writeheader()
        w.writerows(rows_out)

    print(f"OK: wrote {out_csv} (pairs={len(rows_out)})")

if __name__ == "__main__":
    aggregate_and_save()
