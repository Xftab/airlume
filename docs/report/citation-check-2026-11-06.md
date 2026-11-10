# Citation check, report Chapter 2 and the proposal's references

**Date:** 6 November 2026. **Method:** each reference was looked up by web search and, where the page could be read, on a primary record: arXiv abstract page, ACL Anthology, MDPI, ISPRS archives, publisher or repository page. Nothing was confirmed from memory. "Verified" means existence, authors, year and venue match a primary or catalogue record. Where a detail could not be read (mostly IEEE page ranges, behind pages this session cannot open), it is marked **to confirm**, not assumed.

## Proposal references (26)

| # | Reference | Result | Correction or note |
|---|---|---|---|
| 1 | Patel et al. (2024), VayuBuddy, arXiv:2411.12760 | **Verified** | Authors in order: Zeel B Patel, Yash Bachwana, Nitish Sharma, Sarath Guttikunda, Nipun Batra. Submitted 16 Nov 2024 |
| 2 | Acharya et al. (2025), VayuChat, arXiv:2511.01046 | **Verified** | Vedant Acharya, Abhay Pisharodi, Rishabh Mondal, Mohammad Rafiuddin, Nipun Batra. Submitted 2 Nov 2025 |
| 3 | Narechania, Srinivasan & Stasko (2021), NL4DV, *IEEE TVCG* | **Verified**: authors, DOI 10.1109/TVCG.2020.3030378, IEEE VIS 2020 | Volume 27(2), pages 369–379: **to confirm** on IEEE Xplore |
| 4 | Shen et al. (2023), NLI for data visualization survey, *IEEE TVCG* | **Verified**: title and all 8 authors in order (arXiv 2109.03506) | Volume 29(6), pages 3121–3144 and DOI: **to confirm** |
| 5 | Chen et al. (2025), VisEval, *IEEE TVCG* | **Verified**: Nan Chen, Yuge Zhang, Jiahang Xu, Kan Ren, Yuqing Yang; IEEE VIS 2024 paper (arXiv 2407.00981) | Volume 31(1), pages 1301–1311 and DOI: **to confirm** |
| 6 | TechJuice (2025), EcoBot | **Verified**: 10 Oct 2025 | Add author: Manik Aftab |
| 7 | EPA Punjab portal | Live site, our own data source | — |
| 8 | EPD daily AQI reports | Our own data source (backfill) | — |
| 9 | IQAir 2024 World Air Quality Report | **Verified via press**: Pakistan ranked 3rd most polluted in 2024 (Dawn, 11 Mar 2025) | Cite the report itself; the press report is a fallback |
| 10 | IQAir 2025 report, via Al Jazeera, 24 Mar 2026 | **Verified** | Figures in the article: Pakistan 2025 mean PM2.5 67.3 µg/m³ (73.7 in 2024), "up to 13 times" the WHO guideline |
| 11 | WHO (2021) global air quality guidelines | **Verified**: ISBN 9789240034228 | — |
| 12 | AQLI (2024) Pakistan fact sheet | **Verified** | Uses 2022 data. Pakistan: 3.3 years of life expectancy lost against the WHO guideline. Lahore: 5.3 years; 2022 mean PM2.5 59.5 µg/m³ |
| 13 | Dibia (2023), LIDA, ACL demos, 113–126 | **Verified exactly** | DOI 10.18653/v1/2023.acl-demo.11 |
| 14 | Maddigan & Susnjak (2023), Chat2VIS, *IEEE Access* 11, 45181–45193 | **Verified** (Massey repository) | The IEEE title spells it "Visualizations"; the arXiv title spells it "Visualisations". Cite the journal version with **DOI 10.1109/ACCESS.2023.3274199** instead of the arXiv link |
| 15 | Batty (2018), Digital twins, *EPB* 45(5), 817–820 | **Verified exactly** | DOI 10.1177/2399808318796416 |
| 16 | Shahat, Hyun & Yeom (2021), *Sustainability* 13(6), 3386 | **Verified exactly** | DOI 10.3390/su13063386 |
| 17 | Shabbir et al. (2025), *Environment International* 200, 109521 | **Verified** (DOAJ) | Authors: Muneeba Shabbir, Talha Saeed, Ahmad Saleem, Parkash Bhave, Mike Bergin, Muhammad Fahim Khokhar |
| 18 | Saeed et al. (2024), EGUsphere preprint | **Verified** | 12 authors. Received 25 Jun 2024, posted 30 Oct 2024. No journal version found; keep "preprint" |
| 19 | Chang et al. (2023), Dr.Spider, ICLR | **Verified**: ICLR 2023 poster, arXiv 2301.08881 | — |
| 20 | Chen et al. (2023), Program of Thoughts, TMLR | **Verified**: TMLR 2023, arXiv 2211.12588 | — |
| 21 | OpenAI (2024, Aug 6), Structured Outputs | **Verified** | — |
| 22 | Pydantic JSON Schema docs | Documentation; cite with access date | — |
| 23 | Raasveldt & Mühleisen (2019), DuckDB, SIGMOD | **Verified**: SIGMOD '19, Amsterdam, DOI 10.1145/3299869.3320212, 4 pages | Pages 1981–1984: consistent, **to confirm** |
| 24 | deck.gl / pydeck docs | Documentation; cite with access date | — |
| 25 | CAMS global forecasts, DOI 10.24381/04a0b097; Open-Meteo API | **Verified**: DOI on the ADS dataset page; 0.4° × 0.4° resolution, 5-day forecast | The report's "45 km cell" is about 44 km north–south and 38 km east–west at Lahore; write "about 40 km" |
| 26 | US EPA (2024, updated 2026), AQI technical assistance document | **Verified**: AirNow page, last updated May 2026 | Number EPA-454/B-24-002 not shown on the page; keep as given in `aqi.py` |

