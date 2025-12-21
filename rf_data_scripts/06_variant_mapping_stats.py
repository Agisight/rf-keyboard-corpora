# -*- coding: utf-8 -*-
# data_scripts/06_variant_mapping_stats.py
#
# Вход:
#   summaries/variant_mapping_atomic.csv
#   summaries/speakers_global.csv
#   summaries/global_symbol_popularity_weighted.csv
#
# Выход:
#   1) summaries/variant_mapping_stats.csv
#   2) summaries/variant_mapping_priorities_apple.csv
#   3) summaries/variant_mapping_priorities_unicode.csv
#
# Правила отображения долей:
#   - в stats: 2 знака; <1% → "<1%"; если в группе >1 и топ ≥99.5% → ">99%"
#   - в apple: 1 знак; <1% → "<1%"; если в группе >1 и топ ≥99.5% → ">99%"
#   - в unicode-выводе только коды в скобках.

import csv
import os
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Set

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

MAP_ATOMIC = Path("summaries/variant_mapping_atomic.csv")
SPEAKERS   = Path("summaries/speakers_global.csv")
SYMBOL_POP = Path("summaries/global_symbol_popularity_weighted.csv")

OUT_STATS   = Path("summaries/variant_mapping_stats.csv")
OUT_APPLE   = Path("summaries/variant_mapping_priorities_apple.csv")
OUT_UNICODE = Path("summaries/variant_mapping_priorities_unicode.csv")  # ← новое

ALMOST_ONE = Decimal("0.995")  # ≥99.5% считаем почти 100% (для правила >99%)
LT_ONE     = Decimal("0.01")   # всё <1% отображаем как "<1%"

def nfc_upper(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "").strip()).upper()

def _sniff_delimiter(sample: str) -> str:
    return ";" if sample.count(";") > sample.count(",") else ","

