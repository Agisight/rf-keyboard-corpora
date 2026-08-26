# rf-keyboard-corpora

> **Languages:** **English** · [Русский](README.ru.md) · [Тыва дыл](README.tyv.md)

**Corpus base for the “RF Keyboard” project — system keyboard layouts for every Cyrillic language.**

> **Project goals**
>
> 1. Extend the **Russian system layout** so that long-press covers every Cyrillic language of the Russian Federation.
> 2. Prepare **individual system keyboards** for each language of the RF.
> 3. Serve academic use, for any researcher.
> 4. Prepare the project to support every Cyrillic language in the world.

---

## 1. What data we collect and why

| Component | File / folder | Purpose |
| --- | --- | --- |
| **Monocorpus** | `raw/lang_mono_<N>.txt` | Continuous text in the target language; `N` = number of characters. Primary source of **per-character** statistics (one token = one Unicode character). |
| **Frequencies** | `frequencies/lang_monocorpus_freq.csv` | A “character → occurrences” table — drives the sort order of long-press variants. |
| **Layouts** | `keyboard/lang_key_*.json` | Base, 4-row, complex, etc. — ready-to-use iOS files. |
| **Long-press mapping** | `mapping/lang_key_mapping.json` | Specifies which **base** Russian letter reveals each additional letter/symbol of the language. |
| **Speaker statistics** | `stats/lang_population.csv` | Weights “frequency × reach” and justifies priorities to Apple. Reach = number of speakers. |
| **Manifest** | `metadata.json` | Machine-readable metadata (version, license, contacts). |
| **README** | `README.md` | Human-readable description: corpus sources, cleaning, specifics. |

> `lang` — ISO 639-3 code (e.g. `tyv`, `kbd`).

---

## 2. Mapping your letters onto Russian letters

When a letter on the standard Russian keyboard is long-pressed (as Е → [Ё] works today), your letters should sit under the nearest similar letter, through which they will appear once the extended RF Keyboard is built.

Map your letters to Russian keys in **lang_key_mapping.json**:

```json
{
  "О": ["Ӧ", "Ө", "О̄"],
  "У": ["Ӱ", "Ү"],
  "Н": ["Ң"],
  "Е": ["Ё"]
}
```

or use a simpler text form in **lang_key_mapping.txt**:

```
О | Ӧ, Ө, О̄
У | Ӱ, Ү
Н | Ң
Е | Ё
```

*Key = base Russian key; values = variants in descending frequency order (not critical yet).*

---

## 3. Vendor mini-pipeline (not working yet)

