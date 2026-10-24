# Данные для языка `lbe` от вендора Ali Kuzhuget

## raw/
Содержит монокорпуса различных размеров:
- lbe_mono_11.8M.txt

## stats/
Один файл lbe_population.csv со столбцами:
- year
- total_speakers_global
- total_speakers_rf
- source_name
- source_url

## keyboard/
JSON‑файлы с вариантами раскладок:
- lbe_key_default.json

## frequencies/
lbe_monocorpus_freq.csv — частотности символов.

## mapping/
lbe_key_mapping.json — маппинг расширенных букв на русские клавиши.

## metadata.json
Обязательные поля: version, source, date_collected, contact, description.
Допускаются дополнительные поля.

---  
**Подсказка:** можно добавлять аудиоданные, фонетику, примеры предложений, графики и др.

## Код для подсчета частот букв: 

```sql
WITH raw_text AS (
  SELECT UPPER(text) AS text
  FROM lbe_cyrl_train
),
pre_norm_text AS (
  SELECT
    regexp_replace(text, '^(\d+)([А-Я])', '\1 \2', 'g') AS text
  FROM raw_text
),
normalized_text AS (
  SELECT
    regexp_replace(
      regexp_replace(text, '([а-яА-ЯӀ])[ⅠＩǀ│┃∣❘I1l|І]', '\1Ӏ', 'g'),
      '[ⅠＩǀ│┃∣❘I1l|І]([а-яА-ЯӀ])', 'Ӏ\1', 'g'
    ) AS norm_text
  FROM pre_norm_text
),
extracted_letters AS (
  SELECT
    regexp_extract_all(
      norm_text,
      '(ХЬХЬ)|(АЬ)|(ГЪ)|(ГЬ)|(КЪ)|(КК)|(КЬ)|(КӀ)|(ОЬ)|(ПП)|(ПӀ)|(СС)|(ТТ)|(ТӀ)|(ХХ)|(ХЪ)|(ХЬ)|(ХӀ)|(ЦЦ)|(ЦӀ)|(ЧЧ)|(ЧӀ)|([АБВГҒДЕЁЖЗИЙӀКЛМНҢОӦПРСТУӰФХЦЧӋШЩЪЫЬЭЮЯ])'
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

### Проверка палочки

```sql
-- What stands before a palochka that is NOT part of a digraph (КӀ ПӀ ТӀ ХӀ ЦӀ ЧӀ)?
-- '·' = start of text, a space or punctuation: the palochka begins a word.
-- Anything else (a vowel, another letter) is worth a look: a missing digraph or a false conversion.
WITH t AS (
  SELECT regexp_replace(
           regexp_replace(
             regexp_replace(UPPER(text), '^(\d+)([А-Я])', '\1 \2', 'g'),
             '([а-яА-ЯӀ])[ⅠＩǀ│┃∣❘I1l|І]', '\1Ӏ', 'g'),
           '[ⅠＩǀ│┃∣❘I1l|І]([а-яА-ЯӀ])', 'Ӏ\1', 'g') AS s
  FROM lbe_cyrl_train
),
hits AS (
  SELECT unnest(regexp_extract_all(' ' || s, '(.)Ӏ', 1)) AS prev
  FROM t
)
SELECT CASE WHEN regexp_matches(prev, '[А-ЯЁӀ]') THEN prev ELSE '·' END AS before_palochka,
       COUNT(*) AS n
FROM hits
WHERE prev NOT IN ('К', 'П', 'Т', 'Х', 'Ц', 'Ч')
GROUP BY before_palochka
ORDER BY n DESC;
```