#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, unicodedata as ud
from pathlib import Path
from collections import defaultdict

# -------------------- Paths & outputs --------------------
META = Path("metadata")
OUT_LETTERS       = META / "mapped_letters.csv"        # наборные буквы (атомарные + standalone Ӏ, ᵸ)
OUT_LETTERS_FULL  = META / "mapped_letters_full.csv"   # полный набор (ничего не фильтруем)
OUT_SEQS          = META / "mapped_sequences.csv"      # справочно
OUT_MISSING       = META / "mapping_missing.csv"
OUT_MODS          = META / "modifier_priority_global.csv"

# -------------------- Keyboard & rules --------------------
JC_BASE = ["Й","Ц","У","К","Е","Н","Г","Ш","Щ","З","Х","Ъ",
           "Ф","Ы","В","А","П","Р","О","Л","Д","Ж","Э",
           "Я","Ч","С","М","И","Т","Ь","Б","Ю"]

H_EQUIV = {"ᵸ","ᴴ","ʰ"}
STANDALONE_LETTERS = {"Ӏ","ᵸ"}              # всегда считаем наборными
HARD_EXTRAS = {"Н": {"ᵸ"}}                   # спец-исключение: ᵸ всегда под Н

# -------------------- Helpers --------------------
def canon(s: str) -> str:
    """NFC + UPPER, для стабильного сравнения и дедупликации."""
    return ud.normalize("NFC", (s or "").strip()).upper()

def strip_combining(s: str) -> str:
    """Удаляем только комбинируемые знаки (Mn), не трогая автономные символы типа 'Ӏ', 'ᵸ'."""
    return "".join(ch for ch in s if ud.category(ch) != "Mn")

def is_atomic_letter_or_standalone(s: str) -> bool:
    """
    Наборная буква, если:
      • это одна из специальных самостоятельных: Ӏ, ᵸ
      • ИЛИ «атомарная» буква (А̄, Е̄, Ӣ и пр.): после удаления комбинируемых знаков остаётся 1 буква,
        и в записи отсутствуют автономные мод‑символы (Ӏ, ᵸ/ᴴ/ʰ).
    """
    s_nfc = ud.normalize("NFC", s)
    if s_nfc in STANDALONE_LETTERS:
        return True
    if "Ӏ" in s_nfc or any(m in s_nfc for m in H_EQUIV):
        return False
    base = strip_combining(s_nfc)
    return len(base) == 1

def pick(headers, *cands):
    for c in cands:
        if c in headers:
            return c
    raise KeyError(f"Нет столбца из {cands}. Есть: {headers}")

# -------------------- I/O --------------------
def read_variant_mapping():
    """Берём modcanon, если есть, иначе оригинал. Возвращает dict[BASE]->[VARIANTS...] в каноне."""
    path = META / "variant_mapping_modcanon.csv"
    if not path.exists():
        path = META / "variant_mapping.csv"
    mapping = defaultdict(list); seen = defaultdict(set)
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f); hdr = r.fieldnames or []
        base_col = pick(hdr, "base_letter","base","key","Base","BASE")
        var_col  = pick(hdr, "variant","Variant","letter","char")
        for row in r:
            base = canon(row.get(base_col,""))
            var  = canon(row.get(var_col,""))
            if not base or not var:
                continue
            if var not in seen[base]:
                mapping[base].append(var)
                seen[base].add(var)
    return mapping

