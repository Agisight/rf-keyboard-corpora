# rf-keyboard-corpora

**Corpus-based infrastructure for scalable support of Cyrillic languages on mobile keyboards**

*Русская версия описания находится ниже.*

> **Project Goals**
>
> 1. Extend the Russian keyboard layout with corpus-derived long-press mappings to improve support for additional Cyrillic languages.
> 2. Prepare language-specific keyboard resources and layouts for individual Cyrillic languages.
> 3. Provide open language infrastructure for researchers, language communities, linguists, and software developers.
> 4. Develop a scalable framework that can support Cyrillic languages beyond the Russian Federation.
> 5. Contribute reusable language resources for future keyboard technologies, localization systems, NLP research, and AI applications.

RF Keyboard Corpora is a corpus-based language infrastructure project designed to improve digital support for Cyrillic languages.

The project currently includes 53 languages representing approximately 138.9 million speakers and more than 6.1 billion corpus words. It combines language metadata, corpus-derived frequency statistics, character mappings, speaker demographics, and machine-readable keyboard specifications.

The framework explores how existing Russian keyboard infrastructure can be extended through corpus-based long-press optimization to support a much broader multilingual Cyrillic ecosystem. The resulting approach may benefit not only speakers of underrepresented languages, but also Russian-speaking users, bilingual communities, researchers, students, and travelers who regularly interact with multiple Cyrillic languages.

In addition to mobile keyboard development, the dataset may be useful for localization, spell checking, predictive text systems, educational software, language technology research, natural language processing, and future AI systems.

The project is based on a simple principle: if a language has a writing system, it should be practical to use that writing system on modern devices.

---

## Documentation

For readers, researchers, and contributors:

* **ARCHITECTURE.md** — corpus processing workflow, frequency analysis, long-press generation, and keyboard infrastructure design.
* **DATASET_OVERVIEW.md** — project statistics, language coverage, speaker coverage, geographic scope, and ecosystem impact.
* **AUTHORS_AND_CONTRIBUTORS.md** — project authorship, language contributors, and community collaboration.

For language-specific data, see the corresponding folders under `data/`.

---

# Клавиатура РФ

**Корпусная инфраструктура проекта «Клавиатура РФ» для поддержки кириллических языков**

> **Цели проекта**  
> 1. Расширить **русскую системную раскладку**, чтобы через long-press покрыть все кириллические языки Российской Федерации.  
> 2. Подготовить **индивидуальные системные клавиатуры** для каждого языка РФ.
> 3. Создать открытый набор языковых данных для исследователей, языковых сообществ и разработчиков.
> 4. Разработать масштабируемую инфраструктуру для поддержки кириллических языков за пределами Российской Федерации.
> 5. Подготовить данные для будущих клавиатур, локализации, NLP и AI-систем.

---

## 1. Какие данные собираем и зачем

| Компонент                | Файл/папка                             | Назначение                                                                              |
| ------------------------ | -------------------------------------- | --------------------------------------------------------------------------------------- |
| **Монокорпус**           | `raw/lang_mono_<N>.txt`                | Сплошной текст на языке-цели; `N` — примерный размер корпуса в словах. Основной источник статистики по **символам** (один токен = один Unicode‑символ).        |
| **Частотности**          | `frequencies/lang_monocorpus_freq.csv` | Таблица «символ → вхождений» — влияет на сортировку вариантов long‑press                |
| **Раскладки**            | `keyboard/lang_key_*.json`             | Базовая, 4‑рядная, комплексная и т. д. — готовые файлы iOS                              |
| **Long‑press‑маппинг**   | `mapping/lang_key_mapping.json`        | Указывает, под какой **базовой** русской буквой показывать дополнительные буквы/символы языка |
| **Статистика носителей** | `stats/lang_population.csv`            | Взвешиваем «частота × охват» и аргументируем приоритеты перед Apple. Охват = носители   |
| **Манифест**             | `metadata.json`                        | Машинно‑читаемые метаданные (версия, лицензия, контакты)                                |
| **README**               | `README.md`                            | Человеческое описание: источники корпуса, очистка, особенности                          |

> `lang` — код ISO 639‑3 (пример: `tyv`, `kbd`).

---

## 2. Маппинг ваших букв на буквы Русского языка

В случае долгого нажатия буквы в стандартной русской клавиатуре (например, как сейчас Е -> [Ё]), ваши буквы должны иметь ближайшую похожую букву, через которую покажется в случае создания расширенной Клавиатуры РФ.

Соответствие ваших букв к букве Русского языка в файле **lang_key_mapping.json**:

```jsonc
{
  "О": ["Ӧ", "Ө", "О̄"],
  "У": ["Ӱ", "Ү"],
  "Н": ["Ң"],
  "Е": ["Ё", "Ё"]
}
```

или же создать более простой вариант в текстовом формате **lang_key_mapping.txt**:

```txt
О | Ӧ, Ө, О̄
У | Ӱ, Ү
Н | Ң
Е | Ё, Ё
```


*Ключ — базовая русская клавиша; значения — варианты в порядке убывания частоты (но пока это не столь важно).*

---

## 3. Мини-пайплайн добавления языка

1. **Соберите корпус** → `raw/`, один символ = один токен.