## Chapter 2 additions

| Reference | Result | Use |
|---|---|---|
| Shwartz-Ziv & Armon (2022), "Tabular data: Deep learning is not all you need", *Information Fusion* 81, 84–90 (arXiv 2106.03253) | **Exists**; volume and pages as commonly cited, **to confirm** | Discussion point 1 |
| Rahman, Usama, Tahir & Uppal (2022), "Data driven framework for analysis of air quality landscape for the city of Lahore", ISPRS Archives XLVIII-4/W5-2022, 167–173, DOI 10.5194/isprs-archives-XLVIII-4-W5-2022-167-2022 | **Verified** | Comparison point for C7. Uses 4 reference-grade stations and 9 low-cost sensors, and proposes station locations |
| "Gupta et al. (2022)", anti-smog guns | **Not found.** Dropped | Replaced by Patra, Sahbaz & Ganesan (CEEW, 18 Nov 2025), "Are anti-smog guns the right choice for reducing Delhi's dust during winters?". It finds limited evidence and about 2% road coverage. Background only |
| Wilson (1927), *JASA* 22(158), 209–212 | **Verified** | Score intervals |
| Newcombe (1998), *Statistics in Medicine* 17(8), 873–890 | **Verified** (DOI in the record) | Difference of proportions |
| Landis & Koch (1977), *Biometrics* 33(1), 159–174 | **Verified** (PubMed 843571) | Kappa bands |
| Brooke (1996), "SUS: a quick and dirty usability scale", in Jordan et al. (eds.), *Usability Evaluation in Industry*, 189–194 | **Verified** | SUS |
| Karp & Flatt (1990), "Measuring parallel processor performance", *CACM* 33(5), 539–543, DOI 10.1145/78607.78614 | **Verified** | Serial fraction |

## Claims in Chapter 2 that still need a source

- **"Commercial maps interpolate without disclosing distance-to-sensor."** No source was searched for, and none is cited. Either find documentation from a named provider, or present it as an observation with dated screenshots, labelled as such.

## Sources used for this check

- [arXiv: VayuBuddy](https://arxiv.org/abs/2411.12760)
- [arXiv: VayuChat](https://arxiv.org/abs/2511.01046v1)
- [arXiv: NL4DV](https://arxiv.org/abs/2008.10723)
- [ar5iv: NLI survey](https://ar5iv.arxiv.org/html/2109.03506)
- [arXiv: VisEval](https://arxiv.org/abs/2407.00981v2)
- [TechJuice: EcoBot](https://www.techjuice.pk/punjab-launches-pakistans-first-ai-ecobot-for-real-time-air-quality-monitoring/)
- [ACL Anthology: LIDA](https://aclanthology.org/2023.acl-demo.11)
- [Massey repository: Chat2VIS](https://mro.massey.ac.nz/items/8ed87e95-c02b-479b-854e-e137ea97e282)
- [RePEc: Batty](https://econpapers.repec.org/RePEc:sae:envirb:v:45:y:2018:i:5:p:817-820)
- [MDPI: Shahat et al.](https://www.mdpi.com/2071-1050/13/6/3386)
- [DOAJ: Shabbir et al.](https://doaj.org/article/fcb76f8a2ead424ea351f11036f9c61e)
- [EGUsphere: Saeed et al.](https://egusphere.copernicus.org/preprints/2024/egusphere-2024-1932/)
- [ICLR 2023: Dr.Spider](https://iclr.cc/virtual/2023/poster/11467)
- [ML Anthology: PoT](https://mlanthology.org/tmlr/2023/chen2023tmlr-program)
- [OpenAI: Structured Outputs](https://openai.com/index/introducing-structured-outputs-in-the-api/)
- [DuckDB paper](https://DuckDB.org/pdf/SIGMOD2019-demo-duckdb.pdf)
- [CAMS ADS dataset](https://ads.atmosphere.copernicus.eu/datasets/cams-global-atmospheric-composition-forecasts)
- [AirNow TAD](https://www.airnow.gov/publications/air-quality-index/technical-assistance-document-for-reporting-the-daily-aqi/)
- [Al Jazeera, 24 Mar 2026](https://www.aljazeera.com/news/2026/3/24/pakistan-worlds-most-polluted-country-in-2025-report)
- [Dawn, IQAir 2024](https://www.dawn.com/news/1897218)
- [AQLI Pakistan 2024](https://aqli.epic.uchicago.edu/wp-content/uploads/2024/08/Pakistan-FactSheet_2024.pdf)
- [WHO AQG 2021](https://who.int/publications/i/item/9789240034228)
- [ISPRS Lahore 2022](https://isprs-archives.copernicus.org/articles/XLVIII-4-W5-2022/167/2022/)
- [CEEW anti-smog guns](https://www.ceew.in/node/4774)
- [Wilson 1927 record](https://scilit.com/publications/51ab62bc5a19b66438acfe9c66479b31)
- [Landis & Koch, PubMed](https://pubmed.ncbi.nlm.nih.gov/843571/)
- [Karp–Flatt](https://en.wikipedia.org/wiki/Karp%E2%80%93Flatt_metric)
- [Brooke 1996 record](https://verdi.cs.ucl.ac.uk/constructDB/publications/brooke-susa-1996.html)
- [Tabular data (arXiv 2106.03253)](https://arxiv.org/abs/2106.03253v2)
