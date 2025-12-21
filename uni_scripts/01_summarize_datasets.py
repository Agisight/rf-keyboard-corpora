#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, csv, json, re
from pathlib import Path

# Поддерживаем:
#   <lang>_mono_1.1M.txt
#   <lang>_mono_707M.txt
#   <lang>_mono_291k.txt
#   <lang>_mono_1B.txt
#   <lang>_mono_11985083.txt   (голое число)
SIZE_RE = re.compile(r"_mono_([0-9]+(?:\.[0-9]+)?)([KkMmGgBb]?)\.txt$")
UNIT = {"K": 1_000, "M": 1_000_000, "G": 1_000_000_000, "B": 1_000_000_000}

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Корень репозитория")
    # НОВЫЙ АРГУМЕНТ:
    ap.add_argument("--scope", default="global", choices=["global", "rf"], 
                    help="Область применения данных о носителях: global или rf. По умолчанию global.")
    return ap.parse_args()

def human_int(n: int | None) -> str:
    if n is None:
        return "—"
    return f"{n:,}".replace(",", " ")

def human_token_from_value(v: float | int | None) -> str:
    if v is None:
        return "—"
    v = float(v)
    if v >= 1_000_000_000:
        return f"{round(v/1_000_000_000, 1):g}B"
    if v >= 1_000_000:
        return f"{round(v/1_000_000, 1):g}M"
    if v >= 1_000:
        return f"{round(v/1_000, 1):g}K"
    return str(int(v))

def size_token_value(num_str: str, unit: str) -> float:
    if unit == "":
        return float(num_str)  # без единиц, просто число
    return float(num_str) * UNIT[unit.upper()]

def pick_first_vendor(lang_dir: Path) -> Path | None:
    vendors = sorted([p for p in lang_dir.iterdir() if p.is_dir()])
    return vendors[0] if vendors else None

def max_corpus_size_token(raw_dir: Path, lang: str) -> tuple[str | None, float | None]:
    """Возвращает (токен, численное значение) для самого большого файла."""
    if not raw_dir.exists():
        return (None, None)
    best = None  # (value, token_str)
    for p in raw_dir.glob(f"{lang}_mono_*.txt"):
        m = SIZE_RE.search(p.name)
        if not m:
            continue
        num, unit = m.group(1), m.group(2)
        val = size_token_value(num, unit)
        token = f"{num}{unit.upper()}" if unit else num
        if best is None or val > best[0]:
            best = (val, token)
    return (best[1], best[0]) if best else (None, None)

# ФУНКЦИЯ read_population ИЗМЕНЕНА ДЛЯ РАБОТЫ С scope
def read_population(stats_dir: Path, lang: str, scope: str) -> int | None:
    """Берём stats/<lang>_population.csv:
       1) группируем по year,
       2) внутри года берём максимум по приоритету (выбранный scope → альтернативный),
       3) выбираем год = max(year) и возвращаем максимум для него.
    """
    path = stats_dir / f"{lang}_population.csv"
    if not path.exists():
        return None

    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Определяем приоритеты ключей на основе параметра scope
    if scope == "rf":
        primary_key, secondary_key = "total_speakers_rf", "total_speakers_global"
    else: # global
        primary_key, secondary_key = "total_speakers_global", "total_speakers_rf"
        
    def _to_int(x):
        s = str(x or "").replace(" ", "").replace(",", "")
        try:
            return int(float(s))
        except:
            return None

    best_by_year: dict[int, int] = {}

    for r in rows:
        # год
        try:
            y = int(str(r.get("year", "")).strip())
        except:
            continue

        # значение по приоритету: выбранный scope → альтернативный
        v = _to_int(r.get(primary_key))
        if v is None:
            v = _to_int(r.get(secondary_key))

        if v is None:
            continue

        # максимум внутри одного года
        if (y not in best_by_year) or (v > best_by_year[y]):
            best_by_year[y] = v

    if not best_by_year:
        return None

    y_max = max(best_by_year.keys())
    return best_by_year[y_max]

