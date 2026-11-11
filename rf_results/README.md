# rf_results — снимок для Apple

**Состояние, переданное в Apple: сентябрь 2026.** Эти файлы не обновляются.

Данные в папке посчитаны 2025-12-21 (коммит `e9e7be8`) и до сентября 2026 года не менялись. По ним Apple сделала долгое нажатие для языков РФ в системной русской клавиатуре.

- **iOS 27** (сентябрь 2026): первая версия — вошли не все буквы, порядок на долгом нажатии был неправильным.
- **iOS 27.2** (26 октября 2026): исправлено по договорённости с разработчиком Apple — все буквы и порядок по этому снимку.

Финальное состояние отмечено тегом `apple-ios-27.2`.

| Файл | Что внутри | Копия чего |
|---|---|---|
| `rf_priorities_apple.csv` | порядок дополнительных букв на долгом нажатии | `rf_summaries/variant_mapping_priorities_apple.csv` |
| `rf_priorities_unicode.csv` | то же по Unicode | `rf_summaries/variant_mapping_priorities_unicode.csv` |
| `rf_stats.csv` | статистика по буквам, языкам и носителям | `rf_summaries/variant_mapping_stats.csv` |

**Актуальные сводки — в `rf_summaries/`.** После снимка там исправлены данные лакского, тиндинского, кабардинского, чеченского и кайтагского (2026-10-23). Порядок букв от этого не изменился, сдвинулись только проценты в строках `И`, `Н`, `Х`.

Палочка `Ӏ` в снимке стоит на долгом нажатии `Ь` (>99% в группе, 17 языков).

---

# rf_results — snapshot for Apple

**State handed to Apple: September 2026.** These files are not updated.

The data here was computed on 2025-12-21 (commit `e9e7be8`) and did not change until September 2026. Apple used it for the long-press letters for languages of Russia on the system Russian keyboard.

- **iOS 27** (September 2026): first version — not all letters were included and the long-press order was wrong.
- **iOS 27.2** (October 26, 2026): fixed as agreed with an Apple engineer — all letters, in the order from this snapshot.

The final state is marked with the tag `apple-ios-27.2`.

Current summaries live in `rf_summaries/`. Data fixes made after the snapshot (2026-10-23: Lak, Tindi, Kabardian, Chechen, Kaitag) did not change the letter order; only percentages in the `И`, `Н`, `Х` rows moved.

The palochka `Ӏ` is a long-press on `Ь` in this snapshot (>99% within the group, 17 languages).
