# Данные для языка bel от вендора Ali Kuzhuget

## raw/
Содержит монокорпуса различных размеров:
- bel_mono_1B.txt

## stats/
Один файл bel_population.csv со столбцами:
- year
- total_speakers_global
- total_speakers_rf
- source_name
- source_url

## keyboard/
JSON‑файлы с вариантами раскладок:
- bel_key_default.json (вариант по умолчанию)

## frequencies/
- bel_monocorpus_freq.csv — частотности символов.

## mapping/
- bel_key_mapping.json — маппинг расширенных букв на русские клавиши.

## metadata.json
Обязательные поля: version, vendor, source, date_collected, contact, description.
Допускаются дополнительные поля.

---  
**Подсказка:** можно добавлять аудиоданные, фонетику, примеры предложений, графики и др.

--- 

## Код для анализа частот букв на датасете https://huggingface.co/datasets/WiNE-iNEFF/1M-OpenOrca_be/sql-console/wakyFkc

```sql
WITH raw_text AS (
  -- объединяем два столбца через пробел и приводим к верхнему регистру
  SELECT
    UPPER( question || ' ' || response ) AS full_text
  FROM train
),
normalized AS (
  SELECT
    -- любые ваши замены, если нужно
    regexp_replace(full_text, '[1]', '1', 'g') AS norm_text
  FROM raw_text
),
extracted AS (
  SELECT
    regexp_extract_all(
      norm_text,
      '([АБВГДЕЁЖЗІЙКЛМНОПРСТУЎФХЦЧШЫЬЭЮЯ])'
    ) AS letters
  FROM normalized
),
flattened AS (
  SELECT unnest(letters) AS letter
  FROM extracted
),
grouped AS (
  SELECT letter,
         COUNT(*) AS frequency
  FROM flattened
  GROUP BY letter
),
total_count AS (
  SELECT SUM(frequency) AS total_chars
  FROM grouped
)
SELECT
  letter,
  frequency,
  ROUND(frequency * 100.0 / total_chars, 4) AS percent
FROM grouped, total_count
ORDER BY frequency DESC
;

```