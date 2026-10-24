# Данные для языка `tin` от вендора Ali Kuzhuget

## raw/
Содержит монокорпуса различных размеров:
- tin_mono_12K.txt


## stats/
Один файл tin_population.csv со столбцами:
- year
- total_speakers_global
- total_speakers_rf
- source_name
- source_url

## keyboard/
JSON‑файлы с вариантами раскладок:
- tin_key_default.json

## frequencies/
- tin_monocorpus_freq.csv — частотности символов.

## mapping/
- tin_key_mapping.json — маппинг расширенных букв на русские клавиши.

## metadata.json
Обязательные поля: version, vendor, source, date_collected, contact, description.
Допускаются дополнительные поля.

---  
**Подсказка:** можно добавлять аудиоданные, фонетику, примеры предложений, графики и др.

## Код для подсчета частот

```sql
WITH raw_text AS (
  SELECT UPPER(text) AS text
  FROM train
),
normalized_text AS (
  SELECT
    regexp_replace(
      regexp_replace(text, '([А-ЯЁӀ])[ⅠＩǀ│┃∣❘I1|І]', '\1Ӏ', 'g'),
      '[ⅠＩǀ│┃∣❘I1|І]([А-ЯЁӀ])', 'Ӏ\1', 'g'
    ) AS norm_text
  FROM raw_text
),
extracted_letters AS (
  SELECT
    regexp_extract_all(
      norm_text,
      '(ᵸ)|(А̄)|(Аᴴ)|(А̄ᴴ)|(ГЪ)|(ГЬ)|(ГӀ)|(Еᴴ)|(Е̄)|(ДЖ)|(Ӣ)|(Иᴴ)|(Ӣᴴ)|(КК)|(КӀ)|(ЛЪ)|(ЛЛЪ)|(ЛӀ)|(О̄)|(Оᴴ)|(C̄)|(ТӀ)|(Ӯ)|(Уᴴ)|(Ӯᴴ)|(ХХ)|(ХЪ)|(ХЬ)|(ХӀ)|(ЦЦ)|(ЦӀ)|(ЧЧ)|([АБВГҒДЕЁЖЗИЙӀКЛМНҢОӦПРСТУӰФХЦЧӋШЩЪЫЬЭЮЯ])'
    ) AS letter
  FROM normalized_text
),
flattened AS (
  SELECT unnest(letter) AS letter
  FROM extracted_letters
),
grouped AS (
  SELECT
    letter,
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
  ROUND((frequency * 100.0) / total_chars, 4) AS percent
FROM grouped
CROSS JOIN total_count
ORDER BY frequency DESC;
```