# Данные для языка `xdq` от вендора Urssivar

**Спецификация:** [urssivar/script](https://github.com/urssivar/script) (v1.2, май 2026)

- `raw/xdq_mono_33k.txt` — Символьный монокорпус (пока слабый, требуется переработка)
- `frequencies/xdq_monocorpus_freq.csv` — частотности _символов_ (30) из монокорпуса; раскладка построена с опорой на них
- `stats/xdq_population.csv` — численность носителей
- `keyboard/xdq_key_default.json` — базовая 3-рядная раскладка
- `keyboard/xdq_key_4row.json` — 4-рядная раскладка с сохранением ЙЦУКЕН и расширенными буквами в верхнем ряду
- `mapping/xdq_key_mapping.json` — маппинг расширенных букв на русские клавиши. `Ә` отнесена к `Э`, как во всех языках РФ в этом проекте (`abk`, `kaz`, `sty`, `tat`, `xal`; `Ӭ` у `yrk` тоже на `Э`): так разгружается `А`. Это общая сводная схема для статистики; раскладка конкретной клавиатуры может отличаться, её стоит уточнять в проекте [ios-system-keyboard](https://github.com/Agisight/ios-system-keyboard)
- `metadata.json` — дополнительная информация
