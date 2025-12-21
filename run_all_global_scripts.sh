#!/bin/bash
# run_all_global_scripts.sh - Запуск всех скриптов обработки данных

set -e  # останавливаться при ошибке

echo "================================"
echo "Запуск пайплайна обработки данных"
echo "================================"
echo ""

# Переходим в корень репозитория
cd "$(dirname "$0")"

echo "[1/6] Создание общей сводки..."
python3 data_scripts/01_summarize_datasets.py
echo ""

echo "[2/6] Сбор данных о носителях языков..."
echo "      → Без изменений (не работает с буквами)"
python3 data_scripts/02_speakers_global.py
echo ""

echo "[3/6] Агрегация маппингов..."
python3 data_scripts/03_aggregate_mappings.py
echo ""

echo "[4/6] Сбор частот по языкам..."
python3 data_scripts/04_collect_language_frequencies.py
echo ""

echo "[5/6] Расчёт взвешенной популярности..."
python3 data_scripts/05_build_weighted_letter_popularity.py
echo ""

echo "[6/6] Создание статистики маппингов..."
python3 data_scripts/06_variant_mapping_stats.py
echo ""


echo "================================"
echo "✅ Пайплайн завершён успешно!"
echo "================================"
echo ""
echo "Созданные файлы в summaries/:"
ls -lh summaries/*.{csv,md} 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