def _read_csv_flex(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8") as f:
        head = f.read(4096); delim = _sniff_delimiter(head); f.seek(0)
        return list(csv.DictReader(f, delimiter=delim))

def _to_dec(x) -> Decimal:
    if x is None: return Decimal("0")
    s = str(x).strip().replace(" ", "")
    if s == "": return Decimal("0")
    try: return Decimal(s)
    except Exception:
        try: return Decimal(s.replace(",", ""))
        except Exception: return Decimal("0")

def _fmt_stats_percent(share: Decimal, multi: bool, is_top: bool) -> str:
    if share < LT_ONE: return "<1%"
    if multi and is_top and share >= ALMOST_ONE: return ">99%"
    val = (share * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{val}%"

def _fmt_apple_percent(share: Decimal, multi: bool, is_top: bool) -> str:
    if share < LT_ONE: return "<1%"
    if multi and is_top and share >= ALMOST_ONE: return ">99%"
    val = (share * Decimal("100")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{val}%"

def _fmt_base_speakers_percent(pct: Decimal) -> str:
    if pct < LT_ONE: return "<1%"
    return f"{(pct * Decimal('100')).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"

def _codes(s: str) -> str:
    """Вернуть строку вида 'U+0410 U+0304' для переданной строки."""
    return " ".join(f"U+{ord(ch):04X}" for ch in s)

def main():
    # входы
    if not MAP_ATOMIC.exists(): print(f"ERR: not found {MAP_ATOMIC}"); return
    if not SPEAKERS.exists():   print(f"ERR: not found {SPEAKERS}"); return
    if not SYMBOL_POP.exists(): print(f"ERR: not found {SYMBOL_POP}"); return

    map_rows   = _read_csv_flex(MAP_ATOMIC)
    speak_rows = _read_csv_flex(SPEAKERS)
    sym_rows   = _read_csv_flex(SYMBOL_POP)

    # lang -> population
    pop_by_lang: Dict[str, Decimal] = {}
    for r in speak_rows:
        lang = (r.get("lang_code") or "").strip()
        pop_by_lang[lang] = _to_dec(r.get("population"))
    grand_total_pop = sum(pop_by_lang.values()) or Decimal("1")

    # symbol -> глобальный вес (weighted_population предпочтительно, иначе share)
    weight_by_symbol: Dict[str, Decimal] = {}
    for r in sym_rows:
        sym = nfc_upper((r.get("symbol") or r.get("variant") or ""))
        if not sym: continue
        w = _to_dec(r.get("weighted_population"))
        if w == 0: w = _to_dec(r.get("share"))
        weight_by_symbol[sym] = w

    # собрать строки
    rows = []
    for r in map_rows:
        base = nfc_upper(r.get("base_letter", ""))
        var  = nfc_upper(r.get("variant", ""))
        langs = [lg.strip() for lg in (r.get("source_languages") or "").split(",") if lg.strip()]
        total_speakers = sum(pop_by_lang.get(lg, Decimal("0")) for lg in langs)
        var_weight = weight_by_symbol.get(var, Decimal("0"))
        rows.append({
            "base_letter": base,
            "variant": var,
            "source_languages": ",".join(langs),
            "langs_set": set(langs),
            "total_speakers": total_speakers,
            "_w": var_weight,
        })

    # группировка по base_letter
    groups: Dict[str, List[dict]] = {}
    for row in rows:
        groups.setdefault(row["base_letter"], []).append(row)

    out_rows: List[dict] = []
    apple_rows: List[dict] = []
    unicode_rows: List[dict] = []  # ← новое

    for base in sorted(groups.keys()):
        items = groups[base]
        items.sort(key=lambda r: (-r["_w"], r["variant"]))      # порядок по убыванию веса
        group_sum = sum(r["_w"] for r in items)
        multi = len(items) > 1
        shares = [Decimal("0")] * len(items) if group_sum == 0 else [(it["_w"] / group_sum) for it in items]

        # процент носителей для этой маппинг-буквы (для Apple-вывода)
        langs_union: Set[str] = set()
        for it in items:
            langs_union |= set(it["langs_set"])
        base_pop = sum(pop_by_lang.get(lg, Decimal("0")) for lg in langs_union)
        base_pct = (base_pop / grand_total_pop) if grand_total_pop > 0 else Decimal("0")

        # 1) детальная таблица
        for idx, (it, sh) in enumerate(zip(items, shares), start=1):
            pct_str = _fmt_stats_percent(sh, multi, idx == 1)
            ts = it["total_speakers"]
            out_rows.append({
                "base_letter": it["base_letter"],
                "variant": it["variant"],
                "source_languages": it["source_languages"],
                "rf_speakers": str(int(ts)) if ts == ts.to_integral() else f"{ts}",
                "relative_freq_in_group": pct_str,
                "_rank": idx,
            })

        # 2) файл для Apple (с процентом носителей в первом столбце)
        base_with_pct = f"{base} ({_fmt_base_speakers_percent(base_pct)})"
        priorities_pct = "; ".join(
            f"{it['variant']} ({_fmt_apple_percent(sh, multi, i==0)})"
            for i, (it, sh) in enumerate(zip(items, shares))
        )
        apple_rows.append({"base_letter": base_with_pct, "priorities": priorities_pct})

        # 3) файл с Unicode-кодами вместо процентов
        base_with_codes = f"{base} ({_codes(base)})"
        priorities_codes = "; ".join(
            f"{it['variant']} ({_codes(it['variant'])})"
            for it in items
        )
        unicode_rows.append({"base_letter": base_with_codes, "priorities": priorities_codes})

    # запись
    out_rows.sort(key=lambda r: (r["base_letter"], r["_rank"]))
    OUT_STATS.parent.mkdir(parents=True, exist_ok=True)

    with OUT_STATS.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "base_letter","variant","source_languages","rf_speakers","relative_freq_in_group"
        ])
        w.writeheader()
        for r in out_rows:
            r = {k: v for k, v in r.items() if k != "_rank"}
            w.writerow(r)

    apple_rows.sort(key=lambda r: r["base_letter"])
    with OUT_APPLE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["base_letter", "priorities"])
        w.writeheader()
        w.writerows(apple_rows)

    unicode_rows.sort(key=lambda r: r["base_letter"])
    with OUT_UNICODE.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["base_letter", "priorities"])
        w.writeheader()
        w.writerows(unicode_rows)

    print(f"OK: wrote {OUT_STATS}")
    print(f"OK: wrote {OUT_APPLE}")
    print(f"OK: wrote {OUT_UNICODE}")

if __name__ == "__main__":
    main()
