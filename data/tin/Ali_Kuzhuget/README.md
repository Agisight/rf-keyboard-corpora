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
  -- NFC joins И+◌̄ → Ӣ and У+◌̄ → Ӯ; А̄ Е̄ О̄ С̄ have no precomposed form and stay as letter + U+0304
  SELECT nfc_normalize(UPPER(text)) AS text
  FROM train
),
normalized_text AS (
  SELECT
    regexp_replace(            -- one nasal marker: ᵸ (U+1D78) → ᴴ (U+1D34)
      regexp_replace(          -- palochka look-alikes next to Cyrillic → Ӏ (U+04C0)
        regexp_replace(text, '([А-ЯЁӀӢӮ])[ⅠＩǀ│┃∣❘I1|І]', '\1Ӏ', 'g'),
        '[ⅠＩǀ│┃∣❘I1|І]([А-ЯЁӀӢӮ])', 'Ӏ\1', 'g'
      ),
      'ᵸ', 'ᴴ', 'g'
    ) AS norm_text
  FROM raw_text
),
extracted_letters AS (
  SELECT
    regexp_extract_all(
      norm_text,
      '(А̄ᴴ)|(ЛЛЪ)|(Е̄ᴴ)|(О̄ᴴ)|(А̄)|(ЧЧ)|(Аᴴ)|(ТӀ)|(ГЬ)|(Ӣᴴ)|(Иᴴ)|(ХӀ)|(ЛӀ)|(ЦЦ)|(Уᴴ)|(ГӀ)|(ХЬ)|(ДЖ)|(О̄)|(ХХ)|(Еᴴ)|(Ӯᴴ)|(ЧӀ)|(ЦӀ)|(Е̄)|(ЛЪ)|(КК)|(КӀ)|(ХЪ)|(ГЪ)|(Оᴴ)|(С̄)|(Ӣ)|(Ӯ)|([АБВГҒДЕЁЖЗИЙӀКЛМНҢОӦПРСТУӰФХЦЧӋШЩЪЫЬЭЮЯ])'
    ) AS letter
  FROM normalized_text
),
flattened AS (
  SELECT unnest(letter) AS letter
  FROM extracted_letters
),
grouped AS (
  SELECT letter, COUNT(*) AS frequency
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
-- Check: what stands before a palochka that wasn't joined into a known digraph?
-- If ЧӀ, ПӀ, КЪ etc. show up here, they should be added to the letter list.
WITH t AS (
  SELECT regexp_replace(regexp_replace(nfc_normalize(UPPER(text)),
           '([А-ЯЁӀӢӮ])[ⅠＩǀ│┃∣❘I1|І]', '\1Ӏ', 'g'), '[ⅠＩǀ│┃∣❘I1|І]([А-ЯЁӀӢӮ])', 'Ӏ\1', 'g') AS s
  FROM train
)
SELECT pair, COUNT(*) AS n
FROM (SELECT unnest(regexp_extract_all(s, '(.Ӏ)')) AS pair FROM t)
GROUP BY pair ORDER BY n DESC;
```