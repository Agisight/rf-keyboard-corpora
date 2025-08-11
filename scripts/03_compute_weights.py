# -*- coding: utf-8 -*-
"""
03_compute_weights.py

Считает глобальные веса W(v) без metadata/languages.csv.
S_i берём из файлов: data/<lang>/<vendor>/stats/<lang>_population.csv
  - колонка: total_speakers_global (обязательна)
  - если несколько строк, берём последнюю по year (макс. год)

Частоты берём у ПЕРВОГО (лексикографически) вендора:
  data/<lang>/<vendor>/frequencies/*.csv  с колонками variant,C_i,M_i

Если у языка нет частот, но есть маппинг -> равномерно добавляем alpha=1% от S_i
по всем его вариантам (из metadata/variant_mapping.csv -> source_languages).

Выход: metadata/global_stats.csv  с колонками variant,W,p
"""

import csv, glob, os, re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# --- рабочий корень ---
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

# --- настройки ---
EXCLUDED_LANGS = {"lang"}        # исключаем шаблонный язык
INCLUDE_RUSSIAN = False
if not INCLUDE_RUSSIAN:
    EXCLUDED_LANGS |= {"ru", "rus"}

FREQ_GLOB   = "data/**/frequencies/*.csv"
STATS_GLOB  = "data/**/stats/*_population.csv"
MAPPING_CSV = "metadata/variant_mapping.csv"
OUT_CSV     = "metadata/global_stats.csv"
ALPHA_MISS  = 0.01               # 1% если нет частот

# --- утилиты ---

def _digits_to_int(s: str) -> Optional[int]:
    """Парсит числа с пробелами/знаками. Возвращает int или None."""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    # оставить цифры и точку/запятую как разделитель
    cleaned = re.sub(r"[^\d.,]", "", s)
    # если и точка и запятая, заменим запятую
    cleaned = cleaned.replace(",", ".")
    try:
        return int(float(cleaned))
    except Exception:
        # последняя попытка – удалить всё, кроме цифр
        only_digits = re.sub(r"\D", "", s)
        return int(only_digits) if only_digits else None

def _extract_lang_from_freq_path(p: str) -> Optional[str]:
    parts = Path(p).parts
    if "data" in parts:
        i = parts.index("data")
        if i + 1 < len(parts):
            return parts[i + 1]      # data/<lang>/<vendor>/frequencies/...
    if "frequencies" in parts and parts.index("frequencies") >= 2:
        j = parts.index("frequencies")
        return parts[j - 2]
    return None

def _extract_lang_from_stats_path(p: str) -> Optional[str]:
    # из имени файла <lang>_population.csv
    name = Path(p).name
    if name.endswith("_population.csv"):
        return name[:-len("_population.csv")]
    return None

# --- загрузка S_i из stats/<lang>_population.csv ---

def _read_Si_from_one_stats_csv(path: str) -> Optional[int]:
    """
    Возвращает total_speakers_global для МАКС. года (если колонка year есть),
    иначе первую валидную цифру.
    """
    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)

    if not rows:
        return None

    # нормализуем имена колонок в нижний регистр
    norm_rows = []
    for row in rows:
        norm_rows.append({(k or "").strip().lower(): v for k, v in row.items()})

    # найти колонку speakers
    SPEAK = "total_speakers_global"
    YEAR  = "year"

    # если есть YEAR — берём запись с максимальным годом, где speakers валидны
    if YEAR in norm_rows[0]:
        candidates: List[Tuple[int, int]] = []  # (year, value)
        for row in norm_rows:
            y = _digits_to_int(row.get(YEAR))
            v = _digits_to_int(row.get(SPEAK))
            if y is not None and v is not None:
                candidates.append((y, v))
        if candidates:
            candidates.sort(key=lambda t: t[0])  # по году
            return candidates[-1][1]

    # иначе — взять первую валидную цифру из колонки speakers
    for row in norm_rows:
        v = _digits_to_int(row.get(SPEAK))
        if v is not None:
            return v
    return None

def load_Si_from_repo() -> Dict[str, int]:
    """
    Идём по data/**/stats/*_population.csv, для каждого языка берём ПЕРВЫЙ файл
    (лексикографически) и читаем total_speakers_global.
    """
    Si: Dict[str, int] = {}
    paths = sorted(glob.glob(STATS_GLOB, recursive=True))
    per_lang: Dict[str, List[str]] = defaultdict(list)
    for p in paths:
        lang = _extract_lang_from_stats_path(p)
        if not lang or lang in EXCLUDED_LANGS:
            continue
        per_lang[lang].append(p)

    for lang, lst in per_lang.items():
        path = sorted(lst)[0]  # первый вендор
        val = _read_Si_from_one_stats_csv(path)
        if val is not None and val > 0:
            Si[lang] = val
        # если нет валидного значения — просто не добавляем язык
    return Si

