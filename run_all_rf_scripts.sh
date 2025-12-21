#!/bin/bash
# run_all.sh - Запуск всех скриптов обработки данных
# Фильтрация Ё и Ъ только в точках входа (01, 03, 04)
# Скрипты 05 и 06 автоматически получают чистые данные

set -e  # останавливаться при ошибке

echo "================================"
echo "Запуск пайплайна обработки данных"
echo "Оптимизированная фильтрация Ё и Ъ"
echo "================================"
echo ""

# Переходим в корень репозитория
cd "$(dirname "$0")"

echo "[1/6] Создание общей сводки..."
echo "      → Фильтрация Ё/Ъ из Special letters"
python3 rf_data_scripts/01_summarize_datasets.py
echo ""

echo "[2/6] Сбор данных о носителях языков..."
echo "      → Без изменений (не работает с буквами)"
python3 rf_data_scripts/02_speakers_rf.py
echo ""

echo "[3/6] Агрегация маппингов..."
echo "      → Фильтрация Ё/Ъ на входе (base_letter + variant)"
python3 rf_data_scripts/03_aggregate_mappings.py
echo ""

echo "[4/6] Сбор частот по языкам..."
echo "      → Фильтрация Ё/Ъ на входе (variant)"
python3 rf_data_scripts/04_collect_language_frequencies.py
echo ""

echo "[5/6] Расчёт взвешенной популярности..."
echo "      → Без изменений (получает чистые данные из 04)"
python3 rf_data_scripts/05_build_weighted_letter_popularity.py
echo ""

echo "[6/6] Создание статистики маппингов..."
echo "      → Без изменений (получает чистые данные из 03+05)"
python3 rf_data_scripts/06_variant_mapping_stats.py
echo ""

echo "[1/1] Тесты"
echo "      → Ряд тестов на корректность сгенерированных данных"
python3 tests/sanity_checks.py || exit 1
echo ""


echo "================================"
echo "✅ Пайплайн завершён успешно!"
echo "================================"
echo ""
echo "Созданные файлы в rf_summaries/:"
ls -lh rf_summaries/*.{csv,md} 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "ℹ️  Фильтрация Ё и Ъ:"
echo "   • Прямая: скрипты 01, 03, 04"
echo "   • Каскадная: скрипты 05, 06 (автоматически)"
