# -*- coding: utf-8 -*-
# 03c_non_russian_letters.py
# Из metadata/global_frequencies.csv делаем:
#  1) non_russian_letters_global.csv — одиночные НЕ русские буквы (вне [А-ЯЁ])
#  2) sequences_global.csv — все последовательности (len(NFC)>1), с флагом contains_non_russian

import csv, unicodedata, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

IN_CSV   = "metadata/global_frequencies.csv"   # variant,W,p,langs_count
OUT_NONR = "metadata/non_russian_letters_global.csv"
OUT_SEQ  = "metadata/sequences_global.csv"

RU_SET = set("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")

def nfc_upper(s: str) -> str:
    return unicodedata.normalize("NFC", s or "").upper()

def to_float(x):
    try:
        return float(str(x).replace(",", "."))
    except Exception:
        return 0.0

def main():
    if not Path(IN_CSV).exists():
        print(f"ERR: нет {IN_CSV}. Сначала запусти 03_build_global_frequencies.py")
        return

    non_rus_rows = []
    seq_rows = []

    with open(IN_CSV, encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            v_raw = (row.get("variant") or "").strip()
            if not v_raw:
                continue
            v = nfc_upper(v_raw)
            W = row.get("W", "")
            p = row.get("p", "")
            langs = row.get("langs_count", "")

            # последовательности
            if len(v) > 1:
                contains_non_russian = any(ch not in RU_SET for ch in v)
                seq_rows.append({
                    "variant": v,
                    "W": W,
                    "p": p,
                    "langs_count": langs,
                    "contains_non_russian": "1" if contains_non_russian else "0",
                })
                continue

            # одиночные — фильтруем НЕ русские
            if v not in RU_SET:
                non_rus_rows.append({
                    "variant": v,
                    "W": W,
                    "p": p,
                    "langs_count": langs,
                })

    # сортировка по W по убыванию
    non_rus_rows.sort(key=lambda d: to_float(d["W"]), reverse=True)
    seq_rows.sort(key=lambda d: to_float(d["W"]), reverse=True)

    Path("metadata").mkdir(parents=True, exist_ok=True)
    with open(OUT_NONR, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["variant","W","p","langs_count"])
        w.writeheader(); w.writerows(non_rus_rows)

    with open(OUT_SEQ, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["variant","W","p","langs_count","contains_non_russian"])
        w.writeheader(); w.writerows(seq_rows)

    print(f"OK: wrote {OUT_NONR} (rows={len(non_rus_rows)})")
    print(f"OK: wrote {OUT_SEQ} (rows={len(seq_rows)})")

if __name__ == "__main__":
    main()
