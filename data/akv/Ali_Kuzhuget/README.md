# Данные для языка `akv` от вендора Ali Kuzhuget

## raw/
Содержит монокорпуса различных размеров:
- akv_mono_1M.txt

## stats/
Один файл akv_population.csv со столбцами:
- year
- total_speakers_global
- total_speakers_rf
- source_name
- source_url

## keyboard/
JSON‑файлы с вариантами раскладок:
- akv_key_default.json

## frequencies/
akv_monocorpus_freq.csv — частотности символов.

## mapping/
akv_key_mapping.json — маппинг расширенных букв на русские клавиши.

## metadata.json
Обязательные поля: version, source, date_collected, contact, description.
Допускаются дополнительные поля.

---  
**Подсказка:** можно добавлять аудиоданные, фонетику, примеры предложений, графики и др.

## Код для подсчета частот букв: 

```sql
WITH raw_text AS (
  SELECT UPPER(text) AS text
  FROM akv_cyrl_train
),
pre_norm_text AS (
  SELECT
    regexp_replace(text, '^(\d+)((?=[А-Я]))', '\1 \2', 'g') AS text
  FROM raw_text
),
normalized_text AS (
  SELECT
    regexp_replace(text, '[ⅠＩǀ│┃∣❘I1l|І](?=[а-яА-ЯӀ])|(?<=[а-яА-ЯӀ])[ⅠＩǀ│┃∣❘I1l|І]', 'Ӏ', 'g') AS norm_text
  FROM pre_norm_text
),
extracted_letters AS (
  SELECT
    regexp_extract_all(
      norm_text,
      '(КӀКӀ)|(ЛЪЛЪ)|(ЦӀЦӀ)|(ЧӀЧӀ)|(КЪӀ)|(КЬӀ)|(ЛЪӀ)|(ХЪӀ)|(Аᴴ)|(ГЬ)|(ГЪ)|(ГӀ)|(Еᴴ)|(ДЖ)|(Иᴴ)|(КК)|(КЪ)|(КЬ)|(КӀ)|(ЛЪ)|(ЛӀ)|(Оᴴ)|(ПӀ)|(СС)|(ТӀ)|(Уᴴ)|(ХХ)|(ХЬ)|(ХЪ)|(ХӀ)|(ЦЦ)|(ЦӀ)|(ЧЧ)|(ЧӀ)|([АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯӀ])'
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
