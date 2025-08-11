# -*- coding: utf-8 -*-
import csv, glob, json, os, unicodedata
from collections import defaultdict

# --- настройки ---
EXCLUDED_LANGS = {"lang"}           # исключить шаблонный язык
INCLUDE_RUSSIAN = False             # как и оговаривали — без русского
if not INCLUDE_RUSSIAN:
    EXCLUDED_LANGS |= {"ru", "rus"}

TOP_K = None                        # ограничение длинны long-press; None = полный список
MISSING_FREQ_ALPHA = 0.01           # 1% влияние языка без частот

def load_Si(path="metadata/languages.csv"):
    S = {}
    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            code = row["language_code"].strip()
            if code in EXCLUDED_LANGS:
                continue
            S[code] = float(row["S_i"])
    return S

def load_mapping(path="metadata/variant_mapping.csv"):
    """
    Ожидаем, что 04_aggregate_mappings.py сделал столбец source_languages
    (через запятую). Возвращаем:
      - base_letter -> set(variants)
      - lang -> set(variants)  (для fallback 1% при отсутствии частот)
    """
    base_to_variants = defaultdict(set)
    lang_to_variants = defaultdict(set)

    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            base = row["base_letter"].strip()
            var  = row["variant"].strip()
            base_to_variants[base].add(var)

            langs = [x.strip() for x in row.get("source_languages","").split(",") if x.strip()]
            for lg in langs:
                if lg not in EXCLUDED_LANGS:
                    lang_to_variants[lg].add(var)

    # к нормальному dict + отсортировать варианты для стабильности
    base_to_variants = {k: sorted(v) for k, v in base_to_variants.items()}
    lang_to_variants = {k: sorted(v) for k, v in lang_to_variants.items()}
    return base_to_variants, lang_to_variants

def list_vendor_freqs_for_lang(lang_code):
    """
    Ищем все частотные файлы данного языка в субмодуле:
      data/raw/**/<lang_code>/<vendor>/frequencies/*.csv
    """
    pattern = f"data/raw/**/{lang_code}/*/frequencies/*.csv"
    return sorted(glob.glob(pattern, recursive=True))

def choose_first_vendor_freq(lang_code):
    paths = list_vendor_freqs_for_lang(lang_code)
    return paths[0] if paths else None

def load_frequencies_first_vendor(S):
    """
    Берём по одному (первому) вендору на язык.
    Возвращаем W по реальным частотам, и множество языков с частотами.
    """
    W = defaultdict(float)
    langs_with_freq = set()

    for lang in sorted(S.keys()):
        p = choose_first_vendor_freq(lang)
        if not p:
            continue
        langs_with_freq.add(lang)

        # суммируем C и M по файлу (если там несколько строк на разные варианты)
        with open(p, encoding="utf-8") as f:
            r = csv.DictReader(f)
            # На случай, если внутри один и тот же variant встречается несколько раз
            Csum, Msum = defaultdict(float), 0.0
            for row in r:
                v = row["variant"].strip()
                C = float(row["C_i"])
                M = float(row["M_i"])
                Csum[v] += C
                Msum = max(Msum, M)  # обычно M одинаков для всех строк

        if Msum <= 0:
            continue
        fi = {v: Csum[v]/Msum for v in Csum.keys()}
        Si = S[lang]
        for v, fv in fi.items():
            W[v] += Si * fv

    return W, langs_with_freq

def add_missing_freq_fallback(W, S, langs_with_freq, lang_to_variants, alpha=MISSING_FREQ_ALPHA):
    """
    Для языков без частот раздаём равномерно alpha*S_i по всем вариантам,
    встречающимся в их маппинге.
    """
    missing = set(S.keys()) - set(langs_with_freq)
    for lang in missing:
        variants = lang_to_variants.get(lang, [])
        if not variants:
            continue
        Si = S[lang]
        share = (alpha * Si) / len(variants)
        for v in variants:
            W[v] += share
    return W

def save_global_stats(W, path="metadata/global_stats.csv"):
    total = sum(W.values()) or 1.0
    rows = [{"variant": v, "W": W[v], "p": W[v]/total} for v in sorted(W.keys())]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["variant","W","p"])
        w.writeheader(); w.writerows(rows)

def build_longpress(W, base_to_variants):
    order = {}
    for base, variants in base_to_variants.items():
        sorted_vs = sorted(variants, key=lambda v: W.get(v, 0.0), reverse=True)

        # ручные фиксы
        if base in ("Е","е"):
            for yo in ("Ё","ё"):
                if yo in sorted_vs:
                    sorted_vs.remove(yo); sorted_vs.insert(0, yo)
        if base in ("Ъ","ъ"):
            for hard in ("Ъ","ъ"):
                if hard in sorted_vs:
                    sorted_vs.remove(hard); sorted_vs.insert(0, hard)

        order[base] = sorted_vs[:TOP_K] if TOP_K else sorted_vs
    return order

def main():
    S = load_Si()  # с учётом EXCLUDED_LANGS
    base_to_variants, lang_to_variants = load_mapping()

    # 1) реальные частоты: по одному (первому) вендору на язык
    W, langs_with_freq = load_frequencies_first_vendor(S)

    # 2) fallback 1% для языков без частот
    W = add_missing_freq_fallback(W, S, langs_with_freq, lang_to_variants, alpha=MISSING_FREQ_ALPHA)

    # 3) сохранить глобальную статистику и построить long-press
    save_global_stats(W)
    order = build_longpress(W, base_to_variants)
    with open("metadata/longpress_order.json","w",encoding="utf-8") as f:
        json.dump(order, f, ensure_ascii=False, indent=2)
    print("OK: wrote metadata/global_stats.csv and metadata/longpress_order.json")

if __name__ == "__main__":
    main()