# --- загрузка mapping: lang -> variants (для fallback) ---

def load_lang_to_variants(mapping_csv: str = MAPPING_CSV) -> Dict[str, List[str]]:
    """
    metadata/variant_mapping.csv: base_letter,variant,source_languages,...
    Разворачиваем source_languages в lang -> set(variants).
    """
    lang2vars: Dict[str, set] = defaultdict(set)
    if not Path(mapping_csv).exists():
        return {}
    with open(mapping_csv, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            langs = (row.get("source_languages") or "").split(",")
            var = (row.get("variant") or "").strip()
            for lg in langs:
                lg = lg.strip()
                if not lg or lg in EXCLUDED_LANGS:
                    continue
                lang2vars[lg].add(var)
    return {k: sorted(v) for k, v in lang2vars.items()}

# --- частоты: берём первого вендора на язык ---

def list_first_freq_per_lang(valid_langs: List[str]) -> Dict[str, str]:
    paths = sorted(glob.glob(FREQ_GLOB, recursive=True))
    per_lang: Dict[str, List[str]] = defaultdict(list)
    for p in paths:
        lang = _extract_lang_from_freq_path(p)
        if not lang or lang not in valid_langs:
            continue
        per_lang[lang].append(p)
    return {lang: sorted(v)[0] for lang, v in per_lang.items()}  # первый

# --- расчёт W и сохранение ---

def accumulate_W_from_freqs(Si: Dict[str, int], first_paths: Dict[str, str]) -> Tuple[Dict[str, float], set]:
    W: Dict[str, float] = defaultdict(float)
    langs_with_freq: set = set()

    for lang, path in first_paths.items():
        try:
            with open(path, encoding="utf-8") as f:
                r = csv.DictReader(f)
                Csum: Dict[str, float] = defaultdict(float)
                Mseen: float = 0.0
                for row in r:
                    v = (row.get("variant") or "").strip()
                    C = float(row.get("C_i") or 0)
                    M = float(row.get("M_i") or 0)
                    if not v:
                        continue
                    Csum[v] += C
                    if M > Mseen:
                        Mseen = M
            if Mseen <= 0:
                continue
            fi = {v: Csum[v] / Mseen for v in Csum}
            Si_val = float(Si[lang])
            for v, fv in fi.items():
                W[v] += Si_val * fv
            langs_with_freq.add(lang)
        except FileNotFoundError:
            continue
    return W, langs_with_freq

def add_fallback_for_missing(W: Dict[str, float],
                             Si: Dict[str, int],
                             langs_with_freq: set,
                             lang2vars: Dict[str, List[str]],
                             alpha: float = ALPHA_MISS) -> Dict[str, float]:
    missing = set(Si.keys()) - set(langs_with_freq)
    for lang in missing:
        variants = lang2vars.get(lang, [])
        if not variants:
            continue
        share = (alpha * float(Si[lang])) / len(variants)
        for v in variants:
            W[v] += share
    return W

def save_global_stats(W: Dict[str, float], out_csv: str = OUT_CSV) -> None:
    total = sum(W.values()) or 1.0
    rows = [{"variant": v, "W": W[v], "p": (W[v] / total)} for v in sorted(W)]
    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["variant", "W", "p"])
        w.writeheader(); w.writerows(rows)
    print(f"OK: wrote {out_csv} (variants={len(rows)})")

# --- main ---

def main():
    # 1) S_i из stats/<lang>_population.csv
    Si = load_Si_from_repo()
    if not Si:
        print("WARN: не найдено ни одного S_i в data/**/stats/*_population.csv")
    valid_langs = [lg for lg in Si.keys() if lg not in EXCLUDED_LANGS]

    # 2) lang -> variants из агрегированного маппинга
    lang2vars = load_lang_to_variants(MAPPING_CSV)

    # 3) первый вендор частот на язык
    first_freq = list_first_freq_per_lang(valid_langs)

    # 4) накапливаем W из частот
    W, langs_with_freq = accumulate_W_from_freqs(Si, first_freq)

    # 5) добавляем fallback 1% для языков без частот
    W = add_fallback_for_missing(W, Si, langs_with_freq, lang2vars, alpha=ALPHA_MISS)

    # 6) сохраняем
    save_global_stats(W, OUT_CSV)

if __name__ == "__main__":
    main()
