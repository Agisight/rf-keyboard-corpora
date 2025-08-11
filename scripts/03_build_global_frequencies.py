# -*- coding: utf-8 -*-
# 03_build_global_frequencies.py
# Глобальные частоты с особыми фолбэками по языкам (akv → 0.1%).
#
# Вход:
#   metadata/speakers_global.csv         (lang_code,population)
#   metadata/frequencies_by_language.csv (lang_code,vendor,variant,C_i,M_i,f_i)
#   metadata/variant_mapping.csv         (base_letter,variant,source_languages,...)  — для фолбэков
#
# Выход:
#   metadata/global_frequencies.csv
#   metadata/global_frequencies_by_base.csv

import csv, os, unicodedata
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

SPEAKERS_CSV = "metadata/speakers_global.csv"
FREQS_CSV    = "metadata/frequencies_by_language.csv"
MAPPING_CSV  = "metadata/variant_mapping.csv"

OUT_GLOBAL   = "metadata/global_frequencies.csv"
OUT_BY_BASE  = "metadata/global_frequencies_by_base.csv"

EXCLUDED_LANGS = {"lang", "ru", "rus"}  # русских не учитываем

# режим веса языка
WEIGHT_MODE = "population"   # "population" | "equal_lang"

# СПЕЦ-ФОЛБЭКИ: lang -> alpha (доля от населения языка, равномерно по его вариантам)
SPECIAL_FALLBACK = {
    "akv": 0.001,   # 0.1%
}

def up_nfc(s: str) -> str:
    return unicodedata.normalize("NFC", (s or "")).upper()