def read_global_by_base():
    """
    Возвращает:
      by_base:    dict[BASE] -> list[(VAR, W, p)] (отсортировано по W убыв.)
      flat:       list[(BASE, VAR, W, p)] — для мод-агрегации
      has_weight: dict[BASE]->set(VAR с весом) — удобно проверять
    """
    path = META / "global_frequencies_by_base.csv"
    by_base = defaultdict(list); flat = []
    has_weight = defaultdict(set)
    if not path.exists():
        return by_base, flat, has_weight

    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f); hdr = r.fieldnames or []
        base_col = pick(hdr, "base_letter","base","key","Base","BASE")
        var_col  = pick(hdr, "variant","Variant")
        w_col = "W" if "W" in hdr else pick(hdr, "p","prob","weight")
        p_col = "p" if "p" in hdr else None

        for row in r:
            base = canon(row.get(base_col,""))
            var  = canon(row.get(var_col,""))
            if not base or not var:
                continue
            try:  W = float(row.get(w_col,"") or 0.0)
            except: W = 0.0
            P = 0.0
            if p_col:
                try: P = float(row.get(p_col,"") or 0.0)
                except: P = 0.0
            by_base[base].append((var, W, P))
            flat.append((base, var, W, P))
            has_weight[base].add(var)

    for b in list(by_base.keys()):
        by_base[b].sort(key=lambda x: (-x[1], x[0]))
    return by_base, flat, has_weight

def read_sequences_with_weights():
    """Возвращает отчёт по последовательностям и missing; не влияет на буквенный маппинг."""
    path = META / "sequences_global.csv"
    seqs = defaultdict(list); missing = []
    if not path.exists():
        return seqs, missing

    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f); hdr = r.fieldnames or []
        var_col = pick(hdr, "variant","Variant","sequence","Sequence","seq")
        w_col = "W" if "W" in hdr else ("p" if "p" in hdr else None)
        buckets = defaultdict(list); seen = defaultdict(set)

        for row in r:
            v = canon(row.get(var_col,""))
            if not v:
                continue
            base = v[0]
            w = 0.0
            if w_col:
                try: w = float(row.get(w_col,"") or 0.0)
                except: w = 0.0
            if base not in JC_BASE:
                missing.append({"type":"seq_base_not_in_jcuken","value":base})
                continue
            if v not in seen[base]:
                buckets[base].append((v,w))
                seen[base].add(v)

        for b, items in buckets.items():
            items.sort(key=lambda x:(-x[1], x[0]))
            seqs[b] = [v for v,_ in items]

    return seqs, missing

def calc_letter_weight_from_sequences(letter: str) -> float:
    """
    Считает суммарный вес W по всем последовательностям, где встречается данная буква,
    на основе metadata/sequences_global.csv. Если W нет — суммируем p.
    """
    path = META / "sequences_global.csv"
    if not path.exists():
        return 0.0

    total = 0.0
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        hdr = r.fieldnames or []
        var_col = pick(hdr, "variant","Variant","sequence","Sequence","seq")
        w_col = "W" if "W" in hdr else ("p" if "p" in hdr else None)

        for row in r:
            v = canon(row.get(var_col,""))
            if not v:
                continue
            if letter in v:
                try:
                    total += float(row.get(w_col,"") or 0.0)
                except:
                    pass
    return total

# -------------------- Modifiers aggregation (report) --------------------
def aggregate_modifiers(flat_rows):
    """
    Считаем только модификаторы из композитов:
      • …ᵸ/ᴴ/ʰ → ключ 'ᵸ'
      • …Ӏ    → ключ 'Ӏ'
    Атомарные буквы и standalone (Ӏ, ᵸ) как самостоятельные — не считаем здесь.
    """
    agg = defaultdict(lambda: {"W":0.0,"P":0.0,"n":0,"examples":set()})

    def tail_after_base(base, var):
        return var[len(base):] if var.startswith(base) else var

    for base, var, W, P in flat_rows:
        if is_atomic_letter_or_standalone(var):
            continue
        tail = tail_after_base(base, var)
        if any(m in tail for m in H_EQUIV):
            key = "ᵸ"
        elif "Ӏ" in tail:
            key = "Ӏ"
        else:
            continue
        agg[key]["W"] += W
        agg[key]["P"] += P
        agg[key]["n"] += 1
        if len(agg[key]["examples"]) < 6:
            agg[key]["examples"].add(var)

    rows = [{
        "modifier": k,
        "W_total": f"{v['W']:.12f}",
        "p_total": f"{v['P']:.12f}",
        "samples": v["n"],
        "examples": " ".join(sorted(v["examples"]))
    } for k, v in agg.items()]
    rows.sort(key=lambda r: -float(r["W_total"]))
    return rows

