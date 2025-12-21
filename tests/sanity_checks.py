# -*- coding: utf-8 -*-
"""
Sanity checks for RF-only keyboard statistics pipeline.

Запуск:
    python tests/sanity_checks.py

Падаем с AssertionError, если что-то не так.
"""

import csv
import os
from collections import defaultdict
from decimal import Decimal

SUMMARIES = "summaries"


# ----------------------------
# helpers
# ----------------------------

def read_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def assert_range(val, lo, hi, msg):
    assert lo <= val <= hi, f"{msg}: {val} not in [{lo}, {hi}]"


# ----------------------------
# 1. SUM TESTS
# ----------------------------

def test_rf_population_sum(expected_total=17_588_062):
    rows = read_csv(f"{SUMMARIES}/speakers_rf.csv")
    total = sum(int(float(r["population"])) for r in rows)
    assert total == expected_total, f"RF population mismatch: {total} != {expected_total}"
    print("✓ RF population sum OK")


# ----------------------------
# 2. FREQUENCY / SHARE TESTS
# ----------------------------

def test_frequencies_normalized():
    rows = read_csv(f"{SUMMARIES}/frequencies_by_language.csv")
    by_lang = defaultdict(float)

    for r in rows:
        by_lang[r["lang_code"]] += float(r["f_i"])

    for lang, s in by_lang.items():
        assert_range(s, 0.98, 1.02, f"{lang} f_i sum")
    print("✓ Frequencies normalized per language")


def test_letter_share_sum():
    rows = read_csv(f"{SUMMARIES}/rf_letter_popularity_weighted.csv")
    s = sum(float(r["share"]) for r in rows)
    assert_range(s, 0.999, 1.001, "Letter shares sum")
    print("✓ Letter share sum OK")


def test_symbol_share_sum():
    rows = read_csv(f"{SUMMARIES}/rf_symbol_popularity_weighted.csv")
    s = sum(float(r["share"]) for r in rows)
    assert_range(s, 0.999, 1.001, "Symbol shares sum")
    print("✓ Symbol share sum OK")


# ----------------------------
# 3. STRUCTURAL INVARIANTS
# ----------------------------

def test_no_standalone_yo_and_hard_sign():
    """
    Ъ и Ё запрещены как САМОСТОЯТЕЛЬНЫЕ варианты,
    но допустимы как ГРАФЕМЫ внутри вариантов и в symbol-статистике.
    """

    bad = {"Ё", "Ъ"}

    # Файлы, где проверяем ТОЛЬКО variants / base_letter
    files = [
        "frequencies_by_language.csv",
        "variant_mapping_atomic.csv",
        "variant_mapping.csv",
        "rf_letter_popularity_weighted.csv",
    ]

    for fn in files:
        path = f"{SUMMARIES}/{fn}"
        if not os.path.exists(path):
            continue

        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                for key in ("variant", "base_letter"):
                    if key in r:
                        val = (r[key] or "").strip()
                        assert val not in bad, f"Standalone {val} found in {fn}"

    print("✓ No standalone Ё or Ъ in variants")


def test_no_global_artifacts():
    for fn in os.listdir(SUMMARIES):
        assert "global" not in fn.lower(), f"Global artifact found: {fn}"
    print("✓ No global artifacts")


# ----------------------------
# 4. MAPPING LOGIC TESTS
# ----------------------------

def test_mapping_group_percentages():
    rows = read_csv(f"{SUMMARIES}/variant_mapping_stats.csv")
    groups = defaultdict(list)

    for r in rows:
        groups[r["base_letter"]].append(r["relative_freq_in_group"])

    for base, vals in groups.items():
        # если один вариант — проверка не нужна
        if len(vals) == 1:
            continue

        # если есть >99% — группа доминирующая, ок
        if any(v.startswith(">") for v in vals):
            continue

        total = Decimal("0")
        numeric_count = 0

        for v in vals:
            if v.startswith("<"):
                continue
            if v.endswith("%"):
                total += Decimal(v.replace("%", ""))
                numeric_count += 1

        # если есть хотя бы 2 численных значения —
        # сумма должна быть "почти 100", но допускаем потери
        if numeric_count >= 2:
            assert total >= Decimal("95"), (
                f"{base} group visible % sum too low: {total}"
            )

    print("✓ Mapping group percentages (rounded) OK")


# ----------------------------
# 5. SMOKE TEST
# ----------------------------

def test_required_outputs_exist():
    required = [
        "speakers_rf.csv",
        "frequencies_by_language.csv",
        "rf_letter_popularity_weighted.csv",
        "rf_symbol_popularity_weighted.csv",
        "variant_mapping_stats.csv",
        "variant_mapping_priorities_apple.csv",
        "variant_mapping_priorities_unicode.csv",
    ]

    for fn in required:
        path = f"{SUMMARIES}/{fn}"
        assert os.path.exists(path), f"Missing output: {fn}"

    print("✓ All required outputs exist")


# ----------------------------
# RUN ALL
# ----------------------------

if __name__ == "__main__":
    print("Running sanity checks...\n")

    test_rf_population_sum()
    test_frequencies_normalized()
    test_letter_share_sum()
    test_symbol_share_sum()
    test_no_standalone_yo_and_hard_sign()
    test_no_global_artifacts()
    test_mapping_group_percentages()
    test_required_outputs_exist()

    print("\n✅ All sanity checks passed")