def load_speakers():
    S = {}
    if not Path(SPEAKERS_CSV).exists():
        print(f"ERR: нет {SPEAKERS_CSV}. Сначала собери его 02-скриптом.")
        return S
    with open(SPEAKERS_CSV, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            lang = (row.get("lang_code") or "").strip()
            if not lang or lang in EXCLUDED_LANGS:
                continue
            try:
                pop = float(str(row.get("population","0")).strip())
            except Exception:
                pop = 0.0
            if pop > 0:
                S[lang] = pop
    return S

def load_freqs():
    rows = []
    if not Path(FREQS_CSV).exists():
        print(f"ERR: нет {FREQS_CSV}. Сначала запусти 02b-скрипт.")
        return rows
    with open(FREQS_CSV, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            lang = (row.get("lang_code") or "").strip()
            if not lang or lang in EXCLUDED_LANGS:
                continue
            variant = (row.get("variant") or "").strip()
            if not variant:
                continue
            fi_str = (row.get("f_i") or "").strip()
            if fi_str == "":
                try:
                    C = float(str(row.get("C_i","0")).strip())
                    M = float(str(row.get("M_i","0")).strip())
                    fi = (C / M) if M > 0 else 0.0
                except Exception:
                    fi = 0.0
            else:
                try:
                    fi = float(fi_str)
                except Exception:
                    fi = 0.0
            # 02b уже сделал NFC+UPPERCASE (кроме спец-ᵸ), тут просто кладём как есть
            rows.append((lang, variant, fi))
    return rows

def load_lang2variants_upper(mapping_csv: str = MAPPING_CSV):
    """
    Из variant_mapping.csv вытаскиваем: lang -> {VARIANT_UPPER}
    Варианты берём «как есть» из файла и поднимаем в UPPERCASE для стыковки с 02b.
    """
    lang2vars = defaultdict(set)
    if not Path(mapping_csv).exists():
        return {}
    with open(mapping_csv, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            var = up_nfc(row.get("variant",""))
            langs = (row.get("source_languages") or "").split(",")
            for lg in langs:
                lg = lg.strip()
                if lg and lg not in EXCLUDED_LANGS:
                    lang2vars[lg].add(var)
    return {k: sorted(v) for k, v in lang2vars.items()}

def load_var2bases():
    var2base = defaultdict(set)
    if not Path(MAPPING_CSV).exists():
        return var2base
    with open(MAPPING_CSV, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            base = up_nfc(row.get("base_letter",""))
            var  = up_nfc(row.get("variant",""))
            if base and var:
                var2base[var].add(base)
    return var2base

def build_global():
    S = load_speakers()
    freq_rows = load_freqs()
    lang2vars = load_lang2variants_upper()

    def lang_weight(lang):
        if WEIGHT_MODE == "equal_lang":
            return 1.0
        return S.get(lang, 0.0)

    W = defaultdict(float)
    langs_per_variant = defaultdict(set)
    langs_used = set()

    # 1) базовый вклад по частотам
    for lang, variant, fi in freq_rows:
        w = lang_weight(lang)
        if w <= 0:
            continue
        W[variant] += w * fi
        langs_per_variant[variant].add(lang)
        langs_used.add(lang)

    # 2) спец-фолбэки (напр., akv: 0.1%), только если у языка нет частот
    for lang, alpha in SPECIAL_FALLBACK.items():
        if lang in EXCLUDED_LANGS:
            continue
        if lang in langs_used:
            continue  # у языка уже есть частоты — не трогаем
        if lang not in S:
            print(f"WARN: SPECIAL_FALLBACK '{lang}' пропущен — нет population в {SPEAKERS_CSV}")
            continue
        variants = lang2vars.get(lang, [])
        if not variants:
            print(f"WARN: SPECIAL_FALLBACK '{lang}' пропущен — нет вариантов в {MAPPING_CSV}")
            continue
        share = (alpha * S[lang]) / len(variants)
        for v in variants:
            W[v] += share
            langs_per_variant[v].add(lang)
        print(f"APPLIED: fallback {lang} alpha={alpha:.4f} | variants={len(variants)} | add per variant={share:.6f}")

    total_W = sum(W.values()) or 1.0
    rows_out = []
    for variant in sorted(W.keys()):
        rows_out.append({
            "variant": variant,
            "W": f"{W[variant]:.10f}",
            "p": f"{(W[variant]/total_W):.10f}",
            "langs_count": len(langs_per_variant[variant]),
        })

    Path("metadata").mkdir(parents=True, exist_ok=True)
    with open(OUT_GLOBAL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["variant","W","p","langs_count"])
        w.writeheader(); w.writerows(rows_out)

    print(f"OK: wrote {OUT_GLOBAL}  | variants={len(rows_out)} | langs_used={len(langs_used)}")
    return W

def build_by_base(W):
    var2bases = load_var2bases()
    if not var2bases:
        print("WARN: нет mapping → пропускаю out-by-base")
        return

    base2vars = defaultdict(list)
    for var, bases in var2bases.items():
        for base in bases:
            base2vars[base].append(var)

    rows = []
    total_W = sum(W.values()) or 1.0
    for base in sorted(base2vars.keys()):
        vs = base2vars[base]
        pairs = [(v, W.get(v, 0.0)) for v in vs if W.get(v, 0.0) > 0.0]
        if not pairs:
            continue
        pairs.sort(key=lambda t: t[1], reverse=True)
        sum_base = sum(x[1] for x in pairs) or 1.0
        for rank, (v, wv) in enumerate(pairs, start=1):
            rows.append({
                "base_letter": base,
                "variant": v,
                "W": f"{wv:.10f}",
                "p_global": f"{(wv/total_W):.10f}",
                "p_in_base": f"{(wv/sum_base):.10f}",
                "rank_in_base": rank,
            })

    with open(OUT_BY_BASE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["base_letter","variant","W","p_global","p_in_base","rank_in_base"]
        )
        w.writeheader(); w.writerows(rows)

    print(f"OK: wrote {OUT_BY_BASE}  | rows={len(rows)}")

def main():
    W = build_global()
    build_by_base(W)

if __name__ == "__main__":
    main()