# -------------------- Special insertion --------------------
def ensure_hard_extras_with_real_weight(key, ordered_list, has_weight_set, extra_weights):
    """
    Для спец-исключений (например, 'Н' → {'ᵸ'}):
      - добавляем вариант, если его ещё нет в списке;
      - сортируем с учётом real-weight: сначала все weighted (из global_by_base),
        затем спец-варианты с real weight, затем хвост без веса.
    """
    extras = HARD_EXTRAS.get(key, set())
    if not extras:
        return ordered_list

    extras_canon = [canon(v) for v in extras]
    current = ordered_list[:]
    present = set(current)

    weighted = [v for v in current if v in has_weight_set.get(key, set())]
    tail     = [v for v in current if v not in has_weight_set.get(key, set())]

    inserts = []
    for v in extras_canon:
        if v in present:
            continue
        inserts.append(v)

    # сортировка inserts по их реальному весу из sequences (desc, затем по алфавиту)
    inserts.sort(key=lambda v: (-extra_weights.get(v, 0.0), v))

    return weighted + inserts + tail

# -------------------- Main --------------------
def main():
    mapping = read_variant_mapping()
    by_base, flat, has_weight = read_global_by_base()
    sequences, seq_missing = read_sequences_with_weights()

    # посчитаем реальные веса для одиночных специальных букв (сейчас нам нужен ᵸ; можно расширять)
    extra_weights = {}
    for letter in {v for s in HARD_EXTRAS.values() for v in s} | STANDALONE_LETTERS:
        extra_weights[letter] = calc_letter_weight_from_sequences(letter)

    OUT_LETTERS.parent.mkdir(parents=True, exist_ok=True)

    # (A) НАБОРНЫЕ БУКВЫ (атомарные + standalone Ӏ, ᵸ)
    with open(OUT_LETTERS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["key","variants"])
        w.writeheader()
        for key in JC_BASE:
            mvars_all = mapping.get(key, [])
            # фильтр: только атомарные и standalone
            mvars = [v for v in mvars_all if is_atomic_letter_or_standalone(v)]
            # упорядочивание по глобальному весу
            weighted = [v for v,_,_ in by_base.get(key, []) if v in mvars]
            tail = [v for v in mvars if v not in weighted]
            ordered = weighted + tail
            # Спец-исключения: добавить, если нет, и отсортировать с учётом реального веса из sequences
            ordered = ensure_hard_extras_with_real_weight(key, ordered, has_weight, extra_weights)
            w.writerow({"key": key, "variants": " ".join(ordered)})

    # (B) ПОЛНЫЙ НАБОР (ничего не фильтруем)
    with open(OUT_LETTERS_FULL, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["key","variants"])
        w.writeheader()
        for key in JC_BASE:
            mvars = mapping.get(key, [])
            weighted = [v for v,_,_ in by_base.get(key, []) if v in mvars]
            tail = [v for v in mvars if v not in weighted]
            ordered = weighted + tail
            # уважим спец-исключения и здесь
            ordered = ensure_hard_extras_with_real_weight(key, ordered, has_weight, extra_weights)
            w.writerow({"key": key, "variants": " ".join(ordered)})

    # sequences (справочно)
    with open(OUT_SEQS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["key","sequences"])
        w.writeheader()
        for key in JC_BASE:
            w.writerow({"key": key, "sequences": " ".join(sequences.get(key, []))})

    # missing
    missing = [{"type":"base_not_in_jcuken","value": b}
               for b in mapping.keys() if b not in JC_BASE]
    missing.extend(seq_missing)
    with open(OUT_MISSING, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["type","value"])
        w.writeheader(); w.writerows(missing)

    # модификаторные приоритеты (из композитов; standalone не считаем)
    mod_rows = aggregate_modifiers(flat)
    with open(OUT_MODS, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["modifier","W_total","p_total","samples","examples"])
        w.writeheader(); w.writerows(mod_rows)

if __name__ == "__main__":
    main()
