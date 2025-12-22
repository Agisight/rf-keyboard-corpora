# Анализ частот букв на монокорпусе

Допустим, вы загрузили монокорпус на [Hugging Face](https://huggingface.co/). На экране Data Studio или viewer (например, тут https://huggingface.co/datasets/Agisight/tin_words/viewer) увидите справа инструмент обработки данных датасета. Внизу скрипт можно вставить, но надо адаптировать под ваш язык.

– Имя таблицы: `train`  
– Имя столбца с текстом: `text`  
– Список заглавных букв казахского алфавита (для регулярки) – **[АӘБВГҒДЕЁЖЗИЙКҚЛМНҢОӨПРСТУҰҮФХҺЦЧШЩЪЫІЬЭЮЯ]**

Для некоторых СевКав языков парные буквы нужно сначала собрать, по ним собрать категорию для посчета их, а потом применять категоризацию букв в тексте.


```sql
WITH raw_text AS (
  SELECT UPPER(text) AS text FROM train
),
normalized_text AS (
  SELECT
    regexp_replace(text, '[1]', '1', 'g') AS norm_text
  FROM raw_text
),
extracted_letters AS (
  SELECT
    regexp_extract_all(
      norm_text,
      '([АӘБВГҒДЕЁЖЗИЙКҚЛМНҢОӨПРСТУҰҮФХҺЦЧШЩЪЫІЬЭЮЯ])'
    ) AS letter
  FROM normalized_text
),
flattened AS (
  SELECT unnest(letter) AS letter FROM extracted_letters
),
grouped AS (
  SELECT letter, COUNT(*) AS frequency
  FROM flattened
  GROUP BY letter
),
total_count AS (
  SELECT SUM(frequency) AS total_chars FROM grouped
)
SELECT 
  letter,
  frequency,
  ROUND((frequency * 100.0) / total_chars, 4) AS percent
FROM grouped, total_count
ORDER BY frequency DESC;
```
