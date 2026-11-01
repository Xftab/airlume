# Second-annotator selection, 1 November 2026

**Keep this file away from the second annotator.** It names each question's category, which would leak the first annotator's reading.

Method: stratified random sample of 20 of the 62 classmate questions, seed 1101, quotas by category taken from the draft pre-annotation (7 out of scope, 3 forecast, 3 guidance, 1 clarify, 2 timeline pattern, 2 named area, 2 plain current reading), re-drawn from seed 1101 upward until at least 10 and at most 13 are Roman Urdu and each contributor (A, B, C) has at least 4. Order shuffled with the same seed. Not chosen for difficulty: the eight REVIEW rows were allowed to fall where the draw put them, so that kappa is not pushed down by selection.

Language: 11 ur-Latn, 9 en. Contributors: A 5, B 8, C 7.

| Row | id | contributor | language | category | question |
|---:|---|---|---|---|---|
| 1 | c038 | B | en | plain_current | Should the weather has smog |
| 2 | c060 | C | ur-Latn | out_of_scope | Zyada smog me rain k kitny chance hoty hain? |
| 3 | c043 | C | en | forecast | What will AQI get better? |
| 4 | c041 | C | en | clarify | What is air quality index of my village? |
| 5 | c051 | C | ur-Latn | out_of_scope | Smog ki wajah sy kiya flu ho skta? |
| 6 | c032 | B | en | out_of_scope | When did the rain in lahore |
| 7 | c035 | B | ur-Latn | guidance | Kiya mujhe walk pr jana chahiye aj |
| 8 | c026 | B | en | guidance | Tell me is going outside is safe |
| 9 | c056 | C | ur-Latn | out_of_scope | Human environment me asa kiya hai jis ki wajah say smog zyada ho jati hai? |
| 10 | c054 | C | ur-Latn | guidance | Smog say bachny k leay kia precautions hain? |
| 11 | c014 | A | ur-Latn | timeline_pattern | kiya rat ko smok kam hojati? |
| 12 | c034 | B | en | forecast | When the air quality get clean today |
| 13 | c007 | A | ur-Latn | timeline_pattern | mujhe 1 week ka smog analysis batao . |
| 14 | c030 | B | ur-Latn | out_of_scope | Kiya barish honi han |
| 15 | c048 | C | en | out_of_scope | How smog is created? |
| 16 | c017 | A | ur-Latn | forecast | kiya kal hawa saf hogi |
| 17 | c039 | B | en | named_area | What is today AQI in bahria |
| 18 | c019 | A | ur-Latn | out_of_scope | suraj kab nikly ga |
| 19 | c011 | A | ur-Latn | named_area | kiya mujhe johar town jana chahiye bcz yaha smog zayada han |
| 20 | c023 | B | en | plain_current | Is air clean in lahore |

Hand over: `airlume/eval/benchmark/second-annotator-sheet-2026-11-01.csv` and `docs/benchmark/annotator-guide.md` (version 2) only. Then `scripts\check_annotation.py` on the returned sheet, and `scripts\annotator_agreement.py` against the first annotator's sheet.