1. **Collect the corpus** → `raw/`, one character = one token.
2. **Compute frequencies** — upload the corpus to Hugging Face and follow the instructions on [this page](https://github.com/Agisight/rf-keyboard-corpora/blob/rf/hf_freq_analyze.md); there is a built-in mechanism that counts the statistics of your monocorpus.
3. **Create `lang_key_mapping.txt` or `lang_key_mapping.json`** by hand, in any editor you like.
4. **Prepare the layouts** (`keyboard/lang_key_default.json` and additional ones if needed).
5. **Add speaker statistics**, fill in `metadata.json` and `README.md`.
6. **Open a pull request.**

---

## 4. FAQ

| Question | Answer |
| --- | --- |
| **Can there be several vendors for one language?** | Yes. Use separate `<vendor>` folders; the scripts merge the frequencies automatically. |
| **How are emoji, Latin script and other foreign characters handled?** | When computing frequencies, the script ignores everything outside the Cyrillic Unicode block by default. The target language’s letters are kept, the noise is discarded. |
| **Should spaces and punctuation be included in `lang_monocorpus_freq.csv`?** | No. Keep only letter characters and the language-specific signs; omit spaces and punctuation. |
| **How should files be named when the corpus is updated?** | Add a version suffix (`_v2`, a date) and update the `version` field in `metadata.json`. |
| **Is a 4-row layout required?** | No. Add it if it’s useful; the base portrait layout (3 rows of characters) is required. |
| **Which license to choose for the corpus?** | We recommend MIT or a compatible open license, so Apple can use the data freely. |

---

**Corpus → Frequencies → Ergonomics** — accurate data gives an objective basis for letter placement. The more precise the corpora and statistics, the stronger the argument for Apple to build full support for every Cyrillic language of the Russian Federation.

## 5. Language readiness

| Language | Frequencies | Mapping | Speakers | by Ali Kuzhuget |
| --- | --- | --- | --- | --- |
| Abaza | ✅ | ✅ | ✅ | ○ |
| Abkhaz | ✅ | ✅ | ✅ | ○ |
| Avar | ✅ | ✅ | ✅ | ○ |
| Agul | ✅ | ✅ | ✅ | ● |
| Adyghe | ✅ | ✅ | ✅ | ○ |
| Altai | ✅ | ✅ | ✅ | ● |
| Andi | ✅ | ✅ | ✅ | ● |
| Akhvakh | ❌ | ✅ | ✅ | ○ |
| Bashkir | ✅ | ✅ | ✅ | ○ |
| Belarusian | ✅ | ✅ | ✅ | ● |
| Buryat | ✅ | ✅ | ✅ | ○ |
| Dargwa | ✅ | ✅ | ✅ | ○ |
| Dolgan | ✅ | ✅ | ✅ | ○ |
| Church Slavonic | ✅ | ✅ | ✅ | ● |
| Ingush | ✅ | ✅ | ✅ | ● |
| Kabardian (Kabardino-Cherkess) | ✅ | ✅ | ✅ | ○ |
| Kazakh | ✅ | ✅ | ✅ | ● |
| Kaitag | ✅ | ✅ | ✅ | ○ |
| Kalmyk | ✅ | ✅ | ✅ | ● |
| Karata | ✅ | ✅ | ✅ | ○ |
| Karachay-Balkar | ✅ | ✅ | ✅ | ○ |
| Komi | ✅ | ✅ | ✅ | ○ |
| Crimean Tatar | ✅ | ✅ | ✅ | ● |
| Kumyk | ✅ | ✅ | ✅ | ● |
| Kyrgyz | ✅ | ✅ | ✅ | ● |
| Lak | ✅ | ✅ | ✅ | ● |
| Lezgian | ✅ | ✅ | ✅ | ○ |
| Mari | ✅ | ✅ | ✅ | ● |
| Moksha | ✅ | ✅ | ✅ | ● |
| Moldovan | ✅ | ✅ | ✅ | ● |
| Nenets | ✅ | ✅ | ✅ | ● |
| Nogai | ✅ | ✅ | ✅ | ○ |
| Ossetian | ✅ | ✅ | ✅ | ○ |
| Rutul | ✅ | ✅ | ✅ | ● |
| Sakha (Yakut) | ✅ | ✅ | ✅ | ○ |
| Siberian Tatar | ✅ | ✅ | ✅ | ○ |
| Tabasaran | ✅ | ✅ | ✅ | ● |
| Tajik | ✅ | ✅ | ✅ | ○ |
| Tatar | ✅ | ✅ | ✅ | ○ |
| Tindi | ✅ | ✅ | ✅ | ● |
| Tuvan | ✅ | ✅ | ✅ | ● |
| Udmurt | ✅ | ✅ | ✅ | ○ |
| Uzbek | ✅ | ✅ | ✅ | ● |
| Ukrainian | ✅ | ✅ | ✅ | ● |
| Khakas | ✅ | ✅ | ✅ | ● |
| Tsudakhar | ✅ | ✅ | ✅ | ● |
| Romani | ✅ | ✅ | ✅ | ● |
| Chechen | ✅ | ✅ | ✅ | ● |
| Chuvash | ✅ | ✅ | ✅ | ○ |
| Erzya | ✅ | ✅ | ✅ | ● |