def extract_special_letters_raw(mapping_path: Path) -> list[str]:
    """
    Читаем mapping/<lang>_key_mapping.json и возвращаем ВСЕ значения «как есть»:
      - каждое значение приводим к UPPERCASE
      - не разбираем по символам, не фильтруем
      - уникализируем, сохраняя порядок появления
    Пример формата:
      { "А": ["Ӕ", "Ӓ"], "С": ["Ҫ", "C’", "С̇"], ... }
    """
    if not mapping_path.exists():
        return []
    try:
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    seen = set()
    ordered = []
    for _base_ru, variants in (data or {}).items():
        if not isinstance(variants, list):
            continue
        for v in variants:
            if not isinstance(v, str):
                continue
            up = v.upper()
            if up not in seen:
                seen.add(up)
                ordered.append(up)
    return ordered

# ФУНКЦИЯ main ИЗМЕНЕНА ДЛЯ РАБОТЫ С scope
def main():
    args = parse_args()
    root = Path(args.root).resolve()
    data_root = root / "data"
    out_dir = root / "summaries"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    scope_name = args.scope.upper()
    # Имя выходного файла с префиксом RF или GLOBAL
    out_md = out_dir / f"SUMMARY_{scope_name}.md" 

    rows = []
    total_speakers_sum = 0
    total_speakers_count = 0
    total_corpus_value_sum = 0.0
    total_corpus_count = 0

    for lang_dir in sorted([p for p in data_root.iterdir() if p.is_dir()]):
        lang = lang_dir.name
        if lang == "lang":  # игнорируем шаблон
            continue

        vendor_dir = pick_first_vendor(lang_dir)
        if vendor_dir is None:
            continue
        vendor = vendor_dir.name

        raw_dir   = vendor_dir / "raw"
        stats_dir = vendor_dir / "stats"
        map_path  = vendor_dir / "mapping" / f"{lang}_key_mapping.json"

        # Передаем выбранный scope
        world = read_population(stats_dir, lang, args.scope)
        token, token_value = max_corpus_size_token(raw_dir, lang)
        special_list = extract_special_letters_raw(map_path)

        if world is not None:
            total_speakers_sum += int(world)
            total_speakers_count += 1
        if token_value is not None:
            total_corpus_value_sum += token_value
            total_corpus_count += 1

        rows.append({
            "Language": lang,
            "Vendor": vendor,
            "WorldSpeakers": human_int(world),
            "CorpusSize": token or "—",
            "SpecialLetters": ", ".join(special_list) if special_list else "—",
        })

    rows.sort(key=lambda r: r["Language"])

    # рендер таблицы
    lines = []
    lines.append(f"# Dataset Summary ({scope_name})\n")
    
    speakers_header = f"Speakers ({scope_name})"
    lines.append(f"| Language | Vendor | {speakers_header} | Corpus size | Special letters |")
    lines.append("|---|---:|---:|---:|---|")
    for r in rows:
        lines.append("| {Language} | {Vendor} | {WorldSpeakers} | {CorpusSize} | {SpecialLetters} |".format(**r))

    # блок итогов
    lines.append("\n**Totals**")
    lines.append(f"- Languages: {len(rows)}")
    lines.append(f"- With speakers data: {total_speakers_count} · Sum {args.scope} speakers: {human_int(total_speakers_sum)}")
    lines.append(f"- With corpus data: {total_corpus_count} · Total corpus size (max per language): {human_token_from_value(total_corpus_value_sum)}")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"✓ Wrote {out_md.relative_to(root)} with {len(rows)} rows")
    print(f"   Sum speakers ({args.scope}) = {human_int(total_speakers_sum)} over {total_speakers_count} languages")
    print(f"   Sum corpus   = {human_token_from_value(total_corpus_value_sum)} over {total_corpus_count} languages")

if __name__ == "__main__":
    main()