2. **Вычислите частоты**
   – на Hugging Face загрузите корпус и сделайте что-то подобное по инструкции на этой [странице](https://github.com/Agisight/rf-keyboard-corpora/blob/rf/hf_freq_analyze.md) – есть встроенный механизм подсчета данных у вашего монокорпуса.

3. **Создайте `lang_key_mapping.txt` или `lang_key_mapping.json`** вручную в удобном редакторе.

4. **Подготовьте раскладки** (`keyboard/lang_key_default.json` и, при необходимости, дополнительные).

5. **Добавьте статистику носителей**, заполните `metadata.json` и `README.md`.

6. **Откройте pull‑request**.

---

## 4. FAQ

| Вопрос                                                                   | Ответ                                                                             |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| **Можно ли несколько вендоров для одного языка?**                        | Да. Используйте разные папки `<vendor>`; скрипты автоматически объединят частоты. |
| **Как обрабатывать emoji, латиницу и другие чужие символы?**             | При расчёте частот скрипт по умолчанию игнорирует всё, что не входит в кириллический блок Unicode. Буквы целевого языка сохраняются, шум отбрасывается. |
| **Нужно ли включать пробелы и пунктуацию в `lang_monocorpus_freq.csv`?** | Нет. Оставляйте только буквенные символы и специфические знаки языка; пробелы и знаки препинания опускайте.                                             |
| **Как именовать файлы при обновлении корпуса?**                          | Добавляйте суффикс версии (`_v2`, дата) и обновляйте поле `version` в `metadata.json`.                                                                  |
| **Обязательна ли 4‑рядная раскладка?**                                   | Нет. Добавляйте её, если она будет полезна; базовая портретная раскладка (3 ряда символов) обязательна.                                       |
| **Какую лицензию выбрать для корпуса?**                                  | Рекомендуем MIT или совместимую открытую лицензию, чтобы Apple могла свободно использовать данные.        


---

**Корпус → Частоты → Инфраструктура языка** — точные данные дают объективное основание для расположения букв. Чем точнее корпуса и статистика, тем убедительнее аргумент для Apple внедрить полноценную поддержку всех кириллических языков Российской Федерации.

## 5. Готовность языков

| Язык                      | Частотность | Маппинг | Носители | by Ali Kuzhuget |
|---------------------------|-------------|---------|----------|------------------|
| Абазинский                | ✅          | ✅      | ✅       | ○                |
| Абхазский                 | ✅          | ✅      | ✅       | ○                |
| Аварский                  | ✅          | ✅      | ✅       | ○                |
| Агульский                 | ✅          | ✅      | ✅       | ●                |
| Адыгейский                | ✅          | ✅      | ✅       | ○                |
| Алтайский                 | ✅          | ✅      | ✅       | ●                |
| Андийский                 | ✅          | ✅      | ✅       | ●                |
| Ахвахский                 | ❌          | ✅      | ✅       | ○                |
| Башкирский                | ✅          | ✅      | ✅       | ○                |
| Белорусский               | ✅          | ✅      | ✅       | ●                |
| Бурятский                 | ✅          | ✅      | ✅       | ○                |
| Даргинский                | ✅          | ✅      | ✅       | ○                |
| Долганский                | ✅          | ✅      | ✅       | ○                |
| Церковнославянский        | ✅          | ✅      | ✅       | ●                |
| Ингушский                 | ✅          | ✅      | ✅       | ●                |
| Кабардино-черкесский      | ✅          | ✅      | ✅       | ○                |
| Казахский                 | ✅          | ✅      | ✅       | ●                |
| Кайтагский                | ✅          | ✅      | ✅       | ○                |
| Калмыцкий                 | ✅          | ✅      | ✅       | ●                |
| Каратинский               | ✅          | ✅      | ✅       | ○                |
| Карачаево-балкарский      | ✅          | ✅      | ✅       | ○                |
| Коми                      | ✅          | ✅      | ✅       | ○                |
| Крымскотатарский          | ✅          | ✅      | ✅       | ●                |
| Кумыкский                 | ✅          | ✅      | ✅       | ●                |
| Кыргыз                    | ✅          | ✅      | ✅       | ●                |
| Лакский                   | ✅          | ✅      | ✅       | ●                |
| Лезгинский                | ✅          | ✅      | ✅       | ○                |
| Марийский                 | ✅          | ✅      | ✅       | ●                |
| Мокшанский                | ✅          | ✅      | ✅       | ●                |
| Молдавский                | ✅          | ✅      | ✅       | ●                |
| Ненецкий                  | ✅          | ✅      | ✅       | ●                |
| Ногайский                 | ✅          | ✅      | ✅       | ○                |
| Осетинский                | ✅          | ✅      | ✅       | ○                |
| Рутульский                | ✅          | ✅      | ✅       | ●                |
| Саха                      | ✅          | ✅      | ✅       | ○                |
| Сибирско-татарский        | ✅          | ✅      | ✅       | ○                |
| Табасаранский             | ✅          | ✅      | ✅       | ●                |
| Таджикский                | ✅          | ✅      | ✅       | ○                |
| Татарский                 | ✅          | ✅      | ✅       | ○                |
| Тиндинский                | ✅          | ✅      | ✅       | ●                |
| Тувинский                 | ✅          | ✅      | ✅       | ●                |
| Удмуртский                | ✅          | ✅      | ✅       | ○                |
| Узбекский                 | ✅          | ✅      | ✅       | ●                |
| Украинский                | ✅          | ✅      | ✅       | ●                |
| Хакасский                 | ✅          | ✅      | ✅       | ●                |
| Цудахарский               | ✅          | ✅      | ✅       | ●                |
| Цыганский                 | ✅          | ✅      | ✅       | ●                |
| Чеченский                 | ✅          | ✅      | ✅       | ●                |
| Чувашский                 | ✅          | ✅      | ✅       | ○                |
| Эрзянский                 | ✅          | ✅      | ✅       | ●                |
