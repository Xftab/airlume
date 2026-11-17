# Interface research and redesign, 17 November 2026

**Why.** Aftab did not like the 10 Nov neumorphic cream and burnt-orange look, and the answer text looked "weird": one long paragraph in a plain box. This memo records what the comparison sites do, what we took from them, and the decisions. It replaces the 10 Nov "Interface design" decision in the plan.

## What real air-quality sites do (observed)

| Site | What it does well | What we took | What we did not take |
|:--|:--|:--|:--|
| AirNow (US EPA) | One number, one named band, plain-language health message together | Band name always written as text beside the colour | Its US colour scheme: Pakistan uses the Punjab EPA bands |
| IQAir | Large index at top, health advice directly under it, map as the second step | Answer first, advice in its own box under it | Pollutant tiles and ads |
| WAQI / aqicn | Map-first, dense station markers | Map stays large and central | Dense legends, which are hard to read on a phone |
| PurpleAir | Map with a clear selected-station detail panel | Ranked chart beside the map | Raw sensor feeds |
| Google and Apple weather style cards | Few elements, big numbers, rounded white cards on a cool ground | Stat tiles, white cards on a pale cool ground | Gauges and dials, which waste space |

Guidance from colour and design literature that decided details: order AQI colours by lightness so they survive grayscale and colour-blindness; do not fill large backgrounds with AQI colours (they stop meaning "this value" and vanish for some users); never write text in a band colour (several fail 3:1 on white); show the band name as text.

## Audit of our own colours (measured)

The official Punjab EPA bands must not be recoloured. Their weak points are stated, not hidden: Moderate and "Unhealthy for sensitive groups" differ by a colour distance of only about 11.9 (CIEDE2000), and the lightness order is not monotonic. So the band is always named in text, and colour is a secondary cue.

## Decisions

1. **Light, cool theme.** Page `#F4F6FA`, cards white, ink `#0F1B2D`, soft text `#475467`, one blue accent `#2457C5` (deep `#1B3F94` for small text). Colour means either an AQI band or the blue accent, never both.
2. **Answer card.** The code-written sentence is split, words unchanged, into a headline (first sentence), detail, and a boxed "What to do near X" for advice. A band-coloured left edge carries the band; the band name is text.
3. **Layout.** Header, wide ask bar, four example chips, answer card, three stat tiles (worst, cleanest, reporting), map and ranked chart, then the analysis tabs. Settings and status are in a collapsed sidebar. Earlier questions sit in an expander.
4. **Security unchanged.** One static stylesheet through `st.html(Path)`; one `unsafe_allow_html` (the header, no user text); answer text and clarify text still pass through `md_escape`. Band slugs come from a fixed list, never from text.
5. **Defect found and fixed.** `st.html` silently drops a whole stylesheet if the sanitiser sees tag-like text. A comment containing `<slug>` did that. `tests/test_ui.py` now fails if the stylesheet contains an angle bracket.

## Limits

- Not user-tested. Judged against the sites above and our own checks, not against a group of users. [To do: show 3 classmates and record their reactions.]
- Screens were checked on demo data in a headless browser at 1440 px and 390 px wide. The CARTO basemap was not reachable there, so the map ground shown is the fallback gradient.
- Colour-blind simulation was reasoned from lightness and distance values, not run on screenshots.